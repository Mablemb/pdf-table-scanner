import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QScrollArea, QFrame
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect, QPoint
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QScrollArea, QFrame
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor
from PyQt5.QtCore import Qt, QRect, QPoint
import os

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
        btn_open = QPushButton('Escolher PDF')
        btn_open.clicked.connect(self.open_pdf)
        layout.addWidget(btn_open)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        btn_save = QPushButton('Salvar Tabelas Selecionadas')
        btn_save.clicked.connect(self.save_tables)
        layout.addWidget(btn_save)

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
