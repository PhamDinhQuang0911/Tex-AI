import re
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QCompleter, QTextEdit, QMenu
from PyQt6.QtGui import QPainter, QTextCursor, QColor, QFont, QAction, QTextFormat
from PyQt6.QtCore import Qt, QRect, QSize, QStringListModel

from .highlighter import LatexHighlighter
from .config import LATEX_COMMANDS, LATEX_TEMPLATES

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, file_path="", main_window=None):
        super().__init__()
        self.file_path = file_path
        self.main_window = main_window 
        
        # --- Cấu hình Font v1.4 ---
        font_family = "Menlo"
        font_size = 14
        if self.main_window and hasattr(self.main_window, 'editor_config'):
            font_family = self.main_window.editor_config.get("font_family", "Menlo")
            font_size = self.main_window.editor_config.get("font_size", 14)

        font = QFont(font_family, font_size) 
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setWeight(QFont.Weight.Medium) 
        self.setFont(font)
        
        self.setStyleSheet("QPlainTextEdit { background-color: #ffffff; color: #111111; }")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        
        space_width = self.fontMetrics().horizontalAdvance(' ')
        self.setTabStopDistance(float(space_width * 2))
        
        self.live_start = None
        self.live_end = None
        self.last_selected_text = "" # Biến tạm lưu text bôi đen v1.6

        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.updateLineNumberAreaWidth(0)
        
        self.highlighter = LatexHighlighter(self.document())
        
        self.active_templates = LATEX_TEMPLATES.copy() 
        self.string_list_model = QStringListModel(list(self.active_templates.keys()), self) 
        self.completer = QCompleter(self.string_list_model, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated[str].connect(self.insert_completion)

        self.document().contentsChange.connect(self.on_contents_change)
        self.textChanged.connect(self.on_text_changed)

    def on_cursor_position_changed(self):
        """Lưu lại văn bản bôi đen mỗi khi con trỏ di chuyển v1.6"""
        self.highlightCurrentLine()
        curr_text = self.textCursor().selectedText().replace('\u2029', '\n').strip()
        if curr_text:
            self.last_selected_text = curr_text

    def on_text_changed(self):
        if getattr(self, 'live_start', None) is not None:
            pos = self.textCursor().position()
            if self.live_start <= pos <= self.live_end + 2:
                current_block = self.textCursor().block()
                block_end = current_block.position() + current_block.length()
                if block_end > self.live_end:
                    self.live_end = block_end 
                    self.highlightCurrentLine()
        if self.main_window:
            if getattr(self.main_window, 'live_preview_enabled', False): self.main_window.live_timer.start(750)
            if hasattr(self.main_window, 'parse_timer'): self.main_window.parse_timer.start(2000) 

        # --- Auto-sync cặp \begin - \end v1.6 ---
        cursor = self.textCursor()
        current_line = cursor.block().text()
        if r"\begin{" in current_line and current_line.strip().endswith("}"):
            match = re.search(r'\\begin\{([a-zA-Z0-9*]+)\}', current_line)
            if match:
                self.sync_end_tag(match.group(1))

    def sync_end_tag(self, new_name):
        r"""Tìm \end tương ứng v1.6"""
        cursor = self.textCursor()
        pos = cursor.position()
        text_after = self.toPlainText()[pos:]
        
        stack = 1
        pattern = re.compile(r'\\(begin|end)\{([a-zA-Z0-9*]+)\}')
        for match in pattern.finditer(text_after):
            tag_type = match.group(1)
            if tag_type == "begin":
                stack += 1
            else:
                stack -= 1
            if stack == 0:
                start_replace = pos + match.start(2)
                end_replace = pos + match.end(2)
                temp_cursor = self.textCursor()
                temp_cursor.setPosition(start_replace)
                temp_cursor.setPosition(end_replace, QTextCursor.MoveMode.KeepAnchor)
                if temp_cursor.selectedText() != new_name:
                    self.blockSignals(True)
                    temp_cursor.insertText(new_name)
                    self.blockSignals(False)
                break

    def insert_completion(self, completion_str):
        r"""NÂNG CẤP v1.6: Fix triệt để lỗi mất text loigiai, immini"""
        tc = self.textCursor()
        # Ưu tiên lấy text từ biến tạm nếu bôi đen vừa bị xóa bởi prefix
        selected_text = self.last_selected_text
        
        prefix = self.completer.completionPrefix()
        if prefix:
            tc.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(prefix))
            tc.removeSelectedText()
            
        content = self.active_templates.get(completion_str, completion_str)
        
        if "%|" in content:
            if selected_text:
                final_text = content.replace("%|", selected_text)
                tc.insertText(final_text)
                self.last_selected_text = "" # Reset sau khi dùng
            else:
                before, after = content.split("%|", 1)
                tc.insertText(before)
                new_pos = tc.position()
                tc.insertText(after)
                tc.setPosition(new_pos)
        else:
            tc.insertText(content)
        self.setTextCursor(tc)

    def apply_macro_code(self, macro_code):
        """Giữ text bôi đen cho Macro Toolbar v1.6"""
        cursor = self.textCursor()
        selected_text = cursor.selectedText().replace('\u2029', '\n').strip()
        
        if "%|" in macro_code:
            if selected_text:
                cursor.insertText(macro_code.replace("%|", selected_text))
            else:
                before, after = macro_code.split("%|", 1)
                cursor.insertText(before)
                pos = cursor.position()
                cursor.insertText(after)
                cursor.setPosition(pos)
                self.setTextCursor(cursor)
        else:
            cursor.insertText(macro_code)

    def update_font(self, font):
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        space_width = self.fontMetrics().horizontalAdvance(' ')
        self.setTabStopDistance(float(space_width * 2))
        self.updateLineNumberAreaWidth(0)

    def update_custom_commands(self, new_commands_dict):
        self.active_templates.update(new_commands_dict)
        self.string_list_model.setStringList(list(self.active_templates.keys()))

    def toggle_comment(self):
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        cursor.setPosition(start_pos)
        start_block = cursor.blockNumber()
        cursor.setPosition(end_pos)
        end_block = cursor.blockNumber()
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        is_commenting = not cursor.block().text().lstrip().startswith('%')
        cursor.beginEditBlock()
        for i in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(i)
            text = block.text()
            c = QTextCursor(block)
            if is_commenting: c.insertText('% ')
            else:
                stripped = text.lstrip()
                if stripped.startswith('%'):
                    idx = text.find('%')
                    c.setPosition(block.position() + idx)
                    c.deleteChar()
                    if c.block().text()[idx:idx+1] == ' ': c.deleteChar()
        cursor.endEditBlock()

    def start_live_region(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
        else:
            text, pos = self.toPlainText(), cursor.position()
            start_pos = text.rfind('\n\n', 0, pos)
            start_pos = 0 if start_pos == -1 else start_pos + 2
            end_pos = text.find('\n\n', pos)
            end_pos = len(text) if end_pos == -1 else end_pos
        start_cursor = QTextCursor(self.document())
        start_cursor.setPosition(start_pos)
        start_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        self.live_start = start_cursor.position()
        end_cursor = QTextCursor(self.document())
        end_cursor.setPosition(end_pos)
        end_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        self.live_end = end_cursor.position()
        self.highlightCurrentLine()

    def stop_live_region(self):
        self.live_start = self.live_end = None
        self.highlightCurrentLine()

    def on_contents_change(self, position, charsRemoved, charsAdded):
        if getattr(self, 'live_start', None) is None: return
        delta = charsAdded - charsRemoved
        if position + charsRemoved < self.live_start:
            self.live_start += delta; self.live_end += delta
        elif position <= self.live_start and position + charsRemoved >= self.live_start:
            self.live_start = position; self.live_end += delta
        elif self.live_start < position <= self.live_end + 1:
            self.live_end += delta
        doc_len = self.document().characterCount() - 1
        self.live_start = max(0, min(self.live_start, doc_len))
        self.live_end = max(self.live_start, min(self.live_end, doc_len))

    def lineNumberAreaWidth(self):
        digits, max_val = 1, max(1, self.blockCount())
        while max_val >= 10: max_val /= 10; digits += 1
        return 15 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy: self.lineNumberArea.scroll(0, dy)
        else: self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#f0f0f0")) 
        block = self.firstVisibleBlock(); blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#777777")) 
                rect_draw = QRect(0, int(top), self.lineNumberArea.width() - 5, self.fontMetrics().height())
                painter.drawText(rect_draw, Qt.AlignmentFlag.AlignRight, str(blockNumber + 1))
            block = block.next(); top = bottom; bottom = top + round(self.blockBoundingRect(block).height()); blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if getattr(self, 'live_start', None) is not None:
            sc = QTextCursor(self.document()); sc.setPosition(self.live_start); sc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            self.live_start = sc.position()
            ec = QTextCursor(self.document()); ec.setPosition(self.live_end); ec.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self.live_end = ec.position()
            live_selection = QTextEdit.ExtraSelection()
            live_selection.format.setBackground(QColor("#E6FFED"))
            live_selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            cursor = QTextCursor(self.document()); cursor.setPosition(self.live_start); cursor.setPosition(self.live_end, QTextCursor.MoveMode.KeepAnchor)
            live_selection.cursor = cursor; extraSelections.append(live_selection)
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#E8F2FF"))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor(); selection.cursor.clearSelection(); extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Tab and e.modifiers() == Qt.KeyboardModifier.NoModifier:
            if not (self.completer.popup() and self.completer.popup().isVisible()):
                self.insertPlainText("  ")
                return
        is_shortcut = (e.modifiers() & Qt.KeyboardModifier.ControlModifier) and e.key() == Qt.Key.Key_Space
        if self.completer.popup() and self.completer.popup().isVisible():
            if e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                e.ignore(); return
        super().keyPressEvent(e)
        tc = self.textCursor(); block_text = tc.block().text(); text_before = block_text[:tc.positionInBlock()]
        match = re.search(r'(\\[a-zA-Z]*|[a-zA-Z]+)$', text_before)
        completion_prefix = match.group(1) if match else ""
        if (completion_prefix.startswith('\\') and len(completion_prefix) >= 2) or is_shortcut:
            self.completer.setCompletionPrefix(completion_prefix)
            popup = self.completer.popup(); popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
            cr = self.cursorRect(); cr.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        elif self.completer.popup().isVisible(): self.completer.popup().hide()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        if self.main_window:
            ai_act = QAction("✨ Ask Gemini AI (Explain/Fix code)", self)
            ai_act.triggered.connect(self.main_window.open_ai_assistant)
            menu.addAction(ai_act)
            menu.addSeparator()
            is_live = getattr(self.main_window, 'live_preview_enabled', False)
            if is_live:
                stop_live_act = QAction("❌ Disable Live Preview", self)
                stop_live_act.triggered.connect(self.main_window.trigger_stop_live_preview)
                menu.addAction(stop_live_act)
            else:
                start_live_act = QAction("⚡ Enable Live Preview", self)
                start_live_act.triggered.connect(self.main_window.trigger_start_live_preview)
                menu.addAction(start_live_act)
            menu.addSeparator()
            is_master = (self.main_window.master_file_path == self.file_path) and self.file_path != ""
            if is_master:
                clear_master_act = QAction("❌ Clear Master File", self)
                clear_master_act.triggered.connect(self.main_window.trigger_clear_master_document)
                menu.addAction(clear_master_act)
            else:
                set_master_act = QAction("⭐ Set as Master File", self)
                set_master_act.triggered.connect(self.trigger_set_master)
                menu.addAction(set_master_act)
            menu.addSeparator()
            forward_search_act = QAction("➡️ Go to PDF (Cmd/Ctrl + Click)", self)
            forward_search_act.triggered.connect(self.trigger_forward_search)
            menu.addAction(forward_search_act)
        menu.exec(event.globalPos())

    def trigger_set_master(self, *args):
        if self.main_window:
            for i in range(self.main_window.editor_tabs.count()):
                if self.main_window.editor_tabs.widget(i) == self: self.main_window.set_master_by_index(i); break

    def trigger_forward_search(self, *args):
        if self.main_window and self.file_path:
            self.main_window.forward_search(self.file_path, self.textCursor().blockNumber() + 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.modifiers() in (Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.MetaModifier):
            cursor = self.cursorForPosition(e.pos())
            if self.main_window and self.file_path: self.main_window.forward_search(self.file_path, cursor.blockNumber() + 1)
            return
        super().mousePressEvent(e)

    def convert_case(self, to_upper=True):
        """Chuyển đổi chữ hoa/thường cho vùng chọn hoặc từ dưới con trỏ"""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        
        text = cursor.selectedText()
        new_text = text.upper() if to_upper else text.lower()
        cursor.insertText(new_text)
        self.setTextCursor(cursor)