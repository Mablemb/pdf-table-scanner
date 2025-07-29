#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Múltiplas Tabelas
Verifica quantas tabelas existem realmente nas páginas de teste
"""

import cv2
import numpy as np
import fitz
import os

def analyze_multiple_tables():
    """Analisa páginas em busca de múltiplas tabelas"""
    
    print("🔍 ANÁLISE DE MÚLTIPLAS TABELAS")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        # Páginas de teste
        test_pages = [97, 148, 185, 186]
        
        doc = fitz.open(pdf_path)
        
        for page_num in test_pages:
            print(f"\n📄 ANALISANDO PÁGINA {page_num}:")
            print("-" * 40)
            
            # Renderizar página
            page = doc.load_page(page_num - 1)
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            
            # Converter para OpenCV
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Criar detector com área mínima MENOR para encontrar mais tabelas
            detector = OpenCVTableDetector(pdf_path, pages=str(page_num), min_table_area=300)
            
            # Detectar estrutura
            table_structure, h_lines, v_lines = detector.detect_lines(img)
            
            # Encontrar TODOS os contornos possíveis (sem filtros rígidos)
            table_contours = detector.find_table_contours(table_structure)
            
            print(f"🔍 Candidatos encontrados: {len(table_contours)}")
            
            # Analisar cada candidato SEM validação rigorosa
            valid_count = 0
            
            for i, table_info in enumerate(table_contours):
                bbox = table_info['bbox']
                area = table_info['area']
                
                # Validação bem permissiva
                x, y, w, h = bbox
                aspect_ratio = w / h
                
                # Critérios muito relaxados
                is_reasonable_size = w > 100 and h > 50
                is_reasonable_aspect = 0.5 <= aspect_ratio <= 20
                is_reasonable_area = area > 5000
                
                print(f"   Candidato {i+1}:")
                print(f"      BBox: {bbox}")
                print(f"      Área: {area}")
                print(f"      Aspecto: {aspect_ratio:.2f}")
                
                if is_reasonable_size and is_reasonable_aspect and is_reasonable_area:
                    print(f"      ✅ POTENCIAL TABELA")
                    valid_count += 1
                    
                    # Salvar imagem do candidato
                    roi = img[y:y+h, x:x+w]
                    filename = f"candidato_multiplo_pag{page_num}_{i+1}.png"
                    cv2.imwrite(filename, roi)
                    print(f"      💾 Salvo: {filename}")
                else:
                    print(f"      ❌ Descartado")
            
            print(f"\n📊 RESUMO PÁGINA {page_num}:")
            print(f"   Total candidatos: {len(table_contours)}")
            print(f"   Tabelas potenciais: {valid_count}")
            
            # Se encontrou múltiplas, investigar por que o detector oficial só pega 1
            if valid_count > 1:
                print(f"   🚨 MÚLTIPLAS TABELAS DETECTADAS!")
                print(f"   Investigar por que detector oficial só retorna 1")
        
        doc.close()
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print("1. Examinar imagens geradas para confirmar tabelas múltiplas")
        print("2. Ajustar detector para encontrar todas as tabelas")
        print("3. Implementar sistema de 'pintar de branco'")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_multiple_tables()
