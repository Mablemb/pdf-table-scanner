#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Extração de Imagens
Testa especificamente a extração de imagens das tabelas detectadas
"""

import fitz
import os
from PyQt5.QtGui import QImage

def debug_image_extraction():
    """Testa a extração de imagem para a tabela perfeita da página 148"""
    
    print("🖼️ DEBUG EXTRAÇÃO DE IMAGENS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        # Dados da tabela perfeita (do nosso teste anterior)
        table_data = {
            'page': 148,
            'bbox': (66, 608, 742, 467),  # bbox refinado do detector
            'confidence': 0.840
        }
        
        print(f"📄 Extraindo tabela da página {table_data['page']}")
        print(f"📐 BBox: {table_data['bbox']}")
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page_num = table_data['page']
        bbox = table_data['bbox']
        
        # Carregar página
        page = doc.load_page(page_num - 1)  # PyMuPDF usa índice 0
        
        print(f"📏 Dimensões da página: {page.rect}")
        
        # Criar retângulo para extração
        print(f"\n🔍 CRIANDO RETÂNGULO:")
        print(f"   bbox original: {bbox}")
        print(f"   x1, y1: {bbox[0]}, {bbox[1]}")
        print(f"   x2, y2: {bbox[0] + bbox[2]}, {bbox[1] + bbox[3]}")
        
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3])
        print(f"   fitz.Rect: {rect}")
        
        # Verificar se o retângulo está dentro da página
        page_rect = page.rect
        print(f"\n📏 VERIFICAÇÃO DE LIMITES:")
        print(f"   Página: {page_rect}")
        print(f"   Tabela: {rect}")
        print(f"   Dentro da página: {rect in page_rect}")
        
        if not rect in page_rect:
            print(f"   ⚠️ AVISO: Retângulo fora dos limites da página!")
            # Ajustar para os limites da página
            rect = rect & page_rect
            print(f"   🔧 Retângulo ajustado: {rect}")
        
        # Extrair pixmap
        print(f"\n🖼️ EXTRAINDO PIXMAP:")
        try:
            pix = page.get_pixmap(clip=rect, dpi=150)
            print(f"   Pixmap criado: {pix.width}x{pix.height}")
            
            if pix.width == 0 or pix.height == 0:
                print(f"   ❌ ERRO: Pixmap vazio!")
                
                # Tentar sem clipping
                print(f"   🔄 Tentando extrair página inteira...")
                pix_full = page.get_pixmap(dpi=150)
                print(f"   Página completa: {pix_full.width}x{pix_full.height}")
                
                # Tentar com outro retângulo
                print(f"   🔄 Tentando retângulo menor...")
                smaller_rect = fitz.Rect(100, 600, 600, 900)
                pix_small = page.get_pixmap(clip=smaller_rect, dpi=150)
                print(f"   Retângulo menor: {pix_small.width}x{pix_small.height}")
                
            else:
                print(f"   ✅ Pixmap válido")
                
                # Converter para QImage
                print(f"\n🖼️ CONVERTENDO PARA QIMAGE:")
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                
                if img.isNull():
                    print(f"   ❌ ERRO: QImage nula!")
                else:
                    print(f"   ✅ QImage criada: {img.width()}x{img.height()}")
                    
                    # Salvar para teste
                    test_path = "debug_extraction_test.png"
                    success = img.save(test_path)
                    
                    if success:
                        print(f"   ✅ Imagem salva: {test_path}")
                        
                        # Verificar tamanho do arquivo
                        if os.path.exists(test_path):
                            file_size = os.path.getsize(test_path)
                            print(f"   📁 Tamanho do arquivo: {file_size} bytes")
                            
                            if file_size == 0:
                                print(f"   ❌ ERRO: Arquivo vazio!")
                            else:
                                print(f"   ✅ Arquivo válido")
                        else:
                            print(f"   ❌ ERRO: Arquivo não foi criado")
                    else:
                        print(f"   ❌ ERRO: Falha ao salvar imagem")
                        
                        # Tentar salvar como BMP
                        bmp_path = "debug_extraction_test.bmp"
                        bmp_success = img.save(bmp_path, "BMP")
                        print(f"   🔄 Tentativa BMP: {'✅ sucesso' if bmp_success else '❌ falha'}")
                
        except Exception as e:
            print(f"   ❌ ERRO ao extrair pixmap: {e}")
            import traceback
            traceback.print_exc()
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Inicializar aplicação Qt para QImage
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    debug_image_extraction()
    app.quit()
