#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector de tabelas usando Tabula-py como alternativa ao OpenCV
"""

import os
import tempfile
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import tabula
import pandas as pd

class TabulaTableDetector(QThread):
    """
    Detector de tabelas usando Tabula-py
    Complementa o OpenCV para detectar tabelas que podem ter sido perdidas
    """
    
    tables_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, pdf_path, pages=None, min_table_area=100):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.min_table_area = min_table_area
        
    def run(self):
        """Executar detecção usando Tabula-py"""
        try:
            self.progress_updated.emit(10, "Iniciando detecção com Tabula-py...")
            
            # Converter páginas para formato do Tabula
            pages_list = self._parse_pages()
            
            self.progress_updated.emit(20, f"Processando {len(pages_list)} páginas...")
            
            all_tables = []
            
            for i, page_num in enumerate(pages_list):
                try:
                    self.progress_updated.emit(
                        20 + int(60 * i / len(pages_list)), 
                        f"Detectando tabelas na página {page_num}..."
                    )
                    
                    # Detectar tabelas na página usando Tabula
                    page_tables = self._detect_tables_on_page(page_num)
                    all_tables.extend(page_tables)
                    
                except Exception as e:
                    print(f"⚠️ Erro na página {page_num}: {str(e)}")
                    continue
            
            self.progress_updated.emit(90, f"Processando {len(all_tables)} tabelas detectadas...")
            
            # Filtrar tabelas muito pequenas
            filtered_tables = self._filter_tables(all_tables)
            
            self.progress_updated.emit(100, f"Concluído! {len(filtered_tables)} tabelas válidas")
            
            self.tables_detected.emit(filtered_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro no Tabula: {str(e)}")
    
    def _parse_pages(self):
        """Converter string de páginas para lista"""
        if not self.pages or self.pages.lower() == "all":
            # Se não especificou páginas, tentar detectar automaticamente
            return list(range(1, 21))  # Primeiras 20 páginas para teste
        
        pages_list = []
        for part in self.pages.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages_list.extend(range(start, end + 1))
            else:
                pages_list.append(int(part))
        
        return pages_list
    
    def _detect_tables_on_page(self, page_num):
        """Detectar tabelas em uma página específica usando Tabula"""
        try:
            # Usar Tabula para extrair tabelas
            # stream=True: para tabelas sem bordas bem definidas
            # lattice=False: não depender apenas de linhas
            dfs = tabula.read_pdf(
                self.pdf_path, 
                pages=page_num,
                multiple_tables=True,
                stream=True,
                lattice=False,
                guess=True,
                pandas_options={'header': None}
            )
            
            tables = []
            
            for i, df in enumerate(dfs):
                if df is None or df.empty:
                    continue
                
                # Estimar área da tabela baseada no conteúdo
                rows, cols = df.shape
                
                # Filtrar tabelas muito pequenas (menos de 2x2)
                if rows < 2 or cols < 2:
                    continue
                
                # Estimar área aproximada (não temos coordenadas exatas do Tabula)
                # Usar número de células como proxy para área
                estimated_area = rows * cols * 100  # Fator arbitrário
                
                if estimated_area < self.min_table_area:
                    continue
                
                # Criar estrutura compatível com OpenCV detector
                table_info = {
                    'page': page_num,
                    'bbox': [0, 0, cols * 50, rows * 20],  # Coordenadas estimadas
                    'confidence': 0.8,  # Confiança padrão para Tabula
                    'area': estimated_area,
                    'rows': rows,
                    'cols': cols,
                    'detector': 'tabula',
                    'table_data': df,  # Dados reais da tabela
                    'table_id': f"tabula_p{page_num}_t{i}",
                    'content_sample': self._get_content_sample(df)
                }
                
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            print(f"⚠️ Erro detectando tabelas na página {page_num}: {str(e)}")
            return []
    
    def _get_content_sample(self, df):
        """Obter amostra do conteúdo da tabela para análise"""
        try:
            # Pegar as primeiras células não-vazias
            sample = []
            for i in range(min(3, df.shape[0])):
                for j in range(min(3, df.shape[1])):
                    cell = str(df.iloc[i, j])
                    if cell and cell != 'nan' and len(cell.strip()) > 0:
                        sample.append(cell.strip())
            
            return sample[:6]  # Máximo 6 células de amostra
            
        except:
            return []
    
    def _filter_tables(self, tables):
        """Filtrar e validar tabelas detectadas"""
        filtered = []
        
        for table in tables:
            # Validações básicas
            if table['rows'] < 2 or table['cols'] < 2:
                continue
            
            # Verificar se tem conteúdo significativo
            sample = table.get('content_sample', [])
            if len(sample) < 2:  # Pelo menos 2 células com conteúdo
                continue
            
            # Verificar se não é apenas cabeçalho repetido
            unique_content = set(sample)
            if len(unique_content) < 2:  # Muito repetitivo
                continue
            
            filtered.append(table)
        
        return filtered

def test_tabula_detector():
    """Teste rápido do detector Tabula"""
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication([])
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    print("🔬 TESTE TABULA DETECTOR")
    print("=" * 40)
    
    detector = TabulaTableDetector(pdf_path, pages="97,148", min_table_area=100)
    
    results = {'completed': False, 'tables': []}
    
    def on_progress(progress, message):
        print(f"   {progress:3d}% - {message}")
    
    def on_tables(tables):
        results['tables'] = tables
        results['completed'] = True
        print(f"\n✅ {len(tables)} tabelas detectadas pelo Tabula!")
        for i, table in enumerate(tables):
            print(f"   {i+1}. Página {table['page']} | {table['rows']}x{table['cols']} | Área: {table['area']}")
            print(f"      Amostra: {table['content_sample'][:3]}")
    
    def on_error(error):
        print(f"❌ Erro: {error}")
        results['completed'] = True
    
    detector.progress_updated.connect(on_progress)
    detector.tables_detected.connect(on_tables)
    detector.error_occurred.connect(on_error)
    
    detector.start()
    
    # Aguardar
    import time
    while not results['completed']:
        app.processEvents()
        time.sleep(0.1)
    
    print("🎯 Teste concluído!")

if __name__ == "__main__":
    test_tabula_detector()
