#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator de Tabelas de PDF com Carregamento Progressivo
Versão otimizada com carregamento por lotes para manter qualidade
"""

import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QPushButton, 
    QScrollArea, QFrame, QMessageBox, QProgressBar, QTabWidget, QSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QTextEdit, QCheckBox, QComboBox, QListWidget, QListWidgetItem,
    QSplitter
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor, QPolygon, QFont
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QThread
import os
from dotenv import load_dotenv
import json
import datetime
import platform
import subprocess
import base64
import camelot
import pandas as pd
from opencv_table_detector import OpenCVTableDetector, TesseractTableDetector
from multi_pass_detector import MultiPassTableDetector

# Import condicional do OpenAI (opcional)
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI não instalado - funcionalidade de IA limitada")


class PDFLoaderThread(QThread):
    """Thread para carregamento progressivo de PDF por lotes"""
    progress_updated = pyqtSignal(int, str)  # progresso, mensagem
    batch_loaded = pyqtSignal(int, list)     # batch_number, list of (page_idx, QImage)
    loading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path, batch_size=50, dpi=150):
        super().__init__()
        self.pdf_path = pdf_path
        self.batch_size = batch_size
        self.dpi = dpi
        self.doc = None
        self.total_pages = 0
        self.should_stop = False
        
    def run(self):
        """Executa o carregamento progressivo"""
        try:
            # Abrir PDF
            self.progress_updated.emit(0, "Abrindo PDF...")
            self.doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.doc)
            
            if self.total_pages == 0:
                self.error_occurred.emit("PDF não possui páginas")
                return
            
            # Calcular número de lotes
            num_batches = (self.total_pages + self.batch_size - 1) // self.batch_size
            
            # Processar por lotes
            for batch_num in range(num_batches):
                if self.should_stop:
                    break
                    
                start_page = batch_num * self.batch_size
                end_page = min((batch_num + 1) * self.batch_size, self.total_pages)
                
                self.progress_updated.emit(
                    int((batch_num / num_batches) * 100),
                    f"Carregando lote {batch_num + 1}/{num_batches} - Páginas {start_page + 1} a {end_page}"
                )
                
                # Carregar páginas do lote atual
                batch_pages = []
                for page_idx in range(start_page, end_page):
                    if self.should_stop:
                        break
                        
                    try:
                        page = self.doc.load_page(page_idx)
                        pix = page.get_pixmap(dpi=self.dpi)
                        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                        batch_pages.append((page_idx, img.copy()))
                        
                        # Mini-update dentro do lote
                        pages_in_batch = end_page - start_page
                        current_in_batch = page_idx - start_page + 1
                        
                        if current_in_batch % 10 == 0:  # Atualiza a cada 10 páginas
                            self.progress_updated.emit(
                                int(((batch_num + current_in_batch/pages_in_batch) / num_batches) * 100),
                                f"Lote {batch_num + 1}/{num_batches} - Página {page_idx + 1}/{self.total_pages}"
                            )
                    
                    except Exception as e:
                        print(f"Erro ao carregar página {page_idx}: {e}")
                        continue
                
                # Emitir lote carregado
                if batch_pages and not self.should_stop:
                    self.batch_loaded.emit(batch_num, batch_pages)
            
            if not self.should_stop:
                self.progress_updated.emit(100, f"Carregamento concluído! {self.total_pages} páginas carregadas")
                self.loading_finished.emit()
                
        except Exception as e:
            self.error_occurred.emit(f"Erro ao carregar PDF: {str(e)}")
        
        finally:
            if self.doc:
                self.doc.close()
    
    def stop(self):
        """Para o carregamento"""
        self.should_stop = True


class CamelotTableDetector(QThread):
    """Thread para detecção automática de tabelas usando Camelot"""
    progress_updated = pyqtSignal(int, str)  # progresso, mensagem
    tables_detected = pyqtSignal(list)       # lista de tabelas detectadas
    error_occurred = pyqtSignal(str)         # erro
    pdf_type_detected = pyqtSignal(str, bool)  # tipo_pdf, tem_texto
    
    def __init__(self, pdf_path, pages="all", method="stream"):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.method = method  # "stream" ou "lattice"
        self.should_stop = False
    
    def check_pdf_type(self):
        """Verifica se o PDF é baseado em texto ou imagens"""
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            # Verificar as primeiras 5 páginas para determinar o tipo
            text_pages = 0
            pages_to_check = min(5, total_pages)
            
            for i in range(pages_to_check):
                page = doc[i]
                text = page.get_text().strip()
                if len(text) > 50:  # Considerar página com texto se tiver mais de 50 caracteres
                    text_pages += 1
            
            doc.close()
            
            # Se pelo menos 40% das páginas verificadas têm texto, considerar como PDF com texto
            has_text = (text_pages / pages_to_check) >= 0.4
            
            if has_text:
                pdf_type = "text-based"
            else:
                pdf_type = "image-based"
                
            return pdf_type, has_text, total_pages
            
        except Exception as e:
            return "unknown", False, 0
    
    def run(self):
        """Executa a detecção de tabelas"""
        try:
            self.progress_updated.emit(5, "Analisando tipo de PDF...")
            
            # Verificar tipo do PDF primeiro
            pdf_type, has_text, total_pages = self.check_pdf_type()
            self.pdf_type_detected.emit(pdf_type, has_text)
            
            if not has_text:
                self.error_occurred.emit(
                    f"⚠️ PDF Baseado em Imagens Detectado\n\n"
                    f"O arquivo '{os.path.basename(self.pdf_path)}' é um PDF escaneado (baseado em imagens) "
                    f"com {total_pages} páginas.\n\n"
                    f"🔍 O Camelot só funciona com PDFs que contêm texto selecionável.\n\n"
                    f"💡 Soluções alternativas:\n"
                    f"• Use a aba '📄 Seleção Manual' para recortar tabelas visualmente\n"
                    f"• Use a aba '🤖 IA - Extração Automática' para extrair tabelas com GPT-4 Vision\n"
                    f"• Converta o PDF para texto usando OCR antes de usar o Camelot\n\n"
                    f"📋 Páginas verificadas: {min(5, total_pages)} de {total_pages}"
                )
                return
            
            # Definir mensagem baseada no método
            if self.method == "hybrid":
                method_msg = "Sistema Híbrido Camelot v3.0"
            else:
                method_msg = f"método {self.method}"
            
            self.progress_updated.emit(15, f"PDF com texto detectado ({total_pages} páginas). Iniciando {method_msg}...")
            
            # Detectar tabelas com sistema apropriado
            if self.pages == "all":
                detected_tables = self.process_all_pages_in_batches(total_pages)
            else:
                detected_tables = self.process_specific_pages(self.pages)
            
            if self.should_stop:
                return
            
            self.progress_updated.emit(100, f"Detecção concluída! {len(detected_tables)} tabelas encontradas")
            self.tables_detected.emit(detected_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na detecção: {str(e)}")
    
    def process_specific_pages(self, pages):
        """Processa páginas específicas com sistema híbrido multi-configuração"""
        self.progress_updated.emit(20, f"Iniciando detecção para páginas: {pages}")
        
        # Verificar se é sistema híbrido ou método tradicional
        if self.method == "hybrid":
            return self.hybrid_detection_system(str(pages), 20, 80)
        else:
            # Método tradicional (stream ou lattice)
            self.progress_updated.emit(30, f"Método tradicional: {self.method}")
            
            if self.method == "lattice":
                tables = camelot.read_pdf(
                    self.pdf_path, 
                    pages=str(pages), 
                    flavor=self.method,
                    process_background=True,
                    line_scale=40
                )
            else:
                tables = camelot.read_pdf(self.pdf_path, pages=str(pages), flavor=self.method)
            
            if self.should_stop:
                return []
            
            return self.convert_tables_to_dict(tables, 40, 80)
    
    def process_all_pages_in_batches(self, total_pages):
        """Processa todas as páginas em lotes com sistema híbrido ou tradicional"""
        batch_size = 50  # Processar 50 páginas por vez
        all_detected_tables = []
        
        # Calcular número de lotes
        num_batches = (total_pages + batch_size - 1) // batch_size
        
        # Definir mensagem baseada no método
        method_name = "Sistema híbrido" if self.method == "hybrid" else f"método {self.method}"
        self.progress_updated.emit(20, f"{method_name}: processando {total_pages} páginas em {num_batches} lotes...")
        
        for batch_num in range(num_batches):
            if self.should_stop:
                break
            
            # Calcular intervalo do lote
            start_page = batch_num * batch_size + 1
            end_page = min((batch_num + 1) * batch_size, total_pages)
            
            # Progresso do lote
            batch_progress = 20 + int((batch_num / num_batches) * 60)
            self.progress_updated.emit(
                batch_progress, 
                f"Lote {batch_num + 1}/{num_batches}: {method_name} páginas {start_page}-{end_page}..."
            )
            
            try:
                # Processar lote com sistema apropriado
                page_range = f"{start_page}-{end_page}"
                
                if self.method == "hybrid":
                    # Usar sistema híbrido
                    batch_detected = self.hybrid_detection_system(page_range, 0, 0)
                else:
                    # Usar método tradicional
                    if self.method == "lattice":
                        batch_tables = camelot.read_pdf(
                            self.pdf_path, 
                            pages=page_range, 
                            flavor=self.method,
                            process_background=True,
                            line_scale=40
                        )
                    else:
                        batch_tables = camelot.read_pdf(self.pdf_path, pages=page_range, flavor=self.method)
                    
                    batch_detected = self.convert_tables_to_dict(batch_tables, 0, 0)
                
                if batch_detected:
                    all_detected_tables.extend(batch_detected)
                    
                    self.progress_updated.emit(
                        batch_progress + 2,
                        f"Lote {batch_num + 1}: {len(batch_detected)} tabelas encontradas (Total: {len(all_detected_tables)})"
                    )
                else:
                    self.progress_updated.emit(
                        batch_progress + 2,
                        f"Lote {batch_num + 1}: nenhuma tabela encontrada"
                    )
                
            except Exception as e:
                # Se um lote falhar, continua com o próximo
                self.progress_updated.emit(
                    batch_progress + 2,
                    f"Lote {batch_num + 1}: erro ignorado - {str(e)[:50]}..."
                )
                continue
        
        return all_detected_tables
    
    def convert_tables_to_dict(self, tables, start_progress, end_progress):
        """Converte tabelas do Camelot para formato dict (apenas tabelas válidas)"""
        detected_tables = []
        
        for i, table in enumerate(tables):
            if self.should_stop:
                break
            
            # Filtrar apenas tabelas com accuracy > 50% (válidas)
            if not hasattr(table, 'accuracy') or table.accuracy <= 50:
                continue
            
            # Informações da tabela
            table_info = {
                "index": len(detected_tables),  # Índice global
                "page": int(table.page),
                "bbox": table._bbox,  # (x1, y1, x2, y2)
                "accuracy": table.accuracy if hasattr(table, 'accuracy') else 0.0,
                "shape": table.shape,
                "data": table.df.to_dict('records') if len(table.df) > 0 else [],
                "preview": table.df.head(3).to_string() if len(table.df) > 0 else "Tabela vazia",
                "detection_method": f"camelot_{self.method}",
                "confidence": table.accuracy / 100.0 if hasattr(table, 'accuracy') else 0.0,
                "estimated_rows": table.shape[0],
                "estimated_cols": table.shape[1],
                "validation_passed": True,  # Camelot já fez validação básica
                "structure_score": 0.8,  # Score padrão
                "content_score": 0.7,   # Score padrão
                "column_consistency": 0.9,  # Score padrão
                "word_count": sum(len(str(cell).split()) for row in table.df.values for cell in row if pd.notna(cell))
            }
            detected_tables.append(table_info)
            
            # Atualizar progresso se especificado
            if end_progress > start_progress:
                progress = start_progress + int((i / len(tables)) * (end_progress - start_progress))
                self.progress_updated.emit(progress, f"Processando tabela {i+1}/{len(tables)}")
        
        return detected_tables
    
    def stop(self):
        """Para a detecção"""
        self.should_stop = True
    
    def hybrid_detection_system(self, page_range, start_progress, end_progress):
        """Sistema híbrido avançado com múltiplas configurações Camelot"""
        
        # Configurações múltiplas para cobertura total
        configurations = {
            'padrão': {
                'flavor': 'lattice',
                'line_scale': 40,
                'description': 'Detecção padrão para tabelas bem definidas'
            },
            'sensível': {
                'flavor': 'lattice', 
                'line_scale': 60,
                'description': 'Captura tabelas com bordas sutis'
            },
            'complementar': {
                'flavor': 'stream',
                'description': 'Método alternativo para casos especiais'
            }
        }
        
        all_tables = []
        config_count = len(configurations)
        
        for i, (config_name, params) in enumerate(configurations.items()):
            if self.should_stop:
                break
            
            # Progresso da configuração
            config_progress = start_progress + int((i / config_count) * (end_progress - start_progress) * 0.8)
            self.progress_updated.emit(
                config_progress, 
                f"Configuração '{config_name}': {params['description']}"
            )
            
            try:
                # Executar detecção com configuração específica
                if params['flavor'] == 'lattice':
                    tables = camelot.read_pdf(
                        self.pdf_path,
                        pages=page_range,
                        flavor=params['flavor'],
                        line_scale=params['line_scale'],
                        process_background=True
                    )
                else:
                    tables = camelot.read_pdf(
                        self.pdf_path,
                        pages=page_range,
                        flavor=params['flavor']
                    )
                
                # Converter e validar tabelas desta configuração
                for table in tables:
                    if self.validate_table_quality(table):
                        table_data = self.create_table_data(table, config_name)
                        all_tables.append(table_data)
                
                self.progress_updated.emit(
                    config_progress + 5,
                    f"'{config_name}': {len([t for t in tables if self.validate_table_quality(t)])} tabelas válidas"
                )
                
            except Exception as e:
                self.progress_updated.emit(
                    config_progress + 5,
                    f"'{config_name}': erro ignorado - {str(e)[:30]}..."
                )
                continue
        
        # Eliminação de duplicatas com algoritmo avançado
        elimination_progress = start_progress + int((end_progress - start_progress) * 0.8)
        self.progress_updated.emit(elimination_progress, "Eliminando duplicatas...")
        
        unique_tables = self.eliminate_overlapping_duplicates(all_tables, threshold=0.4)
        
        final_progress = start_progress + int((end_progress - start_progress) * 0.9)
        self.progress_updated.emit(
            final_progress, 
            f"Sistema híbrido: {len(unique_tables)} tabelas únicas de {len(all_tables)} detecções"
        )
        
        return unique_tables
    
    def validate_table_quality(self, table):
        """Valida a qualidade da tabela detectada"""
        try:
            # Verificar accuracy mínimo
            if not hasattr(table, 'accuracy') or table.accuracy <= 50:
                return False
            
            # Verificar tamanho mínimo
            if table.shape[0] < 2 or table.shape[1] < 2:
                return False
            
            # Verificar se tem dados válidos
            if len(table.df) == 0:
                return False
            
            # Verificar densidade de texto (evitar células isoladas)
            non_empty_cells = 0
            total_cells = table.shape[0] * table.shape[1]
            
            for row in table.df.values:
                for cell in row:
                    if pd.notna(cell) and str(cell).strip():
                        non_empty_cells += 1
            
            density = non_empty_cells / total_cells if total_cells > 0 else 0
            
            # Filtrar células muito esparsas (falsos positivos)
            if density < 0.1:  # Menos de 10% de densidade
                return False
            
            return True
            
        except Exception:
            return False
    
    def create_table_data(self, table, config_name):
        """Cria estrutura de dados para tabela detectada"""
        return {
            "page": int(table.page),
            "bbox": table._bbox,  # (x1, y1, x2, y2) - será convertido com Y-invertida na extração
            "accuracy": table.accuracy if hasattr(table, 'accuracy') else 0.0,
            "shape": table.shape,
            "data": table.df.to_dict('records') if len(table.df) > 0 else [],
            "preview": table.df.head(3).to_string() if len(table.df) > 0 else "Tabela vazia",
            "detection_method": f"camelot_hybrid_{config_name}",
            "config": config_name,
            "confidence": table.accuracy / 100.0 if hasattr(table, 'accuracy') else 0.0,
            "estimated_rows": table.shape[0],
            "estimated_cols": table.shape[1],
            "validation_passed": True,
            "word_count": sum(len(str(cell).split()) for row in table.df.values for cell in row if pd.notna(cell))
        }
    
    def eliminate_overlapping_duplicates(self, tables, threshold=0.4):
        """Elimina tabelas duplicadas usando algoritmo bidireccional de sobreposição"""
        if not tables:
            return []
        
        unique_tables = []
        
        for table in tables:
            is_duplicate = False
            
            for existing in unique_tables:
                # Verificar se estão na mesma página
                if table['page'] != existing['page']:
                    continue
                
                # Calcular sobreposição bidireccional
                overlap_ratio = self.calculate_bidirectional_overlap(
                    table['bbox'], 
                    existing['bbox']
                )
                
                if overlap_ratio > threshold:
                    # É uma duplicata - manter a de maior qualidade
                    if table['accuracy'] > existing['accuracy']:
                        # Remover a existente e adicionar a nova
                        unique_tables.remove(existing)
                        unique_tables.append(table)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_tables.append(table)
        
        # Reindexar tabelas únicas
        for i, table in enumerate(unique_tables):
            table['index'] = i
        
        return unique_tables
    
    def calculate_bidirectional_overlap(self, bbox1, bbox2):
        """Calcula sobreposição bidireccional entre duas bounding boxes"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Área de interseção
        x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
        y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
        intersection_area = x_overlap * y_overlap
        
        # Áreas individuais
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        
        if area1 == 0 or area2 == 0:
            return 0
        
        # Sobreposição bidireccional (máximo das duas direções)
        overlap1 = intersection_area / area1  # % da bbox1 que sobrepõe bbox2
        overlap2 = intersection_area / area2  # % da bbox2 que sobrepõe bbox1
        
        return max(overlap1, overlap2)


