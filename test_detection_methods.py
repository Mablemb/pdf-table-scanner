#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste dos Métodos de Detecção Automática de Tabelas
Script para demonstrar as capacidades dos diferentes métodos implementados
"""

import os
import sys
from opencv_table_detector import OpenCVTableDetector, TesseractTableDetector

def test_opencv_detection(pdf_path):
    """Testa detecção com OpenCV"""
    print("🔍 Testando detecção OpenCV...")
    print("=" * 50)
    
    # Simular detecção (sem UI)
    try:
        import cv2
        import numpy as np
        import fitz
        
        # Abrir PDF e processar primeira página
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        
        # Converter para OpenCV
        img_data = pix.samples
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Detectar linhas
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Linhas horizontais
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Linhas verticais  
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        
        # Encontrar contornos
        table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar por área
        table_candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:
                x, y, w, h = cv2.boundingRect(contour)
                table_candidates.append((x, y, w, h, area))
        
        doc.close()
        
        print(f"✅ Análise OpenCV concluída!")
        print(f"📊 Regiões de interesse encontradas: {len(table_candidates)}")
        print(f"📏 Dimensões da página: {pix.width}x{pix.height}")
        
        for i, (x, y, w, h, area) in enumerate(table_candidates):
            print(f"   Região {i+1}: ({x}, {y}) - {w}x{h} pixels - Área: {area}")
        
        return len(table_candidates)
        
    except Exception as e:
        print(f"❌ Erro OpenCV: {e}")
        return 0

def test_pdf_compatibility(pdf_path):
    """Testa compatibilidade do PDF com diferentes métodos"""
    print("🔍 Analisando compatibilidade do PDF...")
    print("=" * 50)
    
    try:
        import fitz
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)
        
        print(f"📄 Arquivo: {os.path.basename(pdf_path)}")
        print(f"📊 Páginas: {total_pages}")
        print(f"💾 Tamanho: {file_size:.1f} MB")
        print()
        
        # Verificar tipo do PDF (texto vs imagem)
        text_pages = 0
        image_based_pages = 0
        
        # Verificar primeiras 5 páginas
        pages_to_check = min(5, total_pages)
        
        for i in range(pages_to_check):
            page = doc.load_page(i)
            text = page.get_text().strip()
            
            if len(text) > 50:
                text_pages += 1
            else:
                image_based_pages += 1
        
        doc.close()
        
        # Determinar compatibilidade
        has_text = text_pages > 0
        is_mostly_text = (text_pages / pages_to_check) >= 0.4
        
        print("🔍 COMPATIBILIDADE DOS MÉTODOS:")
        print(f"┌─ Camelot: {'✅ COMPATÍVEL' if is_mostly_text else '❌ INCOMPATÍVEL (PDF de imagem)'}")
        print(f"├─ OpenCV: {'✅ COMPATÍVEL' if True else '❌ INCOMPATÍVEL'} (funciona com qualquer PDF)")
        print(f"├─ Tesseract: {'✅ COMPATÍVEL' if True else '❌ INCOMPATÍVEL'} (funciona com qualquer PDF)")
        print(f"└─ GPT-4 Vision: {'✅ COMPATÍVEL' if True else '❌ INCOMPATÍVEL'} (funciona com qualquer PDF)")
        print()
        
        print("📋 RECOMENDAÇÕES:")
        if is_mostly_text:
            print("🎯 Use CAMELOT para melhor precisão (PDF com texto)")
            print("🔄 OpenCV como alternativa para tabelas com bordas")
        else:
            print("🎯 Use OPENCV para tabelas com bordas visíveis")
            print("🔤 Use TESSERACT para tabelas baseadas em texto alinhado")
            print("🤖 Use GPT-4 VISION para casos complexos")
        
        return {
            'total_pages': total_pages,
            'text_pages': text_pages,
            'image_pages': image_based_pages,
            'camelot_compatible': is_mostly_text,
            'file_size_mb': file_size
        }
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def main():
    """Função principal de teste"""
    print("🚀 TESTE DOS MÉTODOS DE DETECÇÃO AUTOMÁTICA")
    print("=" * 60)
    
    # Listar PDFs disponíveis
    pdf_folder = "LivrosPDF"
    if not os.path.exists(pdf_folder):
        print("❌ Pasta LivrosPDF não encontrada!")
        return
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print("❌ Nenhum PDF encontrado na pasta LivrosPDF!")
        return
    
    print(f"📁 Encontrados {len(pdf_files)} PDFs na pasta:")
    for i, pdf in enumerate(pdf_files[:3]):  # Mostrar apenas os primeiros 3
        print(f"   {i+1}. {pdf}")
    
    # Testar com o primeiro PDF
    test_pdf = os.path.join(pdf_folder, pdf_files[0])
    print(f"\n🧪 Testando com: {pdf_files[0]}")
    print("=" * 60)
    
    # Análise de compatibilidade
    compatibility = test_pdf_compatibility(test_pdf)
    print()
    
    # Teste OpenCV
    if compatibility:
        opencv_results = test_opencv_detection(test_pdf)
        print()
    
    print("✅ TESTE CONCLUÍDO!")
    print("💡 Use a aplicação principal para análise completa com interface gráfica.")

if __name__ == "__main__":
    main()
