import os
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QLabel, QMenu
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QPixmap, QColor, QAction
from PyQt6.QtCore import Qt, QRect, QPointF, QMargins, QRectF


class PDFViewer(QPdfView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_editor = parent
        self.pdf_doc = QPdfDocument(self)
        self.setDocument(self.pdf_doc)
        self.setPageMode(QPdfView.PageMode.MultiPage)
        self.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.setDocumentMargins(QMargins(10, 10, 10, 10))

        self.magnifier = QLabel()
        self.magnifier.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.magnifier.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.magnifier.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.is_magnifying = False

    def load_pdf(self, path):
        if os.path.exists(path):
            self.pdf_doc.load(path)
            if self.parent_editor:
                self.parent_editor.update_pdf_total_pages()

    def _get_pdf_coords_at(self, viewport_pos):
        """
        Convert a viewport pixel position to (page_index, x_pt, y_pt) in PDF point units.
        This is the correct method matching how synctex expects coordinates.
        Returns (page_index, x_pt, y_pt) or None if outside any page.
        """
        zoom = self.zoomFactor()
        doc = self.pdf_doc
        if doc.pageCount() == 0:
            return None

        # Get the scroll offset of the viewport
        vscroll = self.verticalScrollBar().value() if self.verticalScrollBar() else 0
        hscroll = self.horizontalScrollBar().value() if self.horizontalScrollBar() else 0

        margins = self.documentMargins()
        page_gap = 4  # Qt default inter-page gap in pixels

        # Walk through pages to find which page the click lands on
        y_cursor = margins.top()
        for page_idx in range(doc.pageCount()):
            page_size_pt = doc.pagePointSize(page_idx)  # QSizeF in PDF points
            page_h_px = page_size_pt.height() * zoom
            page_w_px = page_size_pt.width() * zoom

            # X centering: pages are centered in the viewport width
            viewport_w = self.viewport().width()
            page_x_start = max(margins.left(), (viewport_w - page_w_px) / 2)

            page_top_in_doc = y_cursor       # top of this page in document coords (px)
            page_bot_in_doc = y_cursor + page_h_px

            # Convert viewport_pos to document coords
            doc_x = viewport_pos.x() + hscroll
            doc_y = viewport_pos.y() + vscroll

            if page_top_in_doc <= doc_y <= page_bot_in_doc:
                # Click is on this page
                local_x_px = doc_x - page_x_start
                local_y_px = doc_y - page_top_in_doc

                # Convert pixel offset within page → PDF points
                x_pt = local_x_px / zoom
                y_pt = local_y_px / zoom

                # Clamp to page bounds
                x_pt = max(0.0, min(x_pt, page_size_pt.width()))
                y_pt = max(0.0, min(y_pt, page_size_pt.height()))

                return (page_idx, x_pt, y_pt)

            y_cursor = page_bot_in_doc + page_gap

        return None

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.setZoomMode(QPdfView.ZoomMode.Custom)
            angle = event.angleDelta().y()
            current_zoom = self.zoomFactor()
            new_zoom = current_zoom * 1.1 if angle > 0 else current_zoom * 0.9
            new_zoom = max(0.2, min(new_zoom, 5.0))
            self.setZoomFactor(new_zoom)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_magnifying = True
            self.update_magnifier(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_magnifying:
            self.update_magnifier(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_magnifying = False
            self.magnifier.hide()
        super().mouseReleaseEvent(event)

    def update_magnifier(self, pos):
        mag_size = 300
        zoom_factor = 2.0
        pixel_ratio = self.viewport().devicePixelRatioF()
        grab_size = int(mag_size / zoom_factor)
        rect = QRect(int(pos.x() - grab_size // 2), int(pos.y() - grab_size // 2), grab_size, grab_size)

        pixmap = self.viewport().grab(rect)
        pixmap.setDevicePixelRatio(1.0)

        target_w = int(mag_size * pixel_ratio)
        target_h = int(mag_size * pixel_ratio)
        scaled = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        circular_pixmap = QPixmap(target_w, target_h)
        circular_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        path = QPainterPath()
        path.addEllipse(0, 0, target_w, target_h)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)

        painter.setClipping(False)
        pen_thickness = max(1, int(1.0 * pixel_ratio))
        painter.setPen(QPen(QColor(150, 150, 150, 180), pen_thickness))
        painter.drawEllipse(pen_thickness // 2, pen_thickness // 2, target_w - pen_thickness, target_h - pen_thickness)
        painter.end()

        circular_pixmap.setDevicePixelRatio(pixel_ratio)

        self.magnifier.setPixmap(circular_pixmap)
        self.magnifier.setFixedSize(mag_size, mag_size)

        global_pos = self.viewport().mapToGlobal(pos)
        self.magnifier.move(global_pos.x() - mag_size // 2, global_pos.y() - mag_size // 2)
        self.magnifier.show()

    def contextMenuEvent(self, event):
        coords = self._get_pdf_coords_at(event.pos())
        if coords is not None and self.parent_editor:
            page_idx, x_pt, y_pt = coords
            menu = QMenu(self)
            inverse_act = QAction("Go to Source", self)
            inverse_act.triggered.connect(
                lambda checked=False, p=page_idx, x=x_pt, y=y_pt:
                    self.parent_editor.inverse_search(p, x, y)
            )
            menu.addAction(inverse_act)
            menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            coords = self._get_pdf_coords_at(event.position().toPoint())
            if coords is not None and self.parent_editor:
                page_idx, x_pt, y_pt = coords
                self.parent_editor.inverse_search(page_idx, x_pt, y_pt)
        super().mouseDoubleClickEvent(event)