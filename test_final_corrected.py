#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Final - Extração de Imagem Corrigida
Testa a extração de imagem usando as coordenadas corrigidas
"""

import fitz
import os
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
import sys

def test_corrected_extraction():
    """Testa extração com coordenadas corrigidas"""
    
    print("🎯 TESTE FINAL - EXTRAÇÃO CORRIGIDA")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        app = QApplication(sys.argv)
        
        # Coordenadas corrigidas (da saída do detector v3)
        corrected_bbox = (31.667226975963963, 291.840007625214, 356.0164002449282, 224.1600058568667)
        page_num = 148
        
        print(f"📄 Página: {page_num}")
        print(f"📐 BBox corrigido: {corrected_bbox}")
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        
        print(f"📏 Dimensões da página: {page.rect}")
        
        # Criar retângulo com coordenadas corrigidas
        x, y, w, h = corrected_bbox
        rect = fitz.Rect(x, y, x + w, y + h)
        
        print(f"🔧 Retângulo: {rect}")
        
        # Verificar limites
        dentro_limites = rect in page.rect
        print(f"✅ Dentro dos limites: {dentro_limites}")
        
        # Extrair pixmap
        pix = page.get_pixmap(clip=rect, dpi=150)
        print(f"🖼️ Pixmap: {pix.width}x{pix.height}")
        
        if pix.width > 0 and pix.height > 0:
            # Converter para QImage
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            
            # Salvar
            output_path = "TESTE_FINAL_CORRIGIDO.png"
            success = img.save(output_path)
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ SUCESSO! Imagem salva: {output_path}")
                print(f"📁 Tamanho: {file_size} bytes")
                
                if file_size > 1000:  # Arquivo não vazio
                    print("🎉 PROBLEMA RESOLVIDO! A extração agora funciona corretamente!")
                else:
                    print("❌ Arquivo muito pequeno, pode estar vazio")
            else:
                print("❌ Falha ao salvar")
        else:
            print("❌ Pixmap vazio")
        
        doc.close()
        app.quit()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_corrected_extraction()
