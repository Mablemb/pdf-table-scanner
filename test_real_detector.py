#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Final - Detector Real
Testa o detector real com as páginas que sabemos ter tabelas
"""

import os
from opencv_table_detector import OpenCVTableDetector

def test_real_detector():
    """Testa o detector real com páginas conhecidas"""
    
    print("🎯 TESTE FINAL - DETECTOR REAL")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        # Páginas que confirmamos ter tabelas
        pages_with_tables = "97,148,185,186"
        
        print(f"📄 Testando páginas: {pages_with_tables}")
        print("-" * 40)
        
        # Usar o detector real com as configurações atuais
        detector = OpenCVTableDetector(pdf_path, pages=pages_with_tables, min_table_area=500)
        
        # Executar detecção usando método run()
        import time
        from PyQt5.QtCore import pyqtSignal, QObject
        
        class TestReceiver(QObject):
            def __init__(self):
                super().__init__()
                self.results = []
                self.completed = False
                
            def receive_tables(self, tables):
                self.results = tables
                self.completed = True
                print(f"📊 RESULTADOS RECEBIDOS: {len(tables)} tabelas")
                
                for i, table in enumerate(tables):
                    page = table.get('page', 'N/A')
                    conf = table.get('confidence', 0)
                    bbox = table.get('bbox', 'N/A')
                    method = table.get('detection_method', 'N/A')
                    
                    print(f"   Tabela {i+1}:")
                    print(f"      Página: {page}")
                    print(f"      Confiança: {conf:.3f}")
                    print(f"      BBox: {bbox}")
                    print(f"      Método: {method}")
                    print()
            
            def receive_progress(self, progress, message):
                print(f"   {progress}% - {message}")
            
            def receive_error(self, error):
                print(f"❌ Erro: {error}")
                self.completed = True
        
        # Configurar receptor de sinais
        receiver = TestReceiver()
        detector.tables_detected.connect(receiver.receive_tables)
        detector.progress_updated.connect(receiver.receive_progress)
        detector.error_occurred.connect(receiver.receive_error)
        
        print(f"🚀 Iniciando detecção...")
        
        # Executar em thread separada
        detector.run()
        
        # Aguardar alguns segundos para processamento
        max_wait = 30
        waited = 0
        while not receiver.completed and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
        
        if not receiver.completed:
            print(f"⏰ Timeout após {max_wait}s")
            return
        
        print(f"\n🎯 ANÁLISE FINAL:")
        print(f"   Total de tabelas: {len(receiver.results)}")
        
        if len(receiver.results) > 0:
            avg_confidence = sum(t.get('confidence', 0) for t in receiver.results) / len(receiver.results)
            print(f"   Confiança média: {avg_confidence:.3f}")
            
            pages_detected = set(t.get('page') for t in receiver.results)
            print(f"   Páginas com tabelas: {sorted(pages_detected)}")
            
            print(f"\n✅ SUCESSO! Detector funcionando corretamente!")
        else:
            print(f"\n❌ PROBLEMA: Nenhuma tabela detectada")
            print("Verificar se há problema na configuração ou nos sinais Qt")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Inicializar aplicação Qt para sinais
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    test_real_detector()
    app.quit()