class ImageToJsonlConverter(QThread):
    """Thread para conversão automática de imagens para JSONL"""
    progress_updated = pyqtSignal(int, str)  # progresso, mensagem
    conversion_finished = pyqtSignal(list)   # lista de arquivos criados
    
    def __init__(self, image_folder, output_folder):
        super().__init__()
        self.image_folder = image_folder
        self.output_folder = output_folder
        
    def run(self):
        """Executa a conversão automática"""
        created_files = []
        
        # Buscar todas as imagens PNG na pasta
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith('.png')]
        total_files = len(image_files)
        
        if total_files == 0:
            self.progress_updated.emit(100, "Nenhuma imagem encontrada para conversão")
            self.conversion_finished.emit([])
            return
        
        for i, image_file in enumerate(image_files):
            # Atualizar progresso
            progress = int((i / total_files) * 100)
            self.progress_updated.emit(progress, f"Convertendo {image_file}...")
            
            # Criar estrutura JSONL básica
            jsonl_data = self.create_jsonl_structure(image_file)
            
            # Salvar arquivo JSONL
            jsonl_filename = image_file.replace('.png', '.jsonl')
            jsonl_path = os.path.join(self.output_folder, jsonl_filename)
            
            try:
                with open(jsonl_path, 'w', encoding='utf-8') as f:
                    json.dump(jsonl_data, f, ensure_ascii=False, indent=2)
                created_files.append(jsonl_path)
            except Exception as e:
                self.progress_updated.emit(progress, f"Erro ao salvar {jsonl_filename}: {str(e)}")
        
        self.progress_updated.emit(100, f"Conversão concluída! {len(created_files)} arquivos criados")
        self.conversion_finished.emit(created_files)
    
    def create_jsonl_structure(self, image_filename):
        """Cria a estrutura JSONL para uma imagem"""
        # Extrair informações do nome do arquivo
        base_name = image_filename.replace('.png', '')
        parts = base_name.split('_')
        
        # Tentar identificar fonte e página
        source = "PDF"
        page_num = "1"
        table_num = "1"
        
        if len(parts) >= 3:
            # Formato esperado: livro_pagina_X_tabela_Y
            for i, part in enumerate(parts):
                if part == "pagina" and i + 1 < len(parts):
                    page_num = parts[i + 1]
                elif part == "tabela" and i + 1 < len(parts):
                    table_num = parts[i + 1]
                elif i == 0:
                    source = part.replace('-', ' ').title()
        
        # Estrutura JSONL padrão
        jsonl_structure = {
            "type": "table",
            "source": source,
            "page": int(page_num) if page_num.isdigit() else 1,
            "table_number": int(table_num) if table_num.isdigit() else 1,
            "title": f"Tabela extraída de {base_name}",
            "image_file": image_filename,
            "extraction_date": datetime.datetime.now().isoformat(),
            "text": [],
            "metadata": {
                "conversion_method": "automatic",
                "requires_manual_review": True,
                "confidence": "low"
            }
        }
        
        return jsonl_structure


class OpenAITableExtractor(QThread):
    """Thread para extração de tabela usando OpenAI GPT-4 Vision"""
    
    progress_updated = pyqtSignal(int, str)  # progresso, mensagem
    extraction_completed = pyqtSignal(dict)  # resultado da extração
    error_occurred = pyqtSignal(str)         # erro
    
    def __init__(self, image_path: str, api_key: str = None, custom_prompt: str = None):
        super().__init__()
        self.image_path = image_path
        # Carrega .env e pega a chave se não for passada
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.custom_prompt = custom_prompt
        self.should_stop = False
    
    def encode_image(self, image_path: str) -> str:
        """Codifica imagem em base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def create_extraction_prompt(self) -> str:
        """Cria o prompt para extração de tabela"""
        if self.custom_prompt:
            return self.custom_prompt
        
        return """
Analise esta imagem de tabela e extraia TODOS os dados em formato JSON estruturado.

FORMATO OBRIGATÓRIO:
{
  "type": "table",
  "source": "[nome/fonte da tabela]",
  "title": "[título completo da tabela]",
  "text": [
    {
      "subsection": "[nome da subseção se houver]",
      "headers": ["coluna1", "coluna2", "coluna3", ...],
      "rows": [
        ["valor1", "valor2", "valor3", ...],
        ["valor1", "valor2", "valor3", ...],
        ...
      ]
    }
  ]
}

INSTRUÇÕES ESPECÍFICAS:
1. Extraia TODOS os textos visíveis na tabela
2. Mantenha a estrutura original (colunas e linhas)
3. Se houver múltiplas seções, crie múltiplos objetos em "text"
4. Se não houver subseções, use um nome descritivo ou deixe vazio
5. Preserve números, símbolos e formatação especial
6. Se houver células mescladas, repita o valor nas células correspondentes
7. Para células vazias, use string vazia ""

EXEMPLO DE REFERÊNCIA (Escala de Glasgow):
{
  "type": "table",
  "source": "Escala de Coma de Glasgow",
  "title": "TABELA 1 – Escala de Coma de Glasgow",
  "text": [
    {
      "subsection": "Resposta ocular",
      "headers": ["Critério", "Classificação", "Pontos"],
      "rows": [
        ["Olhos abertos previamente à estimulação", "Espontânea", "4"],
        ["Abertura ocular após ordem em voz normal ou em voz alta", "Ao som", "3"]
      ]
    }
  ]
}

