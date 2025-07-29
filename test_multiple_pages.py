#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Abrangente - Múltiplas Páginas
Verifica se conseguimos detectar mais tabelas no PDF
"""

import cv2
import numpy as np
import fitz
import os

def test_multiple_pages():
    """Testa detecção em múltiplas páginas"""
    
    print("🔍 TESTE ABRANGENTE - MÚLTIPLAS PÁGINAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"📄 PDF: {total_pages} páginas")
        
        # Testar primeiras 5 páginas
        pages_to_test = min(5, total_pages)
        
        total_detected = 0
        
        for page_num in range(pages_to_test):
            print(f"\n📋 PÁGINA {page_num + 1}:")
            print("-" * 30)
            
            # Renderizar página
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            
            # Converter para OpenCV
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            print(f"📐 Dimensões: {img.shape}")
            
            # Criar detector
            detector = OpenCVTableDetector(pdf_path, pages=str(page_num + 1), min_table_area=1000)
            
            # Detectar estrutura
            table_structure, _, _ = detector.detect_lines(img)
            table_contours = detector.find_table_contours(table_structure)
            
            print(f"🔍 Candidatos encontrados: {len(table_contours)}")
            
            page_detected = 0
            
            for j, table_info in enumerate(table_contours):
                bbox = table_info['bbox']
                
                # Validação de estrutura
                is_valid_structure, structure_confidence = detector.validate_table_structure(img, bbox)
                
                if not is_valid_structure:
                    print(f"   Candidato {j+1}: ❌ Estrutura inválida ({structure_confidence:.1%})")
                    continue
                
                # Validação de conteúdo
                has_valid_content, content_confidence, refined_bbox = detector.analyze_table_content(img, bbox)
                
                if not has_valid_content:
                    print(f"   Candidato {j+1}: ❌ Conteúdo inválido ({content_confidence:.1%})")
                    continue
                
                # Score final
                final_confidence = (structure_confidence * 0.6 + content_confidence * 0.4)
                
                if final_confidence >= 0.25:
                    page_detected += 1
                    total_detected += 1
                    
                    print(f"   ✅ Tabela {page_detected}: Confiança {final_confidence:.1%}")
                    print(f"      Bbox: {refined_bbox}")
                    
                    # Salvar imagem da tabela
                    x, y, w, h = refined_bbox
                    table_roi = img[y:y+h, x:x+w]
                    filename = f"tabela_pg{page_num+1}_tb{page_detected}.png"
                    cv2.imwrite(filename, table_roi)
                    print(f"      💾 Salvo: {filename}")
                    
                    # Análise rápida da qualidade
                    gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
                    binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                    text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    text_regions = 0
                    for contour in text_contours:
                        x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
                        area = w_cont * h_cont
                        if 10 <= area <= 15000 and 2 <= w_cont <= 500 and 2 <= h_cont <= 100:
                            text_regions += 1
                    
                    print(f"      📝 Regiões de texto: {text_regions}")
                    
                    if text_regions >= 20:
                        print(f"      🎉 Tabela rica em conteúdo!")
                    elif text_regions >= 10:
                        print(f"      ✅ Tabela com bom conteúdo")
                    elif text_regions >= 5:
                        print(f"      ⚠️ Tabela com pouco conteúdo")
                    else:
                        print(f"      ❌ Tabela possivelmente vazia")
            
            if page_detected == 0:
                print(f"   📋 Nenhuma tabela detectada nesta página")
            else:
                print(f"   📊 Total na página: {page_detected} tabelas")
        
        print(f"\n🎯 RESULTADO FINAL:")
        print("=" * 30)
        print(f"📄 Páginas testadas: {pages_to_test}")
        print(f"📊 Total de tabelas detectadas: {total_detected}")
        print(f"📈 Média por página: {total_detected/pages_to_test:.1f}")
        
        if total_detected == 0:
            print("❌ Nenhuma tabela detectada - possível problema nos critérios")
        elif total_detected < pages_to_test:
            print("⚠️ Poucas tabelas detectadas - pode haver mais no PDF")
        else:
            print("✅ Detecção funcionando bem!")
        
        print(f"\n📁 Arquivos gerados:")
        for page_num in range(pages_to_test):
            for tb_num in range(1, 11):  # Máximo 10 tabelas por página
                filename = f"tabela_pg{page_num+1}_tb{tb_num}.png"
                if os.path.exists(filename):
                    print(f"   📋 {filename}")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiple_pages()
