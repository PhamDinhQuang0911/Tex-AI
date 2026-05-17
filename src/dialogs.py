import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QLineEdit, 
                             QTextEdit, QPushButton, QWidget, QComboBox, QFileDialog, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
from .config import AI_CONFIG_FILE, SHORTCUTS_FILE, DEFAULT_SHORTCUTS

# --- 1. HỘP THOẠI QUẢN LÝ MACROS ---
class MacroDialog(QDialog):
    def __init__(self, parent=None, user_macros=None):
        super().__init__(parent)
        self.setWindowTitle("Macro Manager")
        self.resize(850, 550)
        
        self.user_macros = []
        if user_macros:
            for m in user_macros:
                if isinstance(m, dict):
                    self.user_macros.append(m.copy())
                elif isinstance(m, (list, tuple)) and len(m) >= 3:
                    self.user_macros.append({"icon": m[0], "name": m[1], "code": m[2], "type": "Script", "position": "Top", "shortcut": ""})

        layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_selected_macro)
        left_layout.addWidget(self.list_widget)
        
        move_layout = QHBoxLayout()
        btn_up = QPushButton("⬆️ Move Up")
        btn_up.clicked.connect(self.move_up)
        btn_down = QPushButton("⬇️ Move Down")
        btn_down.clicked.connect(self.move_down)
        move_layout.addWidget(btn_up)
        move_layout.addWidget(btn_down)
        left_layout.addLayout(move_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        layout.addWidget(left_widget, 1)

        form_layout = QFormLayout()
        
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("Ex: B, I, ∑ or Image Path")
        browse_btn = QPushButton("Browse Icon...")
        browse_btn.clicked.connect(self.browse_icon)
        icon_hbox = QHBoxLayout()
        icon_hbox.addWidget(self.icon_input)
        icon_hbox.addWidget(browse_btn)

        self.name_input = QLineEdit()
        self.shortcut_input = QLineEdit()
        self.shortcut_input.setPlaceholderText("Ex: Ctrl+Shift+I (or Cmd+Shift+I)")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Script", "Normal"])
        
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Top", "Left", "Menu Only"])
        
        self.code_input = QTextEdit()

        form_layout.addRow("Icon:", icon_hbox)
        form_layout.addRow("Macro Name:", self.name_input)
        form_layout.addRow("Shortcut:", self.shortcut_input)
        form_layout.addRow("Type:", self.type_combo)
        form_layout.addRow("Position:", self.position_combo)
        form_layout.addRow("LaTeX Code:", self.code_input)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add / Update")
        add_btn.clicked.connect(self.save_macro)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self.delete_macro)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)

        form_layout.addRow(btn_layout)
        
        finish_btn = QPushButton("✅ Finish & Apply")
        finish_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        finish_btn.clicked.connect(self.accept) 
        form_layout.addRow(finish_btn)

        right_widget = QWidget()
        right_widget.setLayout(form_layout)
        layout.addWidget(right_widget, 2)
        
        self.refresh_list()

    def browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon Image", "", "Images (*.png *.jpg *.svg)")
        if path:
            self.icon_input.setText(path)

    def refresh_list(self):
        self.list_widget.clear()
        for m in self.user_macros:
            sc = m.get("shortcut", "")
            sc_text = f" [{sc}]" if sc else ""
            self.list_widget.addItem(f"[{m.get('position', 'Top')}] {m.get('name', 'Macro')}{sc_text}")

    def load_selected_macro(self, index):
        if 0 <= index < len(self.user_macros):
            m = self.user_macros[index]
            self.icon_input.setText(m.get("icon", ""))
            self.name_input.setText(m.get("name", ""))
            self.shortcut_input.setText(m.get("shortcut", ""))
            self.type_combo.setCurrentText(m.get("type", "Script"))
            self.position_combo.setCurrentText(m.get("position", "Top"))
            self.code_input.setPlainText(m.get("code", ""))

    def save_macro(self):
        m = {
            "icon": self.icon_input.text().strip(),
            "name": self.name_input.text().strip() or "Macro",
            "shortcut": self.shortcut_input.text().strip(),
            "type": self.type_combo.currentText(),
            "position": self.position_combo.currentText(),
            "code": self.code_input.toPlainText()
        }
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.user_macros[idx] = m
        else:
            self.user_macros.append(m)
        self.refresh_list()
        if idx >= 0:
            self.list_widget.setCurrentRow(idx)
        else:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_macro(self):
        idx = self.list_widget.currentRow()
        if idx >= 0: 
            self.user_macros.pop(idx)
            self.refresh_list()

    def move_up(self):
        idx = self.list_widget.currentRow()
        if idx > 0:
            self.user_macros[idx - 1], self.user_macros[idx] = self.user_macros[idx], self.user_macros[idx - 1]
            self.refresh_list()
            self.list_widget.setCurrentRow(idx - 1)

    def move_down(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self.user_macros) - 1:
            self.user_macros[idx + 1], self.user_macros[idx] = self.user_macros[idx], self.user_macros[idx + 1]
            self.refresh_list()
            self.list_widget.setCurrentRow(idx + 1)