Analise a imagem e retorne APENAS o JSON estruturado, sem explicações adicionais.
"""
    
    def run(self):
        """Executa a extração usando o novo SDK openai e endpoint /responses"""
        try:
            if not HAS_OPENAI:
                self.error_occurred.emit("OpenAI não está instalado. Execute: pip install openai")
                return
                
            self.progress_updated.emit(10, "Preparando imagem...")
            base64_image = self.encode_image(self.image_path)
            self.progress_updated.emit(30, "Enviando para OpenAI...")
            # Configurar client
            client = openai.OpenAI(api_key=self.api_key)
            # Chamada usando a API oficial conforme documentação OpenAI
            response = client.responses.create(
                model="gpt-4o",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": self.create_extraction_prompt()},
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"},
                        ],
                    }
                ],
            )
            if self.should_stop:
                return
            self.progress_updated.emit(70, "Analisando resposta...")
            # A resposta vem no formato output_text
            content = response.output_text
            try:
                extracted_data = json.loads(content.strip())
            except Exception:
                # fallback: tentar extrair JSON de string
                if "```json" in content:
                    content = content.split("```json")[1].split("```", 1)[0]
                elif "```" in content:
                    content = content.split("```", 1)[1].split("```", 1)[0]
                extracted_data = json.loads(content.strip())
            # Adicionar metadados
            extracted_data["extraction_date"] = datetime.datetime.now().isoformat()
            extracted_data["image_file"] = os.path.basename(self.image_path)
            if "metadata" not in extracted_data:
                extracted_data["metadata"] = {}
            extracted_data["metadata"].update({
                "extraction_method": "openai_gpt4_vision",
                "model": "gpt-4o",
                "confidence": "high",
                "requires_manual_review": False
            })
            self.progress_updated.emit(100, "Extração concluída!")
            self.extraction_completed.emit(extracted_data)
        except Exception as e:
            self.error_occurred.emit(f"Erro durante extração: {str(e)}")
    
    def stop(self):
        """Para a extração"""
        self.should_stop = True


class AITableExtractorWidget(QWidget):
    """Widget para extração de tabelas usando IA"""
    
    def __init__(self):
        super().__init__()
        self.extractor_thread = None
        self.current_image_path = None
        self.extracted_data = None
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface"""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("🤖 Extração Automática de Tabelas com IA")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Configurações da API
        api_group = QGroupBox("Configurações da OpenAI")
        api_layout = QFormLayout(api_group)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        api_layout.addRow("API Key:", self.api_key_input)
        
        layout.addWidget(api_group)
        
        # Seleção de imagem
        image_group = QGroupBox("Selecionar Imagem da Tabela")
        image_layout = QVBoxLayout(image_group)
        
        # Botões de seleção
        image_buttons = QHBoxLayout()
        
        self.select_image_btn = QPushButton("📁 Selecionar Imagem")
        self.select_image_btn.clicked.connect(self.select_image)
        self.select_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.extract_btn = QPushButton("🚀 Extrair Tabela com IA")
        self.extract_btn.clicked.connect(self.start_extraction)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        image_buttons.addWidget(self.select_image_btn)
        image_buttons.addWidget(self.extract_btn)
        image_layout.addLayout(image_buttons)
        
        # Preview da imagem
        self.image_preview = QLabel("Nenhuma imagem selecionada")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                background-color: #ecf0f1;
                min-height: 200px;
                border-radius: 5px;
            }
        """)
        image_layout.addWidget(self.image_preview)
        
        # Info da imagem
        self.image_info = QLabel("")
        self.image_info.setStyleSheet("color: #7f8c8d; font-style: italic;")
        image_layout.addWidget(self.image_info)
        
        layout.addWidget(image_group)
        
        # Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Resultado
        result_group = QGroupBox("Resultado da Extração")
        result_layout = QVBoxLayout(result_group)
        
        # Botões de ação no resultado
        result_buttons = QHBoxLayout()
        
        self.save_json_btn = QPushButton("💾 Salvar JSONL")
        self.save_json_btn.clicked.connect(self.save_jsonl)
        self.save_json_btn.setEnabled(False)
        
        self.copy_json_btn = QPushButton("📋 Copiar JSON")
        self.copy_json_btn.clicked.connect(self.copy_json)
        self.copy_json_btn.setEnabled(False)
        
        self.edit_json_btn = QPushButton("✏️ Editar")
        self.edit_json_btn.clicked.connect(self.toggle_edit_mode)
        self.edit_json_btn.setEnabled(False)
        
        result_buttons.addWidget(self.save_json_btn)
        result_buttons.addWidget(self.copy_json_btn)
        result_buttons.addWidget(self.edit_json_btn)
        result_buttons.addStretch()
        
        result_layout.addLayout(result_buttons)
        
        # Editor de JSON
        self.json_editor = QTextEdit()
        self.json_editor.setFont(QFont("Consolas", 10))
        self.json_editor.setPlaceholderText("O resultado da extração aparecerá aqui...")
        self.json_editor.setReadOnly(True)
        result_layout.addWidget(self.json_editor)
        
        layout.addWidget(result_group)
        
        # Instruções
        instructions = QLabel("""
        <b>Como usar:</b><br>
        1. Insira sua chave da API OpenAI<br>
        2. Selecione uma imagem de tabela (PNG, JPG, JPEG)<br>
        3. Clique em "Extrair Tabela com IA"<br>
        4. Aguarde o processamento<br>
        5. Revise e salve o resultado em formato JSONL
        """)
        instructions.setStyleSheet("background-color: #e8f4fd; padding: 10px; border-radius: 5px; color: #2c3e50;")
        layout.addWidget(instructions)
    
    def select_image(self):
        """Seleciona uma imagem para extração"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem da Tabela",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )
        
        if file_path:
            self.current_image_path = file_path
            self.load_image_preview(file_path)
            self.extract_btn.setEnabled(bool(self.api_key_input.text().strip()))
    
    def load_image_preview(self, image_path: str):
        """Carrega preview da imagem"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Redimensionar para preview
                scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview.setPixmap(scaled_pixmap)
                
                # Informações da imagem
                file_size = os.path.getsize(image_path) / 1024  # KB
                self.image_info.setText(
                    f"📁 {os.path.basename(image_path)} | "
                    f"📐 {pixmap.width()}x{pixmap.height()} | "
                    f"💾 {file_size:.1f} KB"
                )
            else:
                self.image_preview.setText("Erro ao carregar imagem")
                self.image_info.setText("")
        except Exception as e:
            self.image_preview.setText(f"Erro: {str(e)}")
            self.image_info.setText("")
    
    def start_extraction(self):
        """Inicia a extração com IA"""
        if not self.current_image_path:
            QMessageBox.warning(self, "Aviso", "Selecione uma imagem primeiro!")
            return
        
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Aviso", "Insira sua chave da API OpenAI!")
            return
        
        if not api_key.startswith("sk-"):
            QMessageBox.warning(self, "Aviso", "Chave da API parece inválida. Deve começar com 'sk-'")
            return
        
        # Configurar interface para extração
        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.json_editor.clear()
        
        # Iniciar thread de extração
        self.extractor_thread = OpenAITableExtractor(self.current_image_path, api_key)
        self.extractor_thread.progress_updated.connect(self.update_progress)
        self.extractor_thread.extraction_completed.connect(self.on_extraction_completed)
        self.extractor_thread.error_occurred.connect(self.on_extraction_error)
        self.extractor_thread.start()
    
    def update_progress(self, progress: int, message: str):
        """Atualiza o progresso"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def on_extraction_completed(self, data: dict):
        """Callback quando extração completa"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.extract_btn.setEnabled(True)
        
        self.extracted_data = data
        
        # Exibir resultado formatado
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        self.json_editor.setPlainText(json_str)
        
        # Habilitar botões de ação
        self.save_json_btn.setEnabled(True)
        self.copy_json_btn.setEnabled(True)
        self.edit_json_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Extração Concluída",
            "✅ Tabela extraída com sucesso!\n\n"
            "Revise o resultado e salve em formato JSONL se estiver correto."
        )
    
    def on_extraction_error(self, error_message: str):
        """Callback quando ocorre erro"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.extract_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Erro na Extração", error_message)
    
    def toggle_edit_mode(self):
        """Alterna modo de edição do JSON"""
        if self.json_editor.isReadOnly():
            self.json_editor.setReadOnly(False)
            self.edit_json_btn.setText("💾 Salvar Edição")
            self.json_editor.setStyleSheet("background-color: #fff3cd; border: 2px solid #ffc107;")
        else:
            # Tentar salvar as edições
            try:
                edited_text = self.json_editor.toPlainText()
                self.extracted_data = json.loads(edited_text)
                
                self.json_editor.setReadOnly(True)
                self.edit_json_btn.setText("✏️ Editar")
                self.json_editor.setStyleSheet("")
                
                QMessageBox.information(self, "Sucesso", "Edições salvas com sucesso!")
                
            except json.JSONDecodeError as e:
                QMessageBox.warning(
                    self, 
                    "Erro de JSON", 
                    f"JSON inválido. Corrija os erros antes de salvar:\n\n{str(e)}"
                )
    
    def copy_json(self):
        """Copia JSON para área de transferência"""
        if self.extracted_data:
            clipboard = QApplication.clipboard()
            json_str = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
            clipboard.setText(json_str)
            QMessageBox.information(self, "Copiado", "JSON copiado para área de transferência!")
    
    def save_jsonl(self):
        """Salva resultado em arquivo JSONL"""
        if not self.extracted_data:
            QMessageBox.warning(self, "Aviso", "Nenhum dado para salvar!")
            return
        
        # Sugerir nome do arquivo
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        default_name = f"{base_name}.jsonl"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar JSONL",
            default_name,
            "JSONL Files (*.jsonl);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.extracted_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(
                    self,
                    "Arquivo Salvo",
                    f"✅ Arquivo salvo com sucesso:\n{file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo:\n{str(e)}")


