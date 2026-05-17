from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PyQt6.QtCore import QRegularExpression

class LatexHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        
        # Lệnh cơ bản (Đổi sang Dark Blue để chữ sâu và đậm hơn)
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#0033CC")) 
        command_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\[a-zA-Z]+"), command_format))

        # Ngoặc nhọn {}
        brace_format = QTextCharFormat()
        brace_format.setForeground(QColor("#B22222")) 
        self.highlighting_rules.append((QRegularExpression(r"[\{\}]"), brace_format))

        # Ngoặc vuông []
        bracket_format = QTextCharFormat()
        bracket_format.setForeground(QColor("#228B22")) 
        self.highlighting_rules.append((QRegularExpression(r"\[|\]"), bracket_format))

        # Toán học $$ (Đổi sang Dark Purple đậm nét hơn)
        math_format = QTextCharFormat()
        math_format.setForeground(QColor("#660066")) 
        self.highlighting_rules.append((QRegularExpression(r"\$[^$]+\$"), math_format))

        # Ký tự đặc biệt & \\
        special_char_format = QTextCharFormat()
        special_char_format.setForeground(QColor("#D2691E")) 
        special_char_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"&|\\\\"), special_char_format))

        # =====================================================================
        # NÂNG CẤP 1.4: TÔ MÀU RIÊNG BIỆT CHO CÁC MÔI TRƯỜNG (\begin{...} / \end{...})
        # =====================================================================

        # 1. Màu chung cho các môi trường (Teal - Xanh mòng két)
        env_format = QTextCharFormat()
        env_format.setForeground(QColor("#008080")) 
        env_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\(?:begin|end)\{[a-zA-Z0-9_*]+\}"), env_format))

        # 2. Môi trường document (Cobalt Blue - Xanh dương đậm)
        doc_format = QTextCharFormat()
        doc_format.setForeground(QColor("#0055A4")) 
        doc_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\(?:begin|end)\{document\}"), doc_format))

        # 3. Môi trường ex (Crimson Red - Đỏ thẫm)
        ex_format = QTextCharFormat()
        ex_format.setForeground(QColor("#CC0000")) 
        ex_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\(?:begin|end)\{ex\}"), ex_format))

        # 4. Môi trường vd (Dark Orange - Cam đậm)
        vd_format = QTextCharFormat()
        vd_format.setForeground(QColor("#E65100")) 
        vd_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\(?:begin|end)\{vd\}"), vd_format))

        # 5. Môi trường bt (Forest Green - Xanh lá cây thẫm)
        bt_format = QTextCharFormat()
        bt_format.setForeground(QColor("#006400")) 
        bt_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\(?:begin|end)\{bt\}"), bt_format))


        # 6. BẢO VỆ CÁC KÝ TỰ ĐẶC BIỆT (VD: \%, \$, \&, \#, \_) - Tô màu Cam đậm
        escape_format = QTextCharFormat()
        escape_format.setForeground(QColor("#D2691E")) 
        escape_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\\[%$&#_]"), escape_format))

        # 7. COMMENTS (Xám đậm) - Đặt cuối cùng
        # Dùng Negative Lookbehind (?<!\\) để chặn hệ thống tô xám nếu có dấu \ đứng trước %
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A737D")) 
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegularExpression(r"(?<!\\)%.*"), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
