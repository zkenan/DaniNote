"""Main window for Sticky Notes (DaniNote) – full UI redesign.

Design reference: code.html
Layout:
  - Frameless window with native edge/corner resize via WM_NCHITTEST.
  - Title bar: app title left, [pin] [minimize] [close] buttons right.
  - Body split into upper (notes grid) and lower (todo list) halves.
  - Bottom-left: hamburger button to toggle collapsible sidebar overlay.
  - Bottom-right: opacity button + settings (theme) button with popup panels.
  - Sidebar overlay: "所有便签" / "待办事项" / "历史待办" nav.
  - Settings popup: 5-colour theme grid (暖阳/薄荷/玫瑰/天空/拿铁).
  - Opacity popup: slider (30%–100%).
  - Todo input: QDateTimeEdit with calendarPopup + direct keyboard input.
"""

import ctypes
import os
from ctypes import wintypes
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QDate, QEvent, QPoint, Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QMouseEvent, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.models import DatabaseManager, Note, Todo
from src.utils import enable_acrylic_blur, enable_blurbehind
from src.utils.notifier import ReminderChecker, send_notification
from src.views.note_editor import NoteEditor

# ─── Resize margin ─────────────────────────────────────────
_RESIZE_MARGIN = 12

# ─── Windows hit-test constants ────────────────────────────
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17

# ─── Theme definitions ─────────────────────────────────────
THEMES = [
    {
        "key": "warm", "label": "暖阳",
        "bg": "#FFF8E7", "dark": "#F5EDD6", "header": "#F0E4C8",
        "card": "#FFFCF2", "border": "#E8DCC8",
        "text": "#4A3728", "textLight": "#8B7B6B", "accent": "#C07050",
        "todoBg": "#FFF4E8",
    },
    {
        "key": "mint", "label": "薄荷",
        "bg": "#EDF7F0", "dark": "#D8EFE0", "header": "#C8E5D2",
        "card": "#F5FBF7", "border": "#BFDCC8",
        "text": "#2D4A35", "textLight": "#6B8B75", "accent": "#3D8B5F",
        "todoBg": "#EDF5F0",
    },
    {
        "key": "rose", "label": "玫瑰",
        "bg": "#FFF0F0", "dark": "#F5DEDE", "header": "#F0CDCD",
        "card": "#FFF7F7", "border": "#E8C8C8",
        "text": "#4A2D2D", "textLight": "#8B6B6B", "accent": "#C0606A",
        "todoBg": "#FFF2F2",
    },
    {
        "key": "sky", "label": "天空",
        "bg": "#EBF5FF", "dark": "#D6E8F8", "header": "#C5D9F2",
        "card": "#F5FAFF", "border": "#BDCFE8",
        "text": "#2D3A4A", "textLight": "#6B7A8B", "accent": "#4A8BC2",
        "todoBg": "#EDF5FF",
    },
    {
        "key": "latte", "label": "拿铁",
        "bg": "#F5EDE3", "dark": "#E8DDD0", "header": "#DED0BF",
        "card": "#FBF7F2", "border": "#D4C8B8",
        "text": "#3E3228", "textLight": "#8B7E6E", "accent": "#A86B40",
        "todoBg": "#F5EFE5",
    },
]

# ─── Note card colours ─────────────────────────────────────
CARD_COLORS = ["#C07050", "#5BA89B", "#D4B83D", "#8B78C4", "#D4893E", "#4DA88A", "#C4687A", "#5A8FBA"]


# ============================================================
#  Sidebar Overlay
# ============================================================

class SidebarOverlay(QFrame):
    """Full-window overlay with backdrop blur, shown when sidebar is open."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarOverlay")
        self.setStyleSheet("#sidebarOverlay { background-color: rgba(0,0,0,0.3); }")
        self.hide()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class SidebarItem(QFrame):
    """Clickable item in sidebar list."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarNoteItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ============================================================
#  Sidebar
# ============================================================