class AdvancedTableDetector(QWidget):
    """Aba para métodos avançados de detecção automática de tabelas"""
    
    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.detector_thread = None
        self.detected_tables = []
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface da aba de detecção avançada"""
        layout = QVBoxLayout(self)
        
        # Título principal
        title = QLabel("🔬 Detecção Automática Avançada")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 15px; padding: 10px;")
        layout.addWidget(title)
        
        # Descrição dos métodos
        description = QLabel("""
        <b>🎯 Sistema Híbrido Camelot v3.0 (NOVO!):</b><br>
        <b>• Configuração 'Padrão':</b> Lattice com line_scale=40 para tabelas bem definidas<br>
        <b>• Configuração 'Sensível':</b> Lattice com line_scale=60 para bordas sutis<br>
        <b>• Configuração 'Complementar':</b> Stream para casos especiais<br>
        <b>• Anti-Duplicatas:</b> Algoritmo 40% threshold bidireccional<br>
        <b>• Coordenadas Y-Invertidas:</b> Extração pixel-perfect garantida<br>
        <b>• Processamento em Lote:</b> Chunks de 50 páginas para otimização
        """)
        description.setStyleSheet("background-color: #f8f9fa; padding: 15px; border-radius: 8px; color: #2c3e50;")
        layout.addWidget(description)
        
        # Seção de seleção de arquivo
        file_section = QGroupBox("📁 Selecionar PDF")
        file_layout = QVBoxLayout(file_section)
        
        file_controls = QHBoxLayout()
        
        self.select_pdf_btn = QPushButton("📂 Escolher PDF")
        self.select_pdf_btn.clicked.connect(self.select_pdf)
        self.select_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.pdf_info_label = QLabel("Nenhum PDF selecionado")
        self.pdf_info_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        
        file_controls.addWidget(self.select_pdf_btn)
        file_controls.addWidget(self.pdf_info_label)
        file_controls.addStretch()
        
        file_layout.addLayout(file_controls)
        layout.addWidget(file_section)
        
        # Configurações
        config_section = QGroupBox("⚙️ Configurações de Detecção")
        config_layout = QFormLayout(config_section)
        
        # Método de detecção
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "🔬 Sistema Híbrido Camelot v3.0 (Recomendado)",
            "Camelot Stream (PDF com texto - sem bordas)",
            "Camelot Lattice (PDF com texto - com bordas)",
            "OpenCV (Linhas e Contornos)",
            "OpenCV Multi-Passadas (Múltiplas Tabelas)",
            "Tesseract OCR (Análise de Texto)", 
            "Híbrido (OpenCV + Tesseract)"
        ])
        self.method_combo.setCurrentIndex(0)  # Sistema Híbrido por padrão
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        self.method_combo.setToolTip(
            "• Sistema Híbrido v3.0: 3 configurações + anti-duplicatas + Y-invertida\n"
            "• Camelot Stream: Para PDFs com texto, tabelas sem bordas definidas\n"
            "• Camelot Lattice: Para PDFs com texto, tabelas com bordas\n"
            "• OpenCV: Detecção baseada em linhas e contornos\n"
            "• OpenCV Multi-Passadas: Para páginas com múltiplas tabelas\n"
            "• Tesseract OCR: Análise baseada em texto\n"
            "• Híbrido: Combina OpenCV e Tesseract"
        )
        config_layout.addRow("Método:", self.method_combo)
        
        # Páginas
        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("Ex: 1728,1729 ou 1700-1750 ou deixe vazio para todas")
        self.pages_input.setToolTip(
            "Especifique páginas para análise:\n"
            "Exemplos:\n"
            "• 1,2,3 - páginas específicas\n"
            "• 10-20 - intervalo de páginas\n"
            "• 1,5,10-15,20 - combinação\n"
            "• Vazio - todas as páginas (processamento em lotes)"
        )
        config_layout.addRow("Páginas:", self.pages_input)
        
        # Configurações Camelot (aparecem/desaparecem conforme método)
        self.camelot_group = QGroupBox("Configurações Camelot")
        camelot_layout = QFormLayout(self.camelot_group)
        
        # Tolerâncias
        camelot_tolerances = QHBoxLayout()
        
        self.edge_tol_input = QLineEdit("50")
        self.edge_tol_input.setPlaceholderText("50")
        self.edge_tol_input.setMaximumWidth(80)
        self.edge_tol_input.setToolTip("Tolerância de borda para detectar linhas de tabela")
        camelot_tolerances.addWidget(QLabel("Tolerância de Borda:"))
        camelot_tolerances.addWidget(self.edge_tol_input)
        
        self.row_tol_input = QLineEdit("2")
        self.row_tol_input.setPlaceholderText("2")
        self.row_tol_input.setMaximumWidth(80)
        self.row_tol_input.setToolTip("Tolerância entre linhas da tabela")
        camelot_tolerances.addWidget(QLabel("Tolerância de Linha:"))
        camelot_tolerances.addWidget(self.row_tol_input)
        
        camelot_tolerances.addStretch()
        camelot_layout.addRow("Avançado:", camelot_tolerances)
        
        config_layout.addRow("", self.camelot_group)
        
        # Configurações OpenCV
        self.opencv_group = QGroupBox("Configurações OpenCV")
        opencv_layout = QFormLayout(self.opencv_group)
        
        self.min_area_input = QLineEdit("3000")  # Reduzido de 5000 para 3000
        self.min_area_input.setPlaceholderText("3000")
        opencv_layout.addRow("Área Mínima da Tabela:", self.min_area_input)
        
        config_layout.addRow("", self.opencv_group)
        
        # Configurações Tesseract
        self.tesseract_group = QGroupBox("Configurações Tesseract")
        tesseract_layout = QFormLayout(self.tesseract_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["por", "eng", "spa", "fra"])
        self.language_combo.setCurrentText("por")
        tesseract_layout.addRow("Idioma:", self.language_combo)
        
        config_layout.addRow("", self.tesseract_group)
        
        layout.addWidget(config_section)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        
        self.detect_btn = QPushButton("🚀 Iniciar Detecção")
        self.detect_btn.clicked.connect(self.start_detection)
        self.detect_btn.setEnabled(False)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.preview_btn = QPushButton("👁️ Preview")
        self.preview_btn.clicked.connect(self.preview_selected)
        self.preview_btn.setEnabled(False)
        
        self.export_btn = QPushButton("💾 Exportar Selecionadas")
        self.export_btn.clicked.connect(self.export_tables)
        self.export_btn.setEnabled(False)
        
        action_layout.addWidget(self.detect_btn)
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.export_btn)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        # Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Lista de resultados
        results_section = QGroupBox("📋 Tabelas Detectadas")
        results_layout = QVBoxLayout(results_section)
        
        self.results_info_label = QLabel("Aguardando detecção...")
        self.results_info_label.setAlignment(Qt.AlignCenter)
        self.results_info_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        results_layout.addWidget(self.results_info_label)
        
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.results_list.itemSelectionChanged.connect(self.on_selection_changed)
        results_layout.addWidget(self.results_list)
        
        layout.addWidget(results_section)
        
        # Inicializar visibilidade das configurações
        self.on_method_changed()
    
    def on_method_changed(self):
        """Mostra/esconde configurações baseado no método selecionado"""
        method = self.method_combo.currentText()
        
        # Mostrar/esconder configurações específicas
        is_camelot = "Camelot" in method
        is_opencv = "OpenCV" in method
        is_tesseract = "Tesseract" in method
        
        self.camelot_group.setVisible(is_camelot)
        self.opencv_group.setVisible(is_opencv)
        self.tesseract_group.setVisible(is_tesseract)
    
    def select_pdf(self):
        """Seleciona PDF para análise"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF para Detecção Avançada",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            self.pdf_path = file_path
            
            try:
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                file_name = os.path.basename(file_path)
                self.pdf_info_label.setText(f"📄 {file_name} ({file_size:.1f} MB)")
                self.pdf_info_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 10px;")
            except:
                self.pdf_info_label.setText(f"📄 {os.path.basename(file_path)}")
            
            self.detect_btn.setEnabled(True)
            self.detected_tables = []
            self.results_list.clear()
            self.results_info_label.setText("PDF carregado. Configure as opções e clique em 'Iniciar Detecção'.")
    
    def start_detection(self):
        """Inicia a detecção com o método selecionado"""
        if not self.pdf_path:
            QMessageBox.warning(self, "Aviso", "Selecione um PDF primeiro!")
            return
        
        method = self.method_combo.currentText()
        pages = self.pages_input.text().strip() or "all"
        
        # Informação especial para Camelot com PDFs grandes
        if "Camelot" in method and pages == "all":
            try:
                import fitz
                doc = fitz.open(self.pdf_path)
                total_pages = len(doc)
                doc.close()
                
                if total_pages > 100:
                    QMessageBox.information(
                        self,
                        "📊 PDF Grande Detectado",
                        f"O PDF tem {total_pages} páginas.\n\n"
                        f"� O Camelot processará em lotes de 50 páginas para:\n"
                        f"• Evitar problemas de memória\n"
                        f"• Permitir acompanhar o progresso\n"
                        f"• Continuar mesmo se algumas páginas falharem\n\n"
                        f"⏱️ Isso pode levar alguns minutos...\n"
                        f"💡 Para resultados mais rápidos, especifique páginas específicas."
                    )
            except:
                pass  # Se não conseguir verificar, continua normalmente
        
        # Configurar interface
        self.detect_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.results_list.clear()
        
        # Escolher detector baseado no método
        if "Sistema Híbrido Camelot v3.0" in method:
            # Usar sistema híbrido avançado - método "hybrid" especial
            self.detector_thread = CamelotTableDetector(self.pdf_path, pages, "hybrid")
        elif "Camelot" in method:
            # Usar Camelot tradicional
            camelot_method = "stream" if "Stream" in method else "lattice"
            self.detector_thread = CamelotTableDetector(self.pdf_path, pages, camelot_method)
        elif "OpenCV Multi-Passadas" in method:
            min_area = int(self.min_area_input.text() or "5000")
            max_passes = 8  # Aumentado para 8 passadas para detectar mais tabelas
            self.detector_thread = MultiPassTableDetector(self.pdf_path, pages, max_passes)
        elif "OpenCV" in method:
            min_area = int(self.min_area_input.text() or "5000")
            self.detector_thread = OpenCVTableDetector(self.pdf_path, pages, min_area)
        elif "Tesseract" in method:
            language = self.language_combo.currentText()
            self.detector_thread = TesseractTableDetector(self.pdf_path, pages, language)
        else:  # Híbrido tradicional (OpenCV + Tesseract)
            # Para método híbrido tradicional, vamos executar OpenCV primeiro
            min_area = int(self.min_area_input.text() or "5000")
            self.detector_thread = OpenCVTableDetector(self.pdf_path, pages, min_area)
        
        # Conectar sinais
        self.detector_thread.progress_updated.connect(self.update_progress)
        self.detector_thread.error_occurred.connect(self.on_detection_error)
        
        # Conectar sinais específicos baseado no tipo de detector
        if "Camelot" in method:
            # Camelot tem sinais específicos
            self.detector_thread.tables_detected.connect(self.on_tables_detected)
            if hasattr(self.detector_thread, 'pdf_type_detected'):
                self.detector_thread.pdf_type_detected.connect(self.on_pdf_type_detected)
        else:
            # Outros detectores usam sinal padrão
            self.detector_thread.tables_detected.connect(self.on_tables_detected)
        
        # Conectar sinal específico para multi-passadas (PDF final exportado)
        if hasattr(self.detector_thread, 'final_pdf_saved'):
            self.detector_thread.final_pdf_saved.connect(self.on_final_pdf_saved)
        
        self.detector_thread.start()
    
    def update_progress(self, progress, message):
        """Atualiza progresso"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def on_tables_detected(self, tables):
        """Callback para tabelas detectadas"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        self.detected_tables = tables
        
        if not tables:
            self.results_info_label.setText("❌ Nenhuma tabela detectada com este método")
            return
        
        self.results_info_label.setText(f"✅ {len(tables)} tabela(s) detectada(s)")
        
        # Mostrar resultados na lista com informações detalhadas
        for i, table in enumerate(tables):
            method = table.get('detection_method', 'unknown')
            confidence = table.get('confidence', 0.0)
            
            # Informações adicionais para validação
            structure_score = table.get('structure_score', 0.0)
            content_score = table.get('content_score', 0.0)
            validation_passed = table.get('validation_passed', False)
            
            # Ícone baseado na confiança e validação
            if validation_passed and confidence > 0.8:
                conf_icon = "🟢"
                status = "ALTA"
            elif validation_passed and confidence > 0.6:
                conf_icon = "🟡"
                status = "MÉDIA"
            elif validation_passed:
                conf_icon = "🟠"
                status = "BAIXA"
            else:
                conf_icon = "🔴"
                status = "REJEITADA"
            
            # Texto detalhado para o item
            item_text = (
                f"{conf_icon} Página {table['page']} - "
                f"Tabela {i+1} ({table.get('estimated_rows', '?')}x{table.get('estimated_cols', '?')}) - "
                f"Método: {method.split('_')[0].upper()} - "
                f"Qualidade: {status} ({confidence:.1%})"
            )
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, table)
            
            # Tooltip com informações detalhadas
            tooltip_text = f"""
🔍 Detalhes da Validação:
📄 Página: {table['page']}
📐 Posição: ({table['bbox'][0]}, {table['bbox'][1]})
📏 Dimensões: {table['bbox'][2]} x {table['bbox'][3]} px
🎯 Método: {method}
⭐ Confiança Final: {confidence:.1%}
"""
            
            if 'structure_score' in table:
                tooltip_text += f"🏗️ Score Estrutural: {structure_score:.1%}\n"
            if 'content_score' in table:
                tooltip_text += f"📝 Score de Conteúdo: {content_score:.1%}\n"
            if 'column_consistency' in table:
                tooltip_text += f"📊 Consistência Colunas: {table['column_consistency']:.1%}\n"
            if 'word_count' in table:
                tooltip_text += f"🔤 Palavras Detectadas: {table['word_count']}\n"
            
            tooltip_text += f"✅ Validação: {'APROVADA' if validation_passed else 'REJEITADA'}"
            
            item.setToolTip(tooltip_text)
            self.results_list.addItem(item)
        
        self.export_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Detecção Concluída",
            f"🎉 {len(tables)} tabela(s) detectada(s)!\n\n"
            "Selecione as tabelas desejadas e clique em 'Exportar' para salvá-las."
        )
    
    def on_detection_error(self, error_message):
        """Callback para erros"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        self.results_info_label.setText("❌ Erro na detecção")
        QMessageBox.critical(self, "Erro na Detecção", error_message)
    
    def on_pdf_type_detected(self, pdf_type, has_text):
        """Callback específico do Camelot para informar sobre o tipo de PDF"""
        if pdf_type == "text-based" and has_text:
            self.results_info_label.setText("✅ PDF com texto detectado. Continuando com Camelot...")
        elif pdf_type == "image-based":
            self.results_info_label.setText("⚠️ PDF baseado em imagens detectado. Camelot pode ter resultados limitados.")
    
    def on_final_pdf_saved(self, pdf_path):
        """Callback para quando o PDF final com regiões pintadas é exportado"""
        msg = QMessageBox()
        msg.setWindowTitle("📄 PDF com Regiões Extraídas Exportado")
        msg.setIcon(QMessageBox.Information)
        
        pdf_name = os.path.basename(pdf_path)
        pdf_dir = os.path.dirname(pdf_path)
        
        msg.setText(f"✅ PDF exportado com sucesso!")
        msg.setInformativeText(
            f"O PDF com as regiões de tabelas pintadas de branco foi salvo em:\n\n"
            f"📁 {pdf_dir}\n"
            f"📄 {pdf_name}\n\n"
            f"💡 Use este PDF para verificar se alguma tabela ficou para trás.\n"
            f"As áreas BRANCAS mostram onde as tabelas foram detectadas e extraídas."
        )
        
        # Botões para ações
        open_btn = msg.addButton("🔍 Abrir PDF", QMessageBox.ActionRole)
        open_folder_btn = msg.addButton("📁 Abrir Pasta", QMessageBox.ActionRole)
        ok_btn = msg.addButton("✅ OK", QMessageBox.AcceptRole)
        
        msg.exec_()
        
        # Processar ação escolhida
        if msg.clickedButton() == open_btn:
            self.open_file(pdf_path)
        elif msg.clickedButton() == open_folder_btn:
            self.open_folder(pdf_dir)
    
    def open_file(self, file_path):
        """Abre um arquivo com o aplicativo padrão do sistema"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir o arquivo:\n{str(e)}")
    
    def open_folder(self, folder_path):
        """Abre uma pasta no explorador de arquivos"""
        try:
            if platform.system() == 'Windows':
                subprocess.run(['explorer', folder_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', folder_path])
            else:  # Linux
                subprocess.call(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir a pasta:\n{str(e)}")
    
    def on_selection_changed(self):
        """Atualiza interface quando seleção muda"""
        selected = self.results_list.selectedItems()
        self.preview_btn.setEnabled(len(selected) == 1)
    
    def preview_selected(self):
        """Mostra preview da tabela selecionada"""
        selected = self.results_list.selectedItems()
        if not selected:
            return
        
        table_data = selected[0].data(Qt.UserRole)
        bbox = table_data['bbox']
        page = table_data['page']
        
        info_text = f"""
        📄 Página: {page}
        📐 Posição: ({bbox[0]}, {bbox[1]})
        📏 Dimensões: {bbox[2]} x {bbox[3]} pixels
        🔍 Método: {table_data.get('detection_method', 'N/A')}
        📊 Linhas estimadas: {table_data.get('estimated_rows', 'N/A')}
        📋 Colunas estimadas: {table_data.get('estimated_cols', 'N/A')}
        ⭐ Confiança: {table_data.get('confidence', 0):.1%}
        """
        
        QMessageBox.information(self, "Informações da Tabela", info_text)
    
    def export_tables(self):
        """Exporta tabelas selecionadas"""
        selected_items = self.results_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Selecione ao menos uma tabela!")
            return
        
        # Escolher pasta
        out_dir = QFileDialog.getExistingDirectory(self, 'Escolher pasta para salvar tabelas')
        if not out_dir:
            return
        
        # Criar subpasta
        detection_dir = os.path.join(out_dir, 'tabelas_detectadas')
        os.makedirs(detection_dir, exist_ok=True)
        
        try:
            doc = fitz.open(self.pdf_path)
            pdf_base = os.path.splitext(os.path.basename(self.pdf_path))[0]
            saved_count = 0
            jsonl_data = []
            
            for item in selected_items:
                table_data = item.data(Qt.UserRole)
                page_num = table_data['page']
                bbox = table_data['bbox']
                
                # Extrair região da tabela
                page = doc.load_page(page_num - 1)
                
                # CORREÇÃO: Sistema de coordenadas Y (Camelot vs PyMuPDF)
                page_height = page.rect.height
                margin = 15  # Margem para capturar conteúdo ao redor
                
                # Camelot usa Y crescendo para baixo, PyMuPDF usa Y crescendo para cima
                # Inverter coordenadas Y
                expanded_bbox = [
                    max(0, bbox[0] - margin),
                    max(0, page_height - bbox[3] - margin),  # Y invertido
                    min(page.rect.width, bbox[2] + margin),
                    min(page.rect.height, page_height - bbox[1] + margin)  # Y invertido
                ]
                
                rect = fitz.Rect(expanded_bbox)
                pix = page.get_pixmap(clip=rect, dpi=200)  # Maior resolução
                
                # Converter e salvar
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                
                method_name = table_data.get('detection_method', 'auto').split('_')[0]
                table_name = f'{pdf_base}_pag{page_num}_tab{saved_count+1}_{method_name}.png'
                img_path = os.path.join(detection_dir, table_name)
                img.save(img_path)
                
                # Dados JSONL
                jsonl_entry = {
                    "type": "table",
                    "source": pdf_base,
                    "page": page_num,
                    "table_number": saved_count + 1,
                    "title": f"Tabela Detectada - {method_name.upper()}",
                    "image_file": table_name,
                    "extraction_date": datetime.datetime.now().isoformat(),
                    "detection_method": table_data.get('detection_method', 'unknown'),
                    "bbox": bbox,
                    "estimated_dimensions": f"{table_data.get('estimated_rows', '?')}x{table_data.get('estimated_cols', '?')}",
                    "confidence": table_data.get('confidence', 0.0),
                    "text": [],
                    "metadata": {
                        "conversion_method": "automatic_detection",
                        "requires_manual_review": table_data.get('confidence', 0) < 0.7,
                        "confidence_level": "high" if table_data.get('confidence', 0) > 0.8 else "medium" if table_data.get('confidence', 0) > 0.5 else "low"
                    }
                }
                jsonl_data.append(jsonl_entry)
                saved_count += 1
            
            doc.close()
            
            # Salvar JSONL
            jsonl_file = os.path.join(detection_dir, f'{pdf_base}_deteccao_automatica.jsonl')
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for entry in jsonl_data:
                    json.dump(entry, f, ensure_ascii=False)
                    f.write('\n')
            
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"🎉 {saved_count} tabela(s) exportada(s)!\n\n"
                f"📁 Pasta: {detection_dir}\n"
                f"🖼️ Imagens: {saved_count} arquivos PNG\n"
                f"📄 Dados: {os.path.basename(jsonl_file)}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar: {str(e)}")


class CamelotPDFAnalyzer(QWidget):
    """Aba dedicada para análise de PDF com Camelot - sem renderização de imagens"""
    
    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.detector_thread = None
        self.detected_tables = []
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface da aba Camelot"""
        layout = QVBoxLayout(self)
        
        # Título principal
        title = QLabel("🔍 Camelot - Detecção Automática de Tabelas")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 15px; padding: 10px;")
        layout.addWidget(title)
        
        # Seção de seleção de arquivo
        file_section = QGroupBox("📁 Selecionar PDF")
        file_layout = QVBoxLayout(file_section)
        
        # Botão de seleção e info do arquivo
        file_controls = QHBoxLayout()
        
        self.select_pdf_btn = QPushButton("📂 Escolher PDF para Análise")
        self.select_pdf_btn.clicked.connect(self.select_pdf)
        self.select_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.pdf_info_label = QLabel("Nenhum PDF selecionado")
        self.pdf_info_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        
        file_controls.addWidget(self.select_pdf_btn)
        file_controls.addWidget(self.pdf_info_label)
        file_controls.addStretch()
        
        file_layout.addLayout(file_controls)
        layout.addWidget(file_section)
        
        # Seção de configurações
        config_section = QGroupBox("⚙️ Configurações de Detecção")
        config_layout = QFormLayout(config_section)
        
        # Método de detecção
        self.method_combo = QComboBox()
        self.method_combo.addItems(["stream", "lattice"])
        self.method_combo.setCurrentText("stream")
        self.method_combo.setToolTip(
            "stream: Para tabelas sem bordas (texto alinhado)\n"
            "lattice: Para tabelas com bordas definidas"
        )
        config_layout.addRow("Método de Detecção:", self.method_combo)
        
        # Páginas a processar
        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("Ex: 1,3,5-10 ou deixe vazio para todas as páginas")
        self.pages_input.setToolTip("Especifique páginas específicas ou deixe vazio para analisar todo o PDF")
        config_layout.addRow("Páginas:", self.pages_input)
        
        # Configurações avançadas
        advanced_layout = QHBoxLayout()
        
        self.edge_tol_input = QLineEdit("50")
        self.edge_tol_input.setPlaceholderText("50")
        self.edge_tol_input.setMaximumWidth(80)
        advanced_layout.addWidget(QLabel("Tolerância de Borda:"))
        advanced_layout.addWidget(self.edge_tol_input)
        
        self.row_tol_input = QLineEdit("2")
        self.row_tol_input.setPlaceholderText("2")
        self.row_tol_input.setMaximumWidth(80)
        advanced_layout.addWidget(QLabel("Tolerância de Linha:"))
        advanced_layout.addWidget(self.row_tol_input)
        
        advanced_layout.addStretch()
        config_layout.addRow("Avançado:", advanced_layout)
        
        layout.addWidget(config_section)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        
        self.detect_btn = QPushButton("🚀 Detectar Tabelas")
        self.detect_btn.clicked.connect(self.start_detection)
        self.detect_btn.setEnabled(False)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 12px 25px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.preview_btn = QPushButton("👁️ Visualizar Tabela")
        self.preview_btn.clicked.connect(self.preview_selected_table)
        self.preview_btn.setEnabled(False)
        
        self.export_selected_btn = QPushButton("💾 Exportar Selecionadas")
        self.export_selected_btn.clicked.connect(self.export_selected_tables)
        self.export_selected_btn.setEnabled(False)
        
        self.export_all_btn = QPushButton("📥 Exportar Todas")
        self.export_all_btn.clicked.connect(self.export_all_tables)
        self.export_all_btn.setEnabled(False)
        
        action_layout.addWidget(self.detect_btn)
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.export_selected_btn)
        action_layout.addWidget(self.export_all_btn)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        # Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Lista de tabelas detectadas
        tables_section = QGroupBox("📋 Tabelas Detectadas")
        tables_layout = QVBoxLayout(tables_section)
        
        # Informações das tabelas
        self.tables_info_label = QLabel("Nenhuma tabela detectada ainda")
        self.tables_info_label.setAlignment(Qt.AlignCenter)
        self.tables_info_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        tables_layout.addWidget(self.tables_info_label)
        
        # Lista de tabelas
        self.tables_list = QListWidget()
        self.tables_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.tables_list.itemSelectionChanged.connect(self.on_table_selection_changed)
        tables_layout.addWidget(self.tables_list)
        
        # Preview da tabela selecionada
        self.table_preview = QTextEdit()
        self.table_preview.setMaximumHeight(200)
        self.table_preview.setPlaceholderText("Selecione uma tabela para ver o preview...")
        self.table_preview.setReadOnly(True)
        self.table_preview.setFont(QFont("Consolas", 9))
        tables_layout.addWidget(QLabel("Preview da Tabela Selecionada:"))
        tables_layout.addWidget(self.table_preview)
        
        layout.addWidget(tables_section)
        
        # Instruções
        instructions = QLabel("""
        <b>🔧 Como usar o Camelot:</b><br>
        <b>1.</b> Selecione um PDF que contenha <u>texto real</u> (não imagens de texto)<br>
        <b>2.</b> Escolha o método adequado:<br>
        &nbsp;&nbsp;&nbsp;• <b>stream</b>: Tabelas sem bordas, texto alinhado em colunas<br>
        &nbsp;&nbsp;&nbsp;• <b>lattice</b>: Tabelas com bordas e linhas visíveis<br>
        <b>3.</b> Especifique páginas específicas ou deixe vazio para todas<br>
        <b>4.</b> Clique em "Detectar Tabelas" e aguarde<br>
        <b>5.</b> Selecione as tabelas desejadas e exporte<br><br>
        <b>⚠️ Importante:</b> O Camelot funciona melhor com PDFs que contêm texto selecionável, não imagens escaneadas.
        """)
        instructions.setStyleSheet("""
            background-color: #e8f4fd; 
            padding: 15px; 
            border-radius: 8px; 
            color: #2c3e50;
            border: 1px solid #3498db;
        """)
        layout.addWidget(instructions)
    
    def select_pdf(self):
        """Seleciona um PDF para análise"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF para Análise com Camelot",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            self.pdf_path = file_path
            
            # Atualizar informações do PDF
            try:
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                file_name = os.path.basename(file_path)
                self.pdf_info_label.setText(f"📄 {file_name} ({file_size:.1f} MB)")
                self.pdf_info_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 10px;")
            except:
                self.pdf_info_label.setText(f"📄 {os.path.basename(file_path)}")
            
            # Habilitar detecção
            self.detect_btn.setEnabled(True)
            
            # Limpar dados anteriores
            self.detected_tables = []
            self.tables_list.clear()
            self.table_preview.clear()
            self.tables_info_label.setText("PDF carregado. Clique em 'Detectar Tabelas' para começar.")
            self.export_selected_btn.setEnabled(False)
            self.export_all_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
    
    def start_detection(self):
        """Inicia a detecção de tabelas"""
        if not self.pdf_path:
            QMessageBox.warning(self, "Aviso", "Selecione um PDF primeiro!")
            return
        
        # Obter configurações
        method = self.method_combo.currentText()
        pages = self.pages_input.text().strip() or "all"
        
        # Configurar interface
        self.detect_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.tables_list.clear()
        self.table_preview.clear()
        
        # Iniciar thread de detecção
        self.detector_thread = CamelotTableDetector(self.pdf_path, pages, method)
        self.detector_thread.progress_updated.connect(self.update_progress)
        self.detector_thread.tables_detected.connect(self.on_tables_detected)
        self.detector_thread.error_occurred.connect(self.on_detection_error)
        self.detector_thread.pdf_type_detected.connect(self.on_pdf_type_detected)
        self.detector_thread.start()
    
    def update_progress(self, progress, message):
        """Atualiza o progresso"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def on_tables_detected(self, tables):
        """Callback quando tabelas são detectadas"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        self.detected_tables = tables
        
        if not tables:
            self.tables_info_label.setText("❌ Nenhuma tabela detectada. Tente outro método ou verifique se o PDF contém texto selecionável.")
            return
        
        # Atualizar info
        self.tables_info_label.setText(f"✅ {len(tables)} tabela(s) detectada(s)")
        
        # Exibir tabelas na lista
        for i, table in enumerate(tables):
            accuracy = table.get('accuracy', 0.0)
            accuracy_icon = "🟢" if accuracy > 0.8 else "🟡" if accuracy > 0.5 else "🔴"
            
            item_text = (
                f"{accuracy_icon} Página {table['page']} - Tabela {i+1} "
                f"({table['shape'][0]}x{table['shape'][1]}) - "
                f"Precisão: {accuracy:.1%}"
            )
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, table)
            
            # Adicionar preview como tooltip
            if table.get('preview'):
                item.setToolTip(f"Preview:\n{table['preview']}")
            
            self.tables_list.addItem(item)
        
        # Habilitar botões
        self.export_all_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Detecção Concluída",
            f"🎉 {len(tables)} tabela(s) detectada(s)!\n\n"
            "Selecione as tabelas desejadas na lista para ver o preview "
            "e clique em 'Exportar' para salvar."
        )
    
    def on_detection_error(self, error_message):
        """Callback quando ocorre erro"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        self.tables_info_label.setText("❌ Erro na detecção")
        QMessageBox.critical(self, "Erro na Detecção", f"Erro ao detectar tabelas:\n\n{error_message}")
    
    def on_pdf_type_detected(self, pdf_type, has_text):
        """Callback para informação sobre o tipo de PDF"""
        if has_text:
            self.tables_info_label.setText(f"✅ PDF com texto detectado - Compatível com Camelot")
        else:
            self.tables_info_label.setText(f"⚠️ PDF baseado em imagens - Use outras abas para extração")
    
    def on_table_selection_changed(self):
        """Atualiza preview quando seleção muda"""
        selected_items = self.tables_list.selectedItems()
        
        if selected_items:
            self.export_selected_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            
            # Mostrar preview da primeira tabela selecionada
            if len(selected_items) == 1:
                table_data = selected_items[0].data(Qt.UserRole)
                preview_text = table_data.get('preview', 'Preview não disponível')
                self.table_preview.setPlainText(preview_text)
            else:
                self.table_preview.setPlainText(f"{len(selected_items)} tabelas selecionadas")
        else:
            self.export_selected_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            self.table_preview.clear()
    
    def preview_selected_table(self):
        """Mostra preview detalhado da tabela selecionada"""
        selected_items = self.tables_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Selecione uma tabela primeiro!")
            return
        
        if len(selected_items) > 1:
            QMessageBox.warning(self, "Aviso", "Selecione apenas uma tabela para preview!")
            return
        
        table_data = selected_items[0].data(Qt.UserRole)
        
        # Criar janela de preview
        preview_dialog = QMessageBox(self)
        preview_dialog.setWindowTitle("Preview da Tabela")
        preview_dialog.setText(f"Tabela da Página {table_data['page']} - {table_data['shape'][0]}x{table_data['shape'][1]} células")
        preview_dialog.setDetailedText(table_data.get('preview', 'Preview não disponível'))
        preview_dialog.exec_()
    
    def export_selected_tables(self):
        """Exporta as tabelas selecionadas"""
        selected_items = self.tables_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Selecione ao menos uma tabela!")
            return
        
        selected_tables = [item.data(Qt.UserRole) for item in selected_items]
        self._export_tables(selected_tables)
    
    def export_all_tables(self):
        """Exporta todas as tabelas detectadas"""
        if not self.detected_tables:
            QMessageBox.warning(self, "Aviso", "Nenhuma tabela detectada!")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar Exportação",
            f"Deseja exportar todas as {len(self.detected_tables)} tabelas detectadas?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._export_tables(self.detected_tables)
    
    def _export_tables(self, tables_to_export):
        """Exporta as tabelas especificadas"""
        # Escolher pasta para salvar
        out_dir = QFileDialog.getExistingDirectory(self, 'Escolher pasta para salvar tabelas Camelot')
        if not out_dir:
            return
        
        # Criar pasta 'tabelas_camelot' se não existir
        tabelas_dir = os.path.join(out_dir, 'tabelas_camelot')
        os.makedirs(tabelas_dir, exist_ok=True)
        
        pdf_base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        saved_count = 0
        jsonl_data = []
        
        try:
            # Abrir PDF para extrair as imagens das tabelas
            doc = fitz.open(self.pdf_path)
            
            for table in tables_to_export:
                page_num = table['page']
                bbox = table['bbox']  # (x1, y1, x2, y2)
                table_index = table['index']
                
                # Carregar página
                page = doc.load_page(page_num - 1)  # Camelot usa 1-based, fitz usa 0-based
                
                # Extrair região da tabela com correção de coordenadas Y
                page_height = page.rect.height
                margin = 15  # Margem para capturar conteúdo ao redor das bordas
                
                # CORREÇÃO: Camelot usa Y crescendo para baixo, PyMuPDF usa Y crescendo para cima
                expanded_bbox = [
                    max(0, bbox[0] - margin),
                    max(0, page_height - bbox[3] - margin),  # Y invertido
                    min(page.rect.width, bbox[2] + margin),
                    min(page.rect.height, page_height - bbox[1] + margin)  # Y invertido
                ]
                
                rect = fitz.Rect(expanded_bbox)
                pix = page.get_pixmap(clip=rect, dpi=250)  # Alta resolução para melhor qualidade
                
                # Converter para QImage
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                
                # Salvar imagem
                table_name = f'{pdf_base}_pag{page_num}_tab{table_index}_camelot.png'
                img_path = os.path.join(tabelas_dir, table_name)
                img.save(img_path)
                
                # Criar dados JSONL
                jsonl_entry = {
                    "type": "table",
                    "source": pdf_base,
                    "page": page_num,
                    "table_number": table_index,
                    "title": f"Tabela Camelot - Página {page_num}, Tabela {table_index}",
                    "image_file": table_name,
                    "extraction_date": datetime.datetime.now().isoformat(),
                    "detection_method": "camelot",
                    "bbox": bbox,
                    "shape": table['shape'],
                    "accuracy": table.get('accuracy', 0.0),
                    "text": table.get('data', []),
                    "metadata": {
                        "conversion_method": "camelot_automatic",
                        "requires_manual_review": table.get('accuracy', 0) < 0.8,
                        "confidence": "high" if table.get('accuracy', 0) > 0.8 else "medium" if table.get('accuracy', 0) > 0.5 else "low"
                    }
                }
                jsonl_data.append(jsonl_entry)
                saved_count += 1
            
            doc.close()
            
            # Salvar arquivo JSONL consolidado
            jsonl_file = os.path.join(tabelas_dir, f'{pdf_base}_tabelas_camelot.jsonl')
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for entry in jsonl_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"🎉 {saved_count} tabela(s) exportada(s) com sucesso!\n\n"
                f"📁 Pasta: {tabelas_dir}\n"
                f"🖼️ Imagens: {saved_count} arquivos PNG\n"
                f"📄 Dados: {os.path.basename(jsonl_file)}\n\n"
                f"💡 Use a aba 'Visualizar Tabelas' para revisar os resultados!"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar tabelas:\n{str(e)}")


class CamelotTableDetectorWidget(QWidget):
    """Widget para detecção automática de tabelas usando Camelot"""
    
    tables_selected = pyqtSignal(list)  # Signal emitido quando tabelas são selecionadas
    
    def __init__(self):
        super().__init__()
        self.detector_thread = None
        self.pdf_path = None
        self.detected_tables = []
        self.init_ui()
    
    def init_ui(self):
        """Inicializa a interface"""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("🔍 Detecção Automática de Tabelas")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)
        
        # Configurações
        config_group = QGroupBox("Configurações de Detecção")
        config_layout = QFormLayout(config_group)
        
        # Método de detecção
        self.method_combo = QComboBox()
        self.method_combo.addItems(["stream", "lattice"])
        self.method_combo.setCurrentText("lattice")  # Padrão para lattice agora
        self.method_combo.setToolTip(
            "• Stream: Detecta tabelas baseado no texto\n"
            "• Lattice: Detecta tabelas baseado nas bordas (🆕 Configuração otimizada - detecta mais tabelas!)"
        )
        config_layout.addRow("Método:", self.method_combo)
        
        # Páginas a processar
        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("Ex: 1,3,5-10 ou deixe vazio para todas")
        config_layout.addRow("Páginas:", self.pages_input)
        
        layout.addWidget(config_group)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        self.detect_btn = QPushButton("🚀 Detectar Tabelas")
        self.detect_btn.clicked.connect(self.start_detection)
        self.detect_btn.setEnabled(False)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.select_all_btn = QPushButton("✅ Selecionar Todas")
        self.select_all_btn.clicked.connect(self.select_all_tables)
        self.select_all_btn.setEnabled(False)
        
        self.export_btn = QPushButton("💾 Exportar Selecionadas")
        self.export_btn.clicked.connect(self.export_selected_tables)
        self.export_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.detect_btn)
        buttons_layout.addWidget(self.select_all_btn)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Lista de tabelas detectadas
        self.tables_list = QListWidget()
        self.tables_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(QLabel("Tabelas Detectadas:"))
        layout.addWidget(self.tables_list)
        
        # Instruções
        instructions = QLabel("""
        <b>Como usar:</b><br>
        1. Selecione um PDF primeiro na área principal<br>
        2. Escolha o método: "stream" para texto alinhado, "lattice" para tabelas com bordas (🆕 otimizado!)<br>
        3. Especifique páginas (opcional) ou deixe vazio para todas<br>
        4. Clique em "Detectar Tabelas"<br>
        <br>
        <b>🎯 Filtros automáticos:</b><br>
        • Apenas tabelas com accuracy > 50% são mostradas<br>
        • Extração com alta resolução (DPI 250) e margem<br>
        • Dados salvos em CSV + imagens PNG de qualidade
        5. Selecione as tabelas desejadas na lista<br>
        6. Clique em "Exportar Selecionadas" para extrair as tabelas
        """)
        instructions.setStyleSheet("background-color: #e8f4fd; padding: 10px; border-radius: 5px; color: #2c3e50;")
        layout.addWidget(instructions)
    
    def set_pdf_path(self, pdf_path):
        """Define o caminho do PDF"""
        self.pdf_path = pdf_path
        self.detect_btn.setEnabled(True)
        self.tables_list.clear()
        self.detected_tables = []
        self.select_all_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
    
    def start_detection(self):
        """Inicia a detecção de tabelas"""
        if not self.pdf_path:
            QMessageBox.warning(self, "Aviso", "Nenhum PDF selecionado!")
            return
        
        method = self.method_combo.currentText()
        pages = self.pages_input.text().strip() or "all"
        
        # Configurar interface
        self.detect_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.tables_list.clear()
        
        # Iniciar thread de detecção
        self.detector_thread = CamelotTableDetector(self.pdf_path, pages, method)
        self.detector_thread.progress_updated.connect(self.update_progress)
        self.detector_thread.tables_detected.connect(self.on_tables_detected)
        self.detector_thread.error_occurred.connect(self.on_detection_error)
        self.detector_thread.start()
    
    def update_progress(self, progress, message):
        """Atualiza o progresso"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def on_tables_detected(self, tables):
        """Callback quando tabelas são detectadas"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        self.detected_tables = tables
        
        # Exibir tabelas na lista
        for table in tables:
            item_text = (
                f"Página {table['page']} - Tabela {table['index']} "
                f"({table['shape'][0]}x{table['shape'][1]} células)"
            )
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, table)  # Armazenar dados da tabela
            
            # Adicionar preview como tooltip
            if table['preview']:
                item.setToolTip(f"Preview:\n{table['preview']}")
            
            self.tables_list.addItem(item)
        
        self.select_all_btn.setEnabled(len(tables) > 0)
        self.export_btn.setEnabled(len(tables) > 0)
        
        QMessageBox.information(
            self,
            "Detecção Concluída",
            f"✅ {len(tables)} tabelas detectadas!\n\n"
            "Selecione as tabelas desejadas na lista e clique em 'Exportar Selecionadas'."
        )
    
    def on_detection_error(self, error_message):
        """Callback quando ocorre erro"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Erro na Detecção", error_message)
    
    def select_all_tables(self):
        """Seleciona todas as tabelas da lista"""
        for i in range(self.tables_list.count()):
            self.tables_list.item(i).setSelected(True)
    
    def export_selected_tables(self):
        """Exporta as tabelas selecionadas"""
        selected_items = self.tables_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Selecione ao menos uma tabela!")
            return
        
        # Coletar dados das tabelas selecionadas
        selected_tables = []
        for item in selected_items:
            table_data = item.data(Qt.UserRole)
            selected_tables.append(table_data)
        
        # Emitir signal para a classe principal processar
        self.tables_selected.emit(selected_tables)


