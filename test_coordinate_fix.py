#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Final - Correção de Coordenadas
"""

import fitz

def test_coordinate_conversion():
    """Testa a conversão de coordenadas"""
    
    print("🧪 TESTE DE CONVERSÃO DE COORDENADAS")
    print("=" * 40)
    
    # Simular bbox do OpenCV: (x, y, width, height)
    opencv_bbox = (212, 401, 761, 347)
    x, y, w, h = opencv_bbox
    
    print(f"📋 Bbox OpenCV: {opencv_bbox}")
    print(f"   x={x}, y={y}, width={w}, height={h}")
    
    # Conversão INCORRETA (antiga)
    rect_incorreto = fitz.Rect(x, y, w, h)
    print(f"❌ Conversão INCORRETA: {tuple(rect_incorreto)}")
    print(f"   Interpreta width={w} como x2, height={h} como y2")
    
    # Conversão CORRETA (nova)
    rect_correto = fitz.Rect(x, y, x + w, y + h)
    print(f"✅ Conversão CORRETA: {tuple(rect_correto)}")
    print(f"   x1={x}, y1={y}, x2={x+w}, y2={y+h}")
    
    # Comparar áreas
    area_opencv = w * h
    area_incorreta = rect_incorreto.width * rect_incorreto.height
    area_correta = rect_correto.width * rect_correto.height
    
    print(f"\n📊 COMPARAÇÃO DE ÁREAS:")
    print(f"   OpenCV: {area_opencv} pixels")
    print(f"   Incorreta: {area_incorreta:.0f} pixels")
    print(f"   Correta: {area_correta:.0f} pixels")
    
    print(f"\n🎯 RESULTADO:")
    if abs(area_opencv - area_correta) < 1:
        print("✅ Conversão correta preserva a área!")
    else:
        print("❌ Área não bate")
    
    # Verificar posições
    print(f"\n📐 POSIÇÕES:")
    print(f"   OpenCV canto superior esquerdo: ({x}, {y})")
    print(f"   Correta canto superior esquerdo: ({rect_correto.x0}, {rect_correto.y0})")
    print(f"   OpenCV canto inferior direito: ({x+w}, {y+h})")
    print(f"   Correta canto inferior direito: ({rect_correto.x1}, {rect_correto.y1})")

if __name__ == "__main__":
    test_coordinate_conversion()
