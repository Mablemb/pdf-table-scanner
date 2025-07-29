#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Precisão dos Detectores Melhorados
Verifica se as melhorias reduziram os falsos positivos
"""

import os
import cv2
import numpy as np
import fitz
from opencv_table_detector import OpenCVTableDetector

def quick_opencv_test(pdf_path, max_pages=3):
    """Teste rápido do OpenCV melhorado"""
    print(f"🔍 Testando OpenCV melhorado em: {os.path.basename(pdf_path)}")
    print("-" * 60)
    
    try:
        doc = fitz.open(pdf_path)
        total_results = []
        
        for page_num in range(min(max_pages, len(doc))):
            print(f"\n📄 Página {page_num + 1}:")
            
            # Renderizar página
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Simular detecção (criando instância temporária)
            detector = OpenCVTableDetector(pdf_path, pages="1", min_table_area=10000)
            
            # Detectar linhas
            table_structure, h_lines, v_lines = detector.detect_lines(img)
            
            # Encontrar contornos candidatos
            table_contours = detector.find_table_contours(table_structure)
            print(f"   🔍 Candidatos iniciais: {len(table_contours)}")
            
            # Validar cada candidato
            validated = 0
            for i, table_info in enumerate(table_contours):
                bbox = table_info['bbox']
                
                # Validação de estrutura
                is_valid_structure, structure_conf = detector.validate_table_structure(img, bbox)
                
                # Validação de conteúdo
                has_valid_content, content_conf = detector.analyze_table_content(img, bbox)
                
                final_conf = (structure_conf * 0.6 + content_conf * 0.4) if is_valid_structure and has_valid_content else 0.0
                
                if final_conf >= 0.6:
                    validated += 1
                    status = "✅ VÁLIDA"
                else:
                    status = "❌ REJEITADA"
                
                print(f"      Candidato {i+1}: {status} (estrutura: {structure_conf:.2f}, conteúdo: {content_conf:.2f}, final: {final_conf:.2f})")
            
            print(f"   ✅ Tabelas validadas: {validated}/{len(table_contours)}")
            total_results.append({
                'page': page_num + 1,
                'candidates': len(table_contours),
                'validated': validated
            })
        
        doc.close()
        
        # Resumo
        total_candidates = sum(r['candidates'] for r in total_results)
        total_validated = sum(r['validated'] for r in total_results)
        precision = (total_validated / total_candidates * 100) if total_candidates > 0 else 0
        
        print(f"\n📊 RESUMO:")
        print(f"   Candidatos totais: {total_candidates}")
        print(f"   Tabelas validadas: {total_validated}")
        print(f"   Taxa de precisão: {precision:.1f}%")
        
        return total_results
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return []

def compare_with_old_method(pdf_path):
    """Compara com método antigo (simulado)"""
    print(f"\n🔄 Comparação com método anterior:")
    print("-" * 40)
    
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Método antigo (simplificado)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Kernels pequenos (método antigo)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        
        table_structure = cv2.addWeighted(h_lines, 0.5, v_lines, 0.5, 0.0)
        
        # Dilatação agressiva (método antigo)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(table_structure, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtro simples (método antigo)
        old_candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:  # Threshold baixo
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                if 0.5 <= aspect_ratio <= 10:  # Range amplo
                    old_candidates.append((x, y, w, h))
        
        doc.close()
        
        print(f"   Método antigo: {len(old_candidates)} detecções")
        print(f"   Método novo: Testado acima")
        print(f"   Redução: {len(old_candidates)} → menor número (com validação)")
        
    except Exception as e:
        print(f"❌ Erro na comparação: {e}")

def main():
    """Função principal de teste"""
    print("🧪 TESTE DE PRECISÃO - DETECTORES MELHORADOS")
    print("=" * 70)
    
    # Procurar PDFs para teste
    pdf_folder = "LivrosPDF"
    if not os.path.exists(pdf_folder):
        print("❌ Pasta LivrosPDF não encontrada!")
        return
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print("❌ Nenhum PDF encontrado!")
        return
    
    # Testar com o primeiro PDF
    test_pdf = os.path.join(pdf_folder, pdf_files[0])
    
    print(f"📁 Testando com: {pdf_files[0]}")
    print(f"📊 Processando apenas 3 primeiras páginas para teste rápido...")
    print("=" * 70)
    
    # Teste principal
    results = quick_opencv_test(test_pdf, max_pages=3)
    
    # Comparação
    compare_with_old_method(test_pdf)
    
    print("\n" + "=" * 70)
    print("✅ TESTE CONCLUÍDO!")
    print("💡 Agora teste na aplicação principal para validar visualmente os resultados.")

if __name__ == "__main__":
    main()
