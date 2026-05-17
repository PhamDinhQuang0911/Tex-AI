import os
import json

# Thư mục lưu cấu hình người dùng (Home/User/.tex_ai_editor)
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".tex_ai_editor")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Quy hoạch toàn bộ file cấu hình về thư mục CONFIG_DIR
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")
AUTOCOMPLETE_FILE = os.path.join(CONFIG_DIR, "autocomplete.json")
AI_CONFIG_FILE = os.path.join(CONFIG_DIR, "ai_config.json")
SHORTCUTS_FILE = os.path.join(CONFIG_DIR, "shortcuts.json")
USER_MACROS_FILE = os.path.join(CONFIG_DIR, "user_macros.json") 
EDITOR_CONFIG_FILE = os.path.join(CONFIG_DIR, "editor_config.json") # <--- THÊM DÒNG NÀY

TEXBIN_DIR = "/Library/TeX/texbin"
SYNCTEX_PATH = os.path.join(TEXBIN_DIR, "synctex")

# Phím tắt mặc định
DEFAULT_SHORTCUTS = {
    "new_file": "Ctrl+N",
    "open_file": "Ctrl+O",
    "save_file": "Ctrl+S",
    "compile": "F5",
    "toggle_comment": "Ctrl+/",
    "find": "Ctrl+F",
    "replace": "Ctrl+H",
    "goto": "Ctrl+G"
}

