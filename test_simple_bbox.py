#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Simples das Melhorias de Enquadramento
"""

import cv2
import numpy as np
import fitz
import os

def simple_test():
    """Teste simples para verificar as melhorias"""
    
    print("🔧 TESTE SIMPLES - MELHORIAS DE ENQUADRAMENTO")
    print("=" * 50)
    
    # Testar um PDF específico
    pdf_path = os.path.join("LivrosPDF", "Medicina_de_emergencia_abordagem_pratica.pdf")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF não encontrado")
        return
    
    try:
        from opencv_table_detector import OpenCVTableDetector
        
        print(f"📄 Testando: {os.path.basename(pdf_path)}")
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)  # Primeira página
        pix = page.get_pixmap(dpi=150)
        img_data = pix.samples
        
        # Converter para OpenCV
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        print(f"📐 Dimensões da página: {img.shape[1]}x{img.shape[0]}")
        
        # Criar detector
        detector = OpenCVTableDetector(pdf_path, pages="1", min_table_area=1000)  # Área menor
        
        # Detectar estrutura
        table_structure, h_lines, v_lines = detector.detect_lines(img)
        
        # Encontrar contornos
        table_contours = detector.find_table_contours(table_structure)
        
        print(f"🔍 Candidatos encontrados: {len(table_contours)}")
        
        validated_count = 0
        refined_count = 0
        
        for i, table_info in enumerate(table_contours[:5]):  # Testar até 5
            original_bbox = table_info['bbox']
            
            print(f"\n📋 Candidato {i+1}:")
            print(f"   Bbox Original: {original_bbox}")
            print(f"   Área: {table_info['area']}")
            
            # Testar validação
            is_valid, structure_conf = detector.validate_table_structure(img, original_bbox)
            print(f"   Estrutura válida: {'✅' if is_valid else '❌'} ({structure_conf:.1%})")
            
            if is_valid:
                # Testar refinamento
                print(f"   🔍 Chamando analyze_table_content...")
                has_content, content_conf, refined_bbox = detector.analyze_table_content(img, original_bbox)
                print(f"   📤 Retornou: has_content={has_content}, score={content_conf}")
                print(f"   Conteúdo válido: {'✅' if has_content else '❌'} ({content_conf:.1%})")
                
                if has_content:
                    validated_count += 1
                    
                    # Verificar se bbox foi refinado
                    if refined_bbox != original_bbox:
                        refined_count += 1
                        print(f"   Bbox Refinado: {refined_bbox}")
                        
                        # Calcular diferenças
                        x1, y1, w1, h1 = original_bbox
                        x2, y2, w2, h2 = refined_bbox
                        
                        dx = x2 - x1
                        dy = y2 - y1
                        dw = w2 - w1
                        dh = h2 - h1
                        
                        print(f"   Ajustes: dx={dx:+d}, dy={dy:+d}, dw={dw:+d}, dh={dh:+d}")
                        print("   ✅ Bbox refinado com sucesso!")
                    else:
                        print("   ➖ Bbox não necessitou refinamento")
                    
                    final_conf = (structure_conf * 0.6 + content_conf * 0.4)
                    print(f"   Confiança Final: {final_conf:.1%}")
        
        print(f"\n📊 RESULTADOS:")
        print(f"   Candidatos testados: {min(len(table_contours), 5)}")
        print(f"   Tabelas validadas: {validated_count}")
        print(f"   Bboxes refinados: {refined_count}")
        print(f"   Taxa de refinamento: {refined_count/max(validated_count,1):.1%}")
        
        doc.close()
        
        # Mostrar melhorias
        print(f"\n🎯 MELHORIAS IMPLEMENTADAS:")
        print("   ✅ Algoritmo de refinamento de bbox")
        print("   ✅ Detecção de contorno principal da tabela")
        print("   ✅ Remoção de texto externo")
        print("   ✅ Padding otimizado")
        print("   ✅ Validação de dimensões")
        
        print(f"\n💡 NEXT STEPS:")
        print("   1. Execute a aplicação principal")
        print("   2. Teste na aba 'Detecção Avançada'")
        print("   3. Compare o enquadramento antes/depois")
        print("   4. Verifique se as tabelas estão bem cortadas")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test()