class Sidebar(QFrame):
    """Collapsible left sidebar with nav and content."""

    note_selected = Signal(int)
    view_changed = Signal(str)
    history_delete_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(270)
        self._notes: List[Note] = []
        self._todos: List[Todo] = []
        self._history: List[Todo] = []
        self._current_view = "notes"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("sidebarHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 22, 20, 16)
        title = QLabel("张张便签管理")
        title.setObjectName("sidebarTitle")
        subtitle = QLabel("浏览与管理你的所有记录")
        subtitle.setObjectName("sidebarSubtitle")
        hl.addWidget(title)
        hl.addWidget(subtitle)
        layout.addWidget(header)

        # Nav buttons
        nav = QFrame()
        nav.setObjectName("sidebarNav")
        nl = QVBoxLayout(nav)
        nl.setContentsMargins(10, 10, 10, 10)
        nl.setSpacing(2)

        self.note_btn = QPushButton("  📝  所有便签")
        self.note_btn.setObjectName("sidebarNavBtn")
        self.note_btn.clicked.connect(lambda: self._switch("notes", self.note_btn))
        self.note_count = QLabel("0")
        self.note_count.setObjectName("sidebarCount")

        nb_layout = QHBoxLayout()
        nb_layout.setContentsMargins(0, 0, 0, 0)
        nb_layout.addWidget(self.note_btn, 1)
        nb_layout.addWidget(self.note_count)
        nl.addLayout(nb_layout)

        self.todo_btn = QPushButton("  ✅  待办事项")
        self.todo_btn.setObjectName("sidebarNavBtn")
        self.todo_btn.clicked.connect(lambda: self._switch("todos", self.todo_btn))
        self.todo_count = QLabel("0")
        self.todo_count.setObjectName("sidebarCount")

        tb_layout = QHBoxLayout()
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.addWidget(self.todo_btn, 1)
        tb_layout.addWidget(self.todo_count)
        nl.addLayout(tb_layout)

        self.history_btn = QPushButton("  📋  历史待办")
        self.history_btn.setObjectName("sidebarNavBtn")
        self.history_btn.clicked.connect(lambda: self._switch("history", self.history_btn))
        self.history_count = QLabel("0")
        self.history_count.setObjectName("sidebarCount")

        hb_layout = QHBoxLayout()
        hb_layout.setContentsMargins(0, 0, 0, 0)
        hb_layout.addWidget(self.history_btn, 1)
        hb_layout.addWidget(self.history_count)
        nl.addLayout(hb_layout)

        layout.addWidget(nav)

        # Content area
        self.content_area = QScrollArea()
        self.content_area.setObjectName("sidebarContentArea")
        self.content_area.setWidgetResizable(True)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 消除 viewport 默认灰色背景
        self.content_area.viewport().setAutoFillBackground(False)
        sidebar_vp_pal = self.content_area.viewport().palette()
        sidebar_vp_pal.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        self.content_area.viewport().setPalette(sidebar_vp_pal)
        self.content_widget = QWidget()
        self.content_widget.setAutoFillBackground(False)
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(14, 12, 14, 12)
        self.content_layout.setSpacing(6)
        self.content_layout.addStretch()
        self.content_area.setWidget(self.content_widget)
        layout.addWidget(self.content_area, 1)

        self._highlight(self.note_btn)

    def _style(self) -> str:
        """返回空样式——颜色完全由 apply_theme() 统一管理，避免硬编码导致主题切换后颜色不统一。"""
        return ""

    def set_data(self, notes: List[Note], todos: List[Todo], history: List[Todo]):
        self._notes = notes
        self._todos = [t for t in todos if not t.is_done]
        self._history = history
        self.note_count.setText(str(len(notes)))
        self.todo_count.setText(str(len(self._todos)))
        self.history_count.setText(str(len(history)))
        self._render_content()

    def _switch(self, view: str, btn: QPushButton):
        self._current_view = view
        self._highlight(btn)
        self._render_content()
        self.view_changed.emit(view)

    def _highlight(self, btn: QPushButton):
        for b in [self.note_btn, self.todo_btn, self.history_btn]:
            b.setProperty("active", b is btn)
            b.style().unpolish(b)
            b.style().polish(b)

    def _render_content(self):
        self._clear_layout(self.content_layout)
        if self._current_view == "notes":
            if not self._notes:
                empty = QLabel("暂无便签")
                empty.setObjectName("sidebarEmpty")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.addWidget(empty)
            else:
                for n in self._notes:
                    item = SidebarItem()
                    il = QVBoxLayout(item)
                    il.setContentsMargins(12, 10, 12, 10)
                    il.setSpacing(2)
                    h4 = QLabel(n.title)
                    h4.setObjectName("sidebarNoteTitle")
                    il.addWidget(h4)
                    p = QLabel(getattr(n, '_content_preview', ''))
                    p.setObjectName("sidebarNotePreview")
                    il.addWidget(p)
                    item.clicked.connect(lambda checked=False, nid=n.id: self.note_selected.emit(nid))
                    self.content_layout.addWidget(item)
        elif self._current_view == "todos":
            if not self._todos:
                empty = QLabel("所有待办已完成")
                empty.setObjectName("sidebarEmpty")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.addWidget(empty)
            else:
                for t in self._todos:
                    item = QLabel(f"  ○  {t.content}")
                    item.setObjectName("sidebarTodoItem")
                    self.content_layout.addWidget(item)
        elif self._current_view == "history":
            if not self._history:
                empty = QLabel("暂无历史记录")
                empty.setObjectName("sidebarEmpty")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.content_layout.addWidget(empty)
            else:
                for t in self._history:
                    item = QFrame()
                    item.setObjectName("sidebarHistoryItem")
                    h_layout = QHBoxLayout(item)
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    h_layout.setSpacing(6)
                    label = QLabel(f"  ✓  {t.content}")
                    label.setObjectName("sidebarTodoItem")
                    del_btn = QPushButton("×")
                    del_btn.setObjectName("sidebarHistoryDelBtn")
                    del_btn.setFixedSize(20, 20)
                    del_btn.clicked.connect(lambda checked=False, tid=t.id: self.history_delete_requested.emit(tid))
                    h_layout.addWidget(label, 1)
                    h_layout.addWidget(del_btn)
                    self.content_layout.addWidget(item)
        self.content_layout.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def apply_theme(self, t: dict):
        self.setStyleSheet(f"""
            #sidebar {{
                background-color: {t['bg']};
                border-right: 1px solid {t['border']};
            }}
            #sidebarHeader {{
                border-bottom: 1px solid {t['border']};
                background-color: {t['bg']};
            }}
            QLabel#sidebarTitle {{ color: {t['text']}; font-size: 20px; font-weight: 900; }}
            QLabel#sidebarSubtitle {{ color: {t['textLight']}; font-size: 11px; }}
            QPushButton#sidebarNavBtn {{
                background: transparent; border: none; border-radius: 10px;
                color: {t['text']}; font-size: 14px; font-weight: 500;
                text-align: left; padding: 11px 16px;
            }}
            QPushButton#sidebarNavBtn:hover {{ background-color: rgba(0,0,0,0.05); }}
            QPushButton#sidebarNavBtn.active {{ background-color: {t['accent']}22; color: {t['accent']}; }}
            QLabel#sidebarCount {{ color: {t['textLight']}; background: rgba(0,0,0,0.06); }}
            QScrollArea#sidebarContentArea {{ border: none; background: transparent; }}
            QScrollArea#sidebarContentArea > QWidget {{ background: transparent; border: none; }}
            QLabel#sidebarNoteTitle {{ color: {t['text']}; font-size: 13px; font-weight: 600; }}
            QLabel#sidebarNotePreview {{ color: {t['textLight']}; font-size: 11px; }}
            QLabel#sidebarTodoItem {{ color: {t['text']}; font-size: 13px; padding: 6px 12px; }}
            QLabel#sidebarEmpty {{ color: {t['textLight']}; font-size: 13px; }}
            QFrame#sidebarNoteItem {{
                background: transparent; border-radius: 8px;
            }}
            QFrame#sidebarNoteItem:hover {{
                background: {t['dark']};
            }}
            QFrame#sidebarHistoryItem {{
                background: {t['card']}; border-radius: 6px;
            }}
            QFrame#sidebarHistoryItem:hover {{
                background: {t['dark']};
            }}
            QPushButton#sidebarHistoryDelBtn {{
                background: transparent; border: none; color: {t['textLight']}; font-size: 13px;
            }}
            QPushButton#sidebarHistoryDelBtn:hover {{ color: #e74c3c; }}
        """)


# ============================================================
#  NoteCard
# ============================================================

class NoteCard(QFrame):
    """Card widget for a single note in the grid."""

    clicked = Signal(int)
    deleted = Signal(int)

    def __init__(self, note: Note, parent=None):
        super().__init__(parent)
        self.note = note
        self.setObjectName("noteCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(80)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 10)
        layout.setSpacing(6)

        # Color bar at top
        self.color_bar = QFrame()
        self.color_bar.setFixedHeight(3)
        color_idx = self.note.id % len(CARD_COLORS) if self.note.id else 0
        self._card_color = CARD_COLORS[color_idx]
        self.color_bar.setStyleSheet(f"background-color: {self._card_color}; border-radius: 2px;")

        # Title
        self.title_label = QLabel(self.note.title)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(False)

        # Preview
        self.preview_label = QLabel("")
        self.preview_label.setObjectName("cardPreview")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMaximumHeight(48)

        # Delete button (top-right corner)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self.title_label, 1)

        self.del_btn = QPushButton("×")
        self.del_btn.setObjectName("cardDeleteBtn")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self.note.id))
        self.del_btn.hide()

        header_layout.addWidget(self.del_btn)

        layout.addWidget(self.color_bar)
        layout.addLayout(header_layout)
        layout.addWidget(self.preview_label)

    def update_preview(self, content: str):
        preview = content.strip()[:80]
        if len(content.strip()) > 80:
            preview += "..."
        self.preview_label.setText(preview)

    def enterEvent(self, event):
        self.del_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.del_btn.hide()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.note.id)
        super().mouseDoubleClickEvent(event)


