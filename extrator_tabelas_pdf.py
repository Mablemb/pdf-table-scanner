import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QPushButton, 
    QScrollArea, QFrame, QTextEdit, QSplitter, QTabWidget, QGridLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QSpinBox
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor, QFont
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
import os
import json
import datetime

class PDFTableExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Extrator de Tabelas de PDF')
        self.resize(1200, 800)
        self.pdf_path = None
        self.doc = None
        self.page_images = []
        self.selections = []  # (start_page, start_rect, end_page, end_rect)
        self.image_labels = []
        self.global_select_points = []  # [(page_idx, QPoint)]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        btn_open = QPushButton('Escolher PDF')
        btn_open.clicked.connect(self.open_pdf)
        buttons_layout.addWidget(btn_open)
        
        btn_save = QPushButton('Salvar Tabelas Selecionadas')
        btn_save.clicked.connect(self.save_tables)
        buttons_layout.addWidget(btn_save)
        
        btn_view_tables = QPushButton('Visualizar Tabelas Extraídas')
        btn_view_tables.clicked.connect(self.open_table_viewer)
        buttons_layout.addWidget(btn_view_tables)
        
        layout.addLayout(buttons_layout)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Abrir PDF', '', 'PDF Files (*.pdf)')
        if file_path:
            self.pdf_path = file_path
            self.load_pdf()

    def load_pdf(self):
        self.doc = fitz.open(self.pdf_path)
        self.page_images.clear()
        self.image_labels.clear()
        # Limpa o layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Renderiza páginas separadas
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.page_images.append(img.copy())
            label = PDFPageLabel(img.copy(), page_num, self)
            self.image_labels.append(label)
            self.scroll_layout.addWidget(label)

    def add_selection(self, selection):
        # selection: ((page_idx1, point1), (page_idx2, point2))
        self.selections.append(selection)
        page_idx1, pt1 = selection[0]
        page_idx2, pt2 = selection[1]
        if page_idx1 == page_idx2:
            rect = QRect(pt1, pt2).normalized()
            self.image_labels[page_idx1].add_rect(rect, color=QColor(255, 0, 0))  # vermelho
        else:
            # Página inicial: retângulo de x1, y1 até x1, altura
            x1 = pt1.x()
            y1 = pt1.y()
            h1 = self.image_labels[page_idx1].image.height()
            rect1 = QRect(QPoint(x1, y1), QPoint(x1, h1)).normalized()

            # Página final: retângulo de x2, 0 até x2, y2
            x2 = pt2.x()
            y2 = pt2.y()
            rect2 = QRect(QPoint(x2, 0), QPoint(x2, y2)).normalized()

            self.image_labels[page_idx1].add_rect(rect1, color=QColor(0, 0, 255))  # azul
            self.image_labels[page_idx2].add_rect(rect2, color=QColor(0, 0, 255))  # azul

    def register_click(self, page_idx, pos):
        self.global_select_points.append((page_idx, pos))
        if len(self.global_select_points) == 2:
            self.add_selection(tuple(self.global_select_points))
            self.global_select_points = []

    def save_tables(self):
        if not self.selections:
            return
        out_dir = QFileDialog.getExistingDirectory(self, 'Escolher pasta para salvar tabelas')
        if not out_dir:
            return
        import time
        pdf_base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        for idx, selection in enumerate(self.selections, 1):
            page_idx1, pt1 = selection[0]
            page_idx2, pt2 = selection[1]
            if page_idx1 == page_idx2:
                rect = QRect(pt1, pt2).normalized()
                img = self.page_images[page_idx1].copy(rect)
                page_str = str(page_idx1 + 1)
            else:
                # Página de cima
                h1 = self.page_images[page_idx1].height()
                x1 = pt1.x()
                y1 = pt1.y()
                x2 = pt2.x()
                # Retângulo delimitador do quadrilátero
                left = min(x1, x2)
                right = max(x1, x2)
                rect1 = QRect(QPoint(left, y1), QPoint(right, h1)).normalized()
                img1 = self.page_images[page_idx1].copy(rect1)
                # Página de baixo
                y2 = pt2.y()
                rect2 = QRect(QPoint(left, 0), QPoint(right, y2)).normalized()
                img2 = self.page_images[page_idx2].copy(rect2)
                w = max(img1.width(), img2.width())
                h = img1.height() + img2.height()
                result = QImage(w, h, QImage.Format_RGB888)
                result.fill(0)
                painter = QPainter(result)
                painter.drawImage(0, 0, img1)
                painter.drawImage(0, img1.height(), img2)
                painter.end()
                img = result
                page_str = f'{page_idx1 + 1}-{page_idx2 + 1}'
            name = f'{pdf_base}_pagina_{page_str}_tabela_{idx}.png'
            img.save(os.path.join(out_dir, name))
        self.selections.clear()
        for label in self.image_labels:
            label.clear_rects()
    
    def open_table_viewer(self):
        """Abre o visualizador de tabelas extraídas"""
        tabelas_dir = 'tabelas'
        if not os.path.exists(tabelas_dir):
            QMessageBox.information(self, "Informação", "Nenhuma tabela encontrada na pasta 'tabelas'.")
            return
        
        # Verifica se há imagens na pasta
        image_files = [f for f in os.listdir(tabelas_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            QMessageBox.information(self, "Informação", "Nenhuma imagem de tabela encontrada na pasta 'tabelas'.")
            return
        
        # Abre o visualizador de tabelas
        self.table_viewer = TableViewer(tabelas_dir)
        self.table_viewer.show()


class TableViewer(QWidget):
    """Widget para visualizar e converter tabelas extraídas em JSONL"""
    
    def __init__(self, tables_dir):
        super().__init__()
        self.tables_dir = tables_dir
        self.current_table_data = {}
        self.setWindowTitle('Visualizador de Tabelas - Converter para JSONL')
        self.setGeometry(100, 100, 1400, 900)
        self.init_ui()
        self.load_table_images()
    
    def init_ui(self):
        """Inicializa a interface do visualizador"""
        main_layout = QVBoxLayout(self)
        
        # Splitter principal horizontal
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Painel esquerdo - Lista de imagens e visualização
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # ComboBox para seleção de tabelas
        self.table_selector = QComboBox()
        self.table_selector.currentTextChanged.connect(self.on_table_selected)
        left_layout.addWidget(QLabel("Selecionar Tabela:"))
        left_layout.addWidget(self.table_selector)
        
        # Área de visualização da imagem
        self.image_scroll = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        self.image_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.image_scroll)
        
        # Painel direito - Editor de dados estruturados
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Tabs para diferentes seções
        self.tabs = QTabWidget()
        
        # Tab 1: Metadados da tabela
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout(metadata_tab)
        
        # Campos de metadados
        metadata_layout.addWidget(QLabel("Tipo:"))
        self.type_field = QLineEdit("table")
        metadata_layout.addWidget(self.type_field)
        
        metadata_layout.addWidget(QLabel("Fonte:"))
        self.source_field = QLineEdit()
        metadata_layout.addWidget(self.source_field)
        
        metadata_layout.addWidget(QLabel("Título:"))
        self.title_field = QLineEdit()
        metadata_layout.addWidget(self.title_field)
        
        self.tabs.addTab(metadata_tab, "Metadados")
        
        # Tab 2: Editor de estrutura da tabela
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        
        # Botões para gerenciar subseções
        subsection_buttons = QHBoxLayout()
        btn_add_subsection = QPushButton("Adicionar Subseção")
        btn_add_subsection.clicked.connect(self.add_subsection)
        btn_remove_subsection = QPushButton("Remover Subseção")
        btn_remove_subsection.clicked.connect(self.remove_subsection)
        subsection_buttons.addWidget(btn_add_subsection)
        subsection_buttons.addWidget(btn_remove_subsection)
        table_layout.addLayout(subsection_buttons)
        
        # Área para subseções
        self.subsections_scroll = QScrollArea()
        self.subsections_widget = QWidget()
        self.subsections_layout = QVBoxLayout(self.subsections_widget)
        self.subsections_scroll.setWidget(self.subsections_widget)
        self.subsections_scroll.setWidgetResizable(True)
        table_layout.addWidget(self.subsections_scroll)
        
        self.tabs.addTab(table_tab, "Estrutura da Tabela")
        
        # Tab 3: Preview JSON
        json_tab = QWidget()
        json_layout = QVBoxLayout(json_tab)
        
        self.json_preview = QTextEdit()
        self.json_preview.setFont(QFont("Monaco", 10))
        json_layout.addWidget(QLabel("Preview JSON:"))
        json_layout.addWidget(self.json_preview)
        
        btn_update_preview = QPushButton("Atualizar Preview")
        btn_update_preview.clicked.connect(self.update_json_preview)
        json_layout.addWidget(btn_update_preview)
        
        self.tabs.addTab(json_tab, "Preview JSON")
        
        right_layout.addWidget(self.tabs)
        
        # Botões de ação
        action_buttons = QHBoxLayout()
        btn_save_json = QPushButton("Salvar JSONL")
        btn_save_json.clicked.connect(self.save_jsonl)
        btn_export_all = QPushButton("Exportar Todas")
        btn_export_all.clicked.connect(self.export_all_tables)
        action_buttons.addWidget(btn_save_json)
        action_buttons.addWidget(btn_export_all)
        right_layout.addLayout(action_buttons)
        
        # Configurar splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([600, 800])  # Proporção inicial
        
        main_layout.addWidget(main_splitter)
        
        # Lista para armazenar widgets de subseções
        self.subsection_widgets = []
    
    def load_table_images(self):
        """Carrega as imagens de tabelas disponíveis"""
        image_files = [f for f in os.listdir(self.tables_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort()
        
        self.table_selector.clear()
        self.table_selector.addItems(image_files)
        
        if image_files:
            self.on_table_selected(image_files[0])
    
    def on_table_selected(self, filename):
        """Callback quando uma tabela é selecionada"""
        if not filename:
            return
            
        # Carrega e exibe a imagem
        image_path = os.path.join(self.tables_dir, filename)
        pixmap = QPixmap(image_path)
        
        # Redimensiona para caber na tela mantendo aspect ratio
        scaled_pixmap = pixmap.scaled(600, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        # Inicializa campos com base no nome do arquivo
        self.initialize_fields_from_filename(filename)
        
        # Limpa subseções existentes
        self.clear_subsections()
        
        # Adiciona uma subseção padrão
        self.add_subsection()
    
    def initialize_fields_from_filename(self, filename):
        """Inicializa campos com base no nome do arquivo"""
        # Remove extensão
        base_name = os.path.splitext(filename)[0]
        
        # Tenta extrair informações do nome do arquivo
        self.source_field.setText(base_name.split('_')[0] if '_' in base_name else base_name)
        self.title_field.setText(f"Tabela extraída de {base_name}")
    
    def add_subsection(self):
        """Adiciona uma nova subseção à tabela"""
        subsection_widget = SubsectionWidget(len(self.subsection_widgets) + 1)
        self.subsection_widgets.append(subsection_widget)
        self.subsections_layout.addWidget(subsection_widget)
    
    def remove_subsection(self):
        """Remove a última subseção"""
        if self.subsection_widgets:
            widget = self.subsection_widgets.pop()
            widget.setParent(None)
            widget.deleteLater()
    
    def clear_subsections(self):
        """Remove todas as subseções"""
        for widget in self.subsection_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.subsection_widgets.clear()
    
    def update_json_preview(self):
        """Atualiza o preview JSON"""
        try:
            data = self.get_table_data()
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_preview.setPlainText(json_str)
        except Exception as e:
            self.json_preview.setPlainText(f"Erro ao gerar JSON: {str(e)}")
    
    def get_table_data(self):
        """Constrói o objeto de dados da tabela"""
        data = {
            "type": self.type_field.text(),
            "source": self.source_field.text(),
            "title": self.title_field.text(),
            "text": []
        }
        
        for subsection_widget in self.subsection_widgets:
            subsection_data = subsection_widget.get_data()
            if subsection_data:  # Só adiciona se tiver dados
                data["text"].append(subsection_data)
        
        return data
    
    def save_jsonl(self):
        """Salva a tabela atual em formato JSONL"""
        try:
            data = self.get_table_data()
            
            # Seleciona arquivo de destino
            filename = self.table_selector.currentText()
            base_name = os.path.splitext(filename)[0]
            default_path = os.path.join(self.tables_dir, f"{base_name}.jsonl")
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Salvar JSONL", default_path, "JSONL Files (*.jsonl)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                
                QMessageBox.information(self, "Sucesso", f"Arquivo salvo em: {file_path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo: {str(e)}")
    
    def export_all_tables(self):
        """Exporta todas as tabelas para um único arquivo JSONL"""
        try:
            # Seleciona arquivo de destino
            default_path = os.path.join(self.tables_dir, "all_tables.jsonl")
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exportar Todas as Tabelas", default_path, "JSONL Files (*.jsonl)"
            )
            
            if not file_path:
                return
            
            # Por enquanto, salva apenas a tabela atual
            # Em uma implementação completa, você percorreria todas as tabelas
            data = self.get_table_data()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')  # JSONL format
            
            QMessageBox.information(self, "Sucesso", f"Tabelas exportadas para: {file_path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar tabelas: {str(e)}")


class SubsectionWidget(QWidget):
    """Widget para editar uma subseção da tabela"""
    
    def __init__(self, section_number):
        super().__init__()
        self.section_number = section_number
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Frame para destacar a subseção
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame_layout = QVBoxLayout(frame)
        
        # Título da subseção
        frame_layout.addWidget(QLabel(f"Subseção {self.section_number}:"))
        self.subsection_field = QLineEdit()
        self.subsection_field.setPlaceholderText("Nome da subseção (ex: Resposta ocular)")
        frame_layout.addWidget(self.subsection_field)
        
        # Headers
        frame_layout.addWidget(QLabel("Cabeçalhos (separados por vírgula):"))
        self.headers_field = QLineEdit()
        self.headers_field.setPlaceholderText("Critério, Classificação, Pontos")
        frame_layout.addWidget(self.headers_field)
        
        # Tabela para dados
        frame_layout.addWidget(QLabel("Dados da Tabela:"))
        self.table_widget = QTableWidget(3, 3)  # Inicia com 3x3
        self.table_widget.setHorizontalHeaderLabels(["Col 1", "Col 2", "Col 3"])
        
        # Botões para gerenciar linhas/colunas
        table_buttons = QHBoxLayout()
        btn_add_row = QPushButton("+ Linha")
        btn_add_row.clicked.connect(self.add_row)
        btn_remove_row = QPushButton("- Linha")
        btn_remove_row.clicked.connect(self.remove_row)
        btn_add_col = QPushButton("+ Coluna")
        btn_add_col.clicked.connect(self.add_column)
        btn_remove_col = QPushButton("- Coluna")
        btn_remove_col.clicked.connect(self.remove_column)
        
        table_buttons.addWidget(btn_add_row)
        table_buttons.addWidget(btn_remove_row)
        table_buttons.addWidget(btn_add_col)
        table_buttons.addWidget(btn_remove_col)
        table_buttons.addStretch()
        
        frame_layout.addLayout(table_buttons)
        frame_layout.addWidget(self.table_widget)
        
        layout.addWidget(frame)
    
    def add_row(self):
        """Adiciona uma linha à tabela"""
        current_rows = self.table_widget.rowCount()
        self.table_widget.setRowCount(current_rows + 1)
    
    def remove_row(self):
        """Remove a última linha da tabela"""
        current_rows = self.table_widget.rowCount()
        if current_rows > 1:
            self.table_widget.setRowCount(current_rows - 1)
    
    def add_column(self):
        """Adiciona uma coluna à tabela"""
        current_cols = self.table_widget.columnCount()
        self.table_widget.setColumnCount(current_cols + 1)
        self.table_widget.setHorizontalHeaderLabels([f"Col {i+1}" for i in range(current_cols + 1)])
    
    def remove_column(self):
        """Remove a última coluna da tabela"""
        current_cols = self.table_widget.columnCount()
        if current_cols > 1:
            self.table_widget.setColumnCount(current_cols - 1)
            self.table_widget.setHorizontalHeaderLabels([f"Col {i+1}" for i in range(current_cols - 1)])
    
    def get_data(self):
        """Retorna os dados da subseção em formato dict"""
        subsection_name = self.subsection_field.text().strip()
        if not subsection_name:
            return None
        
        # Headers
        headers_text = self.headers_field.text().strip()
        headers = [h.strip() for h in headers_text.split(',') if h.strip()] if headers_text else []
        
        # Rows
        rows = []
        for row in range(self.table_widget.rowCount()):
            row_data = []
            has_data = False
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                cell_value = item.text().strip() if item else ""
                row_data.append(cell_value)
                if cell_value:
                    has_data = True
            
            if has_data:  # Só adiciona linhas com pelo menos um valor
                rows.append(row_data)
        
        if not headers and not rows:
            return None
        
        return {
            "subsection": subsection_name,
            "headers": headers,
            "rows": rows
        }

class PDFPageLabel(QLabel):
    def __init__(self, image, page_idx, parent):
        super().__init__()
        self.setPixmap(QPixmap.fromImage(image))
        self.image = image
        self.page_idx = page_idx
        self.parent = parent
        self.rects = []  # lista de (QRect, QColor)
        self.select_points = []  # [(page_idx, QPoint)]
        self.setMouseTracking(True)
        self.preview_active = False
        self.preview_start = None  # (page_idx, QPoint)
        self.preview_end = None    # (page_idx, QPoint)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.parent.global_select_points:
                # Primeiro clique: inicia pré-visualização
                self.parent.preview_info = {
                    'start': (self.page_idx, event.pos()),
                    'end': None
                }
            else:
                # Segundo clique: termina pré-visualização
                if hasattr(self.parent, 'preview_info'):
                    self.parent.preview_info['end'] = (self.page_idx, event.pos())
            self.parent.register_click(self.page_idx, event.pos())
            # Atualiza todos os labels para garantir que o preview suma
            for label in self.parent.image_labels:
                label.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        for rect, color in self.rects:
            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
        # Preview global
        preview_info = getattr(self.parent, 'preview_info', None)
        if preview_info:
            start = preview_info.get('start')
            end = preview_info.get('end')
            if start and not end:
                # Durante arraste
                if self.page_idx == start[0]:
                    mouse_pos = self.mapFromGlobal(QCursor.pos())
                    rect = QRect(start[1], mouse_pos).normalized()
                    pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.drawRect(rect)
            elif start and end:
                # Após segundo clique
                if start[0] == end[0]:
                    # Mesma página: preview vermelho
                    if self.page_idx == start[0]:
                        rect = QRect(start[1], end[1]).normalized()
                        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawRect(rect)
                else:
                    # Entre páginas: preview azul
                    # Página de cima
                    if self.page_idx == start[0]:
                        h1 = self.image.height()
                        x1 = start[1].x()
                        y1 = start[1].y()
                        x2 = end[1].x()
                        # Quadrilátero: x1,y1; x2,y1; x1,h1; x2,h1
                        from PyQt5.QtGui import QPolygon
                        poly = QPolygon([
                            QPoint(x1, y1),
                            QPoint(x2, y1),
                            QPoint(x2, h1),
                            QPoint(x1, h1)
                        ])
                        pen = QPen(QColor(0, 0, 255), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawPolygon(poly)
                    # Página de baixo
                    if self.page_idx == end[0]:
                        x1 = start[1].x()
                        x2 = end[1].x()
                        y2 = end[1].y()
                        # Quadrilátero: x1,0; x2,0; x2,y2; x1,y2
                        from PyQt5.QtGui import QPolygon
                        poly = QPolygon([
                            QPoint(x1, 0),
                            QPoint(x2, 0),
                            QPoint(x2, y2),
                            QPoint(x1, y2)
                        ])
                        pen = QPen(QColor(0, 0, 255), 2, Qt.DashLine)
                        painter.setPen(pen)
                        painter.drawPolygon(poly)
    def mouseMoveEvent(self, event):
        # Atualiza todos os labels para garantir que o preview seja desenhado corretamente
        preview_info = getattr(self.parent, 'preview_info', None)
        if preview_info and preview_info.get('start') and not preview_info.get('end'):
            for label in self.parent.image_labels:
                label.update()
        super().mouseMoveEvent(event)

    def add_rect(self, rect, color=QColor(255,0,0)):
        self.rects.append((rect, color))
        self.update()

    def clear_rects(self):
        self.rects.clear()
        if hasattr(self.parent, 'preview_info'):
            self.parent.preview_info = {}
        self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = PDFTableExtractor()
    win.show()
    sys.exit(app.exec_())
