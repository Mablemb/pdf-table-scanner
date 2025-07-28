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
    QGroupBox, QFormLayout, QTextEdit, QCheckBox
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

import openai


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
            self.progress_updated.emit(10, "Preparando imagem...")
            base64_image = self.encode_image(self.image_path)
            self.progress_updated.emit(30, "Enviando para OpenAI...")
            # Configurar client
            client = openai.OpenAI(api_key=self.api_key)
            # Chamada conforme docs https://platform.openai.com/docs/guides/images-vision?api-mode=responses&format=base64-encoded#analyze-images
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
            # A resposta já vem como texto JSON
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

        # Área de scroll para o PDF
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        extraction_layout.addWidget(self.scroll)
        
        # Instruções
        instructions = QLabel("""
        <b>Como usar:</b><br>
        1. Clique em "Escolher PDF" para selecionar um arquivo<br>
        2. Aguarde o carregamento progressivo por lotes<br>
        3. Clique em dois pontos para selecionar uma tabela (mesmo página ou entre páginas)<br>
        4. Clique em "Salvar Tabelas Selecionadas" para extrair as imagens<br>
        5. Use a aba "Visualizar Tabelas" para converter para JSONL
        """)
        instructions.setStyleSheet("background-color: #ecf0f1; padding: 10px; border-radius: 5px;")
        extraction_layout.addWidget(instructions)
        
        self.tabs.addTab(extraction_tab, "📄 Extração de PDF")
        
        # Tab 2: Visualizador de tabelas
        self.image_viewer = ImageViewer()
        self.tabs.addTab(self.image_viewer, "🖼️ Visualizar Tabelas")
        
        # Tab 3: Extração com IA
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
