import sys
import os
import json
import re
import subprocess
import requests

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QSplitter, QWidget, QVBoxLayout,
    QTextEdit, QListWidget, QLabel, QLineEdit, QComboBox, QMessageBox,
    QFileDialog, QMenu, QHBoxLayout, QListWidgetItem, QPushButton, QInputDialog,
    QApplication, QFontDialog, QTabBar, QToolButton   # <--- Thêm QTabBar, QToolButton
)
from PyQt6.QtGui import (
    QAction, QKeySequence, QColor, QTextCursor, QTextFormat, QIcon, 
    QTextDocument, QPixmap, QPainter, QFont
)
from PyQt6.QtCore import Qt, QProcess, QTimer, QPointF, QSize, QRect
from PyQt6.QtPdfWidgets import QPdfView

from .config import (TEXBIN_DIR, SYNCTEX_PATH, DEFAULT_MACROS, SESSION_FILE, 
                     AI_CONFIG_FILE, SHORTCUTS_FILE, DEFAULT_SHORTCUTS, 
                     CONFIG_DIR, USER_MACROS_FILE, EDITOR_CONFIG_FILE, 
                     RECENT_FILES_FILE, TEMPLATE_DIR) # <--- THÊM TEMPLATE_DIR Ở ĐÂY
from .widgets import CodeEditor
from .dialogs import MacroDialog, ShortcutDialog, AIDialog, AIWindow
from .pdf_viewer import PDFViewer
from .about import AboutDialog

class ScrollableTabBar(QTabBar):
    def wheelEvent(self, event):
        angle = event.angleDelta().x() if event.angleDelta().x() != 0 else event.angleDelta().y()
        
        if angle > 0: 
            for child in self.children():
                if isinstance(child, QToolButton) and child.arrowType() == Qt.ArrowType.LeftArrow:
                    child.click(); break
        elif angle < 0: 
            for child in self.children():
                if isinstance(child, QToolButton) and child.arrowType() == Qt.ArrowType.RightArrow:
                    child.click(); break
        
        event.accept() 

class LatexEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_name = "TeX-AI Pro Editor v1.8.5"
        self.setWindowTitle(self.app_name)
        self.resize(1400, 900)

        self.working_dir = ""
        self.master_file_path = ""
        self.full_log_output = ""
        self.last_live_content = "" # Biến lưu content để tối ưu Live Preview
        
        self.api_key = self.load_api_key()
        self.shortcuts = self.load_shortcuts()
        self.editor_config = self.load_editor_config() 

        self.live_preview_enabled = False
        self.live_timer = QTimer(self)
        self.live_timer.setSingleShot(True)
        self.live_timer.timeout.connect(self.do_live_compile)
        
        self.live_compile_process = QProcess(self)
        self.live_compile_process.finished.connect(self.on_live_compile_finished)

        self.parse_timer = QTimer(self)
        self.parse_timer.setSingleShot(True)
        self.parse_timer.timeout.connect(self.parse_custom_commands)

        self.macro_file = USER_MACROS_FILE
        self.session_file = SESSION_FILE
        self.user_macros = [m.copy() for m in DEFAULT_MACROS]
        
        self.load_user_macros()

        self.compile_process = QProcess(self)
        self.compile_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.compile_process.readyReadStandardError.connect(self.handle_stderr)
        self.compile_process.finished.connect(self.compile_finished)

        # QProcess cho SyncTeX để chống đơ giao diện
        self.forward_search_process = QProcess(self)
        self.forward_search_process.finished.connect(self.on_forward_search_finished)
        self.inverse_search_process = QProcess(self)
        self.inverse_search_process.finished.connect(self.on_inverse_search_finished)

        self.init_ui()
        self.load_session()
        
        import sys
        if len(sys.argv) > 1:
            file_to_open = sys.argv[-1] 
            if os.path.exists(file_to_open) and file_to_open.lower().endswith(".tex"):
                QTimer.singleShot(200, lambda: self.open_specific_file(file_to_open))
        
        self.update_window_title()

    def get_emoji_icon(self, emoji_str):
        pixmap = QPixmap(128, 128)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        import sys
        if sys.platform == "darwin":
            font = QFont("Apple Color Emoji", 92)
        else:
            font = QFont("Segoe UI Emoji", 92)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, 128, 128), Qt.AlignmentFlag.AlignCenter, emoji_str)
        painter.end()
        return QIcon(pixmap)

    def load_api_key(self):
        if os.path.exists(AI_CONFIG_FILE):
            try:
                import json
                with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f: 
                    return json.load(f).get("api_key", "")
            except: pass
        return ""

    def load_shortcuts(self):
        if os.path.exists(SHORTCUTS_FILE):
            try:
                import json
                with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f: 
                    return json.load(f)
            except: pass
        return DEFAULT_SHORTCUTS.copy()

    def load_editor_config(self):
        if os.path.exists(EDITOR_CONFIG_FILE):
            try:
                import json
                with open(EDITOR_CONFIG_FILE, "r", encoding="utf-8") as f: 
                    return json.load(f)
            except: pass
        return {"font_family": "Menlo", "font_size": 14}

    def change_editor_font(self):
        current_font = QFont(self.editor_config.get("font_family", "Menlo"), self.editor_config.get("font_size", 14))
        font, ok = QFontDialog.getFont(current_font, self, "Select Editor Font")
        if ok:
            self.editor_config["font_family"] = font.family()
            self.editor_config["font_size"] = font.pointSize()
            try:
                import json
                with open(EDITOR_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.editor_config, f, indent=4)
            except: pass
            
            for i in range(self.editor_tabs.count()):
                editor = self.editor_tabs.widget(i)
                if hasattr(editor, 'update_font'):
                    editor.update_font(font)

    def load_user_macros(self):
        if os.path.exists(self.macro_file):
            try:
                import json
                with open(self.macro_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data: 
                        loaded_macros = []
                        for item in data:
                            if isinstance(item, dict):
                                loaded_macros.append(item)
                            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                                loaded_macros.append({
                                    "icon": item[0], "name": item[1], "code": item[2],
                                    "type": "Script", "position": "Top", "shortcut": ""
                                })
                        if loaded_macros:
                            self.user_macros = loaded_macros
            except: pass

    def update_window_title(self):
        import os
        master_info = ""
        if self.master_file_path:
            master_info = f" | ⭐ Master: {os.path.basename(self.master_file_path)}"
        
        curr_ed = self.get_current_editor()
        curr_info = ""
        if curr_ed and curr_ed.file_path:
            curr_info = f" - [{curr_ed.file_path}]"
        elif curr_ed:
            curr_info = " - [Untitled]"
            
        self.setWindowTitle(f"{self.app_name}{master_info}{curr_info}")

    def init_ui(self):
        self.recent_files = self.load_recent_files()
        
        self.create_actions_and_menus()

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabBar(ScrollableTabBar(self.editor_tabs)) 
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setUsesScrollButtons(True) 
        self.editor_tabs.setElideMode(Qt.TextElideMode.ElideNone)

        self.editor_tabs.setStyleSheet("""
            QTabBar::scroller {
                width: 50px;
            }
            QTabBar QToolButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTabBar QToolButton:hover {
                background-color: #e0e0e0;
            }
        """)

        left_corner_widget = QWidget()
        left_corner_layout = QHBoxLayout(left_corner_widget)
        left_corner_layout.setContentsMargins(0, 0, 0, 0)
        left_corner_layout.setSpacing(2)
        
        btn_scroll_left = QToolButton()
        btn_scroll_left.setArrowType(Qt.ArrowType.LeftArrow)
        btn_scroll_right = QToolButton()
        btn_scroll_right.setArrowType(Qt.ArrowType.RightArrow)
        
        btn_scroll_left.clicked.connect(lambda: self.scroll_tabs_manual(Qt.ArrowType.LeftArrow))
        btn_scroll_right.clicked.connect(lambda: self.scroll_tabs_manual(Qt.ArrowType.RightArrow))
        
        left_corner_layout.addWidget(btn_scroll_left)
        left_corner_layout.addWidget(btn_scroll_right)
        
        self.editor_tabs.setCornerWidget(left_corner_widget, Qt.Corner.TopLeftCorner)

        self.editor_tabs.tabCloseRequested.connect(self.close_tab)
        self.editor_tabs.currentChanged.connect(self.on_tab_changed)
        self.editor_tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor_tabs.tabBar().customContextMenuRequested.connect(self.show_tab_context_menu)

        self.search_frame = QWidget()
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(5, 5, 5, 5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find...")
        self.search_input.returnPressed.connect(self.find_next)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        self.replace_input.returnPressed.connect(self.replace_text)
        
        self.btn_find_prev = QPushButton("◀")
        self.btn_find_next = QPushButton("▶")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("Replace All")
        self.btn_close_search = QPushButton("❌")
        
        self.btn_find_prev.clicked.connect(self.find_prev)
        self.btn_find_next.clicked.connect(self.find_next)
        self.btn_replace.clicked.connect(self.replace_text)
        self.btn_replace_all.clicked.connect(self.replace_all)
        self.btn_close_search.clicked.connect(self.search_frame.hide)
        
        search_layout.addWidget(QLabel("Find:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_find_prev)
        search_layout.addWidget(self.btn_find_next)
        
        self.replace_label = QLabel("Replace:")
        search_layout.addWidget(self.replace_label)
        search_layout.addWidget(self.replace_input)
        search_layout.addWidget(self.btn_replace)
        search_layout.addWidget(self.btn_replace_all)
        search_layout.addStretch()
        search_layout.addWidget(self.btn_close_search)
        self.search_frame.hide()

        self.log_tabs = QTabWidget()
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("font-family: 'Courier New'; font-size: 11pt; background-color: #f9f9f9;")
        
        self.error_viewer = QListWidget()
        self.error_viewer.setStyleSheet("font-family: 'Courier New'; font-size: 11pt; color: #b22222; background-color: #fce8e8; padding: 5px;")
        self.error_viewer.itemDoubleClicked.connect(self.on_error_item_clicked)
        
        self.log_tabs.addTab(self.log_viewer, "Compilation Log")
        self.log_tabs.addTab(self.error_viewer, "⚠️ Issues")

        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.addWidget(self.editor_tabs)
        self.left_splitter.addWidget(self.log_tabs)
        self.left_splitter.setSizes([650, 200])

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search_frame)
        left_layout.addWidget(self.left_splitter)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        pdf_toolbar = QToolBar("PDF Tools")
        pdf_toolbar.setMovable(False)
        pdf_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        pdf_toolbar.setIconSize(QSize(24, 24))
        
        zoom_in_act = QAction(self.get_emoji_icon("➕"), "Zoom In", self)
        zoom_in_act.triggered.connect(self.zoom_in_pdf)
        zoom_out_act = QAction(self.get_emoji_icon("➖"), "Zoom Out", self)
        zoom_out_act.triggered.connect(self.zoom_out_pdf)
        fit_width_act = QAction(self.get_emoji_icon("↔️"), "Fit Width", self)
        fit_width_act.triggered.connect(self.fit_to_width)
        fit_page_act = QAction(self.get_emoji_icon("📄"), "Fit Page", self)
        fit_page_act.triggered.connect(self.fit_to_page)
        first_page_act = QAction(self.get_emoji_icon("⏮️"), "First Page", self)
        first_page_act.triggered.connect(self.first_pdf_page)
        prev_page_act = QAction(self.get_emoji_icon("◀️"), "Prev Page", self)
        prev_page_act.triggered.connect(self.prev_pdf_page)
        next_page_act = QAction(self.get_emoji_icon("▶️"), "Next Page", self)
        next_page_act.triggered.connect(self.next_pdf_page)
        last_page_act = QAction(self.get_emoji_icon("⏭️"), "Last Page", self)
        last_page_act.triggered.connect(self.last_pdf_page)
        open_external_act = QAction(self.get_emoji_icon("🔗"), "Open PDF in Default Viewer", self)
        open_external_act.triggered.connect(self.open_pdf_in_default_viewer)

        self.page_input = QLineEdit("1")
        self.page_input.setFixedWidth(40)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.returnPressed.connect(self.goto_pdf_page)
        self.page_count_label = QLabel(" / 0")

        pdf_toolbar.addAction(zoom_in_act)
        pdf_toolbar.addAction(zoom_out_act)
        pdf_toolbar.addAction(fit_width_act)
        pdf_toolbar.addAction(fit_page_act)
        pdf_toolbar.addSeparator()
        pdf_toolbar.addAction(first_page_act)
        pdf_toolbar.addAction(prev_page_act)
        pdf_toolbar.addWidget(self.page_input)
        pdf_toolbar.addWidget(self.page_count_label)
        pdf_toolbar.addAction(next_page_act)
        pdf_toolbar.addAction(last_page_act)
        pdf_toolbar.addSeparator()
        pdf_toolbar.addAction(open_external_act)

        self.pdf_viewer = PDFViewer(self)
        right_layout.addWidget(pdf_toolbar)
        right_layout.addWidget(self.pdf_viewer)
        self.pdf_viewer.pageNavigator().currentPageChanged.connect(self.update_page_input)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([700, 700])
        self.setCentralWidget(splitter)

        self.status_label = QLabel("Ready.")
        self.statusBar().addWidget(self.status_label)

    def scroll_tabs_manual(self, arrow_type):
        for child in self.editor_tabs.tabBar().children():
            if isinstance(child, QToolButton) and child.arrowType() == arrow_type:
                child.click()
                break

    def load_recent_files(self):
        import os, json
        if os.path.exists(RECENT_FILES_FILE):
            with open(RECENT_FILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)[:10] 
        return []

    def update_recent_menu(self):
        import os
        self.recent_menu.clear()
        for f_path in self.recent_files:
            act = QAction(os.path.basename(f_path), self)
            act.setData(f_path)
            act.triggered.connect(lambda chk, p=f_path: self.open_specific_file(p))
            self.recent_menu.addAction(act)

    def clean_auxiliary_files(self):
        import os
        target = self.get_compilation_target()
        if not target: return
        
        folder = os.path.dirname(target)
        base_name = os.path.splitext(os.path.basename(target))[0]
        from .config import AUX_EXTENSIONS
        
        count = 0
        for ext in AUX_EXTENSIONS:
            file_to_del = os.path.join(folder, base_name + ext)
            if os.path.exists(file_to_del):
                os.remove(file_to_del)
                count += 1
        self.status_label.setText(f"✨ Cleaned {count} auxiliary files.")

    def reset_settings_to_default(self):
        reply = QMessageBox.question(self, "Confirmation", 
            "Are you sure you want to reset all settings (Macros, Shortcuts, Configs)?\nThe application will close after this.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            from .config import USER_MACROS_FILE, SHORTCUTS_FILE, EDITOR_CONFIG_FILE, AUTOCOMPLETE_FILE, SESSION_FILE
            import os
            files_to_reset = [USER_MACROS_FILE, SHORTCUTS_FILE, EDITOR_CONFIG_FILE, AUTOCOMPLETE_FILE, SESSION_FILE]
            for f in files_to_reset:
                if os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
            
            self.is_resetting = True
            self.close()

    def closeEvent(self, event):
        if getattr(self, 'is_resetting', False):
            event.accept()
            return
            
        self.save_session() 
        self.save_user_macros()
        self.clear_live_temp_files()
        try:
            if self.compile_process.state() != QProcess.ProcessState.NotRunning:
                self.compile_process.kill()
            if self.live_compile_process.state() != QProcess.ProcessState.NotRunning:
                self.live_compile_process.kill()
            if self.forward_search_process.state() != QProcess.ProcessState.NotRunning:
                self.forward_search_process.kill()
            if self.inverse_search_process.state() != QProcess.ProcessState.NotRunning:
                self.inverse_search_process.kill()
            if hasattr(self, 'pdf_viewer'):
                self.pdf_viewer.setDocument(None)
        except: pass
        event.accept()

    def trigger_new_file(self, *args):
        self.add_new_tab("Untitled.tex", "")

    def trigger_open_file(self, *args):
        self.open_tex_file_dialog()

    def trigger_save_file(self, *args):
        self.save_all_files()

    def trigger_close(self, *args):
        self.close()

    def trigger_cut(self, *args):
        editor = self.get_current_editor()
        if editor: editor.cut()

    def trigger_copy(self, *args):
        editor = self.get_current_editor()
        if editor: editor.copy()

    def trigger_paste(self, *args):
        editor = self.get_current_editor()
        if editor: editor.paste()

    def trigger_find(self, *args):
        self.show_find()

    def trigger_replace(self, *args):
        self.show_replace()

    def trigger_goto(self, *args):
        self.goto_line()

    def trigger_toggle_comment(self, *args):
        editor = self.get_current_editor()
        if editor: editor.toggle_comment()

    def trigger_compile(self, *args):
        self.start_compile_latex()

    def trigger_stop_compile(self, *args):
        self.stop_compilation()

    def trigger_about(self, *args):
        dlg = AboutDialog(self)
        dlg.exec()

    def trigger_clear_master_document(self, *args):
        self.clear_master_document()

    def trigger_start_live_preview(self, *args):
        editor = self.get_current_editor()
        if editor: self.start_live_preview(editor)

    def trigger_stop_live_preview(self, *args):
        self.stop_live_preview()

    def create_shortcut_handler(self, code, m_type):
        def handler(*args):
            self.insert_macro_to_editor(code, m_type)
        return handler

    def create_actions_and_menus(self):
        self.new_action = QAction(self.get_emoji_icon("📄"), "New File", self)
        self.new_action.setShortcut(QKeySequence(self.shortcuts.get("new_file", "Ctrl+N")))
        self.new_action.triggered.connect(self.trigger_new_file)

        self.open_action = QAction(self.get_emoji_icon("📂"), "Open...", self)
        self.open_action.setShortcut(QKeySequence(self.shortcuts.get("open_file", "Ctrl+O")))
        self.open_action.triggered.connect(self.trigger_open_file)

        self.save_action = QAction(self.get_emoji_icon("💾"), "Save", self)
        self.save_action.setShortcut(QKeySequence(self.shortcuts.get("save_file", "Ctrl+S")))
        self.save_action.triggered.connect(self.trigger_save_file)

        self.save_as_action = QAction(self.get_emoji_icon("💾"), "Save As...", self)
        self.save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_as_action.triggered.connect(self.save_file_as)

        self.open_folder_action = QAction(self.get_emoji_icon("📂"), "Reveal in Finder/Explorer", self)
        self.open_folder_action.triggered.connect(lambda: self.open_containing_folder(-1))
        
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.trigger_close)

        self.cut_action = QAction(self.get_emoji_icon("✂️"), "Cut", self)
        self.cut_action.setShortcut(QKeySequence("Ctrl+X"))
        self.cut_action.triggered.connect(self.trigger_cut)

        self.copy_action = QAction(self.get_emoji_icon("📑"), "Copy", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_action.triggered.connect(self.trigger_copy)

        self.paste_action = QAction(self.get_emoji_icon("📋"), "Paste", self)
        self.paste_action.setShortcut(QKeySequence("Ctrl+V"))
        self.paste_action.triggered.connect(self.trigger_paste)

        self.find_action = QAction("🔍 Find", self)
        self.find_action.setShortcut(QKeySequence(self.shortcuts.get("find", "Ctrl+F")))
        self.find_action.triggered.connect(self.trigger_find)

        self.replace_action = QAction("🔄 Replace", self)
        self.replace_action.setShortcut(QKeySequence(self.shortcuts.get("replace", "Ctrl+H")))
        self.replace_action.triggered.connect(self.trigger_replace)

        self.goto_action = QAction("🔢 Go to Line...", self)
        self.goto_action.setShortcut(QKeySequence(self.shortcuts.get("goto", "Ctrl+G")))
        self.goto_action.triggered.connect(self.trigger_goto)

        self.comment_action = QAction("Toggle Comment", self)
        self.comment_action.setShortcut(QKeySequence(self.shortcuts.get("toggle_comment", "Ctrl+/"))) 
        self.comment_action.triggered.connect(self.trigger_toggle_comment)
        
        self.format_code_action = QAction("✨ Auto-Format Code", self)
        self.format_code_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        self.format_code_action.triggered.connect(self.trigger_standardize_code)

        self.compile_action = QAction(self.get_emoji_icon("▶️"), "Compile", self)
        self.compile_action.setShortcut(QKeySequence(self.shortcuts.get("compile", "F5")))
        self.compile_action.triggered.connect(self.trigger_compile)

        self.stop_compile_action = QAction(self.get_emoji_icon("⏹️"), "Stop Build", self)
        self.stop_compile_action.triggered.connect(self.trigger_stop_compile)
        self.stop_compile_action.setEnabled(False)

        self.clean_aux_action = QAction("🧹 Clean Auxiliary Files", self)
        self.clean_aux_action.triggered.connect(self.clean_auxiliary_files)

        self.toggle_log_action = QAction(self.get_emoji_icon("📋"), "Toggle Log", self)
        self.toggle_log_action.setShortcut(QKeySequence("Ctrl+L"))
        self.toggle_log_action.triggered.connect(self.toggle_log_window)

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        
        self.recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self.recent_menu)
        self.update_recent_menu()
        
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.open_folder_action)
        
        template_menu = QMenu("Templates", self)
        new_tpl_act = QAction("📄 New from Template...", self)
        new_tpl_act.triggered.connect(self.new_from_template)
        save_tpl_act = QAction("💾 Save as Template...", self)
        save_tpl_act.triggered.connect(self.save_as_template)
        template_menu.addAction(new_tpl_act)
        template_menu.addAction(save_tpl_act)
        file_menu.addMenu(template_menu)
        
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.cut_action)
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.find_action)
        edit_menu.addAction(self.replace_action)
        edit_menu.addAction(self.goto_action)
        edit_menu.addSeparator()
        
        text_op_menu = QMenu("Text Operations", self)
        to_upper_act = QAction("To UPPERCASE", self)
        to_lower_act = QAction("To lowercase", self)
        to_upper_act.triggered.connect(lambda: self.get_current_editor().convert_case(True) if self.get_current_editor() else None)
        to_lower_act.triggered.connect(lambda: self.get_current_editor().convert_case(False) if self.get_current_editor() else None)
        text_op_menu.addAction(to_upper_act)
        text_op_menu.addAction(to_lower_act)
        edit_menu.addMenu(text_op_menu)
        
        edit_menu.addAction(self.comment_action)
        edit_menu.addAction(self.format_code_action)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.toggle_log_action)

        ai_menu = menubar.addMenu("&AI")
        ai_run_act = QAction("✨ AI Assistant (Explain/Fix code)", self)
        ai_run_act.triggered.connect(self.open_ai_assistant)
        ai_set_act = QAction("🤖 Configure Gemini API", self)
        ai_set_act.triggered.connect(self.open_ai_config)
        ai_menu.addAction(ai_run_act)
        ai_menu.addSeparator()
        ai_menu.addAction(ai_set_act)

        settings_menu = menubar.addMenu("&Settings")
        shortcut_set_act = QAction("⌨️ Edit Shortcuts", self)
        shortcut_set_act.triggered.connect(self.open_shortcut_config)
        settings_menu.addAction(shortcut_set_act)
        font_set_act = QAction("🔠 Editor Font Settings...", self)
        font_set_act.triggered.connect(self.change_editor_font)
        settings_menu.addAction(font_set_act)
        settings_menu.addSeparator()
        reset_settings_act = QAction("⚠️ Reset to Default (Clear JSON Config)", self)
        reset_settings_act.triggered.connect(self.reset_settings_to_default)
        settings_menu.addAction(reset_settings_act)

        build_menu = menubar.addMenu("&Build")
        build_menu.addAction(self.compile_action)
        build_menu.addAction(self.stop_compile_action)
        build_menu.addAction(self.clean_aux_action)
        build_menu.addSeparator()

        self.engine_pdflatex = QAction("PDFLaTeX (Default)", self)
        self.engine_pdflatex.setCheckable(True)
        self.engine_xelatex = QAction("XeLaTeX", self)
        self.engine_xelatex.setCheckable(True)
        self.engine_lualatex = QAction("LuaLaTeX", self)
        self.engine_lualatex.setCheckable(True)
        self.engine_pdflatex.setChecked(True)
        self.engine_pdflatex.triggered.connect(lambda *args: [self.engine_xelatex.setChecked(False), self.engine_lualatex.setChecked(False)])
        self.engine_xelatex.triggered.connect(lambda *args: [self.engine_pdflatex.setChecked(False), self.engine_lualatex.setChecked(False)])
        self.engine_lualatex.triggered.connect(lambda *args: [self.engine_pdflatex.setChecked(False), self.engine_xelatex.setChecked(False)])
        build_menu.addAction(self.engine_pdflatex)
        build_menu.addAction(self.engine_xelatex)
        build_menu.addAction(self.engine_lualatex)

        latex_menu = menubar.addMenu("&LaTeX")
        shortcut_mappings = [
            ("Inline Math", "Ctrl+Shift+M", "$%|$", "Script"),
            ("Display Math", "Alt+Shift+M", "\\[\n\t%|\n\\]", "Script"),
            ("Fraction", "Alt+Shift+F", "\\frac{%|}{}", "Script"),
            ("Square Root", "Ctrl+Alt+Q", "\\sqrt{%|}", "Script"),
            ("Superscript", "Ctrl+Shift+U", "^{%|}", "Script"),
            ("Subscript", "Ctrl+Shift+D", "_{%|}", "Script"),
            ("Itemize Environment", "Ctrl+Shift+L", "\\begin{itemize}\n\t\\item %|\n\\end{itemize}", "Script"),
            ("Enumerate Environment", "Ctrl+Shift+K", "\\begin{enumerate}\n\t\\item %|\n\\end{enumerate}", "Script"),
            ("New Environment", "Ctrl+E", "\\begin{%|}\n\t\n\\end{}", "Script"),
            ("Insert \\item", "Ctrl+Shift+I", "\\item %|", "Script")
        ]

        for name, key, code, m_type in shortcut_mappings:
            act = QAction(name, self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(self.create_shortcut_handler(code, m_type))
            latex_menu.addAction(act)
            self.addAction(act)

        self.macro_menu = menubar.addMenu("&Macros")
        texai_menu = menubar.addMenu("TeX-AI")
        about_act = QAction("About TeX-AI Pro v1.8.5", self)
        about_act.triggered.connect(self.trigger_about)
        texai_menu.addAction(about_act)

        self.top_toolbar = self.addToolBar("Main Tools")
        self.top_toolbar.setObjectName("TopToolbar")
        self.top_toolbar.setIconSize(QSize(16, 16))
        self.top_toolbar.addAction(self.new_action)
        self.top_toolbar.addAction(self.open_action)
        self.top_toolbar.addAction(self.save_action)
        self.top_toolbar.addSeparator()
        self.top_toolbar.addAction(self.cut_action)
        self.top_toolbar.addAction(self.copy_action)
        self.top_toolbar.addAction(self.paste_action)
        self.top_toolbar.addSeparator()
        self.top_toolbar.addAction(self.compile_action)
        self.top_toolbar.addAction(self.stop_compile_action)
        self.top_toolbar.addSeparator()
        self.top_toolbar.addAction(self.toggle_log_action)
        self.top_macro_separator = self.top_toolbar.addSeparator()
        
        self.left_toolbar = QToolBar("Macro Toolbar")
        self.left_toolbar.setObjectName("LeftToolbar")
        self.left_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.left_toolbar)

        self.build_macro_toolbars()

    def toggle_log_window(self):
        is_visible = self.log_tabs.isVisible()
        self.log_tabs.setVisible(not is_visible)
        if not is_visible:
            self.left_splitter.setSizes([600, 200])

    def open_ai_config(self):
        dlg = AIDialog(self)
        if dlg.exec():
            self.api_key = self.load_api_key()

    def open_shortcut_config(self):
        dlg = ShortcutDialog(self)
        if dlg.exec():
            self.shortcuts = self.load_shortcuts()
            self.new_action.setShortcut(QKeySequence(self.shortcuts.get("new_file", "Ctrl+N")))
            self.open_action.setShortcut(QKeySequence(self.shortcuts.get("open_file", "Ctrl+O")))
            self.save_action.setShortcut(QKeySequence(self.shortcuts.get("save_file", "Ctrl+S")))
            self.compile_action.setShortcut(QKeySequence(self.shortcuts.get("compile", "F5")))
            self.find_action.setShortcut(QKeySequence(self.shortcuts.get("find", "Ctrl+F")))
            self.replace_action.setShortcut(QKeySequence(self.shortcuts.get("replace", "Ctrl+H")))
            self.goto_action.setShortcut(QKeySequence(self.shortcuts.get("goto", "Ctrl+G")))
            self.comment_action.setShortcut(QKeySequence(self.shortcuts.get("toggle_comment", "Ctrl+/")))

    def open_ai_assistant(self):
        editor = self.get_current_editor()
        if not editor:
            return
        
        selected_text = editor.textCursor().selectedText()
        dlg = AIWindow(self, selected_text)
        
        def handle_generate():
            if not self.api_key:
                QMessageBox.warning(self, "AI Error", "Please configure Gemini API Key in the AI menu!")
                return
            
            dlg.btn_generate.setEnabled(False)
            dlg.btn_generate.setText("⌛ Processing (Vision & Text)...")
            
            try:
                import requests
                import base64
                import mimetypes
                
                selected_model = dlg.model_combo.currentText().strip()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={self.api_key}"
                
                prompt = dlg.prompt_input.toPlainText()
                full_prompt = f"Bạn là chuyên gia LaTeX. Yêu cầu: {prompt}.\n\nNội dung văn bản hiện tại (nếu có): {selected_text}\n\nHãy trả về mã LaTeX tối ưu nhất, KHÔNG giải thích dông dài, KHÔNG dùng markdown block dư thừa."
                
                # Cấu trúc nội dung gửi đi (có thể chứa cả Text và Image)
                parts = [{"text": full_prompt}]
                
                # Nếu có ảnh đính kèm, mã hóa base64 và thêm vào
                if dlg.image_path and os.path.exists(dlg.image_path):
                    mime_type, _ = mimetypes.guess_type(dlg.image_path)
                    with open(dlg.image_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode("utf-8")
                    
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type or "image/jpeg",
                            "data": img_data
                        }
                    })
                
                payload = {
                    "contents": [{"parts": parts}]
                }
                
                response = requests.post(url, json=payload, timeout=45) # Tăng timeout vì upload ảnh có thể lâu hơn
                
                if response.status_code == 200:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    import re
                    clean_text = re.sub(r"```[a-zA-Z]*\n?", "", text).replace("```", "").strip()
                    dlg.result_output.setPlainText(clean_text)
                else:
                    dlg.result_output.setPlainText(f"API Error ({response.status_code}):\n{response.text}")
            except Exception as e:
                QMessageBox.critical(self, "API Error", f"Connection error: {str(e)}")
            finally:
                dlg.btn_generate.setEnabled(True)
                dlg.btn_generate.setText("✨ Send to Gemini AI")
                
        dlg.btn_generate.clicked.connect(handle_generate)

        try:
            dlg.btn_copy.clicked.disconnect()
            dlg.btn_replace.clicked.disconnect()
        except: pass

        def safe_copy():
            text_to_copy = dlg.result_output.toPlainText()
            if text_to_copy:
                QApplication.clipboard().setText(text_to_copy)
                self.status_label.setText("Copied AI output to clipboard!")
                
        dlg.btn_copy.clicked.connect(safe_copy)

        def replace_and_close():
            text_to_replace = dlg.result_output.toPlainText()
            if text_to_replace:
                editor.insertPlainText(text_to_replace)
            dlg.accept()
            
        dlg.btn_replace.clicked.connect(replace_and_close)
        
        dlg.exec()

    def show_find(self):
        self.search_frame.show()
        self.replace_label.hide()
        self.replace_input.hide()
        self.btn_replace.hide()
        self.btn_replace_all.hide()
        editor = self.get_current_editor()
        if editor and editor.textCursor().hasSelection():
            self.search_input.setText(editor.textCursor().selectedText())
        self.search_input.setFocus()

    def show_replace(self):
        self.search_frame.show()
        self.replace_label.show()
        self.replace_input.show()
        self.btn_replace.show()
        self.btn_replace_all.show()
        editor = self.get_current_editor()
        if editor and editor.textCursor().hasSelection():
            self.search_input.setText(editor.textCursor().selectedText())
        self.search_input.setFocus()

    def find_next(self):
        editor = self.get_current_editor()
        text = self.search_input.text()
        if not editor or not text: return
        found = editor.find(text)
        if not found:
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            editor.setTextCursor(cursor)
            editor.find(text)

    def find_prev(self):
        editor = self.get_current_editor()
        text = self.search_input.text()
        if not editor or not text: return
        options = QTextDocument.FindFlag.FindBackward
        found = editor.find(text, options)
        if not found:
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            editor.setTextCursor(cursor)
            editor.find(text, options)

    def replace_text(self):
        editor = self.get_current_editor()
        if not editor: return
        cursor = editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.search_input.text():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        editor = self.get_current_editor()
        text = self.search_input.text()
        replace_with = self.replace_input.text()
        if not editor or not text: return
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        count = 0
        while editor.find(text):
            editor.textCursor().insertText(replace_with)
            count += 1
        cursor.endEditBlock()
        self.status_label.setText(f"Replaced {count} occurrences.")

    def goto_line(self):
        editor = self.get_current_editor()
        if not editor: return
        max_lines = max(1, editor.blockCount())
        line, ok = QInputDialog.getInt(self, "Go to Line", f"Enter line number (1 - {max_lines}):", 1, 1, max_lines)
        if ok:
            cursor = editor.textCursor()
            cursor.setPosition(editor.document().findBlockByLineNumber(line - 1).position())
            editor.setTextCursor(cursor)
            editor.centerCursor()
            editor.setFocus()

    def build_macro_toolbars(self):
        self.macro_menu.clear()
        self.left_toolbar.clear()

        remove = False
        for act in self.top_toolbar.actions():
            if act == self.top_macro_separator:
                remove = True
                continue
            if remove:
                self.top_toolbar.removeAction(act)

        for m in self.user_macros:
            self.add_macro_action(m)

        self.macro_menu.addSeparator()
        cfg_act = QAction("Manage Macros...", self)
        cfg_act.triggered.connect(lambda *args: self.open_macro_dialog())
        self.macro_menu.addAction(cfg_act)

    def add_macro_action(self, m_item):
        import os
        if isinstance(m_item, dict):
            icon_val = m_item.get("icon", "") or ""
            name = m_item.get("name", "Macro")
            code = m_item.get("code", "")
            m_type = m_item.get("type", "Script")
            position = m_item.get("position", "Top")
            sc = m_item.get("shortcut", "")
        else:
            return

        if icon_val and os.path.exists(icon_val):
            act = QAction(QIcon(icon_val), name, self)
        else:
            act = QAction(self.get_emoji_icon(icon_val or "M"), name, self)
            act.setToolTip(name)

        if sc:
            act.setShortcut(QKeySequence(sc))
            self.addAction(act)

        act.triggered.connect(self.create_shortcut_handler(code, m_type))

        self.macro_menu.addAction(act)
        if position == "Left":
            self.left_toolbar.addAction(act)
        elif position == "Top":
            self.top_toolbar.addAction(act)

    def insert_macro_to_editor(self, code, m_type):
        editor = self.get_current_editor()
        if editor:
            editor.apply_macro_code(code)
            editor.setFocus()

    def open_macro_dialog(self):
        dlg = MacroDialog(self, self.user_macros)
        if dlg.exec():
            self.user_macros = dlg.user_macros
            self.save_user_macros()
            self.build_macro_toolbars()

    def save_user_macros(self):
        try:
            import json
            with open(self.macro_file, "w", encoding="utf-8") as f:
                json.dump(self.user_macros, f, ensure_ascii=False, indent=4)
        except Exception: pass

    def save_session(self):
        data = {
            "files": [self.editor_tabs.widget(i).file_path for i in range(self.editor_tabs.count()) 
                      if hasattr(self.editor_tabs.widget(i), 'file_path') and self.editor_tabs.widget(i).file_path]
        }
        try:
            import json
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def load_session(self):
        import os
        if os.path.exists(self.session_file):
            try:
                import json
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    opened = False
                    for path in data.get("files", []):
                        if os.path.exists(path):
                            self.open_specific_file(path)
                            opened = True
                    if opened: return
            except: pass
        if self.editor_tabs.count() == 0:
            self.add_new_tab("Untitled.tex", "")

    def parse_custom_commands(self):
        editor = self.get_current_editor()
        if not editor: return
        import re
        text = editor.toPlainText()
        new_commands = {}
        matches = re.findall(r'\\(?:newcommand|renewcommand|def)\s*\{\s*\\([a-zA-Z0-9]+)\s*\}|\\(?:def|newcommand)\s*\\([a-zA-Z0-9]+)', text)
        for match in matches:
            cmd = match[0] if match[0] else match[1]
            full_cmd = f"\\{cmd}"
            if full_cmd not in new_commands:
                new_commands[full_cmd] = full_cmd
        if new_commands:
            editor.update_custom_commands(new_commands)

    def clear_live_temp_files(self):
        import os
        editor = self.get_current_editor()
        if not editor: return
        compile_dir = self.working_dir if self.working_dir else os.path.dirname(editor.file_path) if editor.file_path else os.getcwd()
        tmp_pdf_path = os.path.join(compile_dir, "live_preview_tmp.pdf")
        tmp_tex_path = os.path.join(compile_dir, "live_preview_tmp.tex")
        try:
            if os.path.exists(tmp_pdf_path): os.remove(tmp_pdf_path)
            if os.path.exists(tmp_tex_path): os.remove(tmp_tex_path)
        except: pass

    def start_live_preview(self, editor):
        self.clear_live_temp_files()
        self.live_preview_enabled = True
        editor.start_live_region() 
        self.status_label.setText("⚡ Live Preview: ON. Auto-compiling...")
        self.status_label.setStyleSheet("color: #D35400; font-weight: bold;")
        self.do_live_compile()

    def stop_live_preview(self):
        self.live_preview_enabled = False
        self.live_timer.stop()
        if self.live_compile_process.state() != QProcess.ProcessState.NotRunning:
            self.live_compile_process.kill()
            self.live_compile_process.waitForFinished(500)
            
        editor = self.get_current_editor()
        if editor:
            editor.stop_live_region()
            
        self.status_label.setText("Live Preview: OFF.")
        self.status_label.setStyleSheet("color: black; font-weight: normal;")
        
        self.clear_live_temp_files()
        self.show_current_pdf() 

    def get_preamble(self):
        import os, re
        target = self.get_compilation_target()
        if not target or not os.path.exists(target):
            editor = self.get_current_editor()
            if not editor: return "\\documentclass{article}\n\\usepackage{amsmath,amssymb,tikz}"
            text = editor.toPlainText()
        else:
            with open(target, 'r', encoding='utf-8') as f:
                text = f.read()

        match = re.search(r'(.*\\begin\{document\})', text, re.DOTALL)
        if match:
            return match.group(1).replace("\\begin{document}", "")
        else:
            return "\\documentclass{article}\n\\usepackage{amsmath,amssymb,tikz}\n"

    def do_live_compile(self):
        if not self.live_preview_enabled: return
        import os
        editor = self.get_current_editor()
        if not editor or getattr(editor, 'live_start', None) is None: return

        cursor = QTextCursor(editor.document())
        cursor.setPosition(editor.live_start)
        cursor.setPosition(editor.live_end, QTextCursor.MoveMode.KeepAnchor)
        content = cursor.selectedText().replace('\u2029', '\n') 

        # Tối ưu hóa: Chỉ biên dịch nếu nội dung thực sự thay đổi
        if content == self.last_live_content:
            return 
        self.last_live_content = content

        preamble = self.get_preamble()
        compile_dir = self.working_dir if self.working_dir else os.path.dirname(editor.file_path) if editor.file_path else os.getcwd()
        tmp_tex_path = os.path.join(compile_dir, "live_preview_tmp.tex")
        
        try:
            with open(tmp_tex_path, "w", encoding="utf-8") as f:
                f.write(preamble + "\n\\begin{document}\n" + content + "\n\\end{document}")
        except Exception: return

        if self.live_compile_process.state() != QProcess.ProcessState.NotRunning:
            self.live_compile_process.kill()
            self.live_compile_process.waitForFinished(500)

        selected_engine = "pdflatex"
        if hasattr(self, 'engine_xelatex') and self.engine_xelatex.isChecked(): selected_engine = "xelatex"
        elif hasattr(self, 'engine_lualatex') and self.engine_lualatex.isChecked(): selected_engine = "lualatex"

        engine_path = os.path.join(TEXBIN_DIR, selected_engine)
        self.live_compile_process.setWorkingDirectory(compile_dir)
        self.live_compile_process.start(engine_path, ["-interaction=nonstopmode", "-halt-on-error", "live_preview_tmp.tex"])

    def on_live_compile_finished(self, exitCode, exitStatus):
        import os
        if not self.live_preview_enabled: return
        editor = self.get_current_editor()
        compile_dir = self.working_dir if self.working_dir else os.path.dirname(editor.file_path) if editor and editor.file_path else os.getcwd()
        tmp_pdf_path = os.path.join(compile_dir, "live_preview_tmp.pdf")
        
        if os.path.exists(tmp_pdf_path) and exitCode == 0:
            self.pdf_viewer.load_pdf(tmp_pdf_path)

    def get_current_editor(self):
        return self.editor_tabs.currentWidget()

    def add_new_tab(self, filename, content, filepath=""):
        editor = CodeEditor(filepath, self)
        index = self.editor_tabs.addTab(editor, filename)
        self.editor_tabs.setCurrentIndex(index)
        editor.setPlainText(content) 
        self.update_tab_appearances()

    def close_tab(self, index):
        editor = self.editor_tabs.widget(index)
        if editor and editor.file_path and editor.file_path == self.master_file_path:
            self.master_file_path = ""
        self.editor_tabs.removeTab(index)
        self.update_window_title()

    def close_other_tabs(self, keep_index):
        total_tabs = self.editor_tabs.count()
        if total_tabs <= 1: return
        reply = QMessageBox.question(self, "Confirm Close", f"Are you sure you want to close {total_tabs - 1} other tabs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        for i in range(total_tabs - 1, -1, -1):
            if i != keep_index: self.close_tab(i)
        self.status_label.setText("Closed other tabs.")

    def on_tab_changed(self, index):
        import os
        if getattr(self, 'live_preview_enabled', False):
            self.stop_live_preview()
        self.update_window_title()
        current_editor = self.editor_tabs.widget(index)
        if current_editor and current_editor.file_path:
            if not self.master_file_path:
                self.working_dir = os.path.dirname(current_editor.file_path)
            self.show_current_pdf()

    def open_tex_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Open LaTeX Files", "", "TeX Files (*.tex)")
        if file_paths:
            for file_path in reversed(file_paths):
                self.open_specific_file(file_path)

    def open_specific_file(self, file_path):
        import os
        target_abs_path = os.path.normpath(os.path.abspath(file_path))
        editor = None
        for i in range(self.editor_tabs.count()):
            ed = self.editor_tabs.widget(i)
            if ed.file_path:
                tab_abs_path = os.path.normpath(os.path.abspath(ed.file_path))
                if tab_abs_path == target_abs_path:
                    self.editor_tabs.setCurrentIndex(i)
                    editor = ed
                    break
        if not editor:
            if not self.master_file_path:
                self.working_dir = os.path.dirname(target_abs_path)
            filename = os.path.basename(target_abs_path)
            try:
                with open(target_abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.add_new_tab(filename, content, target_abs_path)
                editor = self.editor_tabs.currentWidget()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot open file:\n{str(e)}")
                return None
        self.add_to_recent(target_abs_path)
        return editor

    def show_current_pdf(self):
        import os
        target_tex = self.get_compilation_target()
        if not target_tex: return
        pdf_filepath = target_tex.replace(".tex", ".pdf")
        
        if os.path.exists(pdf_filepath):
            self.pdf_viewer.setUpdatesEnabled(False)
            has_old_state = False
            try:
                nav = self.pdf_viewer.pageNavigator()
                current_page = nav.currentPage()
                current_loc = nav.currentLocation()
                current_zoom = self.pdf_viewer.zoomFactor()
                zoom_mode = self.pdf_viewer.zoomMode()
                has_old_state = True
            except: pass

            self.pdf_viewer.load_pdf(pdf_filepath)

            def restore_state():
                try:
                    if has_old_state and current_page >= 0:
                        doc = self.pdf_viewer.document()
                        if doc and doc.pageCount() > 0:
                            safe_page = min(current_page, doc.pageCount() - 1)
                            self.pdf_viewer.setZoomMode(zoom_mode)
                            if hasattr(zoom_mode, 'name') and zoom_mode.name == 'Custom':
                                self.pdf_viewer.setZoomFactor(current_zoom)
                            self.pdf_viewer.pageNavigator().jump(safe_page, current_loc)
                finally:
                    self.pdf_viewer.setUpdatesEnabled(True)
                    self.pdf_viewer.update()
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, restore_state)

    def save_all_files(self):
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if editor.file_path:
                with open(editor.file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
            elif editor.toPlainText().strip() != "":
                self.editor_tabs.setCurrentIndex(i)
                file_path, _ = QFileDialog.getSaveFileName(self, "Save New File", "", "TeX Files (*.tex)")
                if file_path:
                    editor.file_path = file_path
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(editor.toPlainText())
        self.update_tab_appearances()
        return True

    def save_file_as(self):
        import os
        editor = self.get_current_editor()
        if not editor: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "TeX Files (*.tex)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                editor.file_path = file_path
                idx = self.editor_tabs.currentIndex()
                self.editor_tabs.setTabText(idx, os.path.basename(file_path))
                self.add_to_recent(file_path) 
                self.update_window_title()
                self.status_label.setText(f"Saved as: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")

    def save_as_template(self):
        import os
        editor = self.get_current_editor()
        if not editor: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Template", TEMPLATE_DIR, "TeX Files (*.tex)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                self.status_label.setText(f"✨ Template saved: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save:\n{str(e)}")

    def new_from_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Template", TEMPLATE_DIR, "TeX Files (*.tex)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.add_new_tab("Untitled.tex", f.read())
                self.status_label.setText(f"📄 New file created from template.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open:\n{str(e)}")

    def open_containing_folder(self, index=-1):
        import os, sys, subprocess
        editor = self.editor_tabs.widget(index) if index >= 0 else self.get_current_editor()
        if editor and editor.file_path and os.path.exists(editor.file_path):
            if sys.platform == "darwin": subprocess.run(["open", "-R", editor.file_path])
            elif sys.platform == "win32": subprocess.run(["explorer", "/select,", os.path.normpath(editor.file_path)])
        else:
            self.status_label.setText("⚠️ File not saved yet!")

    def add_to_recent(self, file_path):
        import os
        if not file_path: return
        file_path = os.path.abspath(file_path)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10] 
        from .config import RECENT_FILES_FILE
        try:
            import json
            with open(RECENT_FILES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, indent=4)
            self.update_recent_menu()
        except: pass

    def get_compilation_target(self):
        import os, re
        if self.master_file_path and os.path.exists(self.master_file_path):
            return self.master_file_path
        current_editor = self.editor_tabs.currentWidget()
        if current_editor:
            text = current_editor.toPlainText()
            match = re.search(r'%\s*!TeX\s+root\s*=\s*(.+?\.tex)', text, re.IGNORECASE)
            if match and current_editor.file_path:
                root_rel_path = match.group(1).strip()
                root_abs_path = os.path.normpath(os.path.join(os.path.dirname(current_editor.file_path), root_rel_path))
                if os.path.exists(root_abs_path): return root_abs_path
            return current_editor.file_path
        return None

    def start_compile_latex(self):
        import os, re
        if self.compile_process.state() == QProcess.ProcessState.Running: return
        self.save_all_files()
        self.target_tex = self.get_compilation_target()
       
        if not self.target_tex:
            QMessageBox.warning(self, "Error", "No file to compile!")
            return

        compile_dir = os.path.dirname(self.target_tex)
        tex_filename = os.path.basename(self.target_tex)

        selected_engine = "pdflatex"
        if hasattr(self, 'engine_xelatex') and self.engine_xelatex.isChecked(): selected_engine = "xelatex"
        elif hasattr(self, 'engine_lualatex') and self.engine_lualatex.isChecked(): selected_engine = "lualatex"

        try:
            with open(self.target_tex, "r", encoding="utf-8") as f:
                head = f.read(1024)
                if re.search(r'%\s*!TeX\s+program\s*=\s*xelatex', head, re.IGNORECASE):
                    selected_engine = "xelatex"
                    if hasattr(self, 'engine_xelatex'): self.engine_xelatex.setChecked(True)
                elif re.search(r'%\s*!TeX\s+program\s*=\s*lualatex', head, re.IGNORECASE):
                    selected_engine = "lualatex"
                    if hasattr(self, 'engine_lualatex'): self.engine_lualatex.setChecked(True)
                elif re.search(r'%\s*!TeX\s+program\s*=\s*pdflatex', head, re.IGNORECASE):
                    selected_engine = "pdflatex"
                    if hasattr(self, 'engine_pdflatex'): self.engine_pdflatex.setChecked(True)
        except: pass

        engine_path = os.path.join(TEXBIN_DIR, selected_engine)
        if not os.path.exists(engine_path):
            self.log_viewer.setPlainText(f"[ERROR]: Compiler not found at '{engine_path}'.")
            self.log_tabs.setVisible(True)
            self.left_splitter.setSizes([600, 200])
            return

        self.status_label.setText(f"Compiling: {tex_filename}...")
        self.log_viewer.clear()
        self.error_viewer.clear()
        self.full_log_output = ""

        self.log_tabs.setVisible(True)
        if self.left_splitter.sizes()[1] == 0:
            self.left_splitter.setSizes([600, 200])
        self.log_tabs.setCurrentIndex(0)

        self.stop_compile_action.setEnabled(True)
        self.compile_action.setEnabled(False)

        self.compile_process.setWorkingDirectory(compile_dir)
        cmd_arguments = ["-synctex=1", "-interaction=nonstopmode", "-file-line-error", tex_filename]
        self.compile_process.start(engine_path, cmd_arguments)

    def stop_compilation(self):
        if self.compile_process.state() == QProcess.ProcessState.Running:
            self.compile_process.kill()
            self.status_label.setText("Compile Stopped.")
            self.stop_compile_action.setEnabled(False)
            self.compile_action.setEnabled(True)

    def handle_stdout(self):
        data = self.compile_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.log_viewer.insertPlainText(data)
        self.log_viewer.ensureCursorVisible()
        self.full_log_output += data

    def handle_stderr(self):
        data = self.compile_process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.log_viewer.insertPlainText(data)
        self.log_viewer.ensureCursorVisible()
        self.full_log_output += data

    def compile_finished(self, exitCode=0, exitStatus=None):
        import os, re
        self.stop_compile_action.setEnabled(False)
        self.compile_action.setEnabled(True)
        
        pdf_filepath = self.target_tex.replace(".tex", ".pdf")
        tex_filename = os.path.basename(self.target_tex)

        lines = self.full_log_output.split('\n')
        error_count = 0
        
        for i, line in enumerate(lines):
            if line.startswith('!') or "Error" in line:
                error_msg = line.strip()
                line_num = -1
                for j in range(1, 6):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        match = re.search(r'^l\.(\d+)', next_line)
                        if match: line_num = int(match.group(1)); break
                        match = re.search(r'line (\d+)', next_line, re.IGNORECASE)
                        if match: line_num = int(match.group(1)); break
                
                display_text = f"Line {line_num}: {error_msg.replace('! ', '')}" if line_num != -1 else f"Error: {error_msg}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, line_num)
                self.error_viewer.addItem(item)
                error_count += 1

        if os.path.exists(pdf_filepath):
            try:
                self.show_current_pdf() 
                if error_count > 0:
                    self.log_tabs.setVisible(True)
                    self.log_tabs.setCurrentIndex(1) 
                    self.status_label.setText(f"Compiled with {error_count} issues. (PDF generated)")
                else:
                    self.log_tabs.setVisible(False)
                    self.status_label.setText(f"Successfully compiled: {tex_filename}!")
                    from PyQt6.QtCore import QTimer
                    if hasattr(self, 'trigger_forward_search'):
                        QTimer.singleShot(500, self.trigger_forward_search)
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                self.status_label.setText("Error loading PDF, please refresh manually.")
        else:
            self.log_tabs.setVisible(True)
            self.log_tabs.setCurrentIndex(1)
            self.status_label.setText("Critical Error: Could not generate PDF!")

    def show_tab_context_menu(self, position):
        index = self.editor_tabs.tabBar().tabAt(position)
        if index < 0: return

        menu = QMenu(self)
        def make_set_master(i): return lambda *args: self.set_master_by_index(i)
        def make_close_tab(i): return lambda *args: self.close_tab(i)
        def make_open_folder(i): return lambda *args: self.open_containing_folder(i)

        set_master_act = QAction("⭐ Set as Master File", self)
        clear_master_act = QAction("❌ Clear Master File", self)
        open_folder_act = QAction("📂 Reveal in Folder", self)
        close_tab_act = QAction("❌ Close Tab", self)
        
        set_master_act.triggered.connect(make_set_master(index))
        clear_master_act.triggered.connect(self.trigger_clear_master_document)
        open_folder_act.triggered.connect(make_open_folder(index))
        close_tab_act.triggered.connect(make_close_tab(index))

        editor = self.editor_tabs.widget(index)
        if editor.file_path and editor.file_path == self.master_file_path:
            menu.addAction(clear_master_act)
        else:
            menu.addAction(set_master_act)

        menu.addSeparator()
        if editor.file_path: menu.addAction(open_folder_act)
        menu.addAction(close_tab_act)

        menu.addSeparator()
        close_others_act = QAction("❌ Close Other Tabs", self)
        close_others_act.triggered.connect(lambda: self.close_other_tabs(index))
        menu.addAction(close_others_act)

        menu.exec(self.editor_tabs.tabBar().mapToGlobal(position))

    def set_master_by_index(self, index):
        editor = self.editor_tabs.widget(index)
        if editor and editor.file_path:
            self.master_file_path = editor.file_path
            self.update_window_title()
            self.update_tab_appearances()

    def clear_master_document(self):
        self.master_file_path = ""
        self.update_window_title()
        self.update_tab_appearances()

    def update_tab_appearances(self):
        import os
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            filename = os.path.basename(editor.file_path) if editor.file_path else "Untitled.tex"
            if self.master_file_path and editor.file_path == self.master_file_path:
                self.editor_tabs.setTabText(i, f"⭐ {filename}")
                self.editor_tabs.tabBar().setTabTextColor(i, QColor("#CC0000")) 
            else:
                self.editor_tabs.setTabText(i, filename)
                self.editor_tabs.tabBar().setTabTextColor(i, QColor("black")) 

    def zoom_in_pdf(self, *args):
        from PyQt6.QtPdfWidgets import QPdfView
        self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_viewer.setZoomFactor(min(5.0, self.pdf_viewer.zoomFactor() * 1.2))

    def zoom_out_pdf(self, *args):
        from PyQt6.QtPdfWidgets import QPdfView
        self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_viewer.setZoomFactor(max(0.2, self.pdf_viewer.zoomFactor() * 0.8))

    def fit_to_width(self, *args): 
        from PyQt6.QtPdfWidgets import QPdfView
        self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def fit_to_page(self, *args): 
        from PyQt6.QtPdfWidgets import QPdfView
        self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitInView)

    def update_pdf_total_pages(self):
        total = self.pdf_viewer.pdf_doc.pageCount()
        self.page_count_label.setText(f" / {total}")
        self.update_page_input(self.pdf_viewer.pageNavigator().currentPage())

    def update_page_input(self, page_index): 
        self.page_input.setText(str(page_index + 1))

    def first_pdf_page(self, *args): 
        self.pdf_viewer.pageNavigator().jump(0, QPointF(0, 0))

    def prev_pdf_page(self, *args): 
        self.pdf_viewer.pageNavigator().jump(max(0, self.pdf_viewer.pageNavigator().currentPage()-1), QPointF(0, 0))

    def next_pdf_page(self, *args): 
        self.pdf_viewer.pageNavigator().jump(min(self.pdf_viewer.pdf_doc.pageCount()-1, self.pdf_viewer.pageNavigator().currentPage()+1), QPointF(0, 0))

    def last_pdf_page(self, *args): 
        self.pdf_viewer.pageNavigator().jump(self.pdf_viewer.pdf_doc.pageCount()-1, QPointF(0, 0))

    def open_pdf_in_default_viewer(self, *args):
        import os, sys, subprocess
        target_tex = self.get_compilation_target()
        if not target_tex:
            self.status_label.setText("Open PDF: No target file.")
            return
        pdf_filepath = target_tex.replace(".tex", ".pdf")
        if not os.path.exists(pdf_filepath):
            QMessageBox.warning(self, "Open PDF", "PDF not found. Please compile first.")
            return
        try:
            if sys.platform == "darwin": subprocess.run(["open", pdf_filepath])
            elif sys.platform == "win32": os.startfile(pdf_filepath)
            else: subprocess.run(["xdg-open", pdf_filepath])
            self.status_label.setText(f"Opened in default viewer: {os.path.basename(pdf_filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Open PDF Error", str(e))

    def goto_pdf_page(self):
        try:
            p = int(self.page_input.text())
            if 1 <= p <= self.pdf_viewer.pdf_doc.pageCount(): 
                self.pdf_viewer.pageNavigator().jump(p-1, QPointF(0, 0))
        except: pass

    def highlight_editor_position(self, current_editor, line_number, column=-1):
        adjusted_line = max(0, line_number - 1)
        cursor = current_editor.textCursor()
        block = current_editor.document().findBlockByLineNumber(adjusted_line)
        if not block.isValid(): return
        
        cursor.setPosition(block.position())
        if column > 0:
            col_offset = min(max(0, column - 1), max(0, block.length() - 1))
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, col_offset)
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            
        current_editor.setTextCursor(cursor)
        current_editor.ensureCursorVisible()
        current_editor.centerCursor()
        current_editor.setFocus()
        
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("yellow").lighter(0))
        if column <= 0: 
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = cursor
        current_editor.setExtraSelections([selection])
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: current_editor.setExtraSelections([]))

    def on_error_item_clicked(self, item):
        line = item.data(Qt.ItemDataRole.UserRole)
        if line:
            editor = self.get_current_editor()
            if editor: self.highlight_editor_position(editor, line)

    def inverse_search(self, page, x_pt, y_pt):
        import os
        target_tex = self.get_compilation_target()
        if not target_tex:
            self.status_label.setText("Inverse Search: No master/target file set.")
            return

        pdf_filepath = target_tex.replace(".tex", ".pdf")
        if not os.path.exists(pdf_filepath):
            self.status_label.setText("Inverse Search: PDF not found.")
            return

        compile_dir = os.path.dirname(target_tex)
        args = ["edit", "-o", f"{int(page) + 1}:{x_pt:.4f}:{y_pt:.4f}:{pdf_filepath}"]
        
        self.inverse_search_process.setWorkingDirectory(compile_dir)
        self.inverse_search_process.start(SYNCTEX_PATH, args)

    def on_inverse_search_finished(self, exitCode, exitStatus):
        import os
        target_tex = self.get_compilation_target()
        if not target_tex: return
        compile_dir = os.path.dirname(target_tex)
        
        output = self.inverse_search_process.readAllStandardOutput().data().decode('utf-8')
        file_path = None
        line_num = None
        column = None

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Input:"):
                raw = line.split(":", 1)[1].strip() if ":" in line else None
                if raw: file_path = raw
            elif line.startswith("Line:"):
                try: line_num = int(line.split(":", 1)[1].strip())
                except: pass
            elif line.startswith("Column:"):
                try: column = int(line.split(":", 1)[1].strip())
                except: pass

        if file_path is None or line_num is None:
            self.status_label.setText("Inverse Search: Corresponding position not found.")
            return

        if file_path.startswith("./"): file_path = file_path[2:]
        if not os.path.isabs(file_path): file_path = os.path.normpath(os.path.join(compile_dir, file_path))
        else: file_path = os.path.normpath(file_path)

        editor_to_jump = None
        for i in range(self.editor_tabs.count()):
            ed = self.editor_tabs.widget(i)
            if ed.file_path and os.path.normpath(ed.file_path) == file_path:
                self.editor_tabs.setCurrentIndex(i)
                editor_to_jump = ed
                break

        if not editor_to_jump and os.path.exists(file_path):
            editor_to_jump = self.open_specific_file(file_path)

        if editor_to_jump:
            self.highlight_editor_position(editor_to_jump, line_num, column if column and column > 0 else -1)
            self.status_label.setText(f"Inverse Search → {os.path.basename(file_path)}:{line_num}")

    def forward_search(self, tex_file, line):
        import os
        target_tex = self.get_compilation_target()
        if not target_tex: return
        pdf_filepath = target_tex.replace(".tex", ".pdf")
        if not os.path.exists(pdf_filepath): 
            QMessageBox.warning(self, "Error", "Please compile to PDF before using this feature!")
            return

        compile_dir = os.path.dirname(target_tex)
        basename = os.path.basename(tex_file)
        args = ["view", "-i", f"{line}:0:{basename}", "-o", pdf_filepath]
        self.forward_search_process.setWorkingDirectory(compile_dir)
        self.forward_search_process.start(SYNCTEX_PATH, args)

    def on_forward_search_finished(self, exitCode, exitStatus):
        output = self.forward_search_process.readAllStandardOutput().data().decode('utf-8')
        page = -1
        pt_x = 0.0
        pt_y = 0.0
        for out_line in output.split("\n"):
            if "Page:" in out_line and page == -1: page = int(out_line.split(":")[1].strip()) - 1 
            elif "x:" in out_line and pt_x == 0.0: pt_x = float(out_line.split(":")[1].strip())
            elif "y:" in out_line and pt_y == 0.0: pt_y = float(out_line.split(":")[1].strip())
            if page != -1 and pt_x != 0.0 and pt_y != 0.0: break

        if page >= 0 and hasattr(self, 'pdf_viewer'):
            zoom = self.pdf_viewer.zoomFactor()
            margins = self.pdf_viewer.documentMargins()
            page_gap = 4
            y_cursor = margins.top()
            for i in range(page):
                size = self.pdf_viewer.pdf_doc.pagePointSize(i)
                y_cursor += size.height() * zoom + page_gap
            
            y_px_global = y_cursor + (pt_y * zoom)
            viewport_h = self.pdf_viewer.viewport().height()
            target_scroll = int(y_px_global - viewport_h / 2)
            
            scrollbar = self.pdf_viewer.verticalScrollBar()
            scrollbar.setValue(max(0, min(target_scroll, scrollbar.maximum())))
            self.status_label.setText(f"Forward Search: Jumped to page {page + 1}")
        elif page < 0:
            self.status_label.setText("Forward Search: PDF position not found.")

    def trigger_standardize_code(self):
        editor = self.get_current_editor()
        if not editor: return
        cursor = editor.textCursor()
        was_live = False
        if getattr(self, 'live_preview_enabled', False):
            was_live = True
            self.stop_live_preview()
        if hasattr(editor, 'highlighter'):
            editor.highlighter.setDocument(None)
            
        try:
            cursor.beginEditBlock()
            if cursor.hasSelection():
                text = cursor.selectedText().replace('\u2029', '\n')
                formatted_text = self.standardize_latex_text(text)
                cursor.insertText(formatted_text)
            else:
                cursor.select(QTextCursor.SelectionType.Document)
                text = cursor.selectedText().replace('\u2029', '\n')
                formatted_text = self.standardize_latex_text(text)
                cursor.insertText(formatted_text)
                cursor.clearSelection()
            cursor.endEditBlock()
        except Exception as e:
            QMessageBox.critical(self, "Format Error", f"An error occurred:\n{str(e)}")
        finally:
            if hasattr(editor, 'highlighter'):
                editor.highlighter.setDocument(editor.document())
                editor.highlightCurrentLine()
            if was_live:
                self.start_live_preview(editor)
        self.status_label.setText("✨ Code auto-formatting applied successfully!")

    def standardize_latex_text(self, text):
        import re

        comments = []
        def comment_replacer(match):
            comments.append(match.group(0))
            return f"__TEX_AI_COMMENT_{len(comments) - 1}__"

        text = re.sub(r'(?<!\\)%.*', comment_replacer, text)

        for _ in range(2): 
            lines = text.replace('\r\n', '\n').split('\n')
            lines = [line.strip() for line in lines]
            text = '\n'.join(lines)

            if '$$' in text:
                parts = text.split('$$')
                limit = len(parts) - (1 if len(parts) % 2 == 0 else 0)
                for i in range(1, limit, 2):
                    inner_lines = parts[i].strip().split('\n')
                    inner_text = '\n'.join([l.strip() for l in inner_lines if l.strip()])
                    parts[i] = f"\n\\[\n{inner_text}\n\\]\n"
                text = "".join(parts)

            text = re.sub(r'\\\[(.*?)\\\]', lambda m: f"\n\\[\n{chr(10).join([l.strip() for l in m.group(1).strip().split(chr(10)) if l.strip()])}\n\\]\n", text, flags=re.DOTALL)
            text = re.sub(r'\\par\n*\\shortans', r'\n\\shortans', text)
            text = re.sub(r'\n*\\shortans', r'\n\\shortans', text)
            text = re.sub(r'\n*(\\(?:choice|choiceTF|loigiai|immini|hinhvd|hinhbt)(?![a-zA-Z]))', r'\n\1', text)

            matches = list(re.finditer(r'\\(choiceTF|choice|loigiai|immini|hinhvd|hinhbt)(?![a-zA-Z])', text))
            for match in reversed(matches):
                cmd = match.group(1)
                num_args = {"choice": 4, "choiceTF": 4, "loigiai": 1, "immini": 2, "hinhvd": 1, "hinhbt": 1}[cmd]
                start_cmd = match.start()
                curr_idx = match.end()

                opt_arg = ""
                while curr_idx < len(text) and text[curr_idx] in ' \t\n\r': curr_idx += 1
                if curr_idx < len(text) and text[curr_idx] == '[':
                    start_opt = curr_idx
                    while curr_idx < len(text) and text[curr_idx] != ']': curr_idx += 1
                    if curr_idx < len(text):
                        curr_idx += 1
                        opt_arg = text[start_opt:curr_idx]

                args = []
                valid = True
                for _ in range(num_args):
                    while curr_idx < len(text) and text[curr_idx] in ' \t\n\r': curr_idx += 1
                    if curr_idx >= len(text) or text[curr_idx] != '{':
                        valid = False; break
                    brace_count = 1
                    start_brace = curr_idx
                    curr_idx += 1
                    while curr_idx < len(text) and brace_count > 0:
                        if text[curr_idx] == '{' and text[curr_idx - 1] != '\\': brace_count += 1
                        elif text[curr_idx] == '}' and text[curr_idx - 1] != '\\': brace_count -= 1
                        curr_idx += 1
                    if brace_count == 0: args.append(text[start_brace:curr_idx])
                    else: valid = False; break

                if valid:
                    if cmd in ["choice", "choiceTF"]:
                        res = f"\\{cmd}{opt_arg}\n"
                        for arg in args:
                            inner = arg[1:-1].strip()
                            res += f"\t{{{inner}}}\n"
                        res = res.rstrip()
                    elif cmd in ["loigiai", "hinhvd", "hinhbt"]:  
                        inner = args[0][1:-1].strip()
                        if inner.startswith('\\\\'): inner = inner[2:].strip()
                        res = f"\\{cmd}\n{{\n{inner}\n}}"
                    elif cmd == "immini":
                        inner1 = args[0][1:-1].strip()
                        inner2 = args[1][1:-1].strip()
                        res = f"\\immini{opt_arg}\n{{\n{inner1}\n}}\n{{\n{inner2}\n}}"

                    remainder = text[curr_idx:].lstrip(' \t\r\n')
                    text = text[:start_cmd] + res + "\n" + remainder

            text = re.sub(r'\\begin\{([a-zA-Z0-9_*]+)\}', r'\n\\begin{\1}', text)
            text = re.sub(r'\\end\{([a-zA-Z0-9_*]+)\}', r'\n\\end{\1}', text)
            text = re.sub(r'(?<!\\)\\\[', r'\n\\[', text)
            text = re.sub(r'(?<!\\)\\\]', r'\n\\]', text)
            text = re.sub(r'\n+[ \t]*\\begin\{([a-zA-Z0-9_*]+)\}', r'\n\\begin{\1}', text)
            text = re.sub(r'(\\begin\{[a-zA-Z0-9_*]+\}[^\n]*)\n+', r'\1\n', text)
            text = re.sub(r'\n+[ \t]*\\end\{([a-zA-Z0-9_*]+)\}', r'\n\\end{\1}', text)
            text = re.sub(r'\\end\{([a-zA-Z0-9_*]+)\}\n+', r'\\end{\1}\n', text)
            text = re.sub(r'\n*\\begin\{(ex|vd|bt)\}', r'\n\n\\begin{\1}', text)
            text = re.sub(r'\\end\{(ex|vd|bt)\}\n*', r'\\end{\1}\n\n', text)
            text = re.sub(r'\\begin\{(ex|vd|bt)\}([^\n]*)\n', lambda m: f"\\begin{{{m.group(1)}}}\n{m.group(2).strip()}\n" if m.group(2).strip() else f"\\begin{{{m.group(1)}}}\n", text)

            if '\\begin{tikzpicture}' in text:
                blocks = text.split('\\begin{tikzpicture}')
                for i in range(1, len(blocks)):
                    if '\\end{tikzpicture}' in blocks[i]:
                        parts = blocks[i].split('\\end{tikzpicture}', 1)
                        tikz_content = re.sub(r'\n+', '\n', parts[0].replace('{$$}', '{$ $}'))
                        blocks[i] = tikz_content.strip() + '\n\\end{tikzpicture}' + parts[1]
                text = '\\begin{tikzpicture}\n'.join(blocks)

            text = re.sub(r'([^\n])(\\item(?![a-zA-Z]))', r'\1\n\2', text)
            text = re.sub(r'([^\n])(\\itemch(?![a-zA-Z]))', r'\1\n\2', text)
            text = re.sub(r'^\\item(?![a-zA-Z])', '\t\\\\item', text, flags=re.MULTILINE)
            text = re.sub(r'^\\itemch(?![a-zA-Z])', '\t\\\\itemch', text, flags=re.MULTILINE)
            text = re.sub(r'(?<!d)\\frac', r'\\dfrac', text)
            text = text.replace(r'\int_{', r'\int\limits_{')
            text = text.replace(r'\lim_{', r'\lim\limits_{')
            text = text.replace(r'\sum_{', r'\sum\limits_{')
            text = re.sub(r'(?<!\w)\\sim(?!\w)', r'\\backsim', text)
            text = re.sub(r'\n{3,}', '\n\n', text)

        for i, cmt in enumerate(comments):
            text = text.replace(f"__TEX_AI_COMMENT_{i}__", cmt)

        return text.strip() + "\n"
