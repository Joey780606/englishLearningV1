import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from database.db_manager import initializeDatabase
from core.audio_player import initializePlayer
from ui.main_window import MainWindow


def main():
    """應用程式入口點"""
    # 高 DPI 縮放支援
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    App = QApplication(sys.argv)
    App.setApplicationName("英文單字學習系統")
    App.setStyle("Fusion")

    # 初始化資料庫
    try:
        initializeDatabase()
    except RuntimeError as E:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "初始化失敗", f"資料庫初始化失敗：\n{E}")
        sys.exit(1)

    # 初始化語音播放器
    initializePlayer()

    # 建立主視窗
    Window = MainWindow()
    Window.show()

    sys.exit(App.exec())


if __name__ == "__main__":
    main()