# --- 2. HỘP THOẠI CÀI ĐẶT PHÍM TẮT ---
class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Application Shortcuts")
        self.resize(450, 500)
        self.shortcuts = self.load_shortcuts()
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(self.shortcuts), 2)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        for i, (key, val) in enumerate(self.shortcuts.items()):
            self.table.setItem(i, 0, QTableWidgetItem(key))
            self.table.setItem(i, 1, QTableWidgetItem(val))
            self.table.item(i, 0).setFlags(self.table.item(i, 0).flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        layout.addWidget(self.table)
        
        btn_save = QPushButton("Save Configuration")
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

    def load_shortcuts(self):
        if os.path.exists(SHORTCUTS_FILE):
            with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f: 
                return json.load(f)
        return DEFAULT_SHORTCUTS.copy()

    def save_and_close(self):
        new_shortcuts = {}
        for i in range(self.table.rowCount()):
            key = self.table.item(i, 0).text()
            val = self.table.item(i, 1).text().strip()
            new_shortcuts[key] = val
        with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_shortcuts, f, indent=4)
        self.accept()

# --- 3. HỘP THOẠI CÀI ĐẶT AI ---
class AIDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Gemini API")
        self.setFixedWidth(450)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter your Gemini API Key:"))
        
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        if os.path.exists(AI_CONFIG_FILE):
            try:
                with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.api_input.setText(json.load(f).get("api_key", ""))
            except: pass
        
        layout.addWidget(self.api_input)
        
        btn_save = QPushButton("Save API Key")
        btn_save.clicked.connect(self.save_key)
        layout.addWidget(btn_save)

    def save_key(self):
        key = self.api_input.text().strip()
        with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f)
        QMessageBox.information(self, "Success", "API Key saved successfully!")
        self.accept()

