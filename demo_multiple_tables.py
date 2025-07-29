#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demonstração do Sistema de Múltiplas Passadas
Mostra como o sistema funciona para extrair múltiplas tabelas
"""

import os
from multi_pass_detector import MultiPassDetectorWidget

def demo_multiple_tables():
    """Demonstra o sistema com páginas que têm múltiplas tabelas"""
    
    print("🎯 DEMONSTRAÇÃO - SISTEMA DE MÚLTIPLAS PASSADAS")
    print("=" * 60)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    print("📄 PDF de teste:", os.path.basename(pdf_path))
    print("📋 Caso de uso: Páginas com múltiplas estruturas tabulares")
    print()
    
    # Teste 1: Páginas conhecidas (185, 186)
    print("🔍 TESTE 1: Páginas com estruturas conhecidas")
    print("-" * 50)
    
    results_test1 = MultiPassDetectorWidget.detect_with_multiple_passes(
        pdf_path,
        pages="185,186",
        max_passes=3
    )
    
    print(f"\n📊 Resultados Teste 1:")
    print(f"   Total de tabelas: {len(results_test1)}")
    
    for i, table in enumerate(results_test1):
        page = table.get('page')
        pass_num = table.get('detection_pass')
        conf = table.get('confidence', 0)
        method = table.get('detection_method', 'N/A')
        multi_id = table.get('multi_pass_id', 'N/A')
        
        print(f"   📋 Tabela {i+1}:")
        print(f"      • Página: {page}")
        print(f"      • Passada: {pass_num}")
        print(f"      • Confiança: {conf:.3f}")
        print(f"      • Método: {method}")
        print(f"      • ID: {multi_id}")
        print()
    
    # Teste 2: Página individual com potencial para múltiplas tabelas
    print("\n🔍 TESTE 2: Análise intensiva de página única")
    print("-" * 50)
    
    results_test2 = MultiPassDetectorWidget.detect_with_multiple_passes(
        pdf_path,
        pages="148",  # Página que sabemos ter tabela perfeita
        max_passes=3
    )
    
    print(f"\n📊 Resultados Teste 2:")
    print(f"   Total de tabelas: {len(results_test2)}")
    
    for i, table in enumerate(results_test2):
        page = table.get('page')
        pass_num = table.get('detection_pass')
        conf = table.get('confidence', 0)
        bbox = table.get('bbox')
        
        print(f"   📋 Tabela {i+1}:")
        print(f"      • Página: {page}")
        print(f"      • Passada: {pass_num}")
        print(f"      • Confiança: {conf:.3f}")
        print(f"      • BBox: {bbox}")
        print()
    
    # Análise comparativa
    print("\n📈 ANÁLISE COMPARATIVA")
    print("=" * 40)
    
    total_tables = len(results_test1) + len(results_test2)
    pages_tested = [185, 186, 148]
    
    print(f"📊 Estatísticas:")
    print(f"   • Total de tabelas extraídas: {total_tables}")
    print(f"   • Páginas testadas: {len(pages_tested)}")
    print(f"   • Taxa média: {total_tables / len(pages_tested):.2f} tabelas/página")
    
    # Verificar se houve múltiplas passadas
    multi_pass_tables = [t for t in results_test1 + results_test2 if t.get('detection_pass', 1) > 1]
    
    if multi_pass_tables:
        print(f"   • ✅ Múltiplas passadas detectaram: {len(multi_pass_tables)} tabelas adicionais")
        print("   • 🎯 Sistema funcionando: encontrou tabelas que teriam sido perdidas!")
    else:
        print("   • ℹ️ Não foram necessárias múltiplas passadas neste teste")
        print("   • 💡 Isso é normal - significa que o OpenCV padrão já encontrou todas as tabelas")
    
    print(f"\n🎉 DEMONSTRAÇÃO CONCLUÍDA")
    print("💡 Para usar no aplicativo:")
    print("   1. Abra o PDF Scanner")
    print("   2. Selecione 'OpenCV Multi-Passadas'")
    print("   3. Digite as páginas desejadas")
    print("   4. Execute a detecção")
    print("   5. O sistema automaticamente fará múltiplas passadas se necessário")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    demo_multiple_tables()
    app.quit()
