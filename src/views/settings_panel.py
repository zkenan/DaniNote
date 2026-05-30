"""Settings panel widget for the sticky notes application."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QFrame):
    """Collapsible settings panel shown at the bottom of the todos view."""

    settings_changed = Signal(dict)  # emits current settings dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._settings = {
            "reminder_enabled": True,
            "reminder_advance_minutes": 10,
            "sound_enabled": True,
            "theme": "dark",
        }
        self._setup_ui()
        self.setMaximumHeight(0)
        self._apply_styles()

    # ── Public API ──────────────────────────────────────────────

    def get_settings(self) -> dict:
        return dict(self._settings)

    def set_settings(self, settings: dict):
        self._settings.update(settings)
        self._sync_ui_from_settings()

    # ── Expand / Collapse ──────────────────────────────────────

    def toggle(self):
        self._expanded = not self._expanded
        self.setMaximumHeight(0 if not self._expanded else 240)
        self.setVisible(self._expanded)
        if self._expanded:
            self._animate_expand()

    def is_expanded(self) -> bool:
        return self._expanded

    def _animate_expand(self):
        """Simple show; Qt layout will handle the resize."""
        self.raise_()

    # ── UI Setup ───────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Row 1: Reminder toggle + advance time
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        self.reminder_check = QCheckBox("启用提醒")
        self.reminder_check.setChecked(self._settings["reminder_enabled"])
        self.reminder_check.toggled.connect(self._on_reminder_toggled)

        row1.addWidget(self.reminder_check)
        row1.addWidget(QLabel("提前提醒："))

        self.advance_combo = QComboBox()
        self.advance_combo.addItems(["5 分钟", "10 分钟", "15 分钟", "30 分钟", "1 小时"])
        # default: 10 minutes → index 1
        self.advance_combo.setCurrentIndex(1)
        self.advance_combo.currentIndexChanged.connect(self._on_advance_changed)
        row1.addWidget(self.advance_combo)
        row1.addStretch()
        layout.addLayout(row1)

        # Row 2: Sound toggle
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        self.sound_check = QCheckBox("提醒声音")
        self.sound_check.setChecked(self._settings["sound_enabled"])
        self.sound_check.toggled.connect(self._on_sound_toggled)
        row2.addWidget(self.sound_check)
        row2.addStretch()
        layout.addLayout(row2)

        # Row 3: Theme selector
        row3 = QHBoxLayout()
        row3.setSpacing(12)

        row3.addWidget(QLabel("主题："))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色", "浅色"])
        self.theme_combo.setCurrentIndex(0)  # dark default
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        row3.addWidget(self.theme_combo)
        row3.addStretch()
        layout.addLayout(row3)
        layout.addStretch()

    def _sync_ui_from_settings(self):
        self.reminder_check.setChecked(self._settings["reminder_enabled"])
        advance_map = {5: 0, 10: 1, 15: 2, 30: 3, 60: 4}
        self.advance_combo.setCurrentIndex(
            advance_map.get(self._settings["reminder_advance_minutes"], 1)
        )
        self.sound_check.setChecked(self._settings["sound_enabled"])
        theme_idx = 0 if self._settings["theme"] == "dark" else 1
        self.theme_combo.setCurrentIndex(theme_idx)

    # ── Signal handlers ────────────────────────────────────────

    def _on_reminder_toggled(self, checked: bool):
        self._settings["reminder_enabled"] = checked
        self.settings_changed.emit(dict(self._settings))

    def _on_advance_changed(self, index: int):
        minutes_map = [5, 10, 15, 30, 60]
        self._settings["reminder_advance_minutes"] = minutes_map[index]
        self.settings_changed.emit(dict(self._settings))

    def _on_sound_toggled(self, checked: bool):
        self._settings["sound_enabled"] = checked
        self.settings_changed.emit(dict(self._settings))

    def _on_theme_changed(self, index: int):
        self._settings["theme"] = "dark" if index == 0 else "light"
        self.settings_changed.emit(dict(self._settings))

    # ── Styles ─────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            SettingsPanel {
                background-color: rgba(24, 24, 37, 0.95);
                border-top: 1px solid rgba(108, 112, 134, 0.4);
                border-radius: 8px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 13px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #6c7086;
                background-color: rgba(49, 50, 68, 0.8);
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QComboBox {
                background-color: rgba(49, 50, 68, 0.8);
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
            }
        """)