# --- 4. CỬA SỔ TƯƠNG TÁC AI TRỢ LÝ ---
class AIWindow(QDialog):
    def __init__(self, parent=None, selected_text=""):
        super().__init__(parent)
        self.setWindowTitle("TeX-AI Assistant")
        self.resize(650, 650)
        self.selected_text = selected_text
        self.image_path = ""
        
        layout = QVBoxLayout(self)

        # --- Top: Settings & Templates ---
        top_lay = QHBoxLayout()
        top_lay.addWidget(QLabel("🤖 AI Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-3-flash-preview"])
        top_lay.addWidget(self.model_combo)
        
        top_lay.addSpacing(20)
        top_lay.addWidget(QLabel("📝 Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "-- Chọn mẫu Prompt để chèn --",
            "📐 TikZ: Vẽ hình học (tkz-euclide)",
            "📊 Math: Chuẩn hóa công thức/Hồi quy",
            "📝 Exam: Format Trắc nghiệm / Tự luận",
            "🎓 Slides: Tạo Beamer frame",
            "🌐 Translate: Dịch thuật (Giữ nguyên Code)",
            "📈 Vẽ Bảng biến thiên (tkz-tab) / Sơ đồ cây"
        ])
        top_lay.addWidget(self.template_combo)
        
        # NÚT CHÈN GIÚP NỐI THÊM PROMPT THAY VÌ GHI ĐÈ
        self.btn_insert_template = QPushButton("➕ Chèn")
        self.btn_insert_template.clicked.connect(self.apply_template)
        top_lay.addWidget(self.btn_insert_template)
        
        top_lay.setStretch(3, 1)
        layout.addLayout(top_lay)
        
        # --- Middle: Input & Image ---
        layout.addWidget(QLabel("Yêu cầu của bạn (Prompt):"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setMaximumHeight(120) # Tăng chiều cao để dễ nhìn khi chèn nhiều lệnh
        self.prompt_input.setPlaceholderText("Ví dụ: Giải chi tiết, hoặc có thể gõ nội dung rồi bấm '➕ Chèn' các Mẫu ở trên để thêm quy chuẩn...")
        layout.addWidget(self.prompt_input)
        
        attach_lay = QHBoxLayout()
        self.btn_attach = QPushButton("📎 Đính kèm ảnh")
        self.btn_attach.clicked.connect(self.attach_image)
        self.img_label = QLabel("Chưa có ảnh")
        self.img_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.btn_remove_img = QPushButton("❌")
        self.btn_remove_img.setFixedWidth(30)
        self.btn_remove_img.hide()
        self.btn_remove_img.clicked.connect(self.remove_image)
        
        attach_lay.addWidget(self.btn_attach)
        attach_lay.addWidget(self.img_label)
        attach_lay.addWidget(self.btn_remove_img)
        attach_lay.addStretch()
        layout.addLayout(attach_lay)
        
        self.btn_generate = QPushButton("✨ Gửi tới Gemini AI")
        self.btn_generate.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; height: 35px;")
        layout.addWidget(self.btn_generate)
        
        # --- Bottom: Output ---
        layout.addWidget(QLabel("Kết quả từ AI:"))
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setStyleSheet("background-color: #f0f3f4; font-family: 'Courier New'; font-size: 11pt;")
        layout.addWidget(self.result_output)
        
        btn_box = QHBoxLayout()
        self.btn_replace = QPushButton("🔄 Ghi đè (Replace)")
        self.btn_copy = QPushButton("📋 Copy vào Clipboard")
        btn_box.addWidget(self.btn_replace)
        btn_box.addWidget(self.btn_copy)
        layout.addLayout(btn_box)

    def apply_template(self):
        idx = self.template_combo.currentIndex()
        text_to_insert = ""
        
        if idx == 1:
            text_to_insert = "Vẽ hình TikZ dựa trên nội dung/bức ảnh đính kèm. BẮT BUỘC dùng gói tkz-euclide. Luôn bắt đầu bằng \\tkzInit và \\tkzClip. Khai báo điểm bằng \\tkzDefPoints, vẽ đường bằng \\tkzDrawSegments. Để đánh dấu góc vuông dùng \\tkzMarkRightAngles. ĐẶC BIỆT LƯU Ý: Gắn nhãn điểm phải dùng vòng lặp form chuẩn sau: \\foreach \\i/\\g in {A/90, B/-90...} { \\draw[fill=white](\\i) circle (1.5pt) ($(\\i)+(\\g:3mm)$) node[scale=1]{$\\i$}; }. Chỉ trả về code trong tikzpicture, không giải thích."
        elif idx == 2:
            text_to_insert = "Chuẩn hóa các phương trình, công thức Toán học hoặc mô hình hồi quy. Các công thức đứng riêng độc lập một dòng BẮT BUỘC phải bọc trong \\[ \\] hoặc môi trường \\begin{align*} ... \\end{align*}. Căn chỉnh các dấu bằng (=) thẳng hàng dọc. Chú ý format chuẩn các hệ số beta (\\beta), sai số, và các chỉ số dưới (subscript)."
        elif idx == 3:
            text_to_insert = "Chuyển đổi văn bản thành câu hỏi thi LaTeX. Bọc đề bài trong \\begin{ex} ... \\end{ex}. Lời giải bọc trong \\loigiai{...}.\nPhân loại tự động:\n1. 4 đáp án: Dùng \\choice{A}{B}{C}{D}, thêm \\True trước đáp án đúng.\n2. Đúng/Sai: Dùng \\choiceTF{A}{B}{C}{D}, lời giải dùng \\begin{itemchoice} và \\itemch.\n3. Trả lời ngắn: Dùng lệnh \\shortans{đáp_án}.\n4. Tự luận: Chỉ dùng bọc \\begin{ex} và \\loigiai{}, không thêm bất kỳ lệnh trắc nghiệm nào.\n\n*** YÊU CẦU TRÌNH BÀY QUAN TRỌNG ***:\n- Trong phần \\loigiai{}, KHÔNG ĐƯỢC để bất kỳ dòng trống nào. Bổ sung lệnh \\\\ để xuống dòng nếu cần.\n- Các công thức toán độc lập, đứng riêng một dòng BẮT BUỘC phải dùng \\[ \\] hoặc môi trường align*."
        elif idx == 4:
            text_to_insert = "Chuyển đổi nội dung này thành frame trình chiếu Beamer. Dùng \\begin{frame}{Tiêu đề} ... \\end{frame}. Dùng itemize cho ý chính. Tuyệt đối giữ nguyên công thức Toán học."
        elif idx == 5:
            text_to_insert = "Dịch văn bản sang Tiếng Việt (văn phong học thuật Toán/Kinh tế). TUYỆT ĐỐI GIỮ NGUYÊN các công thức Toán học ($...$, $$...$$) và lệnh LaTeX (\\textbf, \\textit...)."
        elif idx == 6:
            text_to_insert = "Vẽ Bảng biến thiên hoặc Sơ đồ cây theo đúng chuẩn sau:\n1. Nếu là BBT: BẮT BUỘC dùng gói tkz-tab. Khởi tạo bằng \\tkzTabInit[nocadre=false,lgt=1.2,espcl=2.5,deltacl=1].\n2. Nếu là Sơ đồ cây: Dùng tikzpicture với các cấu trúc mức [grow=right, level 1/.style={...}, edge from parent/.style={draw, -latex}, sloped].\nChỉ trả về code LaTeX, không giải thích dư thừa."
            
        if text_to_insert:
            current_text = self.prompt_input.toPlainText()
            if current_text.strip():
                # Nối tiếp vào Text hiện tại, cách nhau 2 dấu enter
                self.prompt_input.setPlainText(current_text.strip() + "\n\n" + text_to_insert)
            else:
                self.prompt_input.setPlainText(text_to_insert)
            
            # Tự động cuộn con trỏ xuống cuối để xem nội dung vừa chèn
            from PyQt6.QtGui import QTextCursor
            self.prompt_input.moveCursor(QTextCursor.MoveOperation.End)

    def attach_image(self):
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtCore import Qt
        path, _ = QFileDialog.getOpenFileName(self, "Chọn Ảnh", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            pixmap = QPixmap(path)
            thumb = pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(thumb)
            self.btn_remove_img.show()

    def remove_image(self):
        self.image_path = ""
        self.img_label.setText("Chưa có ảnh")
        self.btn_remove_img.hide()