#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Comparativo: Detector vs Aplicação Principal
Identifica onde está a discrepância no corte das tabelas
"""

import cv2
import numpy as np
import fitz
import os

def test_detector_vs_app():
    """Compara o comportamento do detector isolado vs aplicação principal"""
    
    print("🔍 TESTE: DETECTOR vs APLICAÇÃO")
    print("=" * 50)
    
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        # === TESTE 1: SIMULAÇÃO DO DETECTOR ISOLADO ===
        print("\n📋 TESTE 1: Detector Isolado")
        print("-" * 30)
        
        # Abrir PDF da mesma forma que o detector
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV (mesma forma que o detector)
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"📐 Imagem: {img.shape}")
        
        # Executar detecção completa
        detector = OpenCVTableDetector(pdf_path, pages="1", min_table_area=3000)
        
        # Simular o processo completo
        table_structure, _, _ = detector.detect_lines(img)
        table_contours = detector.find_table_contours(table_structure)
        
        validated_tables = []
        
        for j, table_info in enumerate(table_contours):
            bbox = table_info['bbox']
            
            # Validação 1: Estrutura
            is_valid_structure, structure_confidence = detector.validate_table_structure(img, bbox)
            
            if not is_valid_structure:
                continue
            
            # Validação 2: Conteúdo (com refinamento)
            has_valid_content, content_confidence, refined_bbox = detector.analyze_table_content(img, bbox)
            
            if not has_valid_content:
                continue
            
            # Score final
            final_confidence = (structure_confidence * 0.6 + content_confidence * 0.4)
            
            if final_confidence >= 0.3:
                table_data = {
                    'page': 1,
                    'table_index': len(validated_tables),
                    'bbox': refined_bbox,  # Usar bbox refinado
                    'area': refined_bbox[2] * refined_bbox[3],
                    'aspect_ratio': refined_bbox[2] / refined_bbox[3],
                    'confidence': final_confidence,
                    'structure_score': structure_confidence,
                    'content_score': content_confidence,
                    'original_bbox': bbox,
                    'bbox_refined': True
                }
                validated_tables.append(table_data)
        
        print(f"✅ Tabelas detectadas pelo algoritmo: {len(validated_tables)}")
        
        for i, table in enumerate(validated_tables):
            bbox = table['bbox']
            original_bbox = table['original_bbox']
            
            print(f"\n📋 Tabela {i+1}:")
            print(f"   Bbox Original: {original_bbox}")
            print(f"   Bbox Refinado: {bbox}")
            print(f"   Confiança: {table['confidence']:.1%}")
            
            # Extrair com bbox refinado (como o algoritmo faz)
            x, y, w, h = bbox
            
            try:
                table_roi = img[y:y+h, x:x+w]
                output_filename = f"detector_tabela_{i+1}.png"
                cv2.imwrite(output_filename, table_roi)
                print(f"   💾 Salvo: {output_filename} - {table_roi.shape}")
                
                # Verificar se é uma tabela real
                gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
                binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                text_regions = 0
                for contour in text_contours:
                    x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
                    area = w_cont * h_cont
                    if 20 <= area <= 8000 and 3 <= w_cont <= 300 and 3 <= h_cont <= 80:
                        text_regions += 1
                
                print(f"   📝 Regiões de texto: {text_regions}")
                
                # Análise visual básica
                if text_regions >= 5:
                    print(f"   ✅ Parece uma tabela válida")
                elif text_regions >= 1:
                    print(f"   ⚠️ Pouco texto, mas pode ser tabela")
                else:
                    print(f"   ❌ Sem texto detectado")
                
            except Exception as e:
                print(f"   ❌ Erro ao extrair: {e}")
        
        doc.close()
        
        # === TESTE 2: SIMULAÇÃO DA APLICAÇÃO PRINCIPAL ===
        print(f"\n📱 TESTE 2: Simulação da Aplicação Principal")
        print("-" * 40)
        
        print("🔍 Verificando como a aplicação principal usa os resultados...")
        
        # A aplicação principal recebe os resultados do detector
        # e usa os bboxes para extrair e salvar as tabelas
        
        if validated_tables:
            # Simular o que a aplicação principal faria
            for i, table in enumerate(validated_tables):
                bbox = table['bbox']  # Este é o bbox que a aplicação recebe
                x, y, w, h = bbox
                
                print(f"\n🔄 Processando tabela {i+1} (como a aplicação faria):")
                print(f"   Bbox recebido: {bbox}")
                
                # Reabrir PDF (como a aplicação principal faz)
                doc_app = fitz.open(pdf_path)
                page_app = doc_app.load_page(0)
                pix_app = page_app.get_pixmap(dpi=150)  # Mesmo DPI
                img_data_app = pix_app.samples
                
                # Converter (mesmo processo)
                img_app = np.frombuffer(img_data_app, dtype=np.uint8).reshape(pix_app.height, pix_app.width, 3)
                img_app = cv2.cvtColor(img_app, cv2.COLOR_RGB2BGR)
                
                # Verificar se as imagens são idênticas
                images_identical = np.array_equal(img, img_app)
                print(f"   Imagens idênticas: {'✅' if images_identical else '❌'}")
                
                # Extrair tabela (como a aplicação faria)
                try:
                    table_roi_app = img_app[y:y+h, x:x+w]
                    output_filename_app = f"aplicacao_tabela_{i+1}.png"
                    cv2.imwrite(output_filename_app, table_roi_app)
                    print(f"   💾 Salvo pela 'aplicação': {output_filename_app} - {table_roi_app.shape}")
                    
                    # Comparar com resultado do detector
                    detector_file = f"detector_tabela_{i+1}.png"
                    if os.path.exists(detector_file):
                        detector_img = cv2.imread(detector_file)
                        results_identical = np.array_equal(table_roi_app, detector_img)
                        print(f"   Resultados idênticos: {'✅' if results_identical else '❌'}")
                        
                        if not results_identical:
                            print(f"   ⚠️ DISCREPÂNCIA ENCONTRADA!")
                            print(f"   Detector: {detector_img.shape if detector_img is not None else 'None'}")
                            print(f"   Aplicação: {table_roi_app.shape}")
                    
                except Exception as e:
                    print(f"   ❌ Erro na 'aplicação': {e}")
                
                doc_app.close()
        
        # === ANÁLISE FINAL ===
        print(f"\n🎯 ANÁLISE FINAL:")
        print("-" * 20)
        
        print("📁 Arquivos gerados para análise:")
        for i in range(len(validated_tables)):
            detector_file = f"detector_tabela_{i+1}.png"
            app_file = f"aplicacao_tabela_{i+1}.png"
            
            if os.path.exists(detector_file):
                print(f"   📋 {detector_file} (resultado do detector)")
            if os.path.exists(app_file):
                print(f"   📱 {app_file} (resultado da aplicação)")
        
        print(f"\n💡 Próximos passos:")
        print(f"   1. Examine as imagens geradas visualmente")
        print(f"   2. Compare se as tabelas estão bem enquadradas")
        print(f"   3. Se houver discrepância, o problema está na aplicação")
        print(f"   4. Se as imagens estão ruins, o problema está no detector")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detector_vs_app()
