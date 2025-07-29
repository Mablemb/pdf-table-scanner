#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug do Candidato Perfeito
Investiga por que o candidato perfeito (página 148) está sendo rejeitado
"""

import cv2
import numpy as np
import fitz
import os

def debug_perfect_candidate():
    """Analisa detalhadamente o candidato perfeito da página 148"""
    
    print("🎯 DEBUG DO CANDIDATO PERFEITO")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        page_num = 148
        
        print(f"📋 ANALISANDO PÁGINA {page_num} EM DETALHES:")
        print("-" * 40)
        
        # Renderizar página
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"📐 Dimensões da página: {img.shape}")
        
        # Criar detector com parâmetros atuais
        detector = OpenCVTableDetector(pdf_path, pages=str(page_num), min_table_area=500)
        
        # PASSO 1: Detecção de linhas
        print(f"\n🔍 PASSO 1: DETECÇÃO DE LINHAS")
        table_structure, h_lines, v_lines = detector.detect_lines(img)
        
        h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"   Linhas H: {len(h_contours)} (significativas: {len([c for c in h_contours if cv2.contourArea(c) > 100])})")
        print(f"   Linhas V: {len(v_contours)} (significativas: {len([c for c in v_contours if cv2.contourArea(c) > 100])})")
        
        # PASSO 2: Encontrar contornos
        print(f"\n🔍 PASSO 2: CONTORNOS DE TABELA")
        table_contours = detector.find_table_contours(table_structure)
        
        print(f"   Candidatos encontrados: {len(table_contours)}")
        
        for i, table_info in enumerate(table_contours):
            bbox = table_info['bbox']
            area = table_info['area']
            
            print(f"\n   📊 CANDIDATO {i+1}:")
            print(f"      BBox: {bbox}")
            print(f"      Área: {area}")
            
            x, y, w, h = bbox
            
            # PASSO 3: Validação de estrutura
            print(f"\n🔍 PASSO 3: VALIDAÇÃO DE ESTRUTURA")
            
            roi = img[y:y+h, x:x+w]
            structure_result = detector.validate_table_structure(img, bbox)
            structure_score = structure_result[1] if len(structure_result) > 1 else 0
            
            print(f"      Resultado estrutura: {structure_result}")
            print(f"      Score de estrutura: {structure_score}")
            
            # PASSO 4: Análise de conteúdo
            print(f"\n🔍 PASSO 4: ANÁLISE DE CONTEÚDO")
            
            content_result = detector.analyze_table_content(img, bbox)
            content_score = content_result[1] if len(content_result) > 1 else 0
            
            print(f"      Resultado conteúdo: {content_result}")
            print(f"      Score de conteúdo: {content_score}")
            
            # PASSO 5: Score final
            print(f"\n🔍 PASSO 5: SCORE FINAL")
            
            # Verificar os critérios exatos do detector
            min_structure_score = 0.2  # Valor atual do código
            min_content_score = 0.25   # Valor atual do código
            
            structure_pass = structure_score >= min_structure_score
            content_pass = content_score >= min_content_score
            
            print(f"      Estrutura >= {min_structure_score}: {structure_score} -> {'✅ PASS' if structure_pass else '❌ FAIL'}")
            print(f"      Conteúdo >= {min_content_score}: {content_score} -> {'✅ PASS' if content_pass else '❌ FAIL'}")
            
            final_score = (structure_score + content_score) / 2
            print(f"      Score final: {final_score}")
            
            # PASSO 6: Decisão final
            print(f"\n🎯 DECISÃO FINAL:")
            
            if structure_pass and content_pass:
                print(f"      ✅ CANDIDATO APROVADO!")
                print(f"      Seria incluído nos resultados finais")
            else:
                print(f"      ❌ CANDIDATO REJEITADO!")
                if not structure_pass:
                    print(f"         Motivo: Score de estrutura muito baixo ({structure_score} < {min_structure_score})")
                if not content_pass:
                    print(f"         Motivo: Score de conteúdo muito baixo ({content_score} < {min_content_score})")
                    
                print(f"\n💡 SUGESTÕES DE CORREÇÃO:")
                if not structure_pass:
                    print(f"         - Reduzir min_structure_score para {structure_score - 0.05:.2f}")
                if not content_pass:
                    print(f"         - Reduzir min_content_score para {content_score - 0.05:.2f}")
        
        doc.close()
        
        print(f"\n🔧 PRÓXIMO PASSO:")
        print("Se o candidato foi rejeitado, ajustar os thresholds de validação")
        print("para permitir que candidatos perfeitos sejam aprovados!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_perfect_candidate()
