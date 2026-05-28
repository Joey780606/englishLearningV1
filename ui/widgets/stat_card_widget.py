from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StatCardWidget(QFrame):
    """學習進度統計卡片元件（用於 Tab 5）"""

    def __init__(self, Title: str, Value: str = "0", Parent=None):
        super().__init__(Parent)
        self._Title = Title
        self._setupUI(Value)

    def _setupUI(self, InitialValue: str):
        """建立卡片 UI"""
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("""
            StatCardWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(150, 90)

        Layout = QVBoxLayout(self)
        Layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Layout.setSpacing(4)

        # 數值標籤（大字）
        self._ValueLabel = QLabel(InitialValue)
        ValueFont = QFont()
        ValueFont.setPointSize(24)
        ValueFont.setBold(True)
        self._ValueLabel.setFont(ValueFont)
        self._ValueLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ValueLabel.setStyleSheet("color: #333333;")

        # 說明文字（小字）
        self._TitleLabel = QLabel(self._Title)
        TitleFont = QFont()
        TitleFont.setPointSize(10)
        self._TitleLabel.setFont(TitleFont)
        self._TitleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._TitleLabel.setStyleSheet("color: #888888;")

        Layout.addWidget(self._ValueLabel)
        Layout.addWidget(self._TitleLabel)

    def setValue(self, Value: str) -> None:
        """更新顯示的數值"""
        self._ValueLabel.setText(Value)
