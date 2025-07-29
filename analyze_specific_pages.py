#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Páginas Específicas
Examina páginas que deveriam ter tabelas
"""

import cv2
import numpy as np
import fitz
import os

def analyze_specific_pages():
    """Analisa páginas específicas que deveriam ter tabelas"""
    
    print("🔍 ANÁLISE DE PÁGINAS ESPECÍFICAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        # Páginas conhecidas por terem tabelas (páginas do meio do livro)
        pages_to_analyze = [148, 185, 186, 97]  # Páginas mencionadas nos arquivos
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"📄 PDF: {total_pages} páginas")
        
        for page_num in pages_to_analyze:
            if page_num > total_pages:
                continue
                
            print(f"\n📋 ANALISANDO PÁGINA {page_num}:")
            print("-" * 40)
            
            # Renderizar página
            page = doc.load_page(page_num - 1)  # PyMuPDF usa índice 0
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            
            # Converter para OpenCV
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            print(f"📐 Dimensões: {img.shape}")
            
            # Salvar imagem da página para análise visual
            page_filename = f"debug_pagina_{page_num}.png"
            cv2.imwrite(page_filename, img)
            print(f"💾 Página salva: {page_filename}")
            
            # Criar detector
            detector = OpenCVTableDetector(pdf_path, pages=str(page_num), min_table_area=500)  # Área ainda menor
            
            # Análise detalhada da detecção de linhas
            table_structure, h_lines, v_lines = detector.detect_lines(img)
            
            # Salvar imagens de debug
            cv2.imwrite(f"debug_h_lines_{page_num}.png", h_lines)
            cv2.imwrite(f"debug_v_lines_{page_num}.png", v_lines)
            cv2.imwrite(f"debug_structure_{page_num}.png", table_structure)
            
            print(f"🔍 Análise de linhas:")
            h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            print(f"   Contornos H: {len(h_contours)}")
            print(f"   Contornos V: {len(v_contours)}")
            
            # Contar linhas significativas
            h_significant = len([c for c in h_contours if cv2.contourArea(c) > 100])
            v_significant = len([c for c in v_contours if cv2.contourArea(c) > 100])
            
            print(f"   Linhas H significativas: {h_significant}")
            print(f"   Linhas V significativas: {v_significant}")
            
            # Encontrar contornos de tabelas
            table_contours = detector.find_table_contours(table_structure)
            print(f"🔍 Candidatos de tabela: {len(table_contours)}")
            
            if len(table_contours) == 0:
                print("❌ Nenhum candidato encontrado")
                
                # Tentar com critérios ainda mais relaxados
                print("🔄 Tentando detecção mais permissiva...")
                
                # Detectar qualquer retângulo grande
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                
                # Operações morfológicas para conectar texto
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
                
                # Encontrar contornos grandes
                contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                potential_tables = []
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 5000:  # Área mínima
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = w / h
                        if 1.0 <= aspect_ratio <= 20:  # Aspecto razoável
                            potential_tables.append((x, y, w, h, area))
                
                print(f"🔍 Contornos grandes encontrados: {len(potential_tables)}")
                
                for i, (x, y, w, h, area) in enumerate(potential_tables[:3]):  # Mostrar primeiros 3
                    print(f"   Região {i+1}: ({x}, {y}) {w}x{h}, área={area}")
                    
                    # Extrair e salvar
                    roi = img[y:y+h, x:x+w]
                    filename = f"debug_regiao_{page_num}_{i+1}.png"
                    cv2.imwrite(filename, roi)
                    print(f"   💾 Salvo: {filename}")
            
            else:
                # Processar candidatos encontrados
                for j, table_info in enumerate(table_contours):
                    bbox = table_info['bbox']
                    print(f"   Candidato {j+1}: {bbox}, área={table_info['area']}")
                    
                    # Extrair e salvar
                    x, y, w, h = bbox
                    roi = img[y:y+h, x:x+w]
                    filename = f"debug_candidato_{page_num}_{j+1}.png"
                    cv2.imwrite(filename, roi)
                    print(f"   💾 Salvo: {filename}")
        
        doc.close()
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print("1. Examine as imagens de debug geradas")
        print("2. Verifique se há estruturas tabulares visíveis")
        print("3. Se houver tabelas não detectadas, ajuste os algoritmos")
        print("4. Se não houver tabelas, teste outras páginas")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_specific_pages()
