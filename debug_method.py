#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Direto do Método analyze_table_content
"""

import cv2
import numpy as np
import fitz
import os

def test_method_directly():
    """Testa o método diretamente"""
    
    print("🔬 TESTE DIRETO DO MÉTODO")
    print("=" * 30)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
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
        detector = OpenCVTableDetector(pdf_path, pages="1")
        
        # Bbox do candidato
        bbox = (212, 401, 761, 347)
        
        print(f"📋 Testando bbox: {bbox}")
        
        # Chamar método diretamente
        has_content, content_score, refined_bbox = detector.analyze_table_content(img, bbox)
        
        print(f"✅ Resultado: {has_content}")
        print(f"📊 Score: {content_score}")
        print(f"📐 Bbox refinado: {refined_bbox}")
        
        # Testar passo a passo
        x, y, w, h = bbox
        
        # 1. Refinar bbox
        refined = detector.refine_table_bbox(img, bbox)
        print(f"🔧 Bbox após refinamento: {refined}")
        
        # 2. Extrair ROI
        table_roi = img[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
        
        # 3. Threshold adaptivo
        binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # 4. Contornos
        text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"🔍 Contornos: {len(text_contours)}")
        
        # 5. Filtrar regiões
        text_regions = []
        for contour in text_contours:
            x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
            area = w_cont * h_cont
            
            if 20 <= area <= 8000 and 3 <= w_cont <= 300 and 3 <= h_cont <= 80:
                text_regions.append((x_cont, y_cont, w_cont, h_cont))
        
        print(f"📝 Regiões válidas: {len(text_regions)}")
        
        if len(text_regions) >= 1:  # Deve ser >= 1 agora
            print("✅ Passou no filtro inicial")
            
            # 6. Agrupar por linhas
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
            
            print(f"📏 Linhas: {len(lines)}")
            
            # 7. Verificar linhas válidas
            valid_lines = [line for line in lines if len(line) >= 1]
            print(f"✅ Linhas válidas: {len(valid_lines)}")
            
            if len(valid_lines) >= 1:
                print("🎉 Deveria retornar True!")
                
                # Calcular score
                column_alignment_score = detector.calculate_column_alignment(valid_lines)
                print(f"📊 Alinhamento: {column_alignment_score}")
                
                structure_score = min(1.0, len(valid_lines) / 1.0 * column_alignment_score)
                print(f"📊 Score estrutura: {structure_score}")
                
                should_pass = structure_score >= 0.2
                print(f"🎯 Deveria passar (>=0.2): {should_pass}")
            else:
                # Checar fallback
                if len(text_regions) >= 1:
                    print("🔄 Usando fallback para score 0.2")
                    print("✅ Deveria retornar True com score 0.2")
        else:
            print("❌ Falhou no filtro inicial")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_method_directly()