# ============================================================
#  TodoItem
# ============================================================

class TodoItem(QFrame):
    """Widget for a single todo item in the list."""

    toggled = Signal(int, bool)
    deleted = Signal(int)
    edited = Signal(object)

    def __init__(self, todo: Todo, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.setObjectName("todoItem")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 8, 7)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("todoCheck")
        self.checkbox.setChecked(self.todo.is_done)
        self.checkbox.toggled.connect(lambda v: self.toggled.emit(self.todo.id, v))

        content_layout = QVBoxLayout()
        content_layout.setSpacing(3)

        self.content_label = QLabel(self.todo.content)
        self.content_label.setObjectName("todoContent")
        self.content_label.setWordWrap(True)
        if self.todo.is_done:
            self.content_label.setStyleSheet("text-decoration: line-through;")

        # Time tag
        if self.todo.due_date:
            tag_layout = QHBoxLayout()
            tag_layout.setSpacing(0)
            tag_layout.addStretch()

            tag = QLabel()
            tag.setObjectName("todoTimeTag")
            try:
                dt = datetime.strptime(self.todo.due_date, "%Y-%m-%d %H:%M:%S")
                display = dt.strftime("%m-%d %H:%M")
            except ValueError:
                try:
                    dt = datetime.strptime(self.todo.due_date, "%Y-%m-%d")
                    display = dt.strftime("%m-%d")
                except ValueError:
                    display = self.todo.due_date
                    dt = None

            # Check if overdue
            now = datetime.now()
            if dt and dt < now:
                tag.setText(f"已过期")
                tag.setProperty("overdue", True)
                tag.style().unpolish(tag)
                tag.style().polish(tag)
            else:
                tag.setText(f"截止 {display}")

            tag_layout.addWidget(tag)
            content_layout.addLayout(tag_layout)

        content_layout.addWidget(self.content_label)

        self.edit_btn = QPushButton("✎")
        self.edit_btn.setObjectName("todoEditBtn")
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.clicked.connect(lambda: self.edited.emit(self.todo))

        self.del_btn = QPushButton("×")
        self.del_btn.setObjectName("todoDelBtn")
        self.del_btn.setFixedSize(24, 24)
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self.todo.id))

        layout.addWidget(self.checkbox)
        layout.addLayout(content_layout, 1)
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.del_btn)


# ============================================================
#  Main Window
# ============================================================

