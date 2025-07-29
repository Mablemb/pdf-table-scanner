#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Coordenadas Corretas
Calcula conversão de coordenadas entre DPI da imagem e coordenadas do PDF
"""

import fitz
import cv2
import numpy as np
import os

def test_coordinate_conversion():
    """Testa conversão de coordenadas entre imagem e PDF"""
    
    print("📐 TESTE DE COORDENADAS CORRETAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page_num = 147  # Página 148 (índice 0)
        page = doc.load_page(page_num)
        
        print(f"📄 Página {page_num + 1}")
        print(f"📏 Dimensões PDF: {page.rect}")
        
        # Renderizar com DPI 150 (igual ao detector)
        pix = page.get_pixmap(dpi=150)
        print(f"🖼️ Dimensões imagem (150 DPI): {pix.width}x{pix.height}")
        
        # Converter para OpenCV
        img_data = pix.samples
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"🔧 Dimensões OpenCV: {img.shape}")
        
        # Calcular fatores de escala
        pdf_width = page.rect.width
        pdf_height = page.rect.height
        img_width = img.shape[1]
        img_height = img.shape[0]
        
        scale_x = pdf_width / img_width
        scale_y = pdf_height / img_height
        
        print(f"\n📊 FATORES DE ESCALA:")
        print(f"   PDF: {pdf_width:.1f} x {pdf_height:.1f}")
        print(f"   IMG: {img_width} x {img_height}")
        print(f"   Scale X: {scale_x:.4f}")
        print(f"   Scale Y: {scale_y:.4f}")
        
        # Bbox do detector (coordenadas da imagem 150 DPI)
        bbox_img = (66, 608, 742, 467)  # (x, y, w, h)
        
        print(f"\n🎯 CONVERSÃO DE COORDENADAS:")
        print(f"   BBox imagem: {bbox_img}")
        
        # Converter para coordenadas PDF
        x_pdf = bbox_img[0] * scale_x
        y_pdf = bbox_img[1] * scale_y
        w_pdf = bbox_img[2] * scale_x
        h_pdf = bbox_img[3] * scale_y
        
        bbox_pdf = (x_pdf, y_pdf, w_pdf, h_pdf)
        print(f"   BBox PDF: ({x_pdf:.1f}, {y_pdf:.1f}, {w_pdf:.1f}, {h_pdf:.1f})")
        
        # Coordenadas para fitz.Rect
        x1, y1 = x_pdf, y_pdf
        x2, y2 = x_pdf + w_pdf, y_pdf + h_pdf
        
        print(f"   Rect coords: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
        
        # Verificar se está dentro dos limites
        dentro_limites = (x2 <= pdf_width and y2 <= pdf_height)
        print(f"   Dentro dos limites: {dentro_limites}")
        
        if not dentro_limites:
            print(f"   ❌ FORA DOS LIMITES:")
            print(f"      x2 = {x2:.1f} (max: {pdf_width:.1f})")
            print(f"      y2 = {y2:.1f} (max: {pdf_height:.1f})")
            
            # Ajustar aos limites
            x2_adj = min(x2, pdf_width)
            y2_adj = min(y2, pdf_height)
            w_adj = x2_adj - x1
            h_adj = y2_adj - y1
            
            print(f"   🔧 AJUSTADO:")
            print(f"      Rect: ({x1:.1f}, {y1:.1f}, {x2_adj:.1f}, {y2_adj:.1f})")
            print(f"      Dims: {w_adj:.1f} x {h_adj:.1f}")
        
        # Testar extração
        print(f"\n🖼️ TESTANDO EXTRAÇÃO:")
        
        rect = fitz.Rect(x1, y1, x2, y2)
        if not dentro_limites:
            rect = rect & page.rect  # Interseção com página
        
        print(f"   Rect final: {rect}")
        
        pix_extract = page.get_pixmap(clip=rect, dpi=150)
        print(f"   Pixmap extraído: {pix_extract.width}x{pix_extract.height}")
        
        if pix_extract.width > 0 and pix_extract.height > 0:
            # Salvar para verificação
            from PyQt5.QtGui import QImage
            from PyQt5.QtWidgets import QApplication
            import sys
            
            app = QApplication(sys.argv)
            
            img_qt = QImage(pix_extract.samples, pix_extract.width, pix_extract.height, 
                           pix_extract.stride, QImage.Format_RGB888)
            
            test_path = "debug_coordinates_fixed.png"
            success = img_qt.save(test_path)
            
            if success and os.path.exists(test_path):
                file_size = os.path.getsize(test_path)
                print(f"   ✅ Imagem salva: {test_path} ({file_size} bytes)")
            else:
                print(f"   ❌ Falha ao salvar")
            
            app.quit()
        else:
            print(f"   ❌ Pixmap vazio")
        
        doc.close()
        
        print(f"\n💡 SOLUÇÃO:")
        print("Implementar conversão de coordenadas no detector ou no aplicativo")
        print("para garantir que as coordenadas estejam na escala correta do PDF")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coordinate_conversion()
