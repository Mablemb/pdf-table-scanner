#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Múltiplas Passadas para Detecção de Tabelas
Implementa extração iterativa com "pintura branca" das regiões já extraídas
"""

import fitz
import cv2
import numpy as np
import os
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

class MultiPassTableDetector(QThread):
    """Detector de tabelas com múltiplas passadas"""
    
    progress_updated = pyqtSignal(int, str)
    tables_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path, pages="all", max_passes=5):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.max_passes = max_passes
        self.should_stop = False
        self.all_detected_tables = []
        
    def run(self):
        """Executa detecção com múltiplas passadas"""
        try:
            self.progress_updated.emit(5, "Iniciando detecção com múltiplas passadas...")
            
            # Criar cópia de trabalho do PDF
            working_pdf_path = self.create_working_copy()
            
            total_tables = 0
            
            for pass_num in range(1, self.max_passes + 1):
                if self.should_stop:
                    break
                
                self.progress_updated.emit(
                    5 + (pass_num - 1) * 18, 
                    f"Passada {pass_num}/{self.max_passes} - Detectando tabelas..."
                )
                
                # Detectar tabelas na cópia atual
                pass_tables = self.detect_tables_single_pass(working_pdf_path, pass_num)
                
                if not pass_tables:
                    self.progress_updated.emit(
                        5 + pass_num * 18,
                        f"Passada {pass_num}: Nenhuma nova tabela encontrada. Finalizando."
                    )
                    break
                
                # Adicionar à lista total
                self.all_detected_tables.extend(pass_tables)
                total_tables += len(pass_tables)
                
                self.progress_updated.emit(
                    5 + pass_num * 18,
                    f"Passada {pass_num}: {len(pass_tables)} tabela(s) encontrada(s)"
                )
                
                # "Pintar de branco" as regiões extraídas
                working_pdf_path = self.paint_extracted_regions_white(
                    working_pdf_path, pass_tables, pass_num
                )
                
                self.progress_updated.emit(
                    10 + pass_num * 18,
                    f"Passada {pass_num}: Regiões extraídas pintadas de branco"
                )
            
            # Limpar arquivo temporário
            if os.path.exists(working_pdf_path) and working_pdf_path != self.pdf_path:
                os.remove(working_pdf_path)
            
            self.progress_updated.emit(
                100, 
                f"Detecção concluída! {total_tables} tabela(s) encontrada(s) em {pass_num} passada(s)"
            )
            
            self.tables_detected.emit(self.all_detected_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na detecção multi-passada: {str(e)}")
    
    def create_working_copy(self):
        """Cria uma cópia de trabalho do PDF"""
        try:
            base_name = os.path.splitext(self.pdf_path)[0]
            working_path = f"{base_name}_working_copy.pdf"
            
            # Copiar PDF original
            doc = fitz.open(self.pdf_path)
            doc.save(working_path)
            doc.close()
            
            return working_path
            
        except Exception as e:
            self.error_occurred.emit(f"Erro ao criar cópia de trabalho: {str(e)}")
            return self.pdf_path
    
    def detect_tables_single_pass(self, pdf_path, pass_num):
        """Detecta tabelas em uma única passada"""
        try:
            from opencv_table_detector import OpenCVTableDetector
            
            # Criar detector para esta passada
            detector = OpenCVTableDetector(pdf_path, pages=self.pages, min_table_area=500)
            
            # Configurar sinais para capturar resultados
            detected_tables = []
            
            class PassReceiver:
                def __init__(self):
                    self.results = []
                    self.completed = False
                
                def receive_tables(self, tables):
                    self.results = tables
                    self.completed = True
                
                def receive_error(self, error):
                    self.completed = True
            
            receiver = PassReceiver()
            detector.tables_detected.connect(receiver.receive_tables)
            detector.error_occurred.connect(receiver.receive_error)
            
            # Executar detecção
            detector.run()
            
            # Aguardar conclusão
            import time
            max_wait = 30
            waited = 0
            while not receiver.completed and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1
            
            # Adicionar identificador da passada
            for table in receiver.results:
                table['detection_pass'] = pass_num
                table['multi_pass_id'] = f"pass_{pass_num}_table_{len(detected_tables) + 1}"
            
            return receiver.results
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na passada {pass_num}: {str(e)}")
            return []
    
    def paint_extracted_regions_white(self, pdf_path, extracted_tables, pass_num):
        """Pinta de branco as regiões das tabelas extraídas"""
        try:
            output_path = f"{os.path.splitext(pdf_path)[0]}_pass_{pass_num + 1}.pdf"
            
            doc = fitz.open(pdf_path)
            
            for table in extracted_tables:
                page_num = table['page'] - 1  # Converter para índice 0
                bbox = table['bbox']
                
                # Carregar página
                page = doc.load_page(page_num)
                
                # Criar retângulo branco para cobrir a tabela
                x, y, w, h = bbox
                rect = fitz.Rect(x, y, x + w, y + h)
                
                # Adicionar retângulo branco
                page.draw_rect(rect, color=None, fill=(1, 1, 1), width=0)
                
                # Adicionar texto indicativo (opcional)
                text_rect = fitz.Rect(x, y, x + min(w, 200), y + 20)
                page.insert_textbox(
                    text_rect,
                    f"[TABELA EXTRAÍDA - PASSADA {pass_num}]",
                    fontsize=8,
                    color=(0.5, 0.5, 0.5)
                )
            
            # Salvar PDF modificado
            doc.save(output_path)
            doc.close()
            
            # Remover arquivo anterior se não for o original
            if os.path.exists(pdf_path) and pdf_path != self.pdf_path:
                os.remove(pdf_path)
            
            return output_path
            
        except Exception as e:
            self.error_occurred.emit(f"Erro ao pintar regiões: {str(e)}")
            return pdf_path
    
    def stop(self):
        """Para a detecção"""
        self.should_stop = True

class MultiPassDetectorWidget:
    """Widget para integração com o aplicativo principal"""
    
    @staticmethod
    def detect_with_multiple_passes(pdf_path, pages="all", max_passes=5):
        """Método estático para detecção com múltiplas passadas"""
        
        print("🔄 SISTEMA DE MÚLTIPLAS PASSADAS")
        print("=" * 50)
        print(f"📄 PDF: {os.path.basename(pdf_path)}")
        print(f"📄 Páginas: {pages}")
        print(f"🔄 Máximo de passadas: {max_passes}")
        
        detector = MultiPassTableDetector(pdf_path, pages, max_passes)
        
        # Conectar sinais para debug
        detector.progress_updated.connect(lambda p, m: print(f"   {p}% - {m}"))
        detector.error_occurred.connect(lambda e: print(f"❌ Erro: {e}"))
        
        # Executar
        detector.run()
        
        return detector.all_detected_tables

# Teste da funcionalidade
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if os.path.exists(pdf_path):
        # Testar com página que tem múltiplas tabelas
        results = MultiPassDetectorWidget.detect_with_multiple_passes(
            pdf_path, 
            pages="185,186",  # Páginas conhecidas
            max_passes=3
        )
        
        print(f"\n🎯 RESULTADOS FINAIS:")
        print(f"   Total de tabelas: {len(results)}")
        
        for i, table in enumerate(results):
            pass_num = table.get('detection_pass', '?')
            page = table.get('page', '?')
            conf = table.get('confidence', 0)
            multi_id = table.get('multi_pass_id', '?')
            
            print(f"   Tabela {i+1}: Página {page}, Passada {pass_num}, "
                  f"Confiança {conf:.3f}, ID: {multi_id}")
    else:
        print("❌ PDF não encontrado")
    
    app.quit()
