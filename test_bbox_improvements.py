#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das Melhorias de Enquadramento (Bounding Box)
Verifica se as tabelas estão sendo enquadradas corretamente
"""

import cv2
import numpy as np
import fitz
from opencv_table_detector import OpenCVTableDetector, TesseractTableDetector
import os

def test_bbox_improvements():
    """Testa as melhorias de enquadramento das tabelas"""
    
    print("🔧 TESTE DAS MELHORIAS DE ENQUADRAMENTO")
    print("=" * 60)
    
    # Lista de PDFs para teste
    pdf_folder = "LivrosPDF"
    test_pdfs = [
        "Medicina_de_emergencia_abordagem_pratica.pdf",
        "Manual-ACLS-5°Edição.pdf",
        "livro-basico-2016.pdf"
    ]
    
    for pdf_name in test_pdfs:
        pdf_path = os.path.join(pdf_folder, pdf_name)
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF não encontrado: {pdf_name}")
            continue
        
        print(f"\n📄 Testando: {pdf_name}")
        print("-" * 40)
        
        # Teste com OpenCV melhorado
        print("🔍 Teste OpenCV com Refinamento de Bbox:")
        test_opencv_bbox(pdf_path)
        
        # Teste com Tesseract melhorado
        print("\n📝 Teste Tesseract com Bbox Otimizado:")
        test_tesseract_bbox(pdf_path)

def test_opencv_bbox(pdf_path):
    """Testa OpenCV com melhorias de bbox"""
    try:
        # Criar detector
        detector = OpenCVTableDetector(pdf_path, pages="1", min_table_area=3000)
        
        # Simular detecção para primeira página
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Detectar estrutura
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        results = []
        for i, table_info in enumerate(table_contours[:3]):  # Testar até 3 tabelas
            original_bbox = table_info['bbox']
            
            # Testar validação com refinamento
            is_valid, confidence = detector.validate_table_structure(img, original_bbox)
            
            if is_valid:
                # Testar análise de conteúdo com refinamento
                has_content, content_score, refined_bbox = detector.analyze_table_content(img, original_bbox)
                
                if has_content:
                    # Comparar bboxes
                    x1, y1, w1, h1 = original_bbox
                    x2, y2, w2, h2 = refined_bbox
                    
                    print(f"   Tabela {i+1}:")
                    print(f"     Bbox Original: ({x1}, {y1}) {w1}x{h1}")
                    print(f"     Bbox Refinado: ({x2}, {y2}) {w2}x{h2}")
                    
                    # Calcular melhoria
                    diff_x = abs(x2 - x1)
                    diff_y = abs(y2 - y1)
                    diff_w = abs(w2 - w1)
                    diff_h = abs(h2 - h1)
                    
                    print(f"     Ajustes: Δx={diff_x}, Δy={diff_y}, Δw={diff_w}, Δh={diff_h}")
                    print(f"     Confiança: {confidence:.1%} (estrutura) + {content_score:.1%} (conteúdo)")
                    
                    improvement = "✅ Melhorado" if (diff_x + diff_y + diff_w + diff_h) > 20 else "➖ Pouco ajuste"
                    print(f"     Status: {improvement}")
                    
                    results.append({
                        'original': original_bbox,
                        'refined': refined_bbox,
                        'confidence': confidence,
                        'content_score': content_score
                    })
        
        if not results:
            print("   ⚠️ Nenhuma tabela válida detectada")
        else:
            print(f"   📊 Total: {len(results)} tabelas com bbox refinado")
        
        doc.close()
        
    except Exception as e:
        print(f"   ❌ Erro no teste OpenCV: {e}")

def test_tesseract_bbox(pdf_path):
    """Testa Tesseract com bbox otimizado"""
    try:
        # Criar detector
        detector = TesseractTableDetector(pdf_path, pages="1")
        
        # Simular análise para primeira página
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        
        # Analisar layout de texto
        tables = detector.analyze_text_layout(img)
        
        if not tables:
            print("   ⚠️ Nenhuma tabela detectada pelo Tesseract")
        else:
            for i, table in enumerate(tables):
                bbox = table['bbox']
                tight_bbox = table.get('tight_bbox', False)
                
                print(f"   Tabela {i+1}:")
                print(f"     Bbox: {bbox}")
                print(f"     Dimensões: {bbox[2]}x{bbox[3]}")
                print(f"     Linhas: {table['row_count']}, Colunas: {table['column_count']}")
                print(f"     Confiança: {table['confidence']:.1%}")
                print(f"     Bbox Otimizado: {'✅ Sim' if tight_bbox else '➖ Não'}")
                print(f"     Consistência Colunas: {table['column_consistency']:.1%}")
        
        doc.close()
        
    except ImportError:
        print("   ⚠️ Tesseract não disponível (pytesseract não instalado)")
    except Exception as e:
        print(f"   ❌ Erro no teste Tesseract: {e}")

def print_improvements_summary():
    """Mostra resumo das melhorias implementadas"""
    print("\n🎯 MELHORIAS DE ENQUADRAMENTO IMPLEMENTADAS:")
    print("=" * 60)
    
    print("\n✨ OpenCV - Refinamento de Bbox:")
    print("   • refine_table_bbox(): Analisa linhas para encontrar estrutura real")
    print("   • Detecta contorno principal da tabela")
    print("   • Remove texto externo e padding desnecessário")
    print("   • Adiciona padding mínimo para capturar bordas")
    print("   • Valida dimensões antes de aceitar refinamento")
    
    print("\n✨ Tesseract - Bbox Otimizado:")
    print("   • Calcula bbox baseado apenas nas palavras detectadas")
    print("   • Padding reduzido e mais preciso")
    print("   • Margem superior baseada na altura média das linhas")
    print("   • Diferencia padding horizontal vs vertical")
    print("   • Evita capturar texto não-tabular")
    
    print("\n📈 Benefícios Esperados:")
    print("   ✅ Tabelas enquadradas precisamente")
    print("   ✅ Eliminação de texto externo")
    print("   ✅ Bordas da tabela preservadas")
    print("   ✅ Redução de cortes na parte superior/esquerda")
    print("   ✅ Melhor qualidade das imagens extraídas")
    
    print("\n🔧 Como Verificar na Aplicação:")
    print("   1. Execute a aplicação principal")
    print("   2. Vá para 'Detecção Avançada'")
    print("   3. Selecione um PDF e detecte tabelas")
    print("   4. Observe que as tabelas agora estão bem enquadradas")
    print("   5. Compare com os métodos antigos")

if __name__ == "__main__":
    test_bbox_improvements()
    print_improvements_summary()
