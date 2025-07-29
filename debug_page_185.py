#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Múltiplas Tabelas - Página 185
Investiga por que apenas 1 das 2 tabelas da página 185 é retornada
"""

import cv2
import numpy as np
import fitz
import os

def debug_page_185():
    """Debug específico da página 185 que tem 2 tabelas"""
    
    print("🔍 DEBUG PÁGINA 185 - MÚLTIPLAS TABELAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        page_num = 185
        
        print(f"📄 ANALISANDO PÁGINA {page_num} EM DETALHES:")
        print("-" * 40)
        
        # Renderizar página
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Criar detector
        detector = OpenCVTableDetector(pdf_path, pages=str(page_num), min_table_area=500)
        
        # PASSO 1: Encontrar contornos
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        print(f"🔍 CANDIDATOS ENCONTRADOS: {len(table_contours)}")
        
        validated_tables = []
        
        for i, table_info in enumerate(table_contours):
            bbox = table_info['bbox']
            
            print(f"\n📊 PROCESSANDO CANDIDATO {i+1}:")
            print(f"   BBox: {bbox}")
            
            # VALIDAÇÃO 1: Estrutura
            print(f"   🔍 VALIDAÇÃO 1: ESTRUTURA")
            is_valid_structure, structure_confidence = detector.validate_table_structure(img, bbox)
            
            print(f"      is_valid: {is_valid_structure}")
            print(f"      score: {structure_confidence}")
            
            if not is_valid_structure:
                print(f"      ❌ REJEITADO: Estrutura inválida")
                continue
            
            # VALIDAÇÃO 2: Conteúdo
            print(f"   🔍 VALIDAÇÃO 2: CONTEÚDO")
            has_valid_content, content_confidence, refined_bbox = detector.analyze_table_content(img, bbox)
            
            print(f"      has_content: {has_valid_content}")
            print(f"      score: {content_confidence}")
            print(f"      bbox_refinado: {refined_bbox}")
            
            if not has_valid_content:
                print(f"      ❌ REJEITADO: Conteúdo inválido")
                continue
            
            # SCORE FINAL
            final_confidence = (structure_confidence * 0.6 + content_confidence * 0.4)
            print(f"   📊 SCORE FINAL: {final_confidence}")
            
            if final_confidence >= 0.25:
                print(f"      ✅ APROVADO")
                validated_tables.append({
                    'bbox': refined_bbox,
                    'confidence': final_confidence,
                    'structure_score': structure_confidence,
                    'content_score': content_confidence
                })
            else:
                print(f"      ❌ REJEITADO: Score {final_confidence} < 0.25")
        
        print(f"\n🎯 RESULTADO FINAL:")
        print(f"   Candidatos processados: {len(table_contours)}")
        print(f"   Tabelas validadas: {len(validated_tables)}")
        
        for i, table in enumerate(validated_tables):
            print(f"   Tabela {i+1}: Score {table['confidence']:.3f}, BBox {table['bbox']}")
        
        if len(validated_tables) != len(table_contours):
            print(f"\n❌ PROBLEMA CONFIRMADO:")
            print(f"Algumas tabelas estão sendo rejeitadas na validação!")
            print(f"Solução: Ajustar critérios de validação ou implementar múltiplas passadas")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_page_185()
