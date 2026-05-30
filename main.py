#!/usr/bin/env python3
"""
DaniNote (张张便签) - Desktop Note Taking Application
Main entry point.
"""

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from version import __version__, __app_name__, __app_name_en__
from src.views.main_window import MainWindow


def main():
    """Application entry point."""
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(__app_name_en__)
        app.setApplicationDisplayName(__app_name__)
        app.setStyle("Fusion")

        # Set app icon
        from PySide6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Create main window (always show on launch)
        window = MainWindow()
        window.show()

        # Start event loop
        return app.exec()

    except Exception as e:
        # Show error dialog
        error_msg = f"程序启动失败:\n\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)

        # Reuse existing QApplication if available, or create new one
        app_instance = QApplication.instance()
        if app_instance is None:
            error_app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "启动错误",
            f"程序启动时发生错误:\n\n{str(e)}\n\n请检查日志文件或联系开发者。",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())