# --- BẢN ĐỒNG BỘ AUTO-FORMATTER 100% CHUẨN MỰC ---
DEFAULT_TEMPLATES = {
    # Môi trường Trắc nghiệm & Cấu trúc (Đã chuẩn hóa thụt 1 Tab và đưa ra dòng mới)
    "\\choice": "\\choice\n\t{%|}\n\t{}\n\t{}\n\t{}",
    "\\choiceTF": "\\choiceTF\n\t{%|}\n\t{}\n\t{}\n\t{}",
    "\\choicefix": "\\choicefix\n\t{%|}\n\t{}\n\t{}\n\t{}",
    "\\choicefive": "\\choicefive\n\t{%|}\n\t{}\n\t{}\n\t{}\n\t{}",
    "\\loigiai": "\\loigiai\n{\n%|\n}",
    "\\immini": "\\immini\n{\n%|\n}\n{\n}",
    "\\sidefig": "\\sidefig\n{\n%|\n}\n{\n}",
    "\\hinhvd": "\\hinhvd\n{\n%|\n}",
    "\\hinhbt": "\\hinhbt\n{\n%|\n}",
    "\\ptich": "\\ptich\n{\n%|\n}",
    "\\heva": "\\heva{%|}",
    "\\hoac": "\\hoac{%|}",
    "\\TF": "\\TF{%|}",
    
    # Các môi trường ưu tiên (Đã bọc sẵn 1 dấu xuống dòng \n để chừa dòng trống)
    "\\begin{ex}": "\n\\begin{ex}\n%|\n\\end{ex}\n",
    "\\begin{bt}": "\n\\begin{bt}\n%|\n\\end{bt}\n",
    "\\begin{vd}": "\n\\begin{vd}\n%|\n\\end{vd}\n",
    "\\phanTN":"\\phanTN",
    "\\phanDS":"\\phanDS",
    "\\phanTLN":"\\phanTLN",
    "\\phanTL":"\\phanTL",
    # Các môi trường Liệt kê (Tự động thụt 1 Tab cho \item)
    "\\begin{listEX}": "\\begin{listEX}[%|]\n\t\\item \n\\end{listEX}",
    "\\begin{enumEX}": "\\begin{enumEX}{%|}\n\t\\item \n\\end{enumEX}",
    "\\begin{tasks}": "\\begin{tasks}(%|)\n\t\\task \n\\end{tasks}",
    "\\begin{itemize}": "\\begin{itemize}\n\t\\item %|\n\\end{itemize}",
    "\\begin{enumerate}": "\\begin{enumerate}\n\t\\item %|\n\\end{enumerate}",
    
    # Các môi trường ép sát (Không dòng trống)
    "\\begin{document}": "\\begin{document}\n%|\n\\end{document}",
    "\\begin{center}": "\\begin{center}\n%|\n\\end{center}",
    
    # Phân số, Căn, Tích phân, Giới hạn (Tự động chuyển \frac thành \dfrac)
    "\\dfrac": "\\dfrac{%|}{}",
    "\\frac": "\\dfrac{%|}{}", 
    "\\sqrt": "\\sqrt{%|}",
    "\\int\\limits": "\\int\\limits_{%|}^{}",
    "\\lim\\limits": "\\lim\\limits_{%| \\to }",
    "\\max\\limits": "\\max\\limits_{%|}",
    "\\min\\limits": "\\min\\limits_{%|}",
    "\\sum": "\\sum\\limits_{%|}^{}",
    "\\prod": "\\prod\\limits_{%|}^{}",
    
    # Ký hiệu Hình học
    "\\triangle": "\\triangle",
    "\\angle": "\\angle",
    "\\widehat": "\\widehat{%|}",
    "\\sim": "\\backsim",           # Tự động thay \sim thành \backsim
    "\\backsim": "\\backsim",       # Đồng dạng
    "\\cong": "\\cong",             # Bằng nhau
    "\\perp": "\\perp",             # Vuông góc
    "\\parallel": "\\varparallel",     # Song song
    "\\varparallel": "\\varparallel",     # Song song
    "\\circ": "^\\circ",            # Độ (VD: 90^\circ)
    
    # Ký hiệu Vector & Lượng giác
    "\\vec": "\\vec{%|}",
    "\\overrightarrow": "\\overrightarrow{%|}",
    "\\overline": "\\overline{%|}",
    "\\sin": "\\sin",
    "\\cos": "\\cos",
    "\\tan": "\\tan",
    "\\cot": "\\cot",
    "\\log": "\\log_{%|}",
    "\\ln": "\\ln",
    
    # Bảng chữ cái Hy Lạp
    "\\alpha": "\\alpha", "\\beta": "\\beta", "\\gamma": "\\gamma", "\\delta": "\\delta",
    "\\epsilon": "\\epsilon", "\\theta": "\\theta", "\\lambda": "\\lambda", "\\mu": "\\mu",
    "\\pi": "\\pi", "\\sigma": "\\sigma", "\\phi": "\\phi", "\\omega": "\\omega",
    "\\Delta": "\\Delta", "\\Gamma": "\\Gamma", "\\Omega": "\\Omega",
    
    # Ký hiệu Toán học chung
    "\\infty": "\\infty", "\\approx": "\\approx", "\\neq": "\\neq", "\\equiv": "\\equiv",
    "\\leq": "\\leq", "\\geq": "\\geq", "\\times": "\\times", "\\div": "\\div",
    "\\pm": "\\pm", "\\mp": "\\mp", "\\cap": "\\cap", "\\cup": "\\cup",
    "\\in": "\\in", "\\notin": "\\notin", "\\subset": "\\subset", "\\subseteq": "\\subseteq",
    "\\forall": "\\forall", "\\exists": "\\exists", "\\Rightarrow": "\\Rightarrow", "\\Leftrightarrow": "\\Leftrightarrow",
    "\\cdot": "\\cdot", "\\ldots": "\\ldots", "\\cdots": "\\cdots",
    "\\mathbb": "\\mathbb{%|}", # Cho tập R, N, Z, Q
    
    # Text formatting
    "\\section": "\\section{%|}",
    "\\subsection": "\\subsection{%|}",
    "\\subsubsection": "\\subsubsection{%|}",
    "\\paragraph": "\\paragraph{%|}",
    "\\textbf": "\\textbf{%|}",
    "\\textit": "\\textit{%|}",
    "\\underline": "\\underline{%|}",
    "\\usepackage": "\\usepackage{%|}",
}

# --- Cơ chế Auto-Update Autocomplete: Cập nhật file json nếu có lệnh mới ---
if not os.path.exists(AUTOCOMPLETE_FILE):
    try:
        with open(AUTOCOMPLETE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TEMPLATES, f, ensure_ascii=False, indent=4)
    except: pass
else:
    # Cập nhật thêm các template mới vào file json hiện có
    try:
        with open(AUTOCOMPLETE_FILE, "r", encoding="utf-8") as f:
            existing_templates = json.load(f)
        
        updated = False
        for k, v in DEFAULT_TEMPLATES.items():
            if k not in existing_templates or existing_templates[k] != v:
                existing_templates[k] = v
                updated = True
                
        if updated:
            with open(AUTOCOMPLETE_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_templates, f, ensure_ascii=False, indent=4)
    except: pass

