"""Note editor dialog window – text-based list markers.

Changes from QTextList to plain-text markers:
- Ordered list: "1. " "2. " etc. as normal text
- Bullet list: "• " as normal text
- Markers are regular characters, so font size naturally applies to them
- Auto-continue numbering on Enter
- Toggle list on/off by adding/removing marker prefix
"""

import re

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QFont, QTextCursor, QTextCharFormat
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class NoteEditor(QDialog):
    """Dialog for editing note title and content."""

    def __init__(self, note_title: str = "新建便签", content: str = "", parent=None, data_dir: str = None, theme: dict = None):
        super().__init__(parent)
        self._note_title = note_title
        self._content = content
        self._result_title = note_title
        self._result_content = content
        self._is_rich_text = False
        self._data_dir = data_dir
        self._theme = theme
        self._inserted_images = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("编辑便签")
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setStyleSheet(self._dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_label = QLabel("标题")
        title_label.setObjectName("editorLabel")
        self.title_input = QLineEdit(self._note_title)
        self.title_input.setObjectName("titleInput")
        self.title_input.setPlaceholderText("输入便签标题...")

        content_label = QLabel("内容")
        content_label.setObjectName("editorLabel")
        self.content_editor = QTextEdit()
        self.content_editor.setObjectName("contentEditor")
        self.content_editor.setPlaceholderText("输入便签内容...")
        self.content_editor.setPlainText(self._content)
        font = QFont("Microsoft YaHei", 11)
        self.content_editor.setFont(font)

        # 安装事件过滤器以拦截回车键
        self.content_editor.installEventFilter(self)

        self._create_toolbar(layout)
        self.content_editor.cursorPositionChanged.connect(self._update_format_state)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setDefault(True)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)

        layout.addWidget(title_label)
        layout.addWidget(self.title_input)
        layout.addWidget(content_label)
        layout.addWidget(self.content_editor)
        layout.addLayout(btn_layout)

    def eventFilter(self, obj, event):
        """拦截回车键，只在列表项中自动续行编号。"""
        if obj == self.content_editor and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                prev = cursor.block().previous() if (cursor := self.content_editor.textCursor()) else None
                if prev.isValid() and (re.match(r'^\d+\.\s', prev.text()) or prev.text().startswith("• ")):
                    self._auto_continue_list()
                    return True
        return super().eventFilter(obj, event)

    def _auto_continue_list(self):
        """回车后检查上一行是否是列表项，自动插入下一个编号/圆点。"""
        cursor = self.content_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        prev_text = cursor.block().text()

        # 有序列表：提取编号 + 1
        m = re.match(r'^(\d+)\.\s', prev_text)
        if m:
            next_num = int(m.group(1)) + 1
            cursor = self.content_editor.textCursor()
            cursor.insertText(f"{next_num}. ")
            return

        # 无序列表：直接复制
        if prev_text.startswith("• "):
            cursor = self.content_editor.textCursor()
            cursor.insertText("• ")

    def _create_toolbar(self, parent_layout: QVBoxLayout):
        """Create rich text formatting toolbar."""
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(4)

        self.btn_bold = QPushButton("B")
        self.btn_bold.setObjectName("toolBtn")
        self.btn_bold.setToolTip("加粗 (Ctrl+B)")
        self.btn_bold.setCheckable(True)
        self.btn_bold.clicked.connect(self._toggle_bold)
        bold_font = QFont()
        bold_font.setBold(True)
        self.btn_bold.setFont(bold_font)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setObjectName("toolBtn")
        self.btn_italic.setToolTip("倾斜 (Ctrl+I)")
        self.btn_italic.setCheckable(True)
        self.btn_italic.clicked.connect(self._toggle_italic)
        italic_font = QFont()
        italic_font.setItalic(True)
        self.btn_italic.setFont(italic_font)

        self.btn_underline = QPushButton("U")
        self.btn_underline.setObjectName("toolBtn")
        self.btn_underline.setToolTip("下划线 (Ctrl+U)")
        self.btn_underline.setCheckable(True)
        self.btn_underline.clicked.connect(self._toggle_underline)
        underline_font = QFont()
        underline_font.setUnderline(True)
        self.btn_underline.setFont(underline_font)

        sep1 = QLabel("|")
        sep1.setObjectName("toolbarSep")

        self.btn_font_smaller = QPushButton("A-")
        self.btn_font_smaller.setObjectName("toolBtn")
        self.btn_font_smaller.setToolTip("缩小字号")
        self.btn_font_smaller.clicked.connect(self._font_smaller)

        self.btn_font_larger = QPushButton("A+")
        self.btn_font_larger.setObjectName("toolBtn")
        self.btn_font_larger.setToolTip("增大字号")
        self.btn_font_larger.clicked.connect(self._font_larger)

        sep2 = QLabel("|")
        sep2.setObjectName("toolbarSep")

        self.btn_ordered = QPushButton("1.")
        self.btn_ordered.setObjectName("toolBtn")
        self.btn_ordered.setToolTip("有序列表")
        self.btn_ordered.setCheckable(True)
        self.btn_ordered.clicked.connect(self._toggle_ordered_list)

        self.btn_bullet = QPushButton("•")
        self.btn_bullet.setObjectName("toolBtn")
        self.btn_bullet.setToolTip("无序列表")
        self.btn_bullet.setCheckable(True)
        self.btn_bullet.clicked.connect(self._toggle_bullet_list)

        self.toolbar_layout.addWidget(self.btn_bold)
        self.toolbar_layout.addWidget(self.btn_italic)
        self.toolbar_layout.addWidget(self.btn_underline)
        self.toolbar_layout.addWidget(sep1)
        self.toolbar_layout.addWidget(self.btn_font_smaller)
        self.toolbar_layout.addWidget(self.btn_font_larger)
        self.toolbar_layout.addWidget(sep2)
        self.toolbar_layout.addWidget(self.btn_ordered)
        self.toolbar_layout.addWidget(self.btn_bullet)
        self.toolbar_layout.addStretch()

        parent_layout.addLayout(self.toolbar_layout)

    # ─── Format Actions ─────────────────────────────────────────

    def _toggle_bold(self):
        fmt = self.content_editor.currentCharFormat()
        fmt.setFontWeight(
            QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal
        )
        self.content_editor.mergeCurrentCharFormat(fmt)

    def _toggle_italic(self):
        fmt = self.content_editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.content_editor.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self):
        fmt = self.content_editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.content_editor.mergeCurrentCharFormat(fmt)

    # ─── Font Size ──────────────────────────────────────────────

    def _get_effective_font_size(self) -> float:
        """获取当前光标处文字的实际显示字号。"""
        cursor = self.content_editor.textCursor()
        block = cursor.block()
        base_size = self.content_editor.font().pointSize()
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                fs = fragment.charFormat().fontPointSize()
                if fs > 0:
                    return fs
            it += 1
        return base_size

    def _font_smaller(self):
        current_size = self._get_effective_font_size()
        new_size = max(8, current_size - 2)
        self._apply_font_size(new_size)

    def _font_larger(self):
        current_size = self._get_effective_font_size()
        new_size = min(72, current_size + 2)
        self._apply_font_size(new_size)

    def _apply_font_size(self, size: float):
        """应用字号：有选区→mergeCharFormat；无选区→选当前块再merge。"""
        cursor = self.content_editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)

        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            block = cursor.block()
            if block.length() > 1:
                block_cursor = self.content_editor.textCursor()
                block_cursor.setPosition(block.position())
                block_cursor.setPosition(
                    block.position() + block.length() - 1,
                    QTextCursor.MoveMode.KeepAnchor
                )
                block_cursor.mergeCharFormat(fmt)
                self.content_editor.setTextCursor(cursor)
            self.content_editor.setCurrentCharFormat(fmt)

    # ─── List Actions (text-based markers) ───────────────────────

    def _collect_list_blocks(self, cursor, max_lines=20):
        """收集光标所在行+向上的连续非空段落，用于构造列表。"""
        doc = self.content_editor.document()
        cursor_pos = cursor.position()
        block = doc.findBlock(cursor_pos)
        blocks = []

        # 光标所在行
        if block.text().strip():
            blocks.append(block)

        b = block.previous()
        for _ in range(max_lines - 1):
            if not b.isValid():
                break
            text = b.text().strip()
            if not text:
                break
            blocks.insert(0, b)
            b = b.previous()

        return blocks

    def _remove_prefix_from_blocks(self, blocks, pattern, cursor):
        """从多个块中移除匹配 pattern 的前缀。"""
        cursor.beginEditBlock()
        for block in blocks:
            m = re.match(pattern, block.text())
            if m:
                pos = block.position()
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(m.group(0)), QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
        cursor.endEditBlock()

    def _apply_char_format_to_blocks(self, blocks, fmt):
        """把字符格式应用到多个块的全部文字。"""
        if not blocks:
            return
        cursor = self.content_editor.textCursor()
        cursor.beginEditBlock()
        for block in blocks:
            if block.length() > 1:
                bc = self.content_editor.textCursor()
                bc.setPosition(block.position())
                bc.setPosition(
                    block.position() + block.length() - 1,
                    QTextCursor.MoveMode.KeepAnchor
                )
                bc.mergeCharFormat(fmt)
        cursor.endEditBlock()

    def _is_ordered_list_block(self, block):
        return bool(re.match(r'^\d+\.\s', block.text()))

    def _is_bullet_list_block(self, block):
        return block.text().startswith("• ")

    def _toggle_ordered_list(self):
        cursor = self.content_editor.textCursor()
        blocks = self._collect_list_blocks(cursor)

        if not blocks:
            return

        # 检查是否都是有序列表项 → 取消
        if all(self._is_ordered_list_block(b) for b in blocks):
            self._remove_prefix_from_blocks(blocks, r'^\d+\.\s', cursor)
            self.btn_ordered.setChecked(False)
            return

        # 收集基准字号（取第一个块）
        base_size = 11.0
        it = blocks[0].begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                fs = frag.charFormat().fontPointSize()
                if fs > 0:
                    base_size = fs
                    break
            it += 1

        cursor.beginEditBlock()
        # 移除旧前缀（有序/无序），插入新编号
        for i, block in enumerate(blocks):
            # 先移除任何旧前缀
            for pattern in [r'^\d+\.\s', r'^•\s']:
                m = re.match(pattern, block.text())
                if m:
                    pos = block.position()
                    cursor.setPosition(pos)
                    cursor.setPosition(pos + len(m.group(0)), QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                    break
            # 插入编号
            cursor.setPosition(block.position())
            cursor.insertText(f"{i + 1}. ")
        cursor.endEditBlock()

        # 统一设置格式到所有列表行（关键！）
        fmt = QTextCharFormat()
        fmt.setFontPointSize(base_size)
        blocks2 = self._collect_list_blocks(self.content_editor.textCursor())
        self._apply_char_format_to_blocks(blocks2, fmt)

        self.btn_ordered.setChecked(True)
        self.btn_bullet.setChecked(False)

    def _toggle_bullet_list(self):
        cursor = self.content_editor.textCursor()
        blocks = self._collect_list_blocks(cursor)

        if not blocks:
            return

        # 检查是否都是无序列表项 → 取消
        if all(self._is_bullet_list_block(b) for b in blocks):
            for block in blocks:
                if block.text().startswith("• "):
                    pos = block.position()
                    cursor.setPosition(pos)
                    cursor.setPosition(pos + 2, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
            self.btn_bullet.setChecked(False)
            return

        base_size = 11.0
        it = blocks[0].begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                fs = frag.charFormat().fontPointSize()
                if fs > 0:
                    base_size = fs
                    break
            it += 1

        cursor.beginEditBlock()
        for block in blocks:
            for pattern in [r'^\d+\.\s', r'^•\s']:
                m = re.match(pattern, block.text())
                if m:
                    pos = block.position()
                    cursor.setPosition(pos)
                    cursor.setPosition(pos + len(m.group(0)), QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                    break
            cursor.setPosition(block.position())
            cursor.insertText("• ")
        cursor.endEditBlock()

        fmt = QTextCharFormat()
        fmt.setFontPointSize(base_size)
        blocks2 = self._collect_list_blocks(self.content_editor.textCursor())
        self._apply_char_format_to_blocks(blocks2, fmt)

        self.btn_bullet.setChecked(True)
        self.btn_ordered.setChecked(False)

    # ─── Format State ────────────────────────────────────────────

    def _update_format_state(self):
        """Update toolbar button states based on current cursor format."""
        fmt = self.content_editor.currentCharFormat()
        self.btn_bold.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_underline.setChecked(fmt.fontUnderline())

        cursor = self.content_editor.textCursor()
        block = cursor.block()
        text = block.text()

        self.btn_ordered.setChecked(self._is_ordered_list_block(block))
        self.btn_bullet.setChecked(self._is_bullet_list_block(block))

    # ─── Save / Get ──────────────────────────────────────────────

    def _on_save(self):
        self._result_title = self.title_input.text().strip() or "新建便签"
        self._result_content = self.content_editor.toPlainText()
        self._result_html = self.content_editor.toHtml()
        self.accept()

    def get_inserted_images(self) -> list:
        return self._inserted_images

    def get_title(self) -> str:
        return self._result_title

    def get_content(self) -> str:
        return self._result_content

    def get_html(self) -> str:
        return self.content_editor.toHtml()

    # ─── Styles ──────────────────────────────────────────────────

    def _dialog_style(self) -> str:
        if self._theme:
            t = self._theme
            bg = t.get("bg", "#1e1e2e")
            dark = t.get("dark", "#313244")
            border = t.get("border", "#45475a")
            text = t.get("text", "#cdd6f4")
            textLight = t.get("textLight", "#a6adc8")
            accent = t.get("accent", "#89b4fa")
            input_bg = t.get("card", "#313244")
            btn_hover = t.get("header", "#45475a")
        else:
            bg = "#1e1e2e"
            dark = "#313244"
            border = "#45475a"
            text = "#cdd6f4"
            textLight = "#a6adc8"
            accent = "#89b4fa"
            input_bg = "#313244"
            btn_hover = "#45475a"

        return f"""
            QDialog {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel#editorLabel {{
                color: {text};
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 2px;
            }}
            QLineEdit#titleInput {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 15px;
                font-weight: bold;
            }}
            QLineEdit#titleInput:focus {{
                border-color: {accent};
            }}
            QTextEdit#contentEditor {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 10px;
                selection-background-color: {accent};
                selection-color: {bg};
            }}
            QTextEdit#contentEditor:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#saveBtn {{
                background-color: {accent};
                color: {bg};
            }}
            QPushButton#saveBtn:hover {{
                background-color: {dark};
                color: {text};
            }}
            QPushButton#cancelBtn {{
                background-color: {btn_hover};
                color: {text};
            }}
            QPushButton#cancelBtn:hover {{
                background-color: {dark};
            }}
            QPushButton#toolBtn {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 28px;
                max-height: 28px;
            }}
            QPushButton#toolBtn:hover {{
                background-color: {btn_hover};
            }}
            QPushButton#toolBtn:checked {{
                background-color: {accent};
                color: {bg};
                border-color: {accent};
            }}
        """