from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from database import db_manager


class ImportHistoryTab(QWidget):
    """Tab：YouTube 匯入歷史分頁"""

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._setupUI()

    def _setupUI(self):
        """建立分頁 UI"""
        Layout = QVBoxLayout(self)
        Layout.setSpacing(10)
        Layout.setContentsMargins(16, 16, 16, 16)

        # ── 標題列 ──
        TopRow = QHBoxLayout()
        TitleLabel = QLabel("YouTube 匯入歷史")
        TitleLabel.setStyleSheet("font-size: 14px; font-weight: bold;")
        TopRow.addWidget(TitleLabel)
        TopRow.addStretch()

        RefreshBtn = QPushButton("重新整理")
        RefreshBtn.setFixedWidth(90)
        RefreshBtn.clicked.connect(self.refreshTable)
        TopRow.addWidget(RefreshBtn)
        Layout.addLayout(TopRow)

        # ── 說明文字 ──
        HintLabel = QLabel("雙擊網址欄可在瀏覽器開啟影片。")
        HintLabel.setStyleSheet("color: #888888; font-size: 12px;")
        Layout.addWidget(HintLabel)

        # ── 歷史資料表格 ──
        # 欄位：匯入時間 / 影片標題 / YouTube 網址 / 新增單字數
        self._Table = QTableWidget(0, 4)
        self._Table.setHorizontalHeaderLabels(["匯入時間", "影片標題", "YouTube 網址", "新增單字數"])
        Header = self._Table.horizontalHeader()
        Header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        Header.setStretchLastSection(True)
        self._Table.setColumnWidth(0, 150)
        self._Table.setColumnWidth(1, 280)
        self._Table.setColumnWidth(2, 320)

        self._Table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._Table.verticalHeader().setVisible(False)
        self._Table.setAlternatingRowColors(True)
        self._Table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._Table.setSortingEnabled(True)
        self._Table.cellDoubleClicked.connect(self._onCellDoubleClicked)
        Layout.addWidget(self._Table, stretch=1)

        # ── 底部統計 ──
        self._SummaryLabel = QLabel("")
        self._SummaryLabel.setStyleSheet("color: #666666;")
        Layout.addWidget(self._SummaryLabel)

    def refreshTable(self):
        """從資料庫重新載入匯入歷史"""
        try:
            Records = db_manager.getImportHistory()
        except RuntimeError as E:
            QMessageBox.critical(self, "載入失敗", str(E))
            return

        self._Table.setSortingEnabled(False)
        self._Table.setRowCount(0)

        for Record in Records:
            Row = self._Table.rowCount()
            self._Table.insertRow(Row)

            # 匯入時間
            TimeStr = Record.ImportedAt.strftime("%Y-%m-%d %H:%M") if Record.ImportedAt else ""
            self._Table.setItem(Row, 0, QTableWidgetItem(TimeStr))

            # 影片標題
            self._Table.setItem(Row, 1, QTableWidgetItem(Record.VideoTitle))

            # YouTube 網址（存原始 URL，方便雙擊開啟）
            UrlItem = QTableWidgetItem(Record.SourceUrl)
            UrlItem.setToolTip("雙擊以在瀏覽器開啟")
            UrlItem.setForeground(Qt.GlobalColor.blue)
            self._Table.setItem(Row, 2, UrlItem)

            # 新增單字數
            CountItem = QTableWidgetItem(str(Record.WordCount))
            CountItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._Table.setItem(Row, 3, CountItem)

        self._Table.setSortingEnabled(True)
        TotalWords = sum(R.WordCount for R in Records)
        self._SummaryLabel.setText(
            f"共 {len(Records)} 筆匯入記錄，累計新增 {TotalWords} 個單字。"
        )

    def _onCellDoubleClicked(self, Row: int, Col: int):
        """雙擊網址欄時，在預設瀏覽器開啟 YouTube 影片"""
        if Col != 2:
            return
        Item = self._Table.item(Row, 2)
        if Item and Item.text():
            QDesktopServices.openUrl(QUrl(Item.text()))