class PDFPageLabel(QLabel):
    """Label personalizado para exibir páginas do PDF com seleção de tabelas"""
    
    def __init__(self, image, page_idx, parent):
        super().__init__()
        self.setPixmap(QPixmap.fromImage(image))
        self.image = image
        self.page_idx = page_idx
        self.parent = parent
        self.rects = []  # lista de (QRect, QColor)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.parent.global_select_points:
                # Primeiro clique: inicia pré-visualização
                self.parent.preview_info = {
                    'start': (self.page_idx, event.pos()),
                    'end': None
                }
            else:
                # Segundo clique: termina pré-visualização
                if hasattr(self.parent, 'preview_info'):
                    self.parent.preview_info['end'] = (self.page_idx, event.pos())
            self.parent.register_click(self.page_idx, event.pos())
            # Atualiza todos os labels para garantir que o preview suma
            for label in self.parent.image_labels:
                if label:
                    label.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Desenhar retângulos de seleção
        for rect, color in self.rects:
            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
        
        # Preview global
        preview_info = getattr(self.parent, 'preview_info', None)
        if preview_info:
            start = preview_info.get('start')
            end = preview_info.get('end')
            if start and not end:
                # Durante arraste
                if self.page_idx == start[0]:
                    mouse_pos = self.mapFromGlobal(QCursor.pos())
                    rect = QRect(start[1], mouse_pos).normalized()
                    pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.drawRect(rect)
            elif start and end:
                # Após segundo clique
                if start[0] == end[0]:
                    # Mesma página: preview vermelho
                    if self.page_idx == start[0]:
                        rect = QRect(start[1], end[1]).normalized()
                        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawRect(rect)
                else:
                    # Entre páginas: preview azul
                    if self.page_idx == start[0]:
                        h1 = self.image.height()
                        x1 = start[1].x()
                        y1 = start[1].y()
                        x2 = end[1].x()
                        poly = QPolygon([
                            QPoint(x1, y1),
                            QPoint(x2, y1),
                            QPoint(x2, h1),
                            QPoint(x1, h1)
                        ])
                        pen = QPen(QColor(0, 0, 255), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawPolygon(poly)
                    
                    if self.page_idx == end[0]:
                        x1 = start[1].x()
                        x2 = end[1].x()
                        y2 = end[1].y()
                        poly = QPolygon([
                            QPoint(x1, 0),
                            QPoint(x2, 0),
                            QPoint(x2, y2),
                            QPoint(x1, y2)
                        ])
                        pen = QPen(QColor(0, 0, 255), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawPolygon(poly)

    def mouseMoveEvent(self, event):
        # Atualiza todos os labels para garantir que o preview seja desenhado corretamente
        preview_info = getattr(self.parent, 'preview_info', None)
        if preview_info and preview_info.get('start') and not preview_info.get('end'):
            for label in self.parent.image_labels:
                if label:
                    label.update()
        super().mouseMoveEvent(event)

    def add_rect(self, rect, color=QColor(255,0,0)):
        self.rects.append((rect, color))
        self.update()

    def clear_rects(self):
        self.rects.clear()
        if hasattr(self.parent, 'preview_info'):
            self.parent.preview_info = {}
        self.update()


class ImageViewer(QWidget):
    """Tela 2: Visualizador de imagens com conversão automática"""
    
    def __init__(self):
        super().__init__()
        self.image_folder = ""
        self.converter_thread = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Cabeçalho
        header_layout = QHBoxLayout()
        self.folder_label = QLabel("Nenhuma pasta selecionada")
        self.folder_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.select_folder_btn = QPushButton("Selecionar Pasta de Imagens")
        self.select_folder_btn.clicked.connect(self.select_image_folder)
        
        header_layout.addWidget(QLabel("Pasta:"))
        header_layout.addWidget(self.folder_label)
        header_layout.addStretch()
        header_layout.addWidget(self.select_folder_btn)
        
        # Área de visualização das imagens
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        
        # Área de controles
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Atualizar Lista")
        self.refresh_btn.clicked.connect(self.load_images)
        self.refresh_btn.setEnabled(False)
        
        self.convert_btn = QPushButton("🚀 Converter Todas para JSONL")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.convert_btn)
        
        # Layout principal
        layout.addLayout(header_layout)
        layout.addWidget(QLabel("Visualização das Imagens Extraídas:"))
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addLayout(controls_layout)
        
        self.setLayout(layout)
    
    def select_image_folder(self):
        """Seleciona a pasta com as imagens"""
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Imagens")
        if folder:
            self.image_folder = folder
            self.folder_label.setText(os.path.basename(folder))
            self.refresh_btn.setEnabled(True)
            self.load_images()
    
    def load_images(self):
        """Carrega e exibe as imagens da pasta"""
        if not self.image_folder:
            return
        
        # Limpar layout anterior
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        
        # Buscar imagens PNG
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith('.png')]
        
        if not image_files:
            no_images_label = QLabel("Nenhuma imagem encontrada nesta pasta")
            no_images_label.setAlignment(Qt.AlignCenter)
            no_images_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.scroll_layout.addWidget(no_images_label)
            self.convert_btn.setEnabled(False)
            return
        
        # Exibir imagens em lista vertical
        for image_file in image_files:
            image_widget = self.create_image_widget(image_file)
            self.scroll_layout.addWidget(image_widget)
        
        self.convert_btn.setEnabled(True)
    
    def create_image_widget(self, image_file):
        """Cria widget para exibir uma imagem"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box)
        widget.setMaximumHeight(400)
        
        layout = QHBoxLayout(widget)
        
        # Imagem
        image_path = os.path.join(self.image_folder, image_file)
        pixmap = QPixmap(image_path)
        
        if not pixmap.isNull():
            # Redimensionar mantendo proporção
            scaled_pixmap = pixmap.scaled(300, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label = QLabel()
            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignCenter)
        else:
            image_label = QLabel("Erro ao carregar imagem")
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("color: red;")
        
        # Info da imagem
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        name_label = QLabel(f"<b>{image_file}</b>")
        name_label.setWordWrap(True)
        
        try:
            file_size = os.path.getsize(image_path) / 1024  # KB
            size_label = QLabel(f"Tamanho: {file_size:.1f} KB")
            
            if not pixmap.isNull():
                dim_label = QLabel(f"Dimensões: {pixmap.width()} x {pixmap.height()}")
            else:
                dim_label = QLabel("Dimensões: N/A")
        except:
            size_label = QLabel("Tamanho: N/A")
            dim_label = QLabel("Dimensões: N/A")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label)
        info_layout.addWidget(dim_label)
        info_layout.addStretch()
        
        layout.addWidget(image_label)
        layout.addWidget(info_widget)
        
        return widget
    
    def start_conversion(self):
        """Inicia o processo de conversão automática"""
        if not self.image_folder:
            return
        
        # Verificar se há imagens
        image_files = [f for f in os.listdir(self.image_folder) if f.endswith('.png')]
        if not image_files:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem encontrada para conversão!")
            return
        
        # Confirmar conversão
        reply = QMessageBox.question(
            self, 
            "Confirmar Conversão",
            f"Deseja converter {len(image_files)} imagens para formato JSONL?\n\n"
            "Os arquivos JSONL serão salvos na mesma pasta das imagens.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Configurar interface para conversão
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Iniciando conversão...")
        
        # Iniciar thread de conversão
        self.converter_thread = ImageToJsonlConverter(self.image_folder, self.image_folder)
        self.converter_thread.progress_updated.connect(self.update_progress)
        self.converter_thread.conversion_finished.connect(self.conversion_finished)
        self.converter_thread.start()
    
    def update_progress(self, progress, message):
        """Atualiza o progresso da conversão"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def conversion_finished(self, created_files):
        """Chamado quando a conversão termina"""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        
        if created_files:
            QMessageBox.information(
                self, 
                "Conversão Concluída",
                f"Conversão concluída com sucesso!\n\n"
                f"{len(created_files)} arquivos JSONL foram criados na pasta:\n"
                f"{self.image_folder}\n\n"
                "Você pode agora editar os arquivos JSONL para adicionar o conteúdo das tabelas."
            )
        else:
            QMessageBox.warning(
                self, 
                "Conversão Falhou",
                "Não foi possível criar os arquivos JSONL.\n"
                "Verifique se há imagens na pasta e se você tem permissão de escrita."
            )


