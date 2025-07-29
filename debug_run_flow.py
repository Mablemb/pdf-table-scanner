#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Fluxo Completo do Run()
Acompanha exatamente o que acontece no método run() do detector
"""

import cv2
import numpy as np
import fitz
import os

def debug_run_flow():
    """Simula exatamente o fluxo do método run() para página 148"""
    
    print("🎯 DEBUG FLUXO COMPLETO DO RUN()")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        page_num = 147  # Índice 0-based para página 148
        
        print(f"📋 SIMULANDO RUN() PARA PÁGINA {page_num + 1}:")
        print("-" * 40)
        
        # Simular início do run()
        doc = fitz.open(pdf_path)
        
        # Renderizar página como imagem (igual ao run())
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para formato OpenCV (igual ao run())
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"📐 Imagem carregada: {img.shape}")
        
        # Criar detector (igual ao run())
        detector = OpenCVTableDetector(pdf_path, pages=str(page_num + 1), min_table_area=500)
        
        # Detectar estrutura de tabelas (igual ao run())
        print(f"\n🔍 PASSO 1: DETECTAR ESTRUTURA")
        table_structure, _, _ = detector.detect_lines(img)
        
        # Encontrar contornos de tabelas (igual ao run())
        print(f"\n🔍 PASSO 2: ENCONTRAR CONTORNOS")
        table_contours = detector.find_table_contours(table_structure)
        
        print(f"   Candidatos encontrados: {len(table_contours)}")
        
        # Processar cada tabela encontrada (igual ao run())
        print(f"\n🔍 PASSO 3: PROCESSAR CANDIDATOS")
        validated_tables = []
        
        for j, table_info in enumerate(table_contours):
            bbox = table_info['bbox']
            
            print(f"\n   📊 PROCESSANDO CANDIDATO {j+1}:")
            print(f"      BBox original: {bbox}")
            
            # Validação 1: Estrutura de linhas (igual ao run())
            print(f"\n      🔍 VALIDAÇÃO 1: ESTRUTURA")
            is_valid_structure, structure_confidence = detector.validate_table_structure(img, bbox)
            
            print(f"         Resultado: is_valid={is_valid_structure}, score={structure_confidence}")
            
            if not is_valid_structure:
                print(f"         ❌ REJEITADO: Estrutura inválida")
                continue  # Pular se não tem estrutura válida
            
            print(f"         ✅ PASSOU: Estrutura válida")
            
            # Validação 2: Conteúdo (igual ao run())
            print(f"\n      🔍 VALIDAÇÃO 2: CONTEÚDO")
            has_valid_content, content_confidence, refined_bbox = detector.analyze_table_content(img, bbox)
            
            print(f"         Resultado: has_content={has_valid_content}, score={content_confidence}")
            print(f"         BBox refinado: {refined_bbox}")
            
            if not has_valid_content:
                print(f"         ❌ REJEITADO: Conteúdo inválido")
                continue  # Pular se não tem conteúdo válido
            
            print(f"         ✅ PASSOU: Conteúdo válido")
            
            # Usar bbox refinado (igual ao run())
            final_bbox = refined_bbox
            
            print(f"\n      🔍 PROCESSAMENTO FINAL")
            print(f"         BBox final: {final_bbox}")
            
            # Detectar células (igual ao run())
            intersection_points = detector.detect_table_cells(img, final_bbox)
            print(f"         Pontos de interseção: {len(intersection_points) if intersection_points else 0}")
            
            # Calcular dimensões (igual ao run())
            estimated_rows = max(2, int(structure_confidence * 10))
            estimated_cols = max(2, int(content_confidence * 8))
            
            print(f"         Linhas estimadas: {estimated_rows}")
            print(f"         Colunas estimadas: {estimated_cols}")
            
            # Score final combinado (igual ao run())
            final_confidence = (structure_confidence * 0.6 + content_confidence * 0.4)
            
            print(f"         Score final: {final_confidence}")
            print(f"         Threshold: 0.25")
            
            # Verificar threshold final (igual ao run())
            if final_confidence >= 0.25:
                print(f"         ✅ APROVADO: Score >= 0.25")
                
                table_data = {
                    'page': page_num + 1,
                    'table_index': len(validated_tables),
                    'bbox': final_bbox,
                    'area': final_bbox[2] * final_bbox[3],
                    'aspect_ratio': final_bbox[2] / final_bbox[3],
                    'estimated_rows': estimated_rows,
                    'estimated_cols': estimated_cols,
                    'intersection_points': intersection_points,
                    'detection_method': 'opencv_intelligent_detection_v2',
                    'confidence': final_confidence,
                    'structure_score': structure_confidence,
                    'content_score': content_confidence,
                    'validation_passed': True,
                    'bbox_refined': True
                }
                
                validated_tables.append(table_data)
                print(f"         💾 ADICIONADO à lista de tabelas validadas")
            else:
                print(f"         ❌ REJEITADO: Score {final_confidence} < 0.25")
        
        print(f"\n🎯 RESULTADO FINAL:")
        print(f"   Tabelas validadas: {len(validated_tables)}")
        
        for i, table in enumerate(validated_tables):
            print(f"   Tabela {i+1}: Página {table['page']}, Confiança {table['confidence']:.3f}")
        
        doc.close()
        
        if len(validated_tables) == 0:
            print(f"\n❌ PROBLEMA IDENTIFICADO:")
            print("Candidato perfeito está sendo perdido em alguma validação!")
        else:
            print(f"\n✅ SUCESSO:")
            print("Candidato perfeito está sendo processado corretamente!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_run_flow()
