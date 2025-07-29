#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Específico - Problema de Enquadramento
Verifica se o problema está na conversão de coordenadas PDF->Imagem
"""

import cv2
import numpy as np
import fitz
import os

def debug_page_vs_image_coordinates():
    """Debug das coordenadas PDF vs Imagem"""
    
    print("🔍 DEBUG - COORDENADAS PDF vs IMAGEM")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    try:
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        
        # Obter informações da página
        page_rect = page.rect
        print(f"📄 Página PDF: {page_rect.width:.1f}x{page_rect.height:.1f} pontos")
        
        # Renderizar com diferentes DPIs para testar
        dpis = [150, 200, 300]
        
        for dpi in dpis:
            print(f"\n🔍 Testando DPI {dpi}:")
            
            # Renderizar página
            pix = page.get_pixmap(dpi=dpi)
            img_data = pix.samples
            
            # Converter para OpenCV
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            print(f"   Imagem: {img.shape[1]}x{img.shape[0]} pixels")
            
            # Calcular fator de escala
            scale_x = img.shape[1] / page_rect.width
            scale_y = img.shape[0] / page_rect.height
            print(f"   Escala: x={scale_x:.2f}, y={scale_y:.2f}")
            
            # Testar uma coordenada conhecida (centro da página)
            center_pdf_x = page_rect.width / 2
            center_pdf_y = page_rect.height / 2
            center_img_x = int(center_pdf_x * scale_x)
            center_img_y = int(center_pdf_y * scale_y)
            
            print(f"   Centro PDF: ({center_pdf_x:.1f}, {center_pdf_y:.1f})")
            print(f"   Centro Img: ({center_img_x}, {center_img_y})")
            
        # Agora vamos testar com a detecção real
        print(f"\n🔧 TESTE COM DETECÇÃO REAL (DPI 150):")
        
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        from opencv_table_detector import OpenCVTableDetector
        
        detector = OpenCVTableDetector(pdf_path, pages="1")
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        if table_contours:
            bbox = table_contours[0]['bbox']
            x, y, w, h = bbox
            
            print(f"📋 Bbox detectado: {bbox}")
            
            # Converter para coordenadas PDF
            scale_x = img.shape[1] / page_rect.width
            scale_y = img.shape[0] / page_rect.height
            
            pdf_x = x / scale_x
            pdf_y = y / scale_y
            pdf_w = w / scale_x
            pdf_h = h / scale_y
            
            print(f"📄 Bbox em coordenadas PDF: ({pdf_x:.1f}, {pdf_y:.1f}, {pdf_w:.1f}, {pdf_h:.1f})")
            
            # Testar extração direta da região
            roi = img[y:y+h, x:x+w]
            print(f"🖼️ ROI extraída: {roi.shape}")
            
            # Salvar ROI com informações
            cv2.imwrite(f"debug_roi_dpi150.png", roi)
            
            # Criar visualização com marcações
            img_marked = img.copy()
            cv2.rectangle(img_marked, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(img_marked, f"BBOX ({x},{y})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Marcar centro
            center_x, center_y = x + w//2, y + h//2
            cv2.circle(img_marked, (center_x, center_y), 5, (255, 0, 0), -1)
            cv2.putText(img_marked, "CENTRO", (center_x+10, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            cv2.imwrite("debug_imagem_marcada.png", img_marked)
            
            print(f"💾 Arquivos salvos:")
            print(f"   - debug_roi_dpi150.png (ROI extraída)")
            print(f"   - debug_imagem_marcada.png (imagem com marcações)")
            
            # Verificar se a ROI tem conteúdo visível
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            mean_intensity = np.mean(gray_roi)
            std_intensity = np.std(gray_roi)
            
            print(f"📊 Análise da ROI:")
            print(f"   Intensidade média: {mean_intensity:.1f}")
            print(f"   Desvio padrão: {std_intensity:.1f}")
            
            if std_intensity < 10:
                print(f"   ⚠️ ROI pode estar em branco ou uniforme")
            elif std_intensity > 50:
                print(f"   ✅ ROI tem bastante variação (provável conteúdo)")
            else:
                print(f"   ➖ ROI tem variação moderada")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def analyze_extraction_quality():
    """Analisa a qualidade da extração"""
    
    print(f"\n🔍 ANÁLISE DE QUALIDADE DA EXTRAÇÃO")
    print("=" * 40)
    
    # Verificar se as imagens existem
    images = [
        "debug_roi_original.png",
        "debug_roi_refinado.png", 
        "debug_coordenadas.png"
    ]
    
    for img_name in images:
        if os.path.exists(img_name):
            img = cv2.imread(img_name)
            if img is not None:
                h, w = img.shape[:2]
                print(f"📷 {img_name}: {w}x{h}")
                
                # Analisar se tem conteúdo
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                mean_val = np.mean(gray)
                std_val = np.std(gray)
                
                if std_val < 5:
                    print(f"   ⚠️ Imagem muito uniforme (possível branco)")
                elif std_val > 30:
                    print(f"   ✅ Boa variação de conteúdo")
                else:
                    print(f"   ➖ Variação moderada")
            else:
                print(f"❌ {img_name}: Erro ao carregar")
        else:
            print(f"❌ {img_name}: Não encontrada")

if __name__ == "__main__":
    debug_page_vs_image_coordinates()
    analyze_extraction_quality()
