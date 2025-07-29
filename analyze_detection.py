#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise da Tabela Detectada
Examina se a detecção está correta e propõe melhorias
"""

import cv2
import numpy as np
import fitz
import os

def analyze_detection_quality():
    """Analisa a qualidade da detecção atual"""
    
    print("🔍 ANÁLISE DA QUALIDADE DE DETECÇÃO")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    # Verificar se a imagem da tabela foi gerada
    table_image_path = "detector_tabela_1.png"
    
    if not os.path.exists(table_image_path):
        print("❌ Imagem da tabela não encontrada. Execute o teste anterior primeiro.")
        return
    
    try:
        # Carregar a tabela detectada
        table_img = cv2.imread(table_image_path)
        print(f"📋 Tabela detectada: {table_img.shape}")
        
        # Carregar a página original para comparação
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        original_img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        original_img = cv2.cvtColor(original_img, cv2.COLOR_RGB2BGR)
        
        print(f"📄 Página original: {original_img.shape}")
        
        # Análise da tabela detectada
        print(f"\n🔍 ANÁLISE DA TABELA DETECTADA:")
        print("-" * 35)
        
        # 1. Verificar se há estrutura tabular
        gray_table = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
        
        # Detectar linhas horizontais e verticais
        binary = cv2.adaptiveThreshold(gray_table, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Kernels para detectar linhas
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 80))
        
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
        
        # Contar linhas
        h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        h_count = len([c for c in h_contours if cv2.contourArea(c) > 100])
        v_count = len([c for c in v_contours if cv2.contourArea(c) > 100])
        
        print(f"📏 Linhas horizontais: {h_count}")
        print(f"📏 Linhas verticais: {v_count}")
        
        # 2. Verificar densidade de texto
        text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = 0
        for contour in text_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if 20 <= area <= 8000 and 3 <= w <= 300 and 3 <= h <= 80:
                text_regions += 1
        
        print(f"📝 Regiões de texto: {text_regions}")
        
        # 3. Análise visual
        table_area = table_img.shape[0] * table_img.shape[1]
        
        print(f"📐 Área da tabela: {table_area} pixels")
        print(f"📐 Dimensões: {table_img.shape[1]}x{table_img.shape[0]}")
        
        # 4. Avaliação da qualidade
        quality_score = 0
        quality_issues = []
        
        if h_count >= 3 and v_count >= 2:
            quality_score += 30
            print("✅ Estrutura de linhas adequada")
        else:
            quality_issues.append("Poucas linhas detectadas")
            print("⚠️ Estrutura de linhas inadequada")
        
        if text_regions >= 10:
            quality_score += 40
            print("✅ Densidade de texto alta")
        elif text_regions >= 5:
            quality_score += 20
            print("⚠️ Densidade de texto média")
        else:
            quality_issues.append("Pouco texto detectado")
            print("❌ Densidade de texto baixa")
        
        if 50000 <= table_area <= 500000:
            quality_score += 20
            print("✅ Tamanho apropriado")
        else:
            quality_issues.append("Tamanho inadequado")
            print("⚠️ Tamanho pode ser inadequado")
        
        aspect_ratio = table_img.shape[1] / table_img.shape[0]
        if 1.5 <= aspect_ratio <= 10:
            quality_score += 10
            print("✅ Proporção adequada")
        else:
            quality_issues.append("Proporção inadequada")
            print("⚠️ Proporção pode ser inadequada")
        
        print(f"\n📊 QUALIDADE GERAL: {quality_score}%")
        
        if quality_score >= 80:
            print("🎉 Detecção de alta qualidade!")
        elif quality_score >= 60:
            print("✅ Detecção aceitável")
        elif quality_score >= 40:
            print("⚠️ Detecção questionável")
        else:
            print("❌ Detecção de baixa qualidade")
        
        if quality_issues:
            print(f"\n⚠️ Problemas identificados:")
            for issue in quality_issues:
                print(f"   • {issue}")
        
        # 5. Sugestões de melhoria
        print(f"\n💡 SUGESTÕES DE MELHORIA:")
        print("-" * 25)
        
        if h_count < 3 or v_count < 2:
            print("🔧 Ajustar detecção de linhas:")
            print("   • Reduzir kernel de morfologia")
            print("   • Experimentar diferentes thresholds")
            print("   • Usar Hough Line Transform")
        
        if text_regions < 5:
            print("🔧 Melhorar detecção de texto:")
            print("   • Ajustar filtros de contorno")
            print("   • Usar diferentes métodos de threshold")
            print("   • Considerar OCR para validação")
        
        if table_area < 50000:
            print("🔧 Aumentar área de detecção:")
            print("   • Relaxar critérios de tamanho mínimo")
            print("   • Melhorar detecção de contornos")
        
        if table_area > 500000:
            print("🔧 Refinar área de detecção:")
            print("   • Melhorar algoritmo de refinamento de bbox")
            print("   • Detectar bordas da tabela com mais precisão")
        
        # 6. Criar imagem de análise
        analysis_img = table_img.copy()
        
        # Sobrepor linhas detectadas
        analysis_img = cv2.addWeighted(analysis_img, 0.7, cv2.cvtColor(h_lines, cv2.COLOR_GRAY2BGR), 0.3, 0)
        analysis_img = cv2.addWeighted(analysis_img, 0.7, cv2.cvtColor(v_lines, cv2.COLOR_GRAY2BGR), 0.3, 0)
        
        # Marcar regiões de texto
        for contour in text_contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if 20 <= area <= 8000 and 3 <= w <= 300 and 3 <= h <= 80:
                cv2.rectangle(analysis_img, (x, y), (x+w, y+h), (0, 255, 0), 1)
        
        cv2.imwrite("analise_tabela_detectada.png", analysis_img)
        print(f"\n💾 Análise visual salva: analise_tabela_detectada.png")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_detection_quality()