try:
    with open(AUTOCOMPLETE_FILE, "r", encoding="utf-8") as f:
        LATEX_TEMPLATES = json.load(f)
except:
    LATEX_TEMPLATES = DEFAULT_TEMPLATES.copy()

LATEX_COMMANDS = list(LATEX_TEMPLATES.keys())

# --- DEFAULT_MACROS ---
DEFAULT_MACROS = [
    {"icon": "B", "name": "Bold", "code": "\\textbf{%|}", "type": "Script", "position": "Left", "shortcut": "Ctrl+B"},
    {"icon": "I", "name": "Italic", "code": "\\textit{%|}", "type": "Script", "position": "Left", "shortcut": "Ctrl+I"},
    {"icon": "U", "name": "Underline", "code": "\\underline{%|}", "type": "Script", "position": "Left", "shortcut": "Ctrl+U"},
    {"icon": "$", "name": "Inline Math", "code": "$%|$", "type": "Script", "position": "Left", "shortcut": "Ctrl+Shift+M"},
    {"icon": "\\[\\]", "name": "Display Math", "code": "\\[\n%|\n\\]", "type": "Script", "position": "Left", "shortcut": "Alt+Shift+M"},
    {"icon": "↔", "name": "Căn giữa", "code": "\\begin{center}\n%|\n\\end{center}", "type": "Script", "position": "Left", "shortcut": "Ctrl+Shift+C"},
    {"icon": "←", "name": "Căn trái", "code": "\\begin{flushleft}\n%|\n\\end{flushleft}", "type": "Script", "position": "Left", "shortcut": ""},
    {"icon": "→", "name": "Căn phải", "code": "\\begin{flushright}\n%|\n\\end{flushright}", "type": "Script", "position": "Left", "shortcut": ""},
    {"icon": "•", "name": "Itemize", "code": "\\begin{itemize}\n\t\\item %|\n\\end{itemize}", "type": "Script", "position": "Left", "shortcut": "Ctrl+Shift+L"},
    {"icon": "1.", "name": "Enumerate", "code": "\\begin{enumerate}\n\t\\item %|\n\\end{enumerate}", "type": "Script", "position": "Left", "shortcut": "Ctrl+Shift+K"},
    {"icon": "i", "name": "Insert Item", "code": "\\item %|", "type": "Script", "position": "Menu Only", "shortcut": "Ctrl+Shift+I"},
    
    # --- 35 MACROS TIKZ ---
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/01.png", "name": "Khởi tạo TikZ", "code": "\\begin{tikzpicture}\n\\tkzInit[ymin=-0.5,ymax=7.5,xmin=-0.5,xmax=10.5]\n\\tkzClip\n\\tkzGrid\n\\tkzAxeXY\n\\tkzDefPoints{2/7/A,0/0/B,10/0/C}\n\\tkzDrawSegments(A,B B,C C,A)\n\\foreach \\i/\\g in {A/90,B/-90,C/-90}{\\draw[fill=white](\\i) circle (1.5pt) ($(\\i)+(\\g:3mm)$) node[scale=1]{$\\i$};}\n%|\n\\end{tikzpicture}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/02.png", "name": "Điểm mới", "code": "\\tkzDefPoints{%|}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/03.png", "name": "Nhãn điểm", "code": "\\foreach \\i/\\g in {%|}{\\draw[fill=white](\\i) circle (1.5pt) ($(\\i)+(\\g:3mm)$) node[scale=1]{$\\i$};}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/04.png", "name": "Đoạn thẳng", "code": "\\draw (%|);", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/05.png", "name": "Đa giác", "code": "\\draw[fill=yellow!30] (%|)--cycle;", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/06.png", "name": "Trung điểm", "code": "\\tkzDefMidPoint(%|)\\tkzGetPoint{M}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/07.png", "name": "Trọng tâm", "code": "\\tkzCentroid(%|)\\tkzGetPoint{G}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/08.png", "name": "Trực tâm", "code": "\\tkzOrthoCenter(%|)\\tkzGetPoint{H}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/09.png", "name": "Đ.thẳng song song", "code": "\\tkzDefLine[parallel=through %|]()\\tkzGetPoint{c}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/10.png", "name": "Đ.thẳng vuông góc", "code": "\\tkzDefLine[orthogonal=through %|]()\\tkzGetPoint{c}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/11.png", "name": "Đ.tròn qua 1 điểm", "code": "\\tkzDrawCircle(%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/12.png", "name": "Đ.tròn tâm & b.kính", "code": "\\tkzDefCircle[R](%|)\\tkzGetPoint{x}\\tkzDrawCircle(O,x)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/13.png", "name": "Đ.tròn ngoại tiếp", "code": "\\tkzDefTriangleCenter[circum](%|)\\tkzGetPoint{O} \\tkzDrawCircle(O,A)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/14.png", "name": "Đ.tròn nội tiếp", "code": "\\tkzDefCircle[in](%|) \\tkzGetPoints{I}{i} \\tkzDrawCircle(I,i)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/15.png", "name": "Đ.phân giác", "code": "\\tkzDefLine[bisector](%|)\\tkzGetPoint{d}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/16.png", "name": "Cung tròn", "code": "\\tkzDrawArc(%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/17.png", "name": "Cung góc xác định", "code": "\\tkzDrawSector[rotate](%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/18.png", "name": "Giao 2 đ.thẳng", "code": "\\tkzInterLL(%|)\\tkzGetPoint{E}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/19.png", "name": "Giao 2 đ.tròn", "code": "\\tkzInterCC(%|)\\tkzGetPoints{M}{N}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/20.png", "name": "Giao đ.thẳng đ.tròn", "code": "\\tkzInterLC(%|)\\tkzGetPoints{M}{N}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/21.png", "name": "Tiếp tuyến từ điểm", "code": "\\tkzDefLine[tangent from=%|]()\\tkzGetPoints{P}{Q}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/22.png", "name": "Tiếp tuyến tại điểm", "code": "\\tkzDefLine[tangent at=%|]()\\tkzGetPoint{z}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/23.png", "name": "Hình chiếu v.góc", "code": "\\tkzDefPointBy[projection=onto %|]()\\tkzGetPoint{H}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/24.png", "name": "Phép tịnh tiến", "code": "\\tkzDefPointBy[translation=from %| to ]()\\tkzGetPoint{}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/25.png", "name": "Phép vị tự", "code": "\\tkzDefPointBy[homothety=center %| ratio ]()\\tkzGetPoint{}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/26.png", "name": "Đối xứng trục", "code": "\\tkzDefPointBy[reflection=over %|]()\\tkzGetPoint{}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/27.png", "name": "Đối xứng tâm", "code": "\\tkzDefPointBy[symmetry=center %|]()\\tkzGetPoint{}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/28.png", "name": "Phép quay", "code": "\\tkzDefPointBy[rotation=center %| angle ]()\\tkzGetPoint{}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/29.png", "name": "Kí hiệu góc", "code": "\\tkzMarkAngles[arc=l,mark=s|,size=0.8cm](%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/30.png", "name": "Gán nhãn góc", "code": "\\tkzLabelAngles[pos=0.5,rotate=45](%|){$\\alpha$}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/31.png", "name": "Kí hiệu góc vuông", "code": "\\tkzMarkRightAngles(%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/32.png", "name": "Đánh dấu đ.thẳng", "code": "\\tkzMarkSegments[mark=x](%|)", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/33.png", "name": "Đặt tên đ.thẳng", "code": "\\tkzLabelSegment[pos=0.5](%|){}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/34.png", "name": "Độ dài đ.thẳng", "code": "\\tkzCalcLength[cm](%|)\\tkzGetLength{rAB}", "type": "Script", "position": "Top", "shortcut": ""},
    {"icon": "/Users/trananhtuan/Library/Mobile Documents/com~apple~CloudDocs/LaTeX/TuanTran/icon/icon-tikz-TeX-AI/35.png", "name": "Tính số đo góc", "code": "\\tkzFindAngle(%|)\\tkzGetAngle{ang}", "type": "Script", "position": "Top", "shortcut": ""}
]

# --- THÊM VÀO CUỐI FILE CONFIG.PY ---
# Danh sách các định dạng file phụ trợ cần xóa khi Clean
AUX_EXTENSIONS = ['.aux', '.log', '.out', '.toc', '.synctex.gz', '.pdf_tex', '.bbl', '.blg', '.fdb_latexmk', '.fls']
RECENT_FILES_FILE = os.path.join(CONFIG_DIR, "recent_files.json")
# Đường dẫn thư mục chứa các Template mẫu
TEMPLATE_DIR = os.path.join(CONFIG_DIR, "templates")
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)


