#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Comparativo de Detecção
Compara detecção entre páginas aleatórias vs páginas específicas
"""

import os
from opencv_table_detector import OpenCVTableDetector

def test_detection_comparison():
    """Compara detecção entre diferentes conjuntos de páginas"""
    
    print("🔍 TESTE COMPARATIVO DE DETECÇÃO")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        # Teste 1: Páginas aleatórias (do teste anterior)
        print("\n📋 TESTE 1: Páginas Aleatórias")
        print("-" * 40)
        
        random_pages = [100, 200, 300, 500, 750]  # Páginas do teste anterior
        
        detector1 = OpenCVTableDetector(pdf_path, pages=",".join(map(str, random_pages)))
        results1 = detector1.run()
        
        print(f"📄 Páginas testadas: {random_pages}")
        print(f"🔍 Tabelas detectadas: {len(results1)}")
        
        for i, result in enumerate(results1):
            page = result.get('page', 'N/A')
            conf = result.get('confidence', 0)
            print(f"   Tabela {i+1}: Página {page}, Confiança {conf:.2f}")
        
        # Teste 2: Páginas específicas (páginas conhecidas)
        print("\n📋 TESTE 2: Páginas Específicas")
        print("-" * 40)
        
        specific_pages = [97, 148, 185, 186]  # Páginas que sabemos ter tabelas
        
        detector2 = OpenCVTableDetector(pdf_path, pages=",".join(map(str, specific_pages)))
        results2 = detector2.run()
        
        print(f"📄 Páginas testadas: {specific_pages}")
        print(f"🔍 Tabelas detectadas: {len(results2)}")
        
        for i, result in enumerate(results2):
            page = result.get('page', 'N/A')
            conf = result.get('confidence', 0)
            bbox = result.get('bbox', 'N/A')
            print(f"   Tabela {i+1}: Página {page}, Confiança {conf:.2f}, BBox {bbox}")
        
        # Teste 3: Varredura de páginas do meio do livro
        print("\n📋 TESTE 3: Páginas do Meio (Alta Densidade)")
        print("-" * 40)
        
        middle_pages = list(range(140, 200, 10))  # Páginas 140, 150, 160, etc.
        
        detector3 = OpenCVTableDetector(pdf_path, pages=",".join(map(str, middle_pages)))
        results3 = detector3.run()
        
        print(f"📄 Páginas testadas: {middle_pages}")
        print(f"🔍 Tabelas detectadas: {len(results3)}")
        
        for i, result in enumerate(results3):
            page = result.get('page', 'N/A')
            conf = result.get('confidence', 0)
            print(f"   Tabela {i+1}: Página {page}, Confiança {conf:.2f}")
        
        # Análise comparativa
        print("\n📊 ANÁLISE COMPARATIVA")
        print("=" * 40)
        
        total_pages_1 = len(random_pages)
        total_pages_2 = len(specific_pages)
        total_pages_3 = len(middle_pages)
        
        rate_1 = len(results1) / total_pages_1 if total_pages_1 > 0 else 0
        rate_2 = len(results2) / total_pages_2 if total_pages_2 > 0 else 0
        rate_3 = len(results3) / total_pages_3 if total_pages_3 > 0 else 0
        
        print(f"Taxa de detecção - Aleatórias: {rate_1:.2f} tabelas/página")
        print(f"Taxa de detecção - Específicas: {rate_2:.2f} tabelas/página")
        print(f"Taxa de detecção - Meio do livro: {rate_3:.2f} tabelas/página")
        
        # Confiança média
        if results1:
            avg_conf_1 = sum(r.get('confidence', 0) for r in results1) / len(results1)
            print(f"Confiança média - Aleatórias: {avg_conf_1:.2f}")
        
        if results2:
            avg_conf_2 = sum(r.get('confidence', 0) for r in results2) / len(results2)
            print(f"Confiança média - Específicas: {avg_conf_2:.2f}")
        
        if results3:
            avg_conf_3 = sum(r.get('confidence', 0) for r in results3) / len(results3)
            print(f"Confiança média - Meio do livro: {avg_conf_3:.2f}")
        
        print(f"\n💡 CONCLUSÕES:")
        print("1. Se páginas específicas têm mais tabelas = algoritmo funciona")
        print("2. Se páginas aleatórias têm poucas = problema de distribuição")
        print("3. Taxa ideal: > 0.5 tabelas/página para livros técnicos")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detection_comparison()
