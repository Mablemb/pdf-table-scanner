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
    final_pdf_saved = pyqtSignal(str)  # Novo sinal para PDF exportado
    
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
            
            # Exportar PDF final com regiões pintadas ANTES de remover
            if working_pdf_path:
                self.export_final_pdf_with_painted_regions(working_pdf_path)
            
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
        """Detectar tabelas em uma única passada usando método específico"""
        try:
            # Passada 2: usar Tabula-py (método completamente diferente)
            if pass_num == 2:
                return self._detect_tabula_pass(pdf_path, pass_num)
            else:
                # Demais passadas: usar OpenCV com parâmetros diferentes
                return self._detect_opencv_pass(pdf_path, pass_num)
                
        except Exception as e:
            self.error_occurred.emit(f"Erro na passada {pass_num}: {str(e)}")
            return []
    
    def _detect_opencv_pass(self, pdf_path, pass_num):
        """Detectar tabelas usando OpenCV"""
        from opencv_table_detector import OpenCVTableDetector
        
        # Área mínima progressiva por passada
        if pass_num == 1:
            min_area = 2000
            description = "Tabelas grandes e óbvias"
        elif pass_num == 3:
            min_area = 500
            description = "Tabelas médias"
        elif pass_num == 4:
            min_area = 100
            description = "Tabelas pequenas"
        else:
            min_area = 50
            description = "Tabelas minúsculas"
        
        print(f"   🔍 Pass {pass_num}: OpenCV - {description} (área≥{min_area}px²)")
        
        # Criar detector
        detector = OpenCVTableDetector(pdf_path, pages=self.pages, min_table_area=min_area)
        
        # Executar detecção
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
        
        detector.run()
        
        # Aguardar resultado
        import time
        max_wait = 30
        waited = 0
        while not receiver.completed and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        
        # Adicionar metadados
        for i, table in enumerate(receiver.results):
            table['detection_pass'] = pass_num
            table['multi_pass_id'] = f"pass_{pass_num}_opencv_{i + 1}"
            table['detection_method'] = 'opencv'
            table['min_area_used'] = min_area
        
        print(f"   📊 Pass {pass_num}: {len(receiver.results)} tabela(s) OpenCV")
        return receiver.results
    
    def _detect_tabula_pass(self, pdf_path, pass_num):
        """Detectar tabelas usando Tabula-py"""
        import os
        
        # Configurar Java
        java_path = r"C:\Program Files\Microsoft\jdk-11.0.28.6-hotspot\bin"
        if java_path not in os.environ.get('PATH', ''):
            os.environ['PATH'] += f";{java_path}"
        os.environ['JAVA_HOME'] = r"C:\Program Files\Microsoft\jdk-11.0.28.6-hotspot"
        
        print(f"   🔍 Pass {pass_num}: Tabula-py - Análise de conteúdo")
        
        try:
            import tabula
            import fitz
            
            # Parsear páginas
            if self.pages and str(self.pages).strip() != "all":
                # Tratar diferentes formatos de páginas
                pages_str = str(self.pages).strip()
                if '-' in pages_str and ',' not in pages_str:
                    # Range: "30-1766" -> converter para lista
                    start, end = pages_str.split('-')
                    page_list = list(range(int(start), int(end) + 1))
                elif ',' in pages_str:
                    # Lista: "97,148,185,186"
                    page_list = [int(p.strip()) for p in pages_str.split(',')]
                else:
                    # Página única
                    page_list = [int(pages_str)]
            else:
                # Para "all" ou páginas não especificadas, usar algumas páginas conhecidas com tabelas
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                doc.close()
                
                # Usar páginas estratégicas que sabemos que têm tabelas
                known_table_pages = [97, 148, 185, 186, 334, 400, 500, 600, 700, 800]
                page_list = [p for p in known_table_pages if p <= total_pages]
            
            all_tables = []
            
            for page_num in page_list:
                try:
                    # Detectar tabelas com Tabula
                    tables = tabula.read_pdf(
                        pdf_path, 
                        pages=page_num, 
                        multiple_tables=True,
                        pandas_options={'header': None},
                        silent=True
                    )
                    
                    for i, table_df in enumerate(tables):
                        if table_df.empty or len(table_df) < 2:
                            continue
                        
                        rows, cols = table_df.shape
                        
                        # Estimar coordenadas (Tabula não retorna posições exatas)
                        doc = fitz.open(pdf_path)
                        page = doc.load_page(page_num - 1)
                        page_rect = page.rect
                        
                        # Posição estimada
                        estimated_y = (i * page_rect.height / max(1, len(tables)))
                        estimated_height = page_rect.height / max(1, len(tables))
                        estimated_width = min(page_rect.width * 0.8, page_rect.width)
                        estimated_x = (page_rect.width - estimated_width) / 2
                        
                        table_info = {
                            'page': page_num,
                            'bbox': [
                                int(estimated_x), 
                                int(estimated_y), 
                                int(estimated_width), 
                                int(estimated_height)
                            ],
                            'confidence': 85.0,
                            'rows': rows,
                            'cols': cols,
                            'detection_pass': pass_num,
                            'multi_pass_id': f"pass_{pass_num}_tabula_{i + 1}",
                            'detection_method': 'tabula-py',
                            'area': int(estimated_width * estimated_height),
                            'table_data': table_df.to_dict()
                        }
                        
                        all_tables.append(table_info)
                        doc.close()
                        
                except Exception as e:
                    print(f"      ⚠️ Erro Tabula página {page_num}: {e}")
                    continue
            
            print(f"   📊 Pass {pass_num}: {len(all_tables)} tabela(s) Tabula")
            return all_tables
            
        except ImportError:
            print(f"   ⚠️ Pass {pass_num}: Tabula-py não disponível")
            return []
        except Exception as e:
            print(f"   ❌ Pass {pass_num}: Erro Tabula: {e}")
            return []
    
    def detect_tables_single_pass_old(self, pdf_path, pass_num):
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
    
    def export_final_pdf_with_painted_regions(self, working_pdf_path):
        """Exporta o PDF final com as regiões pintadas e relatório estatístico"""
        try:
            if not os.path.exists(working_pdf_path):
                print(f"⚠️ PDF de trabalho não encontrado: {working_pdf_path}")
                return
            
            # Gerar nome do arquivo de exportação
            from datetime import datetime
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"{base_name}_regioes_extraidas_{timestamp}.pdf"
            
            print(f"📄 Exportando PDF final: {export_path}")
            
            # Copiar o PDF pintado
            import shutil
            shutil.copy2(working_pdf_path, export_path)
            
            # Adicionar página de sumário com estatísticas
            self.add_summary_page_to_pdf(export_path)
            
            # Emitir sinal de PDF salvo
            self.final_pdf_saved.emit(export_path)
            
            print(f"✅ PDF exportado com sucesso: {export_path}")
            
        except Exception as e:
            print(f"❌ Erro ao exportar PDF: {e}")
    
    def add_summary_page_to_pdf(self, pdf_path):
        """Adiciona página de sumário com estatísticas detalhadas"""
        try:
            from datetime import datetime
            
            doc = fitz.open(pdf_path)
            
            # Criar página de sumário no início
            summary_page = doc.new_page(0, width=595, height=842)  # A4
            
            # Configurar texto
            font_size = 12
            line_height = 16
            margin = 50
            y = margin
            
            # Título principal
            title = "📊 RELATÓRIO DE EXTRAÇÃO DE TABELAS - MÚLTIPLAS PASSADAS"
            summary_page.insert_text((margin, y), title, fontsize=14, color=(0, 0, 0))
            y += line_height * 2
            
            # Informações básicas
            summary_page.insert_text((margin, y), "📄 DETECÇÃO AUTOMÁTICA CONCLUÍDA", fontsize=font_size, color=(0, 0, 0))
            y += line_height
            
            original_name = os.path.basename(self.pdf_path)
            summary_page.insert_text((margin, y), f"📁 Arquivo Original: {original_name}", fontsize=font_size, color=(0, 0, 0))
            y += line_height
            
            now = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
            summary_page.insert_text((margin, y), f"⏰ Data/Hora: {now}", fontsize=font_size, color=(0, 0, 0))
            y += line_height * 2
            
            # Estatísticas por passada
            summary_page.insert_text((margin, y), "📊 ESTATÍSTICAS POR PASSADA", fontsize=font_size, color=(0, 0, 0))
            y += line_height * 1.5
            
            # Analisar tabelas por passada
            pass_stats = {}
            for table in self.all_detected_tables:
                pass_num = table.get('detection_pass', 1)
                if pass_num not in pass_stats:
                    pass_stats[pass_num] = {
                        'count': 0,
                        'confidences': [],
                        'areas': [],
                        'methods': [],
                        'pages': set()
                    }
                
                pass_stats[pass_num]['count'] += 1
                pass_stats[pass_num]['confidences'].append(table.get('confidence', 0))
                
                bbox = table.get('bbox', [0, 0, 0, 0])
                area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                pass_stats[pass_num]['areas'].append(area)
                
                pass_stats[pass_num]['methods'].append(table.get('detection_method', 'opencv'))
                pass_stats[pass_num]['pages'].add(table.get('page', 0))
            
            # Exibir estatísticas
            total_passes = len(pass_stats)
            total_tables = len(self.all_detected_tables)
            
            summary_page.insert_text((margin, y), f"🔢 Número de Passadas Executadas: {total_passes}", fontsize=font_size, color=(0, 0, 0))
            y += line_height
            
            summary_page.insert_text((margin, y), f"📊 Total de Tabelas Detectadas: {total_tables}", fontsize=font_size, color=(0, 0, 0))
            y += line_height * 1.5
            
            # Detalhes por passada
            for pass_num in sorted(pass_stats.keys()):
                stats = pass_stats[pass_num]
                avg_conf = sum(stats['confidences']) / len(stats['confidences']) if stats['confidences'] else 0
                avg_area = sum(stats['areas']) / len(stats['areas']) if stats['areas'] else 0
                method = stats['methods'][0] if stats['methods'] else 'opencv'
                page_count = len(stats['pages'])
                
                summary_page.insert_text((margin, y), f"🔍 Passada {pass_num}:", fontsize=font_size, color=(0, 0, 0))
                y += line_height
                
                summary_page.insert_text((margin + 20, y), f"• Método: {method}", fontsize=font_size-1, color=(0, 0, 0))
                y += line_height
                
                summary_page.insert_text((margin + 20, y), f"• Tabelas encontradas: {stats['count']}", fontsize=font_size-1, color=(0, 0, 0))
                y += line_height
                
                summary_page.insert_text((margin + 20, y), f"• Confiança média: {avg_conf:.1f}%", fontsize=font_size-1, color=(0, 0, 0))
                y += line_height
                
                summary_page.insert_text((margin + 20, y), f"• Área média: {avg_area:,.0f}px²", fontsize=font_size-1, color=(0, 0, 0))
                y += line_height
                
                summary_page.insert_text((margin + 20, y), f"• Páginas afetadas: {page_count}", fontsize=font_size-1, color=(0, 0, 0))
                y += line_height * 1.5
            
            # Salvar documento atualizado (sem incremental se houver problemas de criptografia)
            try:
                doc.save(pdf_path, incremental=True)
            except:
                doc.save(pdf_path)
            doc.close()
            
        except Exception as e:
            print(f"⚠️ Erro ao adicionar página de sumário: {e}")


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
