#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug da Análise de Conteúdo
"""

import cv2
import numpy as np
import fitz
import os

def debug_content_analysis():
    """Debug detalhado da análise de conteúdo"""
    
    print("🔍 DEBUG - ANÁLISE DE CONTEÚDO")
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
        
        # Detector
        detector = OpenCVTableDetector(pdf_path, pages="1", min_table_area=1000)
        
        # Encontrar candidatos
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        if not table_contours:
            print("❌ Nenhum candidato encontrado")
            return
        
        # Pegar primeiro candidato
        bbox = table_contours[0]['bbox']
        x, y, w, h = bbox
        
        print(f"📋 Analisando candidato: {bbox}")
        
        # Extrair ROI
        table_roi = img[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
        
        print(f"📐 ROI: {table_roi.shape}")
        
        # Threshold
        _, binary = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Encontrar contornos
        text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"🔍 Contornos encontrados: {len(text_contours)}")
        
        # Analisar cada contorno
        text_regions = []
        for i, contour in enumerate(text_contours):
            x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
            area = w_cont * h_cont
            
            if i < 10:  # Mostrar primeiros 10
                print(f"   Contorno {i}: área={area}, dim={w_cont}x{h_cont}")
            
            # Filtros mais permissivos
            if 20 <= area <= 8000 and 3 <= w_cont <= 300 and 3 <= h_cont <= 80:
                text_regions.append((x_cont, y_cont, w_cont, h_cont))
        
        print(f"📝 Regiões de texto válidas: {len(text_regions)}")
        
        if len(text_regions) == 0:
            print("❌ Nenhuma região de texto encontrada")
            
            # Tentar threshold diferente
            print("🔄 Tentando threshold adaptivo...")
            adaptive_binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            
            # Salvar imagens para debug
            cv2.imwrite("debug_roi.png", table_roi)
            cv2.imwrite("debug_binary.png", binary)
            cv2.imwrite("debug_adaptive.png", adaptive_binary)
            
            print("💾 Imagens de debug salvas: debug_roi.png, debug_binary.png, debug_adaptive.png")
            
            # Tentar com threshold adaptivo
            text_contours2, _ = cv2.findContours(adaptive_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"🔍 Contornos com threshold adaptivo: {len(text_contours2)}")
            
            text_regions2 = []
            for contour in text_contours2:
                x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
                area = w_cont * h_cont
                if 20 <= area <= 8000 and 3 <= w_cont <= 300 and 3 <= h_cont <= 80:
                    text_regions2.append((x_cont, y_cont, w_cont, h_cont))
            
            print(f"📝 Regiões com threshold adaptivo: {len(text_regions2)}")
            
            if len(text_regions2) > 0:
                print("✅ Threshold adaptivo encontrou texto!")
        else:
            # Agrupar por linhas
            text_regions.sort(key=lambda r: (r[1], r[0]))
            
            lines = []
            current_line = []
            last_y = -100
            
            for region in text_regions:
                x_reg, y_reg, w_reg, h_reg = region
                if abs(y_reg - last_y) <= 25:
                    current_line.append(region)
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [region]
                last_y = y_reg
            
            if current_line:
                lines.append(current_line)
            
            print(f"📏 Linhas agrupadas: {len(lines)}")
            for i, line in enumerate(lines):
                print(f"   Linha {i}: {len(line)} elementos")
            
            # Verificar linhas válidas
            valid_lines = [line for line in lines if len(line) >= 1]
            print(f"✅ Linhas válidas: {len(valid_lines)}")
            
            if len(valid_lines) >= 1:
                print("🎉 Conteúdo deveria ser válido!")
            else:
                print("❌ Não há linhas válidas suficientes")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_content_analysis()
