#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector OpenCV Aprimorado para Tabelas Complexas
Focado em detectar todas as tabelas das páginas 1713-1717
"""

import os
import cv2
import numpy as np
import fitz
import json
from datetime import datetime

class EnhancedTableDetector:
    """Detector aprimorado para tabelas complexas e sutis"""
    
    def __init__(self):
        self.pdf_path = "LivrosPDF/Medicina_de_emergencia_abordagem_pratica.pdf"
        self.target_pages = [1713, 1714, 1715, 1716, 1717]
        self.output_dir = f"deteccao_aprimorada_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_page_as_image(self, page_num, dpi=3.0):
        """Carrega página como imagem em alta resolução"""
        doc = fitz.open(self.pdf_path)
        page = doc[page_num - 1]
        
        # DPI muito alto para capturar detalhes sutis
        mat = fitz.Matrix(dpi, dpi)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Converter para OpenCV
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        doc.close()
        return img
    
    def detect_subtle_tables(self, img, page_num):
        """Detecta tabelas sutis com múltiplas técnicas refinadas"""
        print(f"   🔍 Análise detalhada da página {page_num}...")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Salvar imagem original
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_01_original.png"), img)
        
        all_tables = []
        
        # Método 1: Detecção ultra-sensível de linhas
        tables1 = self.detect_ultra_sensitive_lines(gray.copy(), page_num)
        all_tables.extend(tables1)
        print(f"      📏 Linhas ultra-sensíveis: {len(tables1)} tabela(s)")
        
        # Método 2: Análise de densidade textual
        tables2 = self.detect_by_text_density(gray.copy(), page_num)
        all_tables.extend(tables2)
        print(f"      📝 Densidade textual: {len(tables2)} tabela(s)")
        
        # Método 3: Detecção de padrões regulares
        tables3 = self.detect_regular_patterns(gray.copy(), page_num)
        all_tables.extend(tables3)
        print(f"      🔲 Padrões regulares: {len(tables3)} tabela(s)")
        
        # Método 4: Análise de espaçamento
        tables4 = self.detect_by_spacing_analysis(gray.copy(), page_num)
        all_tables.extend(tables4)
        print(f"      📐 Análise de espaçamento: {len(tables4)} tabela(s)")
        
        # Método 5: Detecção por segmentação de regiões
        tables5 = self.detect_by_region_segmentation(gray.copy(), page_num)
        all_tables.extend(tables5)
        print(f"      🗂️ Segmentação de regiões: {len(tables5)} tabela(s)")
        
        # Consolidar todas as detecções
        final_tables = self.smart_consolidation(all_tables, img, page_num)
        
        # Salvar resultado final
        self.visualize_final_result(img, final_tables, page_num)
        
        print(f"      ✅ TOTAL FINAL: {len(final_tables)} tabela(s)")
        return final_tables
    
    def detect_ultra_sensitive_lines(self, gray, page_num):
        """Detecção ultra-sensível de linhas horizontais e verticais"""
        
        # Múltiplos kernels para diferentes espessuras de linha
        kernels = [
            # Linhas muito finas
            cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50)),
            # Linhas médias
            cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30)),
            # Linhas grossas
            cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1)),
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20)),
        ]
        
        all_lines = np.zeros_like(gray)
        
        for i, kernel in enumerate(kernels):
            # Aplicar operação morfológica
            lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            
            # Threshold mais sensível
            _, lines_thresh = cv2.threshold(lines, 127, 255, cv2.THRESH_BINARY)
            
            # Acumular linhas
            all_lines = cv2.bitwise_or(all_lines, lines_thresh)
            
            # Salvar para debug
            cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_02_lines_{i}.png"), lines_thresh)
        
        # Salvar resultado combinado
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_02_all_lines.png"), all_lines)
        
        # Encontrar contornos das intersecções
        contours, _ = cv2.findContours(all_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar por área mínima muito baixa para capturar tabelas pequenas
        min_area = 1000
        tables = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                # Verificar proporção mínima
                if w > 50 and h > 30:
                    tables.append((x, y, w, h, 'lines'))
        
        return tables
    
    def detect_by_text_density(self, gray, page_num):
        """Detecta tabelas pela densidade e alinhamento de texto"""
        
        # Aplicar threshold adaptativo para destacar texto
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY_INV, 15, 10)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_03_adaptive.png"), adaptive)
        
        # Aplicar operação de fechamento para conectar caracteres
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        connected_text = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_03_connected.png"), connected_text)
        
        # Encontrar contornos de regiões de texto
        contours, _ = cv2.findContours(connected_text, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analisar densidade de contornos pequenos (caracteres)
        text_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 20 < area < 500:  # Tamanho típico de caracteres
                x, y, w, h = cv2.boundingRect(contour)
                text_regions.append((x, y, w, h))
        
        # Agrupar regiões próximas (possíveis tabelas)
        tables = self.group_text_regions(text_regions, page_num)
        
        return tables
    
    def group_text_regions(self, text_regions, page_num):
        """Agrupa regiões de texto próximas em possíveis tabelas"""
        
        if not text_regions:
            return []
        
        # Criar grid para análise de densidade
        img_height, img_width = 3000, 2000  # Estimativa baseada no DPI
        grid_size = 100
        grid = np.zeros((img_height // grid_size, img_width // grid_size))
        
        # Marcar células do grid com texto
        for x, y, w, h in text_regions:
            grid_x = min(x // grid_size, grid.shape[1] - 1)
            grid_y = min(y // grid_size, grid.shape[0] - 1)
            grid[grid_y, grid_x] += 1
        
        # Encontrar regiões de alta densidade
        threshold = np.percentile(grid[grid > 0], 75)  # 75% das regiões com texto
        high_density = grid > threshold
        
        # Conectar regiões próximas
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        connected = cv2.morphologyEx(high_density.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
        
        # Encontrar componentes conectados
        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        for contour in contours:
            # Converter coordenadas do grid de volta para pixels
            x_grid, y_grid, w_grid, h_grid = cv2.boundingRect(contour)
            
            x = x_grid * grid_size
            y = y_grid * grid_size
            w = w_grid * grid_size
            h = h_grid * grid_size
            
            # Filtrar por tamanho mínimo
            if w > 200 and h > 100:
                tables.append((x, y, w, h, 'text_density'))
        
        return tables
    
    def detect_regular_patterns(self, gray, page_num):
        """Detecta padrões regulares que indicam estrutura tabular"""
        
        # Aplicar filtro de detecção de bordas mais sensível
        edges = cv2.Canny(gray, 30, 100, apertureSize=3)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_04_edges.png"), edges)
        
        # Detectar linhas usando Transform de Hough
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=30, maxLineGap=10)
        
        if lines is None:
            return []
        
        # Separar linhas horizontais e verticais
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            if abs(angle) < 10 or abs(angle) > 170:  # Linha horizontal
                horizontal_lines.append(line[0])
            elif 80 < abs(angle) < 100:  # Linha vertical
                vertical_lines.append(line[0])
        
        # Criar imagem com linhas
        line_img = np.zeros_like(gray)
        
        for x1, y1, x2, y2 in horizontal_lines:
            cv2.line(line_img, (x1, y1), (x2, y2), 255, 2)
        
        for x1, y1, x2, y2 in vertical_lines:
            cv2.line(line_img, (x1, y1), (x2, y2), 255, 2)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_04_detected_lines.png"), line_img)
        
        # Encontrar intersecções de linhas (possíveis cantos de tabelas)
        intersections = self.find_line_intersections(horizontal_lines, vertical_lines)
        
        # Agrupar intersecções em retângulos (tabelas)
        tables = self.group_intersections_to_tables(intersections, page_num)
        
        return tables
    
    def find_line_intersections(self, h_lines, v_lines):
        """Encontra intersecções entre linhas horizontais e verticais"""
        intersections = []
        
        for hx1, hy1, hx2, hy2 in h_lines:
            for vx1, vy1, vx2, vy2 in v_lines:
                # Verificar se as linhas se cruzam
                h_min_x, h_max_x = min(hx1, hx2), max(hx1, hx2)
                v_min_y, v_max_y = min(vy1, vy2), max(vy1, vy2)
                
                # Coordenadas da intersecção
                x = (vx1 + vx2) // 2  # Centro da linha vertical
                y = (hy1 + hy2) // 2  # Centro da linha horizontal
                
                # Verificar se está dentro dos limites
                if h_min_x <= x <= h_max_x and v_min_y <= y <= v_max_y:
                    intersections.append((x, y))
        
        return intersections
    
    def group_intersections_to_tables(self, intersections, page_num):
        """Agrupa intersecções próximas em retângulos de tabelas"""
        if len(intersections) < 4:
            return []
        
        # Ordenar intersecções por posição
        intersections.sort(key=lambda p: (p[1], p[0]))  # Por Y depois por X
        
        tables = []
        
        # Tentar formar retângulos com 4 pontos
        for i in range(len(intersections)):
            for j in range(i + 1, len(intersections)):
                for k in range(j + 1, len(intersections)):
                    for l in range(k + 1, len(intersections)):
                        
                        points = [intersections[i], intersections[j], 
                                intersections[k], intersections[l]]
                        
                        # Verificar se formam um retângulo aproximado
                        rect = self.check_rectangle_formation(points)
                        if rect:
                            x, y, w, h = rect
                            if w > 100 and h > 50:  # Tamanho mínimo
                                tables.append((x, y, w, h, 'intersections'))
        
        return tables
    
    def check_rectangle_formation(self, points):
        """Verifica se 4 pontos formam aproximadamente um retângulo"""
        if len(points) != 4:
            return None
        
        # Ordenar pontos
        points.sort(key=lambda p: (p[1], p[0]))
        
        # Verificar se formam um padrão retangular
        top_left, top_right = sorted(points[:2], key=lambda p: p[0])
        bottom_left, bottom_right = sorted(points[2:], key=lambda p: p[0])
        
        # Verificar alinhamento
        tolerance = 20
        
        # Verificar se as bordas são aproximadamente alinhadas
        if (abs(top_left[0] - bottom_left[0]) < tolerance and
            abs(top_right[0] - bottom_right[0]) < tolerance and
            abs(top_left[1] - top_right[1]) < tolerance and
            abs(bottom_left[1] - bottom_right[1]) < tolerance):
            
            x = min(top_left[0], bottom_left[0])
            y = min(top_left[1], top_right[1])
            w = max(top_right[0], bottom_right[0]) - x
            h = max(bottom_left[1], bottom_right[1]) - y
            
            return (x, y, w, h)
        
        return None
    
    def detect_by_spacing_analysis(self, gray, page_num):
        """Detecta tabelas pela análise de espaçamento regular"""
        
        # Aplicar threshold para binarizar
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_05_binary.png"), binary)
        
        # Analisar projeções horizontais e verticais
        h_projection = np.sum(binary, axis=1)  # Soma por linha
        v_projection = np.sum(binary, axis=0)  # Soma por coluna
        
        # Encontrar regiões com espaçamento regular
        h_peaks = self.find_regular_spacing(h_projection, min_distance=20)
        v_peaks = self.find_regular_spacing(v_projection, min_distance=30)
        
        # Formar retângulos baseados em picos regulares
        tables = []
        for i in range(len(h_peaks) - 1):
            for j in range(len(v_peaks) - 1):
                y1, y2 = h_peaks[i], h_peaks[i + 1]
                x1, x2 = v_peaks[j], v_peaks[j + 1]
                
                w = x2 - x1
                h = y2 - y1
                
                if w > 150 and h > 80:  # Tamanho mínimo para tabela
                    tables.append((x1, y1, w, h, 'spacing'))
        
        return tables
    
    def find_regular_spacing(self, projection, min_distance=30):
        """Encontra picos com espaçamento regular em uma projeção"""
        
        # Encontrar picos na projeção
        mean_val = np.mean(projection)
        peaks = []
        
        for i in range(1, len(projection) - 1):
            if (projection[i] > projection[i-1] and 
                projection[i] > projection[i+1] and
                projection[i] > mean_val):
                peaks.append(i)
        
        # Filtrar picos muito próximos
        filtered_peaks = []
        for peak in peaks:
            if not filtered_peaks or abs(peak - filtered_peaks[-1]) > min_distance:
                filtered_peaks.append(peak)
        
        return filtered_peaks
    
    def detect_by_region_segmentation(self, gray, page_num):
        """Detecta tabelas por segmentação de regiões uniformes"""
        
        # Aplicar segmentação por watershed
        # Primeiro, encontrar marcadores
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Ruído reduction
        kernel = np.ones((3,3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Área de fundo definida
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Área de primeiro plano definida
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.7*dist_transform.max(), 255, 0)
        
        # Região desconhecida
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        cv2.imwrite(os.path.join(self.output_dir, f"p{page_num}_06_watershed_prep.png"), unknown)
        
        # Encontrar componentes conectados
        contours, _ = cv2.findContours(sure_fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 2000:  # Área mínima
                x, y, w, h = cv2.boundingRect(contour)
                if w > 100 and h > 60:
                    tables.append((x, y, w, h, 'segmentation'))
        
        return tables
    
    def smart_consolidation(self, all_tables, img, page_num):
        """Consolidação inteligente de todas as detecções"""
        
        if not all_tables:
            return []
        
        print(f"      🔗 Consolidando {len(all_tables)} detecções...")
        
        # Remover duplicatas por sobreposição
        consolidated = []
        
        for table in all_tables:
            x, y, w, h = table[:4]
            method = table[4] if len(table) > 4 else 'unknown'
            
            # Verificar sobreposição com tabelas já consolidadas
            is_duplicate = False
            for existing in consolidated:
                ex, ey, ew, eh = existing[:4]
                
                # Calcular IoU (Intersection over Union)
                iou = self.calculate_iou((x, y, w, h), (ex, ey, ew, eh))
                
                if iou > 0.5:  # 50% de sobreposição
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Adicionar informações extras
                confidence = self.calculate_table_confidence(img, x, y, w, h)
                consolidated.append((x, y, w, h, method, confidence))
        
        # Ordenar por confiança
        consolidated.sort(key=lambda t: t[5], reverse=True)
        
        # Filtrar por qualidade
        final_tables = []
        for table in consolidated:
            x, y, w, h, method, confidence = table
            
            # Filtros de qualidade
            if (w > 80 and h > 40 and  # Tamanho mínimo
                confidence > 0.3 and    # Confiança mínima
                0.1 < h/w < 10):       # Proporção razoável
                
                final_tables.append((x, y, w, h, method, confidence))
        
        return final_tables
    
    def calculate_iou(self, box1, box2):
        """Calcula Intersection over Union entre duas caixas"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Coordenadas da intersecção
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        # Áreas
        inter_area = (xi2 - xi1) * (yi2 - yi1)
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def calculate_table_confidence(self, img, x, y, w, h):
        """Calcula confiança de que uma região é realmente uma tabela"""
        
        # Extrair região
        roi = img[y:y+h, x:x+w]
        if roi.size == 0:
            return 0.0
        
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Fatores de confiança
        confidence_factors = []
        
        # 1. Densidade de bordas
        edges = cv2.Canny(gray_roi, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        confidence_factors.append(min(edge_density * 10, 1.0))
        
        # 2. Regularidade de padrões
        h_projection = np.sum(gray_roi, axis=1)
        v_projection = np.sum(gray_roi, axis=0)
        
        h_std = np.std(h_projection) / (np.mean(h_projection) + 1)
        v_std = np.std(v_projection) / (np.mean(v_projection) + 1)
        
        regularity = 1.0 / (1.0 + h_std + v_std)
        confidence_factors.append(regularity)
        
        # 3. Proporção
        aspect_ratio = w / h if h > 0 else 0
        aspect_confidence = 1.0 if 0.5 <= aspect_ratio <= 8 else 0.5
        confidence_factors.append(aspect_confidence)
        
        # 4. Tamanho relativo
        total_area = img.shape[0] * img.shape[1]
        relative_size = (w * h) / total_area
        size_confidence = min(relative_size * 50, 1.0)  # Penalizar tabelas muito pequenas
        confidence_factors.append(size_confidence)
        
        # Média ponderada
        weights = [0.3, 0.3, 0.2, 0.2]
        final_confidence = sum(w * f for w, f in zip(weights, confidence_factors))
        
        return final_confidence
    
    def visualize_final_result(self, img, tables, page_num):
        """Visualiza resultado final com todas as tabelas detectadas"""
        
        result_img = img.copy()
        
        # Cores para diferentes métodos
        colors = {
            'lines': (0, 255, 0),           # Verde
            'text_density': (255, 0, 0),    # Azul
            'intersections': (0, 255, 255), # Amarelo
            'spacing': (255, 0, 255),       # Magenta
            'segmentation': (255, 255, 0),  # Ciano
            'unknown': (128, 128, 128)      # Cinza
        }
        
        for i, table in enumerate(tables):
            x, y, w, h = table[:4]
            method = table[4] if len(table) > 4 else 'unknown'
            confidence = table[5] if len(table) > 5 else 0.0
            
            color = colors.get(method, (128, 128, 128))
            
            # Desenhar retângulo
            cv2.rectangle(result_img, (x, y), (x + w, y + h), color, 4)
            
            # Adicionar texto com informações
            label = f"T{i+1}: {method[:4]} ({confidence:.2f})"
            cv2.putText(result_img, label, (x + 5, y + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # Salvar resultado
        output_path = os.path.join(self.output_dir, f"p{page_num}_FINAL_result.png")
        cv2.imwrite(output_path, result_img)
        
        return output_path
    
    def analyze_all_pages(self):
        """Analisa todas as páginas com detector aprimorado"""
        
        print("🔍 DETECTOR OPENCV APRIMORADO - ANÁLISE COMPLETA")
        print("=" * 70)
        
        all_results = {}
        
        for page_num in self.target_pages:
            print(f"\n📄 PÁGINA {page_num}:")
            print("-" * 50)
            
            # Carregar imagem em alta resolução
            img = self.load_page_as_image(page_num, dpi=3.0)
            
            if img is None:
                print(f"   ❌ Erro ao carregar página {page_num}")
                continue
            
            # Detectar tabelas
            tables = self.detect_subtle_tables(img, page_num)
            
            all_results[page_num] = {
                'total_tables': len(tables),
                'tables': tables,
                'image_size': img.shape
            }
        
        # Salvar resultados
        self.save_enhanced_results(all_results)
        
        # Relatório final
        self.generate_enhanced_report(all_results)
        
        return all_results
    
    def save_enhanced_results(self, results):
        """Salva resultados aprimorados"""
        
        # Converter para formato serializável
        serializable_results = {}
        for page_num, data in results.items():
            serializable_results[page_num] = {
                'total_tables': data['total_tables'],
                'image_size': data['image_size'],
                'tables': []
            }
            
            for table in data['tables']:
                x, y, w, h = table[:4]
                method = table[4] if len(table) > 4 else 'unknown'
                confidence = table[5] if len(table) > 5 else 0.0
                
                serializable_results[page_num]['tables'].append({
                    'bbox': [x, y, w, h],
                    'method': method,
                    'confidence': confidence,
                    'area': w * h
                })
        
        # Salvar JSON
        output_file = os.path.join(self.output_dir, "deteccao_aprimorada_completa.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados salvos: {output_file}")
    
    def generate_enhanced_report(self, results):
        """Gera relatório detalhado dos resultados aprimorados"""
        
        print(f"\n📋 RELATÓRIO DETALHADO - DETECTOR APRIMORADO")
        print("=" * 70)
        
        total_tables = 0
        method_counts = {}
        confidence_stats = []
        
        for page_num, data in results.items():
            page_tables = data['total_tables']
            total_tables += page_tables
            
            print(f"\n📄 PÁGINA {page_num}: {page_tables} tabela(s)")
            
            for i, table in enumerate(data['tables']):
                x, y, w, h = table[:4]
                method = table[4] if len(table) > 4 else 'unknown'
                confidence = table[5] if len(table) > 5 else 0.0
                
                # Estatísticas por método
                method_counts[method] = method_counts.get(method, 0) + 1
                confidence_stats.append(confidence)
                
                print(f"   T{i+1}: {w}×{h}px | {method} | {confidence:.2f}")
        
        print(f"\n🎯 RESUMO GERAL:")
        print(f"   📚 Páginas: {len(self.target_pages)}")
        print(f"   📊 Total de tabelas: {total_tables}")
        
        print(f"\n📈 POR MÉTODO:")
        for method, count in method_counts.items():
            percentage = (count / total_tables) * 100 if total_tables > 0 else 0
            print(f"   {method}: {count} ({percentage:.1f}%)")
        
        if confidence_stats:
            avg_confidence = np.mean(confidence_stats)
            print(f"\n🎖️ CONFIANÇA MÉDIA: {avg_confidence:.2f}")
            print(f"   📁 Resultados em: {self.output_dir}")
        
        return {
            'total_pages': len(self.target_pages),
            'total_tables': total_tables,
            'method_distribution': method_counts,
            'avg_confidence': np.mean(confidence_stats) if confidence_stats else 0,
            'output_dir': self.output_dir
        }

def main():
    """Função principal"""
    detector = EnhancedTableDetector()
    detector.analyze_all_pages()

if __name__ == "__main__":
    main()
