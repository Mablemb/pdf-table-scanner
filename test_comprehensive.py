#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Abrangente dos Detectores
Testa com diferentes PDFs para validar as melhorias
"""

import os
import cv2
import numpy as np
import fitz
from opencv_table_detector import OpenCVTableDetector, TesseractTableDetector

def test_pdf_comprehensive(pdf_path, method="opencv", max_pages=2):
    """Teste abrangente de um PDF específico"""
    pdf_name = os.path.basename(pdf_path)
    print(f"\n🔍 TESTANDO: {pdf_name}")
    print("=" * 80)
    
    try:
        # Análise inicial do PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)
        
        # Verificar tipo do PDF
        text_pages = 0
        for i in range(min(3, total_pages)):
            page = doc.load_page(i)
            text = page.get_text().strip()
            if len(text) > 50:
                text_pages += 1
        
        is_text_based = (text_pages / min(3, total_pages)) >= 0.4
        
        print(f"📊 INFORMAÇÕES BÁSICAS:")
        print(f"   📄 Páginas: {total_pages}")
        print(f"   💾 Tamanho: {file_size:.1f} MB")
        print(f"   📝 Tipo: {'Texto' if is_text_based else 'Imagem/Escaneado'}")
        print(f"   🎯 Recomendação: {'Camelot/Tesseract' if is_text_based else 'OpenCV/GPT-4'}")
        print()
        
        # Testar detecção
        detected_candidates = []
        validated_tables = []
        
        for page_num in range(min(max_pages, total_pages)):
            print(f"📄 PÁGINA {page_num + 1}:")
            
            # Renderizar página
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img_data = pix.samples
            img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            if method == "opencv":
                candidates, validated = test_opencv_on_page(img, page_num + 1)
            else:  # tesseract
                candidates, validated = test_tesseract_on_page(img, page_num + 1)
            
            detected_candidates.extend(candidates)
            validated_tables.extend(validated)
            
            print(f"   🔍 Candidatos: {len(candidates)}")
            print(f"   ✅ Validados: {len(validated)}")
            
            # Mostrar detalhes dos validados
            for i, table in enumerate(validated):
                conf = table.get('confidence', 0.0)
                bbox = table.get('bbox', (0, 0, 0, 0))
                print(f"      Tabela {i+1}: Confiança {conf:.1%}, Pos({bbox[0]}, {bbox[1]}), Tam({bbox[2]}x{bbox[3]})")
        
        doc.close()
        
        # Resumo final
        total_candidates = len(detected_candidates)
        total_validated = len(validated_tables)
        precision = (total_validated / total_candidates * 100) if total_candidates > 0 else 0
        
        print(f"\n📊 RESUMO FINAL:")
        print(f"   🔍 Total de candidatos: {total_candidates}")
        print(f"   ✅ Total validados: {total_validated}")
        print(f"   📈 Taxa de precisão: {precision:.1f}%")
        print(f"   🏆 Qualidade: {'EXCELENTE' if precision > 80 else 'BOA' if precision > 60 else 'REGULAR' if precision > 40 else 'BAIXA'}")
        
        return {
            'pdf_name': pdf_name,
            'is_text_based': is_text_based,
            'total_candidates': total_candidates,
            'total_validated': total_validated,
            'precision': precision,
            'validated_tables': validated_tables
        }
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return None

def test_opencv_on_page(img, page_num):
    """Testa OpenCV em uma página específica"""
    try:
        # Simular o detector OpenCV
        detector = OpenCVTableDetector("dummy.pdf", pages="1", min_table_area=10000)
        
        # Detectar linhas
        table_structure, h_lines, v_lines = detector.detect_lines(img)
        
        # Encontrar contornos
        table_contours = detector.find_table_contours(table_structure)
        
        candidates = []
        validated = []
        
        for table_info in table_contours:
            bbox = table_info['bbox']
            
            # Adicionar à lista de candidatos
            candidates.append({
                'page': page_num,
                'bbox': bbox,
                'area': table_info['area'],
                'method': 'opencv_candidate'
            })
            
            # Validar estrutura
            is_valid_structure, structure_conf = detector.validate_table_structure(img, bbox)
            
            # Validar conteúdo
            has_valid_content, content_conf = detector.analyze_table_content(img, bbox)
            
            # Score final
            final_conf = (structure_conf * 0.6 + content_conf * 0.4) if is_valid_structure and has_valid_content else 0.0
            
            if final_conf >= 0.6:
                validated.append({
                    'page': page_num,
                    'bbox': bbox,
                    'confidence': final_conf,
                    'structure_score': structure_conf,
                    'content_score': content_conf,
                    'method': 'opencv_validated'
                })
        
        return candidates, validated
        
    except Exception as e:
        print(f"   ❌ Erro OpenCV: {e}")
        return [], []

def test_tesseract_on_page(img, page_num):
    """Testa Tesseract em uma página específica"""
    try:
        # Simular o detector Tesseract
        detector = TesseractTableDetector("dummy.pdf", pages="1", language='por')
        
        # Analisar layout
        tables = detector.analyze_text_layout(img)
        
        candidates = []
        validated = []
        
        for table in tables:
            bbox = table['bbox']
            confidence = table['confidence']
            
            # Todos os resultados do Tesseract são candidatos
            candidates.append({
                'page': page_num,
                'bbox': bbox,
                'confidence': confidence,
                'method': 'tesseract_candidate'
            })
            
            # Só aceitar com confiança >= 70%
            if confidence >= 0.7:
                validated.append({
                    'page': page_num,
                    'bbox': bbox,
                    'confidence': confidence,
                    'row_count': table['row_count'],
                    'column_count': table['column_count'],
                    'method': 'tesseract_validated'
                })
        
        return candidates, validated
        
    except Exception as e:
        print(f"   ❌ Erro Tesseract: {e}")
        return [], []

def main():
    """Função principal - testa múltiplos PDFs"""
    print("🧪 TESTE ABRANGENTE DOS DETECTORES MELHORADOS")
    print("=" * 80)
    
    pdf_folder = "LivrosPDF"
    if not os.path.exists(pdf_folder):
        print("❌ Pasta LivrosPDF não encontrada!")
        return
    
    # PDFs para teste (escolhendo alguns mais prováveis de ter tabelas)
    test_pdfs = [
        "Manual-ACLS-5°Edição.pdf",  # Manuais médicos costumam ter tabelas
        "protocolo_suporte_avancado_vida.pdf",  # Protocolos têm tabelas
        "Hghlghts_2020ECCGuidelines_Portuguese Brazilian.pdf",  # Guidelines têm tabelas
        "livro-basico-2016.pdf"  # Livros didáticos têm tabelas
    ]
    
    # Testar com OpenCV
    print("🔬 TESTE COM OPENCV (Detecção de Linhas)")
    print("-" * 80)
    opencv_results = []
    
    for pdf_name in test_pdfs[:2]:  # Testar apenas 2 para não demorar muito
        pdf_path = os.path.join(pdf_folder, pdf_name)
        if os.path.exists(pdf_path):
            result = test_pdf_comprehensive(pdf_path, method="opencv", max_pages=2)
            if result:
                opencv_results.append(result)
        else:
            print(f"⚠️ PDF não encontrado: {pdf_name}")
    
    # Resumo OpenCV
    if opencv_results:
        avg_precision = sum(r['precision'] for r in opencv_results) / len(opencv_results)
        total_validated = sum(r['total_validated'] for r in opencv_results)
        print(f"\n📊 RESUMO OPENCV:")
        print(f"   📄 PDFs testados: {len(opencv_results)}")
        print(f"   ✅ Tabelas validadas: {total_validated}")
        print(f"   📈 Precisão média: {avg_precision:.1f}%")
    
    # Testar com Tesseract (se disponível)
    print(f"\n🔤 TESTE COM TESSERACT (Análise de Texto)")
    print("-" * 80)
    
    try:
        import pytesseract
        tesseract_available = True
    except ImportError:
        tesseract_available = False
        print("⚠️ Tesseract não disponível - instale com: pip install pytesseract")
    
    if tesseract_available:
        tesseract_results = []
        
        for pdf_name in test_pdfs[:2]:  # Testar apenas 2
            pdf_path = os.path.join(pdf_folder, pdf_name)
            if os.path.exists(pdf_path):
                result = test_pdf_comprehensive(pdf_path, method="tesseract", max_pages=2)
                if result:
                    tesseract_results.append(result)
        
        # Resumo Tesseract
        if tesseract_results:
            avg_precision = sum(r['precision'] for r in tesseract_results) / len(tesseract_results)
            total_validated = sum(r['total_validated'] for r in tesseract_results)
            print(f"\n📊 RESUMO TESSERACT:")
            print(f"   📄 PDFs testados: {len(tesseract_results)}")
            print(f"   ✅ Tabelas validadas: {total_validated}")
            print(f"   📈 Precisão média: {avg_precision:.1f}%")
    
    print("\n" + "=" * 80)
    print("✅ TESTE ABRANGENTE CONCLUÍDO!")
    print("💡 Recomendações:")
    print("   🔹 Use OpenCV para PDFs escaneados com bordas visíveis")
    print("   🔹 Use Tesseract para PDFs com texto e estruturas alinhadas")
    print("   🔹 Use Camelot para PDFs com texto selecionável")
    print("   🔹 Use GPT-4 Vision para casos complexos ou tabelas irregulares")
    print("   🔹 Teste na aplicação principal para validação visual!")

if __name__ == "__main__":
    main()
