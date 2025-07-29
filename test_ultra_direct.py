#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste ULTRA direto
"""

import cv2
import numpy as np
import fitz
import os

# Copiar o método aqui para testar diretamente
def test_ultra_direct():
    """Teste ultra direto"""
    
    print("🔬 TESTE ULTRA DIRETO")
    print("=" * 20)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    try:
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Bbox
        bbox = (212, 401, 761, 347)
        x, y, w, h = bbox
        
        # Extrair ROI diretamente
        table_roi = img[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
        
        # Threshold adaptivo
        binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Contornos
        text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar
        text_regions = []
        for contour in text_contours:
            x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
            area = w_cont * h_cont
            
            if 20 <= area <= 8000 and 3 <= w_cont <= 300 and 3 <= h_cont <= 80:
                text_regions.append((x_cont, y_cont, w_cont, h_cont))
        
        print(f"📝 Regiões: {len(text_regions)}")
        
        # Teste direto da lógica
        if len(text_regions) >= 5:
            print("✅ Passou no teste >= 5")
            
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
            
            print(f"📏 Linhas: {len(lines)}")
            
            if len(lines) >= 2:
                print("✅ >= 2 linhas - deveria retornar True")
                score = 0.5  # Score exemplo
                print(f"📊 Score calculado: {score}")
                return True, score
            else:
                print("⚠️ < 2 linhas - score médio")
                return True, 0.4
        
        elif len(text_regions) >= 1:
            print("⚠️ Fallback - score baixo")
            return True, 0.2
        
        else:
            print("❌ Sem texto")
            return False, 0.0
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, 0.0

if __name__ == "__main__":
    result, score = test_ultra_direct()
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"   Válido: {result}")
    print(f"   Score: {score}")
