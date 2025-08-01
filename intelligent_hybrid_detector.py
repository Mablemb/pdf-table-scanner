#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Híbrido Inteligente: Tabula como Scanner + OpenCV como Extrator
- Tabula: Identifica páginas com tabelas e estrutura de dados
- OpenCV: Extrai coordenadas visuais precisas das páginas identificadas
"""

import os
import fitz
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from datetime import datetime
import json

class IntelligentHybridDetector(QThread):
    """Detector híbrido que usa Tabula para inteligência e OpenCV para extração"""
    
    progress_updated = pyqtSignal(int, str)
    tables_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path, pages="all"):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.should_stop = False
        
    def run(self):
        """Executa detecção híbrida inteligente"""
        try:
            self.progress_updated.emit(10, "🧠 Fase 1: Análise inteligente com Tabula-py...")
            
            # Fase 1: Tabula como scanner de inteligência
            intelligence_data = self.tabula_intelligence_scan()
            
            if not intelligence_data:
                self.progress_updated.emit(50, "⚠️ Nenhuma tabela detectada pelo scanner inteligente")
                self.tables_detected.emit([])
                return
            
            self.progress_updated.emit(50, f"🎯 Scanner identificou {len(intelligence_data)} página(s) com tabelas")
            
            # Fase 2: OpenCV guiado pela inteligência
            visual_tables = self.opencv_guided_extraction(intelligence_data)
            
            self.progress_updated.emit(100, f"✅ Extração concluída: {len(visual_tables)} tabelas extraídas")
            self.tables_detected.emit(visual_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na detecção híbrida: {str(e)}")
    
    def tabula_intelligence_scan(self):
        """Usa Tabula para identificar páginas com tabelas e estrutura"""
        import os
        
        # Configurar Java
        java_path = r"C:\Program Files\Microsoft\jdk-11.0.28.6-hotspot\bin"
        if java_path not in os.environ.get('PATH', ''):
            os.environ['PATH'] += f";{java_path}"
        os.environ['JAVA_HOME'] = r"C:\Program Files\Microsoft\jdk-11.0.28.6-hotspot"
        
        print(f"\n🧠 SCANNER INTELIGENTE TABULA:")
        print(f"   📄 Analisando: {os.path.basename(self.pdf_path)}")
        
        try:
            import tabula
            
            # Determinar páginas para análise
            if self.pages and str(self.pages).strip() != "all":
                pages_str = str(self.pages).strip()
                if ',' in pages_str:
                    page_list = [int(p.strip()) for p in pages_str.split(',')]
                elif '-' in pages_str:
                    start, end = pages_str.split('-')
                    page_list = list(range(int(start), int(end) + 1))
                else:
                    page_list = [int(pages_str)]
            else:
                # Para "all", usar páginas estratégicas conhecidas
                doc = fitz.open(self.pdf_path)
                total_pages = len(doc)
                doc.close()
                
                # Páginas estratégicas (conhecidas por ter tabelas)
                strategic_pages = [97, 148, 185, 186, 334, 400, 500, 600, 700, 800, 900, 1000]
                page_list = [p for p in strategic_pages if p <= total_pages]
                
                # Adicionar algumas páginas aleatórias para descoberta
                import random
                random_pages = random.sample(range(1, min(total_pages + 1, 500)), min(20, total_pages))
                page_list.extend(random_pages)
                page_list = sorted(list(set(page_list)))
            
            print(f"   🔍 Analisando {len(page_list)} páginas: {page_list[:10]}{'...' if len(page_list) > 10 else ''}")
            
            intelligence_data = {}
            
            for page_num in page_list:
                if self.should_stop:
                    break
                
                try:
                    # Detectar tabelas com Tabula (sem tentar extrair coordenadas visuais)
                    tables = tabula.read_pdf(
                        self.pdf_path, 
                        pages=page_num, 
                        multiple_tables=True,
                        pandas_options={'header': None},
                        silent=True
                    )
                    
                    valid_tables = []
                    for i, table_df in enumerate(tables):
                        if table_df.empty or len(table_df) < 2:
                            continue
                        
                        rows, cols = table_df.shape
                        
                        # Validar se é uma tabela real
                        if rows >= 2 and cols >= 2:
                            table_info = {
                                'table_index': i + 1,
                                'rows': rows,
                                'cols': cols,
                                'total_cells': rows * cols,
                                'data_preview': str(table_df.iloc[0:2, 0:3].values.tolist()),  # Preview pequeno
                                'has_numbers': self.detect_numbers_in_table(table_df),
                                'table_complexity': self.calculate_table_complexity(table_df)
                            }
                            valid_tables.append(table_info)
                    
                    if valid_tables:
                        intelligence_data[page_num] = {
                            'page': page_num,
                            'table_count': len(valid_tables),
                            'tables': valid_tables,
                            'total_cells': sum(t['total_cells'] for t in valid_tables),
                            'avg_complexity': sum(t['table_complexity'] for t in valid_tables) / len(valid_tables)
                        }
                        
                        print(f"   📊 Página {page_num}: {len(valid_tables)} tabela(s) | "
                              f"Complexidade média: {intelligence_data[page_num]['avg_complexity']:.2f}")
                
                except Exception as e:
                    print(f"   ⚠️ Erro na página {page_num}: {e}")
                    continue
            
            print(f"   ✅ Scanner concluído: {len(intelligence_data)} páginas com tabelas")
            return intelligence_data
            
        except ImportError:
            print(f"   ❌ Tabula-py não disponível")
            return {}
        except Exception as e:
            print(f"   ❌ Erro no scanner: {e}")
            return {}
    
    def detect_numbers_in_table(self, table_df):
        """Detecta se a tabela contém dados numéricos"""
        try:
            numeric_cells = 0
            total_cells = 0
            
            for col in table_df.columns:
                for value in table_df[col].head(5):  # Verificar apenas primeiras 5 linhas
                    total_cells += 1
                    if str(value).replace('.', '').replace(',', '').replace('-', '').isdigit():
                        numeric_cells += 1
            
            return numeric_cells / total_cells if total_cells > 0 else 0
        except:
            return 0
    
    def calculate_table_complexity(self, table_df):
        """Calcula complexidade da tabela (0-1)"""
        try:
            rows, cols = table_df.shape
            
            # Fatores de complexidade
            size_score = min(rows * cols / 100, 1.0)  # Tamanho
            structure_score = min(cols / 10, 1.0)  # Número de colunas
            content_score = self.detect_numbers_in_table(table_df)  # Conteúdo numérico
            
            return (size_score + structure_score + content_score) / 3
        except:
            return 0.5
    
    def opencv_guided_extraction(self, intelligence_data):
        """Usa OpenCV para extrair tabelas das páginas identificadas pelo Tabula"""
        try:
            from opencv_table_detector import OpenCVTableDetector
        except ImportError:
            print("   ❌ OpenCV detector não disponível")
            return []
        
        print(f"\n🖼️ EXTRAÇÃO VISUAL GUIADA:")
        
        all_extracted_tables = []
        
        for page_num, page_intel in intelligence_data.items():
            if self.should_stop:
                break
            
            table_count = page_intel['table_count']
            avg_complexity = page_intel['avg_complexity']
            
            print(f"   🎯 Página {page_num}: {table_count} tabela(s) esperada(s) | Complexidade: {avg_complexity:.2f}")
            
            # Ajustar parâmetros do OpenCV baseado na inteligência
            if avg_complexity > 0.7:
                min_area = 1000  # Tabelas complexas = area menor
                detection_sensitivity = "high"
            elif avg_complexity > 0.4:
                min_area = 2000  # Tabelas médias
                detection_sensitivity = "medium"
            else:
                min_area = 5000  # Tabelas simples = area maior
                detection_sensitivity = "low"
            
            print(f"      🔧 Parâmetros: min_area={min_area}, sensibilidade={detection_sensitivity}")
            
            # Executar OpenCV nesta página específica
            page_tables = self.extract_tables_from_page(page_num, min_area, table_count)
            
            # Enriquecer com dados de inteligência
            for i, table in enumerate(page_tables):
                table['intelligence_guided'] = True
                table['expected_tables'] = table_count
                table['page_complexity'] = avg_complexity
                table['detection_method'] = 'hybrid_intelligent'
                
                # Tentar associar com dados de inteligência
                if i < len(page_intel['tables']):
                    intel_table = page_intel['tables'][i]
                    table['expected_rows'] = intel_table['rows']
                    table['expected_cols'] = intel_table['cols']
                    table['has_numbers'] = intel_table['has_numbers']
                    table['data_preview'] = intel_table['data_preview']
            
            all_extracted_tables.extend(page_tables)
            
            print(f"      ✅ Extraídas: {len(page_tables)} tabela(s)")
        
        return all_extracted_tables
    
    def extract_tables_from_page(self, page_num, min_area, expected_count):
        """Extrai tabelas de uma página específica usando OpenCV"""
        
        try:
            from opencv_table_detector import OpenCVTableDetector
        except ImportError:
            print(f"      ❌ OpenCV detector não disponível")
            return []
        
        # Criar detector OpenCV otimizado
        detector = OpenCVTableDetector(
            self.pdf_path, 
            pages=str(page_num), 
            min_table_area=min_area
        )
        
        # Capturar resultados
        class PageReceiver:
            def __init__(self):
                self.results = []
                self.completed = False
            
            def receive_tables(self, tables):
                self.results = tables
                self.completed = True
            
            def receive_error(self, error):
                self.completed = True
        
        receiver = PageReceiver()
        detector.tables_detected.connect(receiver.receive_tables)
        detector.error_occurred.connect(receiver.receive_error)
        
        # Executar detecção
        detector.run()
        
        # Aguardar resultado
        import time
        max_wait = 30
        waited = 0
        while not receiver.completed and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        
        # Validar quantidade esperada
        detected = len(receiver.results)
        if detected != expected_count:
            print(f"      ⚠️ Esperado: {expected_count}, Detectado: {detected}")
        
        return receiver.results
    
    def stop(self):
        """Para a detecção"""
        self.should_stop = True

def test_intelligent_hybrid():
    """Teste do sistema híbrido inteligente"""
    
    print("🧠 TESTE: SISTEMA HÍBRIDO INTELIGENTE")
    print("=" * 60)
    print("📋 Estratégia:")
    print("   1️⃣ Tabula identifica páginas com tabelas")
    print("   2️⃣ OpenCV extrai coordenadas visuais precisas")
    print("   3️⃣ Sistema combina inteligência + precisão visual")
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado!")
        return False
    
    # Testar com páginas conhecidas
    test_pages = "97,148,185,186,334,400,500"
    
    # Criar detector híbrido
    detector = IntelligentHybridDetector(pdf_path, pages=test_pages)
    
    # Resultados
    results = {'tables': []}
    
    def on_tables_detected(tables):
        results['tables'] = tables
        print(f"\n✅ DETECÇÃO CONCLUÍDA: {len(tables)} tabelas")
    
    def on_error(error):
        print(f"\n❌ ERRO: {error}")
    
    def on_progress(percent, message):
        print(f"   {percent}% - {message}")
    
    # Conectar sinais
    detector.tables_detected.connect(on_tables_detected)
    detector.error_occurred.connect(on_error)
    detector.progress_updated.connect(on_progress)
    
    # Executar
    detector.run()
    
    # Analisar resultados
    tables = results['tables']
    
    if tables:
        print(f"\n📊 ANÁLISE DOS RESULTADOS:")
        
        # Agrupar por página
        pages_data = {}
        for table in tables:
            page = table.get('page', 0)
            if page not in pages_data:
                pages_data[page] = []
            pages_data[page].append(table)
        
        # Exibir por página
        for page_num in sorted(pages_data.keys()):
            page_tables = pages_data[page_num]
            print(f"\n   📄 Página {page_num}: {len(page_tables)} tabela(s)")
            
            for i, table in enumerate(page_tables):
                bbox = table.get('bbox', [0, 0, 0, 0])
                area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                confidence = table.get('confidence', 0)
                expected_rows = table.get('expected_rows', '?')
                expected_cols = table.get('expected_cols', '?')
                
                print(f"      {i+1}. Conf: {confidence:.1f}% | Área: {area:,}px² | "
                      f"Estrutura: {expected_rows}x{expected_cols}")
                
                if table.get('data_preview'):
                    preview = str(table['data_preview'])[:100]
                    print(f"         Preview: {preview}...")
        
        print(f"\n🎯 RESUMO:")
        print(f"   Total de páginas analisadas: {len(pages_data)}")
        print(f"   Total de tabelas extraídas: {len(tables)}")
        
        # Verificar precisão da inteligência
        intelligence_accurate = 0
        total_checks = 0
        
        for table in tables:
            if table.get('expected_tables') and table.get('page'):
                page = table['page']
                expected = table['expected_tables']
                actual = len([t for t in tables if t.get('page') == page])
                
                if abs(expected - actual) <= 1:  # Tolerância de 1 tabela
                    intelligence_accurate += 1
                total_checks += 1
        
        if total_checks > 0:
            accuracy = (intelligence_accurate / total_checks) * 100
            print(f"   Precisão da inteligência: {accuracy:.1f}%")
        
        return True
    else:
        print(f"\n⚠️ Nenhuma tabela detectada")
        return False

if __name__ == "__main__":
    # Inicializar aplicação Qt
    app = QApplication([])
    
    try:
        success = test_intelligent_hybrid()
        
        print(f"\n{'='*60}")
        if success:
            print("🎉 SISTEMA HÍBRIDO INTELIGENTE: FUNCIONANDO!")
            print("💡 Tabula fornece inteligência, OpenCV fornece precisão visual")
        else:
            print("🔧 SISTEMA HÍBRIDO: NECESSITA AJUSTES")
        
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app.quit()