class MainWindow(QMainWindow):
    """Main application window – fully redesigned."""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._is_dragging = False
        self._drag_position = QPoint()
        self._settings = {"reminder_enabled": True, "reminder_advance_minutes": 10, "sound_enabled": True}
        self._reminder_checker: Optional[ReminderChecker] = None
        self._current_theme_index = 0
        self._windows_opacity = 100

        self._setup_window()
        self._setup_tray()
        self._setup_ui()
        self._apply_theme()
        self._load_data()
        self._start_reminder_checker()

    # ─── Window Setup ────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("张张便签")
        self.setMinimumSize(200, 150)
        self.resize(440, 640)

        icon_path = self._get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # 先设置无边框和透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        try:
            enable_acrylic_blur(int(self.winId()))
        except Exception:
            try:
                enable_blurbehind(int(self.winId()))
            except Exception:
                pass

    def showEvent(self, event):
        """窗口首次显示时通过 Win32 API 启用原生调整大小。
        必须在 show 之后调用，确保 native window handle 已就绪且不会被 Qt 后续操作覆盖。
        """
        super().showEvent(event)
        self._enable_native_resize()

    def _enable_native_resize(self):
        _hwnd = int(self.winId())
        GWL_STYLE = -16
        _style = ctypes.windll.user32.GetWindowLongW(_hwnd, GWL_STYLE)
        # 添加调整大小边框、最大化、最小化按钮
        _style |= 0x00040000  # WS_THICKFRAME
        _style |= 0x00010000  # WS_MAXIMIZEBOX
        _style |= 0x00020000  # WS_MINIMIZEBOX
        _style |= 0x00080000  # WS_SYSMENU (系统菜单)
        ctypes.windll.user32.SetWindowLongW(_hwnd, GWL_STYLE, _style)
        ctypes.windll.user32.SetWindowPos(
            _hwnd, 0, 0, 0, 0, 0,
            0x0002 | 0x0001 | 0x0020,  # SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE
        )

    def _get_icon_path(self) -> Optional[str]:
        candidates = [
            r"F:\1zkenan\1xiangmu\sticky notes\assets\app.ico",
            "assets/app.ico",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    # ─── System Tray ─────────────────────────────────────────

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = self._get_icon_path()
        icon = QIcon(icon_path) if icon_path else self.windowIcon()
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip("张张便签")
        menu = QMenu(self)
        show_action = menu.addAction("显示窗口")
        show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self._tray_icon = None
        QApplication.instance().quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self._show_window()

    def closeEvent(self, event):
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    # ─── Native Resize via WM_NCHITTEST ──────────────────────

    def nativeEvent(self, eventType, message):
        """处理 Windows 原生消息，实现边框和四角拖拽调整窗口大小。

        核心思路：
        - 窗口设置为 FramelessWindowHint + WS_THICKFRAME，让系统保留 resize 边框逻辑
        - 在 WM_NCHITTEST 中检测鼠标位置，边缘/角落返回对应 HT 值
        - 坐标提取使用带符号的 short 转换（支持多显示器负坐标）

        注意：PySide6 的 message 参数是 shiboken6.VoidPtr 类型，
        需要先用 int() 转为整数地址才能传给 MSG.from_address()。
        """
        try:
            if bytes(eventType) != b"windows_generic_MSG":
                return False, 0
        except (TypeError, ValueError):
            return False, 0
        try:
            # PySide6: message 是 shiboken6.VoidPtr，需转为 int
            msg = wintypes.MSG.from_address(int(message))
        except Exception:
            return False, 0

        if msg.message == 0x0083:  # WM_NCCALCSIZE
            # wParam != 0 时返回 0，让系统计算非客户区边框（resize 用）
            # wParam == 0 时交给 DefWindowProc
            if msg.wParam:
                return True, 0
            return False, 0

        if msg.message != 0x0084:  # WM_NCHITTEST
            return False, 0

        # 提取屏幕坐标（带符号 16-bit，支持多显示器负坐标）
        x = msg.lParam & 0xFFFF
        y = (msg.lParam >> 16) & 0xFFFF
        if x >= 0x8000:
            x -= 0x10000
        if y >= 0x8000:
            y -= 0x10000

        # 转换为窗口本地坐标
        geom = self.geometry()
        win_x = x - geom.left()
        win_y = y - geom.top()
        w = geom.width()
        h = geom.height()
        border = _RESIZE_MARGIN

        # 超出窗口范围，交给系统处理
        if win_x < 0 or win_x > w or win_y < 0 or win_y > h:
            return False, 0

        # ── 边缘检测：角落优先 ──
        on_left = win_x < border
        on_right = win_x > w - border
        on_top = win_y < border
        on_bottom = win_y > h - border

        if on_top and on_left:
            return True, _HTTOPLEFT
        if on_top and on_right:
            return True, _HTTOPRIGHT
        if on_bottom and on_left:
            return True, _HTBOTTOMLEFT
        if on_bottom and on_right:
            return True, _HTBOTTOMRIGHT
        if on_top:
            return True, _HTTOP
        if on_bottom:
            return True, _HTBOTTOM
        if on_left:
            return True, _HTLEFT
        if on_right:
            return True, _HTRIGHT

        # ── 其他区域：不拦截，让系统默认处理 ──
        return False, 0

    # ─── UI Setup ────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        main_layout.addWidget(self._create_title_bar())

        # Body: upper notes + lower todos
        main_layout.addWidget(self._create_body(), 1)

        # Footer: left hamburger + right settings/opacity
        main_layout.addWidget(self._create_footer())

        # Popup panels (positioned absolutely via parent)
        self._create_popups(central)

        # Sidebar overlay
        self._sidebar_overlay = SidebarOverlay(central)
        self._sidebar_overlay.clicked.connect(self._toggle_sidebar)
        self._sidebar_overlay.setGeometry(0, 0, central.width(), central.height())

        # Sidebar
        self._sidebar = Sidebar(central)
        self._sidebar.note_selected.connect(self._edit_note)
        self._sidebar.view_changed.connect(self._on_sidebar_view_changed)
        self._sidebar.history_delete_requested.connect(self._delete_history_todo)
        self._sidebar.setGeometry(-270, 0, 270, central.height())

    def _create_title_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(42)
        bar.installEventFilter(self)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(0)

        # App icon + title
        icon_label = QLabel("📌")
        icon_label.setObjectName("titleIcon")
        self._title_label = QLabel("张张便签 DaniNote")
        self._title_label.setObjectName("titleLabel")

        layout.addWidget(icon_label)
        layout.addSpacing(6)
        layout.addWidget(self._title_label)
        layout.addStretch()

        # Pin button
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("titlePinBtn")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setFixedSize(30, 30)
        self._pin_btn.setToolTip("置顶窗口")
        self._pin_btn.clicked.connect(self._toggle_pin)

        # Minimize button
        min_btn = QPushButton("─")
        min_btn.setObjectName("titleWinBtn")
        min_btn.setFixedSize(30, 30)
        min_btn.clicked.connect(self.showMinimized)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setObjectName("titleCloseBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)

        layout.addWidget(self._pin_btn)
        layout.addSpacing(4)
        layout.addWidget(min_btn)
        layout.addSpacing(4)
        layout.addWidget(close_btn)

        return bar

    def _create_body(self) -> QWidget:
        body = QWidget()
        body.setObjectName("bodyWidget")
        body.setAutoFillBackground(False)
        body.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 6)
        layout.setSpacing(0)

        # ── Notes section (upper half) ──
        notes_section = QVBoxLayout()
        notes_section.setSpacing(8)

        notes_header = QHBoxLayout()
        notes_header.setSpacing(6)
        notes_label = QLabel("📝 便签")
        notes_label.setObjectName("sectionLabel")
        notes_header.addWidget(notes_label)
        notes_header.addStretch()

        add_note_btn = QPushButton("+")
        add_note_btn.setObjectName("addNoteBtn")
        add_note_btn.setFixedSize(28, 28)
        add_note_btn.setToolTip("添加便签")
        add_note_btn.clicked.connect(self._add_note)
        notes_header.addWidget(add_note_btn)

        notes_section.addLayout(notes_header)

        # Grid scroll area
        self._notes_scroll = QScrollArea()
        self._notes_scroll.setObjectName("notesScroll")
        self._notes_scroll.setWidgetResizable(True)
        self._notes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 彻底消除 QScrollArea viewport 默认灰色背景（QPalette::Base 填充）
        self._notes_scroll.viewport().setAutoFillBackground(False)
        notes_vp_pal = self._notes_scroll.viewport().palette()
        notes_vp_pal.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        self._notes_scroll.viewport().setPalette(notes_vp_pal)
        self._notes_grid_widget = QWidget()
        self._notes_grid_widget.setObjectName("notesGridWidget")
        self._notes_grid_widget.setAutoFillBackground(False)
        self._notes_grid_widget.setStyleSheet("background: transparent;")
        self._notes_grid = QVBoxLayout(self._notes_grid_widget)
        self._notes_grid.setContentsMargins(0, 0, 0, 0)
        self._notes_grid.setSpacing(8)
        self._notes_grid.addStretch()
        self._notes_scroll.setWidget(self._notes_grid_widget)
        notes_section.addWidget(self._notes_scroll, 1)

        layout.addLayout(notes_section, 1)

        # Divider
        divider = QFrame()
        divider.setObjectName("sectionDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # ── Todo section (lower half) ──
        todo_section = QVBoxLayout()
        todo_section.setSpacing(8)

        todo_header = QHBoxLayout()
        todo_label = QLabel("✅ 待办事项")
        todo_label.setObjectName("sectionLabel")
        todo_header.addWidget(todo_label)
        todo_header.addStretch()
        todo_section.addLayout(todo_header)

        # Todo input row: text + add button
        input_row = QHBoxLayout()
        input_row.setSpacing(4)

        self._todo_input = QLineEdit()
        self._todo_input.setObjectName("todoInput")
        self._todo_input.setPlaceholderText("输入待办事项...")
        self._todo_input.returnPressed.connect(self._add_todo)
        input_row.addWidget(self._todo_input, 1)

        add_btn = QPushButton("添加")
        add_btn.setObjectName("todoAddBtn")
        add_btn.clicked.connect(self._add_todo)
        input_row.addWidget(add_btn)

        todo_section.addLayout(input_row)

        # Time settings (collapsible)
        self._time_settings_widget = QWidget()
        self._time_settings_widget.setObjectName("timeSettingsWidget")
        time_settings_layout = QVBoxLayout(self._time_settings_widget)
        time_settings_layout.setContentsMargins(0, 4, 0, 4)
        time_settings_layout.setSpacing(6)

        # Toggle button for date/time
        time_toggle_layout = QHBoxLayout()
        time_toggle_layout.setContentsMargins(0, 0, 0, 0)
        time_toggle_layout.setSpacing(6)
        self._time_toggle_btn = QPushButton("截止时间 ▼")
        self._time_toggle_btn.setObjectName("timeToggleBtn")
        self._time_toggle_btn.setCheckable(True)
        self._time_toggle_btn.setChecked(False)
        self._time_toggle_btn.clicked.connect(self._toggle_time_settings)
        time_toggle_layout.addWidget(self._time_toggle_btn)
        time_toggle_layout.addStretch()
        time_settings_layout.addLayout(time_toggle_layout)

        # Date/time picker (hidden by default)
        self._time_picker_widget = QWidget()
        self._time_picker_widget.setObjectName("timePickerWidget")
        self._time_picker_widget.hide()
        picker_layout = QHBoxLayout(self._time_picker_widget)
        picker_layout.setContentsMargins(0, 0, 0, 0)
        picker_layout.setSpacing(4)

        self._todo_datetime = QDateTimeEdit()
        self._todo_datetime.setObjectName("todoDateTime")
        self._todo_datetime.setCalendarPopup(True)
        self._todo_datetime.setDateTime(datetime.now())
        self._todo_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        self._todo_datetime.setToolTip("选择截止日期和时间")
        self._todo_datetime.setMinimumDate(QDate(2020, 1, 1))
        picker_layout.addWidget(self._todo_datetime)

        # Quick preset buttons for common times
        self._time_preset_combo = QComboBox()
        self._time_preset_combo.setObjectName("timePresetCombo")
        self._time_preset_combo.addItem("快捷选择")
        self._time_preset_combo.addItem("今天 18:00")
        self._time_preset_combo.addItem("今天 21:00")
        self._time_preset_combo.addItem("明天 09:00")
        self._time_preset_combo.addItem("明天 18:00")
        self._time_preset_combo.addItem("后天 09:00")
        self._time_preset_combo.addItem("下周一 09:00")
        self._time_preset_combo.addItem("3天后 18:00")
        self._time_preset_combo.setCurrentIndex(0)
        self._time_preset_combo.currentIndexChanged.connect(self._on_time_preset_selected)
        picker_layout.addWidget(self._time_preset_combo)
        picker_layout.addStretch()

        time_settings_layout.addWidget(self._time_picker_widget)
        todo_section.addWidget(self._time_settings_widget)

        # Todo list scroll
        self._todo_scroll = QScrollArea()
        self._todo_scroll.setObjectName("todoScroll")
        self._todo_scroll.setWidgetResizable(True)
        self._todo_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 彻底消除 QScrollArea viewport 默认灰色背景（QPalette::Base 填充）
        self._todo_scroll.viewport().setAutoFillBackground(False)
        todo_vp_pal = self._todo_scroll.viewport().palette()
        todo_vp_pal.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        self._todo_scroll.viewport().setPalette(todo_vp_pal)
        self._todo_list_widget = QWidget()
        self._todo_list_widget.setObjectName("todoListWidget")
        self._todo_list_widget.setAutoFillBackground(False)
        self._todo_list_widget.setStyleSheet("background: transparent;")
        self._todo_list_layout = QVBoxLayout(self._todo_list_widget)
        self._todo_list_layout.setContentsMargins(0, 2, 0, 0)
        self._todo_list_layout.setSpacing(4)
        self._todo_list_layout.addStretch()
        self._todo_scroll.setWidget(self._todo_list_widget)
        todo_section.addWidget(self._todo_scroll, 1)

        layout.addLayout(todo_section, 1)

        return body

    def _create_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setFixedHeight(42)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(4)

        # Hamburger (sidebar toggle)
        self._sidebar_toggle_btn = QPushButton("☰")
        self._sidebar_toggle_btn.setObjectName("footerBtn")
        self._sidebar_toggle_btn.setFixedSize(32, 32)
        self._sidebar_toggle_btn.setToolTip("展开侧栏")
        self._sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)

        layout.addWidget(self._sidebar_toggle_btn)
        layout.addStretch()

        # Opacity button
        self._opacity_btn = QPushButton("💧")
        self._opacity_btn.setObjectName("footerBtn")
        self._opacity_btn.setFixedSize(32, 32)
        self._opacity_btn.setToolTip("调整透明度")
        self._opacity_btn.clicked.connect(self._toggle_opacity_panel)

        # Settings button
        self._settings_btn = QPushButton("🎨")
        self._settings_btn.setObjectName("footerBtn")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setToolTip("主题颜色")
        self._settings_btn.clicked.connect(self._toggle_settings_panel)

        layout.addWidget(self._opacity_btn)
        layout.addWidget(self._settings_btn)

        return footer

    def _create_popups(self, parent: QWidget):
        """Create settings and opacity popup panels anchored to parent."""
        # Settings / Theme panel
        self._settings_popup = QFrame(parent)
        self._settings_popup.setObjectName("settingsPopup")
        self._settings_popup.setFixedSize(220, 150)
        self._settings_popup.hide()

        sp_layout = QVBoxLayout(self._settings_popup)
        sp_layout.setContentsMargins(14, 12, 14, 12)
        sp_layout.setSpacing(8)

        # Header row with title + close button
        sp_header = QHBoxLayout()
        sp_header.setContentsMargins(0, 0, 0, 0)
        sp_title = QLabel("🎨 主题颜色")
        sp_title.setObjectName("popupTitle")
        sp_close = QPushButton("×")
        sp_close.setObjectName("popupCloseBtn")
        sp_close.setFixedSize(20, 20)
        sp_close.clicked.connect(self._settings_popup.hide)
        sp_header.addWidget(sp_title)
        sp_header.addStretch()
        sp_header.addWidget(sp_close)
        sp_layout.addLayout(sp_header)

        color_grid = QHBoxLayout()
        color_grid.setSpacing(8)
        self._theme_swatches: List[QPushButton] = []
        for i, t in enumerate(THEMES):
            sw = QPushButton()
            sw.setObjectName(f"themeSwatch_{i}")
            sw.setFixedSize(28, 28)
            sw.setToolTip(t["label"])
            sw.setStyleSheet(
                f"QPushButton {{ background-color: {t['bg']}; border: 2px solid {t['border']}; "
                f"border-radius: 14px; }}"
                f"QPushButton:hover {{ transform: scale(1.15); }}"
            )
            sw.clicked.connect(lambda checked, idx=i: self._apply_theme_index(idx))
            self._theme_swatches.append(sw)
            color_grid.addWidget(sw)
        sp_layout.addLayout(color_grid)
        self._popup_active_theme_label = QLabel("当前: 暖阳")
        self._popup_active_theme_label.setObjectName("popupSubtitle")
        sp_layout.addWidget(self._popup_active_theme_label)

        # Opacity panel
        self._opacity_popup = QFrame(parent)
        self._opacity_popup.setObjectName("opacityPopup")
        self._opacity_popup.setFixedSize(190, 100)
        self._opacity_popup.hide()

        op_layout = QVBoxLayout(self._opacity_popup)
        op_layout.setContentsMargins(14, 12, 14, 12)
        op_layout.setSpacing(6)

        op_header = QHBoxLayout()
        op_header.setContentsMargins(0, 0, 0, 0)
        op_title = QLabel("💧 窗口透明度")
        op_title.setObjectName("popupTitle")
        op_close = QPushButton("×")
        op_close.setObjectName("popupCloseBtn")
        op_close.setFixedSize(20, 20)
        op_close.clicked.connect(self._opacity_popup.hide)
        op_header.addWidget(op_title)
        op_header.addStretch()
        op_header.addWidget(op_close)
        op_layout.addLayout(op_header)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setObjectName("opacitySlider")
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        op_layout.addWidget(self._opacity_slider)

        self._opacity_value_label = QLabel("100%")
        self._opacity_value_label.setObjectName("popupSubtitle")
        self._opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        op_layout.addWidget(self._opacity_value_label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        # Reposition overlay and sidebar
        self._sidebar_overlay.setGeometry(0, 0, w, h)
        self._sidebar.setFixedHeight(h)
        # Reposition popups relative to bottom-right
        self._position_popups()

    def _position_popups(self):
        w, h = self.width(), self.height()
        self._settings_popup.move(w - 240, h - 95)
        self._opacity_popup.move(w - 200, h - 95)

    # ─── Theme ───────────────────────────────────────────────

    def _apply_theme(self):
        self._apply_theme_index(self._current_theme_index)

    def _apply_theme_index(self, idx: int):
        self._current_theme_index = idx
        t = THEMES[idx]

        # Main window stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: transparent; }}
            #centralWidget {{
                background-color: {t['bg']};
                border-radius: 14px;
            }}
            #titleBar {{
                background-color: {t['bg']};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom: none;
            }}
            QLabel#titleIcon {{ color: {t['accent']}; font-size: 14px; }}
            QLabel#titleLabel {{
                color: {t['text']}; font-size: 13px; font-weight: 700;
            }}
            QPushButton#titlePinBtn {{
                background: transparent; border: none; border-radius: 8px;
                color: {t['textLight']}; font-size: 14px;
            }}
            QPushButton#titlePinBtn:hover {{ background: rgba(0,0,0,0.07); }}
            QPushButton#titlePinBtn:checked {{ color: {t['accent']}; background: {t['accent']}20; }}
            QPushButton#titleWinBtn {{
                background: transparent; border: none; border-radius: 8px;
                color: {t['textLight']}; font-size: 13px; font-weight: bold;
            }}
            QPushButton#titleWinBtn:hover {{ background: rgba(0,0,0,0.07); }}
            QPushButton#titleCloseBtn {{
                background: transparent; border: none; border-radius: 8px;
                color: {t['textLight']}; font-size: 14px; font-weight: bold;
            }}
            QPushButton#titleCloseBtn:hover {{ background: #e74c3c; color: #fff; }}

            #bodyWidget {{ background-color: transparent; }}

            QLabel#sectionLabel {{
                color: {t['text']}; font-size: 11px; font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QPushButton#addNoteBtn {{
                border: 1.5px dashed {t['border']}; border-radius: 8px;
                background: transparent; color: {t['textLight']}; font-size: 13px;
            }}
            QPushButton#addNoteBtn:hover {{
                border-color: {t['accent']}; color: {t['accent']};
                background: {t['accent']}10;
            }}

            #sectionDivider {{
                background-color: {t['border']}; margin: 0 2px;
            }}

            QScrollArea#notesScroll, QScrollArea#todoScroll {{
                border: none; background: transparent;
            }}
            QScrollArea#notesScroll > QWidget, QScrollArea#todoScroll > QWidget {{
                background: transparent; border: none;
            }}

            QLineEdit#todoInput {{
                background-color: {t['card']}; color: {t['text']};
                border: 1.5px solid {t['border']}; border-radius: 8px;
                padding: 7px 12px; font-size: 12px;
            }}
            QLineEdit#todoInput:focus {{ border-color: {t['accent']}; }}

            QDateTimeEdit#todoDateTime {{
                background-color: {t['card']}; color: {t['text']};
                border: 1.5px solid {t['border']}; border-radius: 8px;
                padding: 4px 6px; font-size: 11px; min-width: 140px;
            }}
            QDateTimeEdit#todoDateTime:focus {{ border-color: {t['accent']}; }}
            QDateTimeEdit#todoDateTime::drop-down {{
                border: none; width: 18px;
            }}

            QComboBox#timePresetCombo {{
                background-color: {t['card']}; color: {t['text']};
                border: 1.5px solid {t['border']}; border-radius: 8px;
                padding: 4px 6px; font-size: 11px; min-width: 90px;
            }}
            QComboBox#timePresetCombo:focus {{ border-color: {t['accent']}; }}
            QComboBox#timePresetCombo::drop-down {{
                border: none; width: 18px;
            }}
            QComboBox#timePresetCombo QAbstractItemView {{
                background-color: {t['card']}; color: {t['text']};
                selection-background-color: {t['accent']};
                border: 1px solid {t['border']}; border-radius: 4px;
            }}

            QPushButton#todoAddBtn {{
                background-color: {t['accent']}; color: {t['text']};
                border: none; border-radius: 8px;
                padding: 7px 14px; font-size: 12px; font-weight: 700;
            }}
            QPushButton#todoAddBtn:hover {{
                background-color: {t['dark']}; color: {t['text']};
                box-shadow: 0 4px 14px {t['accent']}44;
            }}

            QPushButton#timeToggleBtn {{
                background: transparent; border: 1px solid {t['border']};
                border-radius: 6px; color: {t['textLight']};
                font-size: 10px; padding: 3px 8px;
            }}
            QPushButton#timeToggleBtn:hover {{
                border-color: {t['accent']}; color: {t['accent']};
                background: {t['accent']}08;
            }}
            QPushButton#timeToggleBtn:checked {{
                color: {t['accent']}; border-color: {t['accent']};
                background: {t['accent']}12;
            }}

            QLabel#todoTimeTag {{
                font-size: 10px; padding: 1px 7px;
                border-radius: 4px;
                background: {t['accent']}18; color: {t['accent']};
                font-weight: 600;
            }}
            QLabel#todoTimeTag[overdue="true"] {{
                background: #e74c3c22; color: #e74c3c;
            }}

            #footerBar {{
                background-color: {t['bg']};
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border-top: none;
            }}
            QPushButton#footerBtn {{
                background: transparent; border: none; border-radius: 8px;
                color: {t['textLight']}; font-size: 14px;
            }}
            QPushButton#footerBtn:hover {{ background: rgba(0,0,0,0.07); color: {t['text']}; }}

            #noteCard {{
                background-color: {t['card']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            #noteCard:hover {{
                box-shadow: 0 3px 12px rgba(0,0,0,0.1);
            }}
            QLabel#cardTitle {{
                color: {t['text']}; font-size: 11px; font-weight: 700;
            }}
            QLabel#cardPreview {{
                color: {t['textLight']}; font-size: 10px;
            }}
            QPushButton#cardDeleteBtn {{
                background: transparent; border: none; border-radius: 10px;
                color: {t['textLight']}; font-size: 12px;
            }}
            QPushButton#cardDeleteBtn:hover {{
                background: rgba(231,76,60,0.12); color: #e74c3c;
            }}

            #todoItem {{
                background-color: {t['todoBg']}; border-radius: 8px;
            }}
            #todoItem:hover {{ background-color: {t['dark']}; }}
            QCheckBox#todoCheck::indicator {{
                width: 18px; height: 18px; border-radius: 10px;
                border: 2px solid {t['border']};
                background: transparent;
            }}
            QCheckBox#todoCheck::indicator:checked {{
                background: {t['accent']}; border-color: {t['accent']};
            }}
            QLabel#todoContent {{
                color: {t['text']}; font-size: 12px;
            }}
            QPushButton#todoEditBtn {{
                background: transparent; border: none; color: {t['textLight']}; font-size: 13px;
            }}
            QPushButton#todoEditBtn:hover {{ color: {t['accent']}; }}
            QPushButton#todoDelBtn {{
                background: transparent; border: none; color: {t['textLight']}; font-size: 14px; font-weight: bold;
            }}
            QPushButton#todoDelBtn:hover {{ color: #e74c3c; }}

            #settingsPopup, #opacityPopup {{
                background-color: {t['card']};
                border: 1px solid {t['border']};
                border-radius: 12px;
                box-shadow: 0 10px 36px rgba(0,0,0,0.15);
            }}
            QLabel#popupTitle {{
                color: {t['text']}; font-size: 11px; font-weight: 700;
            }}
            QLabel#popupSubtitle {{
                color: {t['textLight']}; font-size: 10px;
            }}
            QPushButton#popupCloseBtn {{
                background: transparent; border: none;
                color: {t['textLight']}; font-size: 14px; font-weight: bold;
                border-radius: 10px;
            }}
            QPushButton#popupCloseBtn:hover {{
                background-color: {t['border']}; color: #e74c3c;
            }}
            #opacitySlider::groove:horizontal {{
                height: 5px; background: {t['border']}; border-radius: 3px;
            }}
            #opacitySlider::handle:horizontal {{
                width: 14px; height: 14px; background: {t['accent']};
                margin: -5px 0; border-radius: 7px;
            }}
        """)

        # Also theme sidebar
        self._sidebar.apply_theme(t)

        # Update swatch markers
        for i, sw in enumerate(self._theme_swatches):
            if i == idx:
                sw.setStyleSheet(
                    f"QPushButton {{ background-color: {THEMES[i]['bg']}; border: 3px solid {t['accent']}; "
                    f"border-radius: 14px; box-shadow: 0 0 0 2px {t['bg']}; }}"
                )
            else:
                sw.setStyleSheet(
                    f"QPushButton {{ background-color: {THEMES[i]['bg']}; border: 2px solid {THEMES[i]['border']}; "
                    f"border-radius: 14px; }}"
                )
        self._popup_active_theme_label.setText(f"当前: {t['label']}")

    # ─── Sidebar Toggle ──────────────────────────────────────

    def _toggle_sidebar(self):
        is_open = self._sidebar.x() >= 0
        if is_open:
            self._animate_sidebar_close()
        else:
            self._update_sidebar_data()
            self._animate_sidebar_open()

    def _animate_sidebar_open(self):
        if hasattr(self, '_sidebar_anim_timer') and self._sidebar_anim_timer.isActive():
            self._sidebar_anim_timer.stop()
        self._sidebar_overlay.show()
        self._sidebar_overlay.raise_()
        self._sidebar.show()
        self._sidebar.raise_()
        self._sidebar_anim_target = 0
        self._sidebar_anim_step = 15
        self._sidebar_anim_timer = QTimer(self)
        self._sidebar_anim_timer.timeout.connect(self._anim_sidebar_step)
        self._sidebar_anim_timer.start(10)

    def _animate_sidebar_close(self):
        if hasattr(self, '_sidebar_anim_timer') and self._sidebar_anim_timer.isActive():
            self._sidebar_anim_timer.stop()
        self._sidebar_anim_target = -270
        self._sidebar_anim_step = -15
        self._sidebar_anim_timer = QTimer(self)
        self._sidebar_anim_timer.timeout.connect(self._anim_sidebar_step)
        self._sidebar_anim_timer.start(10)

    def _anim_sidebar_step(self):
        x = self._sidebar.x() + self._sidebar_anim_step
        if self._sidebar_anim_step > 0:
            if x >= self._sidebar_anim_target:
                x = self._sidebar_anim_target
                self._sidebar_anim_timer.stop()
        else:
            if x <= self._sidebar_anim_target:
                x = self._sidebar_anim_target
                self._sidebar_anim_timer.stop()
                self._sidebar.hide()
                self._sidebar_overlay.hide()
        self._sidebar.move(x, 0)

    def _update_sidebar_data(self):
        notes = self.db.get_all_notes()
        for n in notes:
            content = self.db.get_note_content(n.id)
            preview = content.get("content", "").strip()[:50]
            setattr(n, '_content_preview', preview)
        active = self.db.get_active_todos()
        history = self.db.get_completed_todos()
        self._sidebar.set_data(notes, active, history)

    def _on_sidebar_view_changed(self, view: str):
        """When user clicks a nav item in sidebar, optionally scroll to that section."""
        pass

    # ─── Popup Panels ────────────────────────────────────────

    def _toggle_settings_panel(self):
        self._opacity_popup.hide()
        if self._settings_popup.isVisible():
            self._settings_popup.hide()
        else:
            self._position_popups()
            self._settings_popup.raise_()
            self._settings_popup.show()

    def _toggle_opacity_panel(self):
        self._settings_popup.hide()
        if self._opacity_popup.isVisible():
            self._opacity_popup.hide()
        else:
            self._position_popups()
            self._opacity_popup.raise_()
            self._opacity_popup.show()

    def _on_opacity_changed(self, value: int):
        self._windows_opacity = value
        self.setWindowOpacity(value / 100.0)
        self._opacity_value_label.setText(f"{value}%")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = event.globalPosition().toPoint()
            if self._settings_popup.isVisible():
                if not self._settings_popup.rect().contains(self._settings_popup.mapFromGlobal(pos)) \
                   and not self._settings_btn.rect().contains(self._settings_btn.mapFromGlobal(pos)):
                    self._settings_popup.hide()
            if self._opacity_popup.isVisible():
                if not self._opacity_popup.rect().contains(self._opacity_popup.mapFromGlobal(pos)) \
                   and not self._opacity_btn.rect().contains(self._opacity_btn.mapFromGlobal(pos)):
                    self._opacity_popup.hide()
        if obj.objectName() == "titleBar":
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._is_dragging = True
                    self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif event.type() == QEvent.Type.MouseMove:
                if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                    self.move(event.globalPosition().toPoint() - self._drag_position)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._is_dragging = False
        return super().eventFilter(obj, event)

    # ─── Title Bar Drag (via eventFilter) ──────────────────

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False
        super().mouseReleaseEvent(event)

    def _toggle_pin(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._enable_native_resize()
        self.show()

    # ─── Data Loading ────────────────────────────────────────

    def _load_data(self):
        notes = self.db.get_all_notes()
        for note in notes:
            self._add_note_card(note)

        todos = self.db.get_active_todos()
        self._rebuild_todo_list(todos)

    def _add_note_card(self, note: Note):
        card = NoteCard(note)
        card.clicked.connect(self._edit_note)
        card.deleted.connect(self._delete_note)
        content = self.db.get_note_content(note.id)
        card.update_preview(content.get("content", ""))
        # Insert before stretch
        self._notes_grid.insertWidget(self._notes_grid.count() - 1, card)

    def _rebuild_todo_list(self, todos: list):
        """Clear and rebuild todo list."""
        while self._todo_list_layout.count() > 1:  # keep stretch
            item = self._todo_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for t in todos:
            self._add_todo_widget(t)

    def _add_todo_widget(self, todo: Todo):
        item = TodoItem(todo)
        item.toggled.connect(self._toggle_todo)
        item.deleted.connect(self._delete_todo)
        item.edited.connect(self._edit_todo)
        self._todo_list_layout.insertWidget(self._todo_list_layout.count() - 1, item)

    def _delete_history_todo(self, todo_id: int):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该历史待办吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_todo(todo_id)
        self._update_sidebar_data()

    def _refresh_note_grid(self):
        """Clear and rebuild entire note grid."""
        while self._notes_grid.count() > 1:
            item = self._notes_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        notes = self.db.get_all_notes()
        for note in notes:
            self._add_note_card(note)

    # ─── Note Operations ─────────────────────────────────────

    def _add_note(self):
        note = self.db.create_note()
        self._add_note_card(note)
        self._edit_note(note.id)

    def _edit_note(self, note_id: int):
        note = self.db.get_note(note_id)
        if not note:
            return
        content = self.db.get_note_content(note_id)
        from src.utils import get_data_dir
        editor = NoteEditor(note.title, content.get("content", ""), self, get_data_dir(), theme=THEMES[self._current_theme_index])
        icon_path = self._get_icon_path()
        if icon_path:
            editor.setWindowIcon(QIcon(icon_path))
        if editor.exec() == NoteEditor.DialogCode.Accepted:
            note.title = editor.get_title()
            self.db.save_note_content(note_id, editor.get_content())
            self.db.save_note_html(note_id, editor.get_html(), editor.get_inserted_images())
            self.db.update_note(note)
            self._refresh_note_grid()

    def _delete_note(self, note_id: int):
        reply = QMessageBox.question(self, "确认删除", "确定要删除便签吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_note(note_id)
        self._refresh_note_grid()

    # ─── Todo Operations ─────────────────────────────────────

    def _toggle_time_settings(self):
        """Toggle visibility of date/time picker."""
        if self._time_toggle_btn.isChecked():
            self._time_picker_widget.show()
            self._time_toggle_btn.setText("截止时间 ▲")
        else:
            self._time_picker_widget.hide()
            self._time_toggle_btn.setText("截止时间 ▼")

    def _on_time_preset_selected(self, index: int):
        """Apply quick time preset to the datetime picker."""
        if index <= 0:
            return
        now = datetime.now()
        from PySide6.QtCore import QDateTime
        preset_map = {
            1: QDateTime(now.year, now.month, now.day, 18, 0),          # 今天 18:00
            2: QDateTime(now.year, now.month, now.day, 21, 0),          # 今天 21:00
            3: None,  # 明天 09:00
            4: None,  # 明天 18:00
            5: None,  # 后天 09:00
            6: None,  # 下周一 09:00
            7: None,  # 3天后 18:00
        }
        # Compute relative dates
        from datetime import timedelta
        tomorrow = now + timedelta(days=1)
        day_after = now + timedelta(days=2)
        three_days = now + timedelta(days=3)
        # Next Monday
        days_ahead = 7 - now.weekday() if now.weekday() > 0 else 7
        next_monday = now + timedelta(days=days_ahead)

        preset_map[3] = QDateTime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 0)
        preset_map[4] = QDateTime(tomorrow.year, tomorrow.month, tomorrow.day, 18, 0)
        preset_map[5] = QDateTime(day_after.year, day_after.month, day_after.day, 9, 0)
        preset_map[6] = QDateTime(next_monday.year, next_monday.month, next_monday.day, 9, 0)
        preset_map[7] = QDateTime(three_days.year, three_days.month, three_days.day, 18, 0)

        qdt = preset_map.get(index)
        if qdt:
            self._todo_datetime.setDateTime(qdt)
        # Reset combo to placeholder
        self._time_preset_combo.blockSignals(True)
        self._time_preset_combo.setCurrentIndex(0)
        self._time_preset_combo.blockSignals(False)

    def _add_todo(self):
        content = self._todo_input.text().strip()
        if not content:
            return

        # Use datetime only if time settings is expanded
        if self._time_toggle_btn.isChecked():
            dt = self._todo_datetime.dateTime()
            due_date = dt.toString("yyyy-MM-dd HH:mm:ss")
        else:
            due_date = None

        todo = self.db.create_todo(content, due_date=due_date)
        self._todo_input.clear()
        
        # Collapse time settings after adding
        if self._time_toggle_btn.isChecked():
            self._time_toggle_btn.setChecked(False)
            self._time_picker_widget.hide()
            self._time_toggle_btn.setText("截止时间 ▼")
        
        todos = self.db.get_active_todos()
        self._rebuild_todo_list(todos)

    def _edit_todo(self, todo: Todo):
        """Populate input fields with todo data for re-editing."""
        self._todo_input.setText(todo.content)
        if todo.due_date:
            try:
                d = datetime.strptime(todo.due_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    d = datetime.strptime(todo.due_date, "%Y-%m-%d")
                except ValueError:
                    d = datetime.now()
            self._todo_datetime.setDateTime(d)
            # Expand time settings so user can see/adjust the date
            self._time_toggle_btn.setChecked(True)
            self._time_picker_widget.show()
            self._time_toggle_btn.setText("截止时间 ▲")
        else:
            self._todo_datetime.setDateTime(datetime.now())
        self.db.delete_todo(todo.id)
        self._todo_input.setFocus()

    def _toggle_todo(self, todo_id: int, is_done: bool):
        self.db.toggle_todo(todo_id, is_done)
        todos = self.db.get_active_todos()
        self._rebuild_todo_list(todos)

    def _delete_todo(self, todo_id: int):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该待办事项吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_todo(todo_id)
        todos = self.db.get_active_todos()
        self._rebuild_todo_list(todos)

    # ─── Reminder ────────────────────────────────────────────

    def _start_reminder_checker(self):
        self._reminder_checker = ReminderChecker(self.db, check_interval_ms=60000, parent=self)
        self._reminder_checker.reminder_triggered.connect(self._on_reminder_triggered)
        if self._settings.get("reminder_enabled", True):
            self._reminder_checker.start()

    def _on_reminder_triggered(self, todo: Todo):
        send_notification("待办提醒", f"{todo.content}\n截止: {todo.due_date or '无'}")

    # ─── Show ────────────────────────────────────────────────

    def show(self):
        super().show()