class PDFTableExtractor(QWidget):
    """Aplicação principal para extração de tabelas de PDF"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Extrator de Tabelas de PDF - Carregamento Progressivo')
        self.resize(1400, 900)
        self.pdf_path = None
        self.page_images = []
        self.selections = []
        self.image_labels = []
        self.global_select_points = []
        self.loader_thread = None
        self.loaded_batches = {}
        self.total_pages = 0
        self.batch_size = 50  # páginas por lote
        self.init_ui()

    def init_ui(self):
        """Inicializa a interface do usuário"""
        main_layout = QVBoxLayout(self)
        
        # Criar tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Extração de PDF
        extraction_tab = QWidget()
        extraction_layout = QVBoxLayout(extraction_tab)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        btn_open = QPushButton('📁 Escolher PDF')
        btn_open.clicked.connect(self.open_pdf)
        btn_open.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        buttons_layout.addWidget(btn_open)
        
        btn_save = QPushButton('💾 Salvar Tabelas Selecionadas')
        btn_save.clicked.connect(self.save_tables)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        buttons_layout.addWidget(btn_save)
        
        btn_view_tables = QPushButton('🔍 Abrir Pasta de Tabelas')
        btn_view_tables.clicked.connect(self.open_table_folder)
        btn_view_tables.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        buttons_layout.addWidget(btn_view_tables)
        
        buttons_layout.addStretch()
        
        # Configurações de lote
        batch_label = QLabel("Tamanho do lote:")
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setRange(10, 100)
        self.batch_spinbox.setValue(self.batch_size)
        self.batch_spinbox.setSuffix(" páginas")
        self.batch_spinbox.valueChanged.connect(self.update_batch_size)
        
        buttons_layout.addWidget(batch_label)
        buttons_layout.addWidget(self.batch_spinbox)
        
        extraction_layout.addLayout(buttons_layout)

        # Barra de progresso para carregamento
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        extraction_layout.addWidget(self.progress_bar)
        extraction_layout.addWidget(self.progress_label)

        # Área de scroll para o PDF (apenas seleção manual)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        extraction_layout.addWidget(self.scroll)
        
        # Instruções para seleção manual
        manual_instructions = QLabel("""
        <b>Como usar a Seleção Manual:</b><br>
        • Aguarde o carregamento completo do PDF<br>
        • Clique em dois pontos para selecionar uma tabela (mesmo página ou entre páginas)<br>
        • Use "Salvar Tabelas Selecionadas" para extrair as imagens<br>
        • Para detecção automática, use a aba "� Detecção Avançada" (inclui Camelot, OpenCV, Tesseract)
        """)
        manual_instructions.setStyleSheet("background-color: #e8f6f3; padding: 10px; border-radius: 5px; color: #2c3e50;")
        extraction_layout.addWidget(manual_instructions)
        
        self.tabs.addTab(extraction_tab, "📄 Seleção Manual")
        
        # Tab 2: Visualizador de tabelas
        self.image_viewer = ImageViewer()
        self.tabs.addTab(self.image_viewer, "🖼️ Visualizar Tabelas")
        
        # Tab 3: Detecção Avançada
        self.advanced_detector = AdvancedTableDetector()
        self.tabs.addTab(self.advanced_detector, "🔬 Detecção Avançada")
        
        # Tab 4: Extração com IA
        self.ai_extractor = AITableExtractorWidget()
        self.tabs.addTab(self.ai_extractor, "🤖 IA - Extração Automática")
        
        main_layout.addWidget(self.tabs)

    def update_batch_size(self, value):
        """Atualiza o tamanho do lote"""
        self.batch_size = value

    def open_pdf(self):
        """Abre um arquivo PDF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            'Abrir PDF', 
            '', 
            'PDF Files (*.pdf);;All Files (*)'
        )
        if file_path:
            self.pdf_path = file_path
            self.load_pdf()

    def load_pdf(self):
        """Inicia o carregamento progressivo do PDF"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()
        
        # Validação básica do arquivo
        try:
            file_size = os.path.getsize(self.pdf_path) / (1024 * 1024)  # MB
            if file_size > 200:  # Limite de 200MB
                reply = QMessageBox.question(
                    self, 
                    "Arquivo Grande",
                    f"O arquivo tem {file_size:.1f}MB. O carregamento pode demorar.\n\n"
                    "Deseja continuar?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao acessar arquivo: {str(e)}")
            return
        
        # Limpar dados anteriores
        self.page_images.clear()
        self.image_labels.clear()
        self.loaded_batches.clear()
        self.selections.clear()
        self.global_select_points.clear()
        
        # Limpar layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Configurar interface para carregamento
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Preparando carregamento...")
        
        # Iniciar thread de carregamento
        self.loader_thread = PDFLoaderThread(self.pdf_path, self.batch_size, dpi=150)
        self.loader_thread.progress_updated.connect(self.update_loading_progress)
        self.loader_thread.batch_loaded.connect(self.on_batch_loaded)
        self.loader_thread.loading_finished.connect(self.on_loading_finished)
        self.loader_thread.error_occurred.connect(self.on_loading_error)
        self.loader_thread.start()
    
    def update_loading_progress(self, progress, message):
        """Atualiza o progresso do carregamento"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def on_batch_loaded(self, batch_num, batch_pages):
        """Callback quando um lote de páginas é carregado"""
        self.loaded_batches[batch_num] = batch_pages
        
        # Adicionar páginas ao layout
        for page_idx, img in batch_pages:
            # Garantir que o array page_images tenha o tamanho correto
            while len(self.page_images) <= page_idx:
                self.page_images.append(None)
            
            self.page_images[page_idx] = img
            
            # Criar label para a página
            label = PDFPageLabel(img.copy(), page_idx, self)
            
            # Garantir que o array image_labels tenha o tamanho correto
            while len(self.image_labels) <= page_idx:
                self.image_labels.append(None)
            
            self.image_labels[page_idx] = label
            self.scroll_layout.addWidget(label)
    
    def on_loading_finished(self):
        """Callback quando todo o carregamento termina"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Calcular total de páginas carregadas
        total_loaded = sum(len(batch) for batch in self.loaded_batches.values())
        
        QMessageBox.information(
            self, 
            "Carregamento Concluído",
            f"PDF carregado com sucesso!\n\n"
            f"📄 Total de páginas: {total_loaded}\n"
            f"🎯 Qualidade: 150 DPI (alta qualidade)\n"
            f"📦 Carregamento por lotes: {self.batch_size} páginas por vez\n\n"
            f"✨ Agora você pode selecionar tabelas clicando em dois pontos!"
        )
    
    def on_loading_error(self, error_message):
        """Callback quando ocorre erro no carregamento"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        QMessageBox.critical(self, "Erro de Carregamento", error_message)

    def add_selection(self, selection):
        """Adiciona uma seleção de tabela"""
        self.selections.append(selection)
        page_idx1, pt1 = selection[0]
        page_idx2, pt2 = selection[1]
        
        if page_idx1 == page_idx2:
            rect = QRect(pt1, pt2).normalized()
            if self.image_labels[page_idx1]:
                self.image_labels[page_idx1].add_rect(rect, color=QColor(255, 0, 0))
        else:
            # Seleção entre páginas
            x1 = pt1.x()
            y1 = pt1.y()
            h1 = self.image_labels[page_idx1].image.height()
            rect1 = QRect(QPoint(x1, y1), QPoint(x1, h1)).normalized()

            x2 = pt2.x()
            y2 = pt2.y()
            rect2 = QRect(QPoint(x2, 0), QPoint(x2, y2)).normalized()

            if self.image_labels[page_idx1]:
                self.image_labels[page_idx1].add_rect(rect1, color=QColor(0, 0, 255))
            if self.image_labels[page_idx2]:
                self.image_labels[page_idx2].add_rect(rect2, color=QColor(0, 0, 255))

    def register_click(self, page_idx, pos):
        """Registra um clique para seleção"""
        self.global_select_points.append((page_idx, pos))
        if len(self.global_select_points) == 2:
            self.add_selection(tuple(self.global_select_points))
            self.global_select_points = []

    def save_tables(self):
        """Salva as tabelas selecionadas"""
        if not self.selections:
            QMessageBox.information(self, "Aviso", "Nenhuma tabela selecionada para salvar.")
            return
            
        out_dir = QFileDialog.getExistingDirectory(self, 'Escolher pasta para salvar tabelas')
        if not out_dir:
            return
        
        # Criar pasta 'tabelas' se não existir
        tabelas_dir = os.path.join(out_dir, 'tabelas')
        os.makedirs(tabelas_dir, exist_ok=True)
            
        pdf_base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        saved_count = 0
        
        for idx, selection in enumerate(self.selections, 1):
            page_idx1, pt1 = selection[0]
            page_idx2, pt2 = selection[1]
            
            # Verificar se as páginas foram carregadas
            if (page_idx1 >= len(self.page_images) or self.page_images[page_idx1] is None or
                page_idx2 >= len(self.page_images) or self.page_images[page_idx2] is None):
                QMessageBox.warning(
                    self, 
                    "Erro", 
                    f"Páginas da seleção {idx} ainda não foram carregadas. "
                    "Aguarde o carregamento completo."
                )
                continue
            
            if page_idx1 == page_idx2:
                rect = QRect(pt1, pt2).normalized()
                img = self.page_images[page_idx1].copy(rect)
                page_str = str(page_idx1 + 1)
            else:
                # Página de cima
                h1 = self.page_images[page_idx1].height()
                x1 = pt1.x()
                y1 = pt1.y()
                x2 = pt2.x()
                left = min(x1, x2)
                right = max(x1, x2)
                rect1 = QRect(QPoint(left, y1), QPoint(right, h1)).normalized()
                img1 = self.page_images[page_idx1].copy(rect1)
                
                # Página de baixo
                y2 = pt2.y()
                rect2 = QRect(QPoint(left, 0), QPoint(right, y2)).normalized()
                img2 = self.page_images[page_idx2].copy(rect2)
                
                w = max(img1.width(), img2.width())
                h = img1.height() + img2.height()
                result = QImage(w, h, QImage.Format_RGB888)
                result.fill(0)
                painter = QPainter(result)
                painter.drawImage(0, 0, img1)
                painter.drawImage(0, img1.height(), img2)
                painter.end()
                img = result
                page_str = f'{page_idx1 + 1}-{page_idx2 + 1}'
            
            name = f'{pdf_base}_pagina_{page_str}_tabela_{idx}.png'
            img.save(os.path.join(tabelas_dir, name))
            saved_count += 1
        
        self.selections.clear()
        for label in self.image_labels:
            if label:
                label.clear_rects()
        
        QMessageBox.information(
            self, 
            "Sucesso", 
            f"✅ {saved_count} tabela(s) salva(s) em:\n{tabelas_dir}\n\n"
            f"💡 Use a aba 'Visualizar Tabelas' para converter para JSONL!"
        )
        
        # Atualizar pasta de imagens no visualizador
        self.image_viewer.image_folder = tabelas_dir
        self.image_viewer.folder_label.setText("tabelas")
        self.image_viewer.refresh_btn.setEnabled(True)
        self.image_viewer.load_images()
    
    def open_table_folder(self):
        """Abre a pasta de tabelas"""
        tabelas_dir = 'tabelas'
        if not os.path.exists(tabelas_dir):
            QMessageBox.information(self, "Informação", "Nenhuma tabela encontrada na pasta 'tabelas'.")
            return
        
        try:
            if platform.system() == "Windows":
                os.startfile(tabelas_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", tabelas_dir])
            else:  # Linux
                subprocess.Popen(["xdg-open", tabelas_dir])
        except Exception as e:
            image_files = [f for f in os.listdir(tabelas_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            QMessageBox.information(
                self, 
                "Tabelas Extraídas", 
                f"Tabelas encontradas na pasta: {os.path.abspath(tabelas_dir)}\n\n"
                f"Total de arquivos: {len(image_files)}"
            )


def main():
    """Função principal"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo moderno
    
    # Configurar ícone da aplicação (se disponível)
    app.setApplicationName("PDF Table Extractor")
    app.setApplicationVersion("2.0")
    
    window = PDFTableExtractor()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
