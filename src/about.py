from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TeX-AI Pro & Changelog")
        self.setFixedSize(500, 550)
        
        layout = QVBoxLayout(self)
        
        # --- Phần Tiêu đề ---
        title = QLabel("TeX-AI Pro Editor")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        version = QLabel("Phiên bản: 1.8.5 (Build 2026.05.14)")
        version.setStyleSheet("font-weight: bold; color: #e67e22;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- Phần Nhật ký thay đổi (Changelog) ---
        changelog_label = QLabel("Nhật ký thay đổi (Changelog):")
        changelog_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        self.changelog_view = QTextEdit()
        self.changelog_view.setReadOnly(True)
        self.changelog_view.setStyleSheet("""
            background-color: #fdfdfd; 
            border: 1px solid #dcdde1; 
            border-radius: 5px; 
            padding: 10px;
            font-size: 13px;
        """)
        
        changelog_text = """
🚀 v1.8.5 - SMART AI & ACADEMIC STANDARDS

✨ AI ASSISTANT PRO
• [Mới] Chế độ Multi-Prompt: Nút "➕ Chèn" cho phép cộng dồn nhiều yêu cầu mẫu mà không bị ghi đè.
• [Mới] Hỗ trợ Tự luận: Tự động format câu hỏi tự luận chỉ với \\begin{ex} và \\loigiai.
• [Nâng cấp] Vision API: Đọc hình ảnh và sinh mã TikZ (tkz-euclide) cực kỳ chính xác theo ảnh đính kèm.
• [Quy chuẩn] Ép AI trình bày lời giải không dòng trống, dùng \\\\ xuống dòng và công thức bọc trong \\[ \\] hoặc align*.

📈 NEW TEMPLATES
• [Mới] Bổ sung mẫu Bảng biến thiên (tkz-tab) và Sơ đồ cây xác suất.

--------------------------------------------------

🚀 v1.8.4 - PERFORMANCE & LOCALIZATION

🌍 GLOBALIZATION
• [Mới] Chuyển đổi toàn bộ giao diện (Menu, Dialogs, Buttons) sang Tiếng Anh chuyên nghiệp.
• [Chuẩn hóa] Thuật ngữ LaTeX theo chuẩn quốc tế.

⚡️ ASYNC ENGINE
• [Nâng cấp] Non-blocking SyncTeX: Chuyển sang chạy QProcess, giao diện không còn bị đơ khi Forward/Inverse Search.
• [Tối ưu] Live Preview: Chỉ biên dịch khi nội dung thực sự thay đổi (Content Hashing), giúp tiết kiệm CPU/Pin.
• [Fix] Cải thiện hành vi cuộn TabBar cho Trackpad.

--------------------------------------------------

🚀 v1.8.3 - TAB SYNC & AUTO-FORMAT
• Chống nhảy trang PDF khi biên dịch.
• Bảo vệ Comment (%) khi chuẩn hóa định dạng.
        """
        self.changelog_view.setPlainText(changelog_text.strip())
        
        # --- Phần chân trang ---
        footer = QLabel("Phát triển bởi Thầy Tuấn & Trợ lý TeX-AI.")
        footer.setStyleSheet("font-style: italic; color: #7f8c8d; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_close = QPushButton("Đóng")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("padding: 5px 20px; font-weight: bold;")
        btn_close.clicked.connect(self.accept)
        
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(changelog_label)
        layout.addWidget(self.changelog_view)
        layout.addWidget(footer)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)