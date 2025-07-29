#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector de Tabelas usando OpenCV
Detecta tabelas em imagens através de análise de linhas e contornos
"""

import cv2
import numpy as np
import fitz
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
import os


class OpenCVTableDetector(QThread):
    """Thread para detecção de tabelas usando OpenCV"""
    
    progress_updated = pyqtSignal(int, str)
    tables_detected = pyqtSignal(list)  # Lista de regiões de tabelas detectadas
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path, pages="all", min_table_area=5000):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.min_table_area = min_table_area
        self.should_stop = False
    
    def detect_lines(self, image):
        """Detecta linhas horizontais e verticais na imagem com parâmetros otimizados"""
        # Converter para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar filtro bilateral para reduzir ruído mantendo bordas
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Threshold adaptivo para lidar com variações de iluminação
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Detectar linhas horizontais com kernel mais específico
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))  # Aumentei de 40 para 80
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detectar linhas verticais com kernel mais específico
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 80))  # Aumentei de 40 para 80
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combinar linhas com pesos balanceados
        table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
        
        return table_structure, horizontal_lines, vertical_lines
    
    def refine_table_bbox(self, image, initial_bbox):
        """Refina o bounding box para enquadrar melhor a tabela real"""
        x, y, w, h = initial_bbox
        
        # Se o bbox já é pequeno, não refinar muito
        if w < 200 or h < 100:
            return initial_bbox
        
        # Extrair região com margem pequena para análise
        margin = 10  # Margem reduzida de 20 para 10
        extended_x = max(0, x - margin)
        extended_y = max(0, y - margin)
        extended_w = min(image.shape[1] - extended_x, w + 2 * margin)
        extended_h = min(image.shape[0] - extended_y, h + 2 * margin)
        
        extended_roi = image[extended_y:extended_y+extended_h, extended_x:extended_x+extended_w]
        
        # Detectar linhas na região estendida
        _, h_lines, v_lines = self.detect_lines(extended_roi)
        
        # Combinar linhas para encontrar estrutura da tabela
        combined_lines = cv2.bitwise_or(h_lines, v_lines)
        
        # Encontrar contorno da estrutura principal
        contours, _ = cv2.findContours(combined_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return initial_bbox
        
        # Encontrar o maior contorno (estrutura principal da tabela)
        main_contour = max(contours, key=cv2.contourArea)
        
        # Obter bounding box refinado
        refined_x, refined_y, refined_w, refined_h = cv2.boundingRect(main_contour)
        
        # Ajustar coordenadas para imagem original
        final_x = extended_x + refined_x
        final_y = extended_y + refined_y
        
        # Adicionar padding moderado para capturar bordas
        padding = 8  # Padding reduzido de 5 para 8
        final_x = max(0, final_x - padding)
        final_y = max(0, final_y - padding)
        final_w = min(image.shape[1] - final_x, refined_w + 2 * padding)
        final_h = min(image.shape[0] - final_y, refined_h + 2 * padding)
        
        # Verificar se o bbox refinado é válido e não muito diferente do original
        if final_w > 50 and final_h > 30:  # Dimensões mínimas
            # Se a redução foi muito drástica, manter mais do original
            area_reduction = (final_w * final_h) / (w * h)
            
            if area_reduction < 0.3:  # Redução > 70%, muito agressiva
                # Manter mais área do bbox original
                final_x = max(0, x - 5)
                final_y = max(0, y - 5)
                final_w = min(image.shape[1] - final_x, w + 10)
                final_h = min(image.shape[0] - final_y, h + 10)
            
            return (final_x, final_y, final_w, final_h)
        else:
            return initial_bbox

    def validate_table_structure(self, image, bbox):
        """Valida se a região realmente contém uma estrutura de tabela"""
        x, y, w, h = bbox
        
        # Extrair região da tabela
        table_roi = image[y:y+h, x:x+w]
        
        # Converter para escala de cinza
        gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
        
        # Detectar linhas na região
        _, h_lines, v_lines = self.detect_lines(table_roi)
        
        # Contar linhas horizontais e verticais significativas
        h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar linhas por comprimento mínimo (mais permissivo)
        min_h_length = w * 0.2  # Reduzido de 30% para 20%
        min_v_length = h * 0.2  # Reduzido de 30% para 20%
        
        valid_h_lines = 0
        for contour in h_contours:
            x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
            if w_cont >= min_h_length and h_cont <= 15:  # Linha fina e longa
                valid_h_lines += 1
        
        valid_v_lines = 0
        for contour in v_contours:
            x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
            if h_cont >= min_v_length and w_cont <= 15:  # Linha fina e alta
                valid_v_lines += 1
        
        # Critérios muito mais permissivos
        has_enough_lines = valid_h_lines >= 1 or valid_v_lines >= 1  # Pelo menos 1 linha em qualquer direção
        
        # Verificar densidade de intersecções
        intersections = cv2.bitwise_and(h_lines, v_lines)
        intersection_points = cv2.findNonZero(intersections)
        intersection_density = len(intersection_points) if intersection_points is not None else 0
        
        # Área mínima e máxima relativa
        image_area = image.shape[0] * image.shape[1]
        region_area = w * h
        area_ratio = region_area / image_area
        
        # Validações muito permissivas
        valid_area = 0.001 <= area_ratio <= 0.95  # Reduzido para 0.1%
        valid_aspect = 0.5 <= (w/h) <= 50  # Expandido ainda mais
        valid_intersections = intersection_density >= 0  # Aceitar qualquer valor
        
        # Score de confiança (mais generoso)
        confidence = 0.0
        if has_enough_lines:
            confidence += 0.5  # Aumentado
        if valid_intersections or intersection_density > 0:
            confidence += 0.2
        if valid_area:
            confidence += 0.2
        if valid_aspect:
            confidence += 0.1
        
        # Bonus para muitas linhas
        if valid_h_lines >= 2 and valid_v_lines >= 1:
            confidence += 0.2
        
        return confidence >= 0.2, confidence  # Reduzido para 20%
    
    def analyze_table_content(self, image, bbox):
        """Analisa o conteúdo da região para determinar se é realmente uma tabela"""
        try:
            x, y, w, h = bbox
            
            # Refinar bbox antes da análise
            refined_bbox = self.refine_table_bbox(image, bbox)
            rx, ry, rw, rh = refined_bbox
            
            # Verificar se bbox é válido
            if rx < 0 or ry < 0 or rx + rw > image.shape[1] or ry + rh > image.shape[0]:
                return False, 0.0, bbox
            
            if rw <= 0 or rh <= 0:
                return False, 0.0, bbox
            
            # Usar bbox refinado
            table_roi = image[ry:ry+rh, rx:rx+rw]
            
            # Converter para escala de cinza
            gray_roi = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
            
            # Usar threshold adaptivo
            binary = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            
            # Encontrar contornos de texto
            text_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filtrar contornos por tamanho
            text_regions = []
            for contour in text_contours:
                x_cont, y_cont, w_cont, h_cont = cv2.boundingRect(contour)
                area = w_cont * h_cont
                
                # Filtros MUITO mais permissivos para texto
                if 10 <= area <= 15000 and 2 <= w_cont <= 500 and 2 <= h_cont <= 100:
                    text_regions.append((x_cont, y_cont, w_cont, h_cont))
            
            # Lógica baseada na quantidade real de texto detectado
            num_regions = len(text_regions)
            
            # Scores mais realistas baseados na análise
            if num_regions >= 50:  # Tabela muito rica em texto
                return True, 0.9, refined_bbox
            elif num_regions >= 30:  # Tabela com bastante texto
                return True, 0.8, refined_bbox
            elif num_regions >= 15:  # Tabela com texto moderado
                return True, 0.7, refined_bbox
            elif num_regions >= 8:   # Tabela com pouco texto
                return True, 0.6, refined_bbox
            elif num_regions >= 3:   # Tabela mínima
                return True, 0.4, refined_bbox
            elif num_regions >= 1:   # Qualquer estrutura com texto
                return True, 0.3, refined_bbox
            else:  # Sem texto = inválido
                return False, 0.0, refined_bbox
                
        except Exception as e:
            # Em caso de erro, retornar bbox original
            return False, 0.0, bbox
    
    def calculate_column_alignment(self, lines):
        """Calcula o score de alinhamento das colunas"""
        if len(lines) < 2:
            return 0.0
        
        # Obter posições X de cada elemento em cada linha
        all_x_positions = []
        for line in lines:
            x_positions = [region[0] for region in line]  # x position
            all_x_positions.append(sorted(x_positions))
        
        # Verificar consistência entre linhas
        alignment_scores = []
        
        for i in range(1, len(all_x_positions)):
            line1 = all_x_positions[0]
            line2 = all_x_positions[i]
            
            # Comparar posições (tolerância de 20 pixels)
            matches = 0
            for pos1 in line1:
                for pos2 in line2:
                    if abs(pos1 - pos2) <= 20:
                        matches += 1
                        break
            
            if len(line1) > 0:
                alignment_score = matches / len(line1)
                alignment_scores.append(alignment_score)
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.0

    def find_table_contours(self, table_structure):
        """Encontra contornos de tabelas na estrutura detectada com validação inteligente"""
        # Dilatar de forma mais conservadora
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(table_structure, kernel, iterations=1)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos com critérios mais rigorosos
        table_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Área mínima mais restritiva
            if area < self.min_table_area:
                continue
            
            # Aproximar contorno para retângulo
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Deve ter formato retangular
            if len(approx) < 4:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            
            # Filtros mais rigorosos
            min_width, min_height = 100, 60  # Tamanhos mínimos
            max_area_ratio = 0.8  # Máximo 80% da imagem
            
            # Verificações dimensionais
            if w < min_width or h < min_height:
                continue
                
            if aspect_ratio < 0.8 or aspect_ratio > 15:  # Aspecto mais restrito
                continue
            
            # Verificar se não é muito grande (provavelmente toda a página)
            image_area = table_structure.shape[0] * table_structure.shape[1]
            if area / image_area > max_area_ratio:
                continue
            
            table_contours.append({
                'contour': contour,
                'bbox': (x, y, w, h),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'preliminary_score': min(1.0, area / 50000)  # Score preliminar
            })
        
        # Ordenar por área (maiores primeiro) mas limitando quantidade
        table_contours.sort(key=lambda x: x['area'], reverse=True)
        
        # Retornar no máximo 10 candidatos para validação posterior
        return table_contours[:10]
    
    def detect_table_cells(self, image, table_bbox):
        """Detecta células individuais dentro de uma tabela"""
        x, y, w, h = table_bbox
        table_roi = image[y:y+h, x:x+w]
        
        # Detectar linhas na região da tabela
        table_structure, h_lines, v_lines = self.detect_lines(table_roi)
        
        # Encontrar intersecções das linhas
        intersections = cv2.bitwise_and(h_lines, v_lines)
        
        # Encontrar pontos de intersecção
        contours, _ = cv2.findContours(intersections, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        intersection_points = []
        for contour in contours:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                intersection_points.append((cx + x, cy + y))  # Ajustar para coordenadas globais
        
        return intersection_points
    
    def run(self):
        """Executa a detecção de tabelas"""
        try:
            self.progress_updated.emit(10, "Abrindo PDF...")
            
            # Abrir PDF
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            if self.pages == "all":
                pages_to_process = list(range(total_pages))
            else:
                # Processar páginas específicas
                pages_to_process = self.parse_page_range(self.pages, total_pages)
            
            detected_tables = []
            
            for i, page_num in enumerate(pages_to_process):
                if self.should_stop:
                    break
                
                progress = 10 + int((i / len(pages_to_process)) * 80)
                self.progress_updated.emit(progress, f"Processando página {page_num + 1}...")
                
                # Renderizar página como imagem
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_data = pix.samples
                
                # Converter para formato OpenCV
                img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                # Detectar estrutura de tabelas
                table_structure, _, _ = self.detect_lines(img)
                
                # Encontrar contornos de tabelas
                table_contours = self.find_table_contours(table_structure)
                
                # Processar cada tabela encontrada com validação rigorosa
                validated_tables = []
                
                for j, table_info in enumerate(table_contours):
                    bbox = table_info['bbox']
                    
                    # Validação 1: Estrutura de linhas
                    is_valid_structure, structure_confidence = self.validate_table_structure(img, bbox)
                    
                    if not is_valid_structure:
                        continue  # Pular se não tem estrutura válida
                    
                    # Validação 2: Conteúdo e alinhamento (agora retorna bbox refinado)
                    has_valid_content, content_confidence, refined_bbox = self.analyze_table_content(img, bbox)
                    
                    if not has_valid_content:
                        continue  # Pular se não tem conteúdo válido
                    
                    # Usar bbox refinado para melhor enquadramento
                    final_bbox = refined_bbox
                    
                    # CONVERSÃO DE COORDENADAS: De imagem 150 DPI para coordenadas PDF
                    # Calcular fatores de escala
                    pdf_width = page.rect.width
                    pdf_height = page.rect.height
                    img_width = img.shape[1]
                    img_height = img.shape[0]
                    
                    scale_x = pdf_width / img_width
                    scale_y = pdf_height / img_height
                    
                    # Converter bbox para coordenadas PDF
                    x_pdf = final_bbox[0] * scale_x
                    y_pdf = final_bbox[1] * scale_y
                    w_pdf = final_bbox[2] * scale_x
                    h_pdf = final_bbox[3] * scale_y
                    
                    # Garantir que está dentro dos limites da página
                    x_pdf = max(0, x_pdf)
                    y_pdf = max(0, y_pdf)
                    w_pdf = min(pdf_width - x_pdf, w_pdf)
                    h_pdf = min(pdf_height - y_pdf, h_pdf)
                    
                    # Bbox final em coordenadas PDF
                    pdf_bbox = (x_pdf, y_pdf, w_pdf, h_pdf)
                    
                    # Detectar células (para análise mais detalhada)
                    intersection_points = self.detect_table_cells(img, final_bbox)
                    
                    # Calcular dimensões estimadas baseadas nas validações
                    estimated_rows = max(2, int(structure_confidence * 10))
                    estimated_cols = max(2, int(content_confidence * 8))
                    
                    # Score final combinado
                    final_confidence = (structure_confidence * 0.6 + content_confidence * 0.4)
                    
                    # Só aceitar tabelas com confiança >= 25% (mais permissivo)
                    if final_confidence >= 0.25:
                        table_data = {
                            'page': page_num + 1,
                            'table_index': len(validated_tables),
                            'bbox': pdf_bbox,  # Usar bbox em coordenadas PDF
                            'area': pdf_bbox[2] * pdf_bbox[3],  # Área em coordenadas PDF
                            'aspect_ratio': pdf_bbox[2] / pdf_bbox[3],  # Aspecto em coordenadas PDF
                            'estimated_rows': estimated_rows,
                            'estimated_cols': estimated_cols,
                            'intersection_points': intersection_points,
                            'detection_method': 'opencv_intelligent_detection_v3',  # Nova versão
                            'confidence': final_confidence,
                            'structure_score': structure_confidence,
                            'content_score': content_confidence,
                            'validation_passed': True,
                            'bbox_refined': True,  # Indicar que bbox foi refinado
                            'coordinates_converted': True  # Indicar que coordenadas foram convertidas
                        }
                        
                        validated_tables.append(table_data)
                
                # Adicionar apenas tabelas validadas
                detected_tables.extend(validated_tables)
            
            doc.close()
            
            self.progress_updated.emit(100, f"Detecção concluída! {len(detected_tables)} tabelas encontradas")
            self.tables_detected.emit(detected_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na detecção OpenCV: {str(e)}")
    
    def parse_page_range(self, page_str, total_pages):
        """Converte string de páginas em lista de índices"""
        pages = []
        parts = page_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start - 1, min(end, total_pages)))
            else:
                page_num = int(part) - 1
                if 0 <= page_num < total_pages:
                    pages.append(page_num)
        
        return sorted(list(set(pages)))
    
    def stop(self):
        """Para a detecção"""
        self.should_stop = True


class TesseractTableDetector(QThread):
    """Thread para detecção de tabelas usando Tesseract OCR"""
    
    progress_updated = pyqtSignal(int, str)
    tables_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path, pages="all", language='por'):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.language = language
        self.should_stop = False
    
    def analyze_text_layout(self, image):
        """Analisa o layout do texto para detectar estruturas tabulares com maior precisão"""
        try:
            import pytesseract
        except ImportError:
            self.error_occurred.emit("Tesseract não instalado. Execute: pip install pytesseract")
            return []
        
        # Configurar Tesseract para melhor detecção de layout
        config = f'--psm 6 -l {self.language} -c preserve_interword_spaces=1'
        
        # Obter dados detalhados do OCR com coordenadas
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
        
        # Filtrar apenas texto com boa confiança
        valid_words = []
        for i, text in enumerate(data['text']):
            if text.strip() and data['conf'][i] > 30:  # Confiança mínima
                valid_words.append({
                    'text': text.strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i],
                    'conf': data['conf'][i]
                })
        
        if len(valid_words) < 6:  # Muito pouco texto
            return []
        
        # Agrupar palavras por linhas baseado na coordenada Y
        lines = {}
        line_tolerance = 15  # Tolerância para considerar mesma linha
        
        for word in valid_words:
            y = word['y']
            line_key = None
            
            # Procurar linha existente próxima
            for existing_y in lines.keys():
                if abs(y - existing_y) <= line_tolerance:
                    line_key = existing_y
                    break
            
            # Se não encontrou, criar nova linha
            if line_key is None:
                line_key = y
                lines[line_key] = []
            
            lines[line_key].append(word)
        
        # Filtrar linhas com pelo menos 2 palavras
        valid_lines = {k: v for k, v in lines.items() if len(v) >= 2}
        
        if len(valid_lines) < 3:  # Precisa de pelo menos 3 linhas
            return []
        
        # Detectar tabelas baseado em alinhamento de colunas
        potential_tables = []
        
        # Ordenar linhas por posição Y
        sorted_lines = sorted(valid_lines.items(), key=lambda x: x[0])
        
        # Analisar grupos consecutivos de linhas
        for i in range(len(sorted_lines) - 2):  # Pelo menos 3 linhas
            line_group = []
            
            # Coletar linhas consecutivas similares
            for j in range(i, min(i + 10, len(sorted_lines))):  # Máximo 10 linhas
                current_line = sorted_lines[j][1]
                
                # Ordenar palavras por posição X
                current_line.sort(key=lambda x: x['x'])
                
                if len(current_line) >= 2:  # Pelo menos 2 colunas
                    line_group.append(current_line)
                else:
                    break  # Quebrar sequência se linha inválida
            
            if len(line_group) >= 3:  # Pelo menos 3 linhas válidas
                table_data = self.validate_table_from_lines(line_group, image.shape)
                if table_data:
                    potential_tables.append(table_data)
        
        # Remover tabelas sobrepostas (manter a maior)
        filtered_tables = self.remove_overlapping_tables(potential_tables)
        
        return filtered_tables
    
    def validate_table_from_lines(self, line_group, image_shape):
        """Valida se um grupo de linhas forma uma tabela válida"""
        if len(line_group) < 3:
            return None
        
        # Calcular posições de colunas baseadas na primeira linha
        first_line = line_group[0]
        column_positions = [word['x'] for word in first_line]
        
        # Verificar consistência de colunas em outras linhas
        column_consistency_scores = []
        
        for line in line_group[1:]:
            line_positions = [word['x'] for word in line]
            consistency = self.calculate_position_similarity(column_positions, line_positions)
            column_consistency_scores.append(consistency)
        
        # Média de consistência
        avg_consistency = sum(column_consistency_scores) / len(column_consistency_scores)
        
        if avg_consistency < 0.4:  # Reduzido de 60% para 40%
            return None
        
        # Calcular bbox da tabela com maior precisão
        all_words = []
        for line in line_group:
            all_words.extend(line)
        
        # Encontrar limites reais baseados no texto
        min_x = min(w['x'] for w in all_words)
        min_y = min(w['y'] for w in all_words)
        max_x = max(w['x'] + w['w'] for w in all_words)
        max_y = max(w['y'] + w['h'] for w in all_words)
        
        # Ajustar bbox para capturar apenas a estrutura da tabela
        # Padding reduzido e mais preciso
        padding_x = 8  # Padding horizontal menor
        padding_y = 5  # Padding vertical menor
        
        # Calcular margem superior baseada na altura média das linhas
        avg_line_height = sum(w['h'] for w in all_words) / len(all_words)
        top_margin = max(5, int(avg_line_height * 0.2))  # 20% da altura média da linha
        
        # Ajustar coordenadas com padding otimizado
        min_x = max(0, min_x - padding_x)
        min_y = max(0, min_y - top_margin)
        max_x = min(image_shape[1], max_x + padding_x)
        max_y = min(image_shape[0], max_y + padding_y)
        
        table_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)
        
        # Verificar dimensões mínimas
        if table_bbox[2] < 100 or table_bbox[3] < 60:  # Muito pequena
            return None
        
        # Verificar se não é muito grande (provavelmente toda a página)
        image_area = image_shape[0] * image_shape[1]
        table_area = table_bbox[2] * table_bbox[3]
        
        if table_area / image_area > 0.8:  # Mais de 80% da página
            return None
        
        # Calcular score de qualidade
        quality_score = self.calculate_table_quality_score(line_group, avg_consistency)
        
        return {
            'bbox': table_bbox,
            'lines': line_group,
            'column_count': len(column_positions),
            'row_count': len(line_group),
            'confidence': quality_score,
            'column_consistency': avg_consistency,
            'word_count': len(all_words),
            'tight_bbox': True  # Indicar que bbox é mais preciso
        }
    
    def calculate_table_quality_score(self, line_group, consistency):
        """Calcula score de qualidade da tabela baseado em vários fatores"""
        score = 0.0
        
        # Fator 1: Consistência de colunas (40% do score)
        score += consistency * 0.4
        
        # Fator 2: Número de linhas (20% do score)
        row_score = min(1.0, len(line_group) / 8.0)  # Ideal: 8+ linhas
        score += row_score * 0.2
        
        # Fator 3: Número de colunas (20% do score)
        avg_columns = sum(len(line) for line in line_group) / len(line_group)
        col_score = min(1.0, avg_columns / 4.0)  # Ideal: 4+ colunas
        score += col_score * 0.2
        
        # Fator 4: Densidade de texto (20% do score)
        total_words = sum(len(line) for line in line_group)
        expected_words = len(line_group) * 3  # Pelo menos 3 palavras por linha
        density_score = min(1.0, total_words / expected_words)
        score += density_score * 0.2
        
        return score
    
    def remove_overlapping_tables(self, tables):
        """Remove tabelas sobrepostas, mantendo a melhor"""
        if len(tables) <= 1:
            return tables
        
        # Ordenar por confiança (melhor primeiro)
        tables.sort(key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        
        for table in tables:
            bbox1 = table['bbox']
            overlaps = False
            
            for existing in filtered:
                bbox2 = existing['bbox']
                
                # Calcular sobreposição
                overlap_area = self.calculate_bbox_overlap(bbox1, bbox2)
                area1 = bbox1[2] * bbox1[3]
                area2 = bbox2[2] * bbox2[3]
                
                # Se sobreposição > 50% da menor área, considerar duplicata
                min_area = min(area1, area2)
                if overlap_area / min_area > 0.5:
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(table)
        
        return filtered
    
    def calculate_bbox_overlap(self, bbox1, bbox2):
        """Calcula área de sobreposição entre dois bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Coordenadas dos retângulos
        left1, top1, right1, bottom1 = x1, y1, x1 + w1, y1 + h1
        left2, top2, right2, bottom2 = x2, y2, x2 + w2, y2 + h2
        
        # Calcular interseção
        left = max(left1, left2)
        top = max(top1, top2)
        right = min(right1, right2)
        bottom = min(bottom1, bottom2)
        
        if left < right and top < bottom:
            return (right - left) * (bottom - top)
        else:
            return 0

    def calculate_position_similarity(self, pos1, pos2):
        """Calcula similaridade entre posições de colunas"""
        if len(pos1) != len(pos2):
            return 0.0
        
        tolerance = 20
        matches = 0
        
        for p1, p2 in zip(pos1, pos2):
            if abs(p1 - p2) <= tolerance:
                matches += 1
        
        return matches / len(pos1)
    
    def run(self):
        """Executa a detecção usando Tesseract"""
        try:
            self.progress_updated.emit(10, "Abrindo PDF...")
            
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            if self.pages == "all":
                pages_to_process = list(range(total_pages))
            else:
                pages_to_process = self.parse_page_range(self.pages, total_pages)
            
            detected_tables = []
            
            for i, page_num in enumerate(pages_to_process):
                if self.should_stop:
                    break
                
                progress = 10 + int((i / len(pages_to_process)) * 80)
                self.progress_updated.emit(progress, f"Analisando texto da página {page_num + 1}...")
                
                # Renderizar página
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_data = pix.samples
                
                # Converter para OpenCV
                img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                
                # Detectar tabelas via análise de texto inteligente
                tables = self.analyze_text_layout(img)
                
                for j, table in enumerate(tables):
                    # Só aceitar tabelas com confiança >= 50% (mais permissivo)
                    if table['confidence'] >= 0.5:
                        table_data = {
                            'page': page_num + 1,
                            'table_index': j,
                            'bbox': table['bbox'],
                            'estimated_rows': table['row_count'],
                            'estimated_cols': table['column_count'],
                            'detection_method': 'tesseract_intelligent_analysis_v2',
                            'confidence': table['confidence'],
                            'column_consistency': table.get('column_consistency', 0.0),
                            'word_count': table.get('word_count', 0),
                            'validation_passed': True,
                            'tight_bbox': table.get('tight_bbox', False)  # Indicar bbox otimizado
                        }
                        detected_tables.append(table_data)
            
            doc.close()
            
            self.progress_updated.emit(100, f"Análise OCR concluída! {len(detected_tables)} tabelas encontradas")
            self.tables_detected.emit(detected_tables)
            
        except Exception as e:
            self.error_occurred.emit(f"Erro na detecção Tesseract: {str(e)}")
    
    def parse_page_range(self, page_str, total_pages):
        """Converte string de páginas em lista de índices"""
        pages = []
        parts = page_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start - 1, min(end, total_pages)))
            else:
                page_num = int(part) - 1
                if 0 <= page_num < total_pages:
                    pages.append(page_num)
        
        return sorted(list(set(pages)))
    
    def stop(self):
        """Para a detecção"""
        self.should_stop = True
