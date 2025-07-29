#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Rápido de Páginas Específicas
Testa apenas as páginas que sabemos ter tabelas
"""

import os
from opencv_table_detector import OpenCVTableDetector

def test_known_table_pages():
    """Testa páginas que sabemos ter tabelas"""
    
    print("🔍 TESTE PÁGINAS COM TABELAS CONHECIDAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        # Páginas que acabamos de confirmar ter tabelas
        target_pages = [97, 148, 185, 186]
        
        print(f"📄 Testando páginas: {target_pages}")
        
        # Vamos testar uma página por vez para evitar travamento
        total_found = 0
        
        for page_num in target_pages:
            print(f"\n📋 Testando página {page_num}...")
            
            detector = OpenCVTableDetector(pdf_path, pages=str(page_num))
            results = detector.run()
            
            page_tables = len(results) if results else 0
            total_found += page_tables
            
            print(f"✅ Página {page_num}: {page_tables} tabela(s) detectada(s)")
            
            if results:
                for i, result in enumerate(results):
                    conf = result.get('confidence', 0)
                    bbox = result.get('bbox', 'N/A')
                    print(f"   Tabela {i+1}: Confiança {conf:.2f}, BBox {bbox}")
        
        print(f"\n📊 RESUMO FINAL:")
        print(f"Total de páginas testadas: {len(target_pages)}")
        print(f"Total de tabelas encontradas: {total_found}")
        print(f"Taxa de detecção: {total_found/len(target_pages):.2f} tabelas/página")
        
        if total_found >= 4:  # Esperamos pelo menos 1 tabela por página
            print("✅ SUCESSO: Algoritmo está funcionando bem!")
            print("💡 O problema anterior pode ter sido:")
            print("   - Páginas escolhidas não tinham tabelas")
            print("   - Processamento muito lento para muitas páginas")
        else:
            print("⚠️ ALERTA: Detecção abaixo do esperado")
            print("💡 Possíveis causas:")
            print("   - Algoritmo muito restritivo")
            print("   - Critérios de validação muito rigorosos")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_known_table_pages()
