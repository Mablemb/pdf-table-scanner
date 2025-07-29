#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug das Coordenadas de Corte
Investiga se há problema entre detecção e extração
"""

import cv2
import numpy as np
import fitz
import os

def debug_coordinates():
    """Debug das coordenadas para encontrar o problema"""
    
    print("🔍 DEBUG - COORDENADAS DE CORTE")
    print("=" * 40)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"📐 Imagem original: {img.shape} (H={img.shape[0]}, W={img.shape[1]})")
        
        # Detector
        detector = OpenCVTableDetector(pdf_path, pages="1")
        
        # Encontrar candidatos
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        if not table_contours:
            print("❌ Nenhum candidato encontrado")
            return
        
        # Primeiro candidato
        bbox_original = table_contours[0]['bbox']
        print(f"📋 Bbox original detectado: {bbox_original}")
        
        # Validar estrutura
        is_valid, struct_conf = detector.validate_table_structure(img, bbox_original)
        print(f"✅ Estrutura válida: {is_valid} ({struct_conf:.1%})")
        
        if is_valid:
            # Analisar conteúdo (que também refina o bbox)
            has_content, content_conf, bbox_refinado = detector.analyze_table_content(img, bbox_original)
            print(f"✅ Conteúdo válido: {has_content} ({content_conf:.1%})")
            print(f"🔧 Bbox refinado: {bbox_refinado}")
            
            # Comparar bboxes
            x1, y1, w1, h1 = bbox_original
            x2, y2, w2, h2 = bbox_refinado
            
            print(f"\n📊 COMPARAÇÃO DE COORDENADAS:")
            print(f"   Original:  x={x1:4d}, y={y1:4d}, w={w1:4d}, h={h1:4d}")
            print(f"   Refinado:  x={x2:4d}, y={y2:4d}, w={w2:4d}, h={h2:4d}")
            print(f"   Diferença: Δx={x2-x1:+3d}, Δy={y2-y1:+3d}, Δw={w2-w1:+3d}, Δh={h2-h1:+3d}")
            
            # Testar extração com ambos os bboxes
            print(f"\n🔪 TESTE DE EXTRAÇÃO:")
            
            # Bbox original
            try:
                roi_original = img[y1:y1+h1, x1:x1+w1]
                print(f"   ROI Original: {roi_original.shape} - ✅ OK")
                cv2.imwrite("debug_roi_original.png", roi_original)
            except Exception as e:
                print(f"   ROI Original: ❌ ERRO - {e}")
            
            # Bbox refinado
            try:
                roi_refinado = img[y2:y2+h2, x2:x2+w2]
                print(f"   ROI Refinado: {roi_refinado.shape} - ✅ OK")
                cv2.imwrite("debug_roi_refinado.png", roi_refinado)
            except Exception as e:
                print(f"   ROI Refinado: ❌ ERRO - {e}")
            
            # Criar imagem com marcações para visualização
            img_debug = img.copy()
            
            # Desenhar bbox original em vermelho
            cv2.rectangle(img_debug, (x1, y1), (x1+w1, y1+h1), (0, 0, 255), 3)
            cv2.putText(img_debug, "ORIGINAL", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Desenhar bbox refinado em verde
            cv2.rectangle(img_debug, (x2, y2), (x2+w2, y2+h2), (0, 255, 0), 3)
            cv2.putText(img_debug, "REFINADO", (x2, y2-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Salvar imagem de debug
            cv2.imwrite("debug_coordenadas.png", img_debug)
            print(f"\n💾 Imagens salvas:")
            print(f"   - debug_coordenadas.png (visualização dos bboxes)")
            print(f"   - debug_roi_original.png (recorte original)")
            print(f"   - debug_roi_refinado.png (recorte refinado)")
            
            # Verificar se as coordenadas estão dentro dos limites
            print(f"\n🔍 VALIDAÇÃO DE LIMITES:")
            print(f"   Imagem: {img.shape[1]}x{img.shape[0]} (WxH)")
            
            def check_bounds(name, x, y, w, h):
                valid = True
                if x < 0:
                    print(f"   {name}: ❌ x={x} < 0")
                    valid = False
                if y < 0:
                    print(f"   {name}: ❌ y={y} < 0")
                    valid = False
                if x + w > img.shape[1]:
                    print(f"   {name}: ❌ x+w={x+w} > largura={img.shape[1]}")
                    valid = False
                if y + h > img.shape[0]:
                    print(f"   {name}: ❌ y+h={y+h} > altura={img.shape[0]}")
                    valid = False
                if valid:
                    print(f"   {name}: ✅ Coordenadas válidas")
                return valid
            
            check_bounds("Original", x1, y1, w1, h1)
            check_bounds("Refinado", x2, y2, w2, h2)
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_coordinates()
