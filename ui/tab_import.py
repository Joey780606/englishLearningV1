from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QCheckBox, QGroupBox,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from ui.widgets.vocab_table_widget import VocabTableWidget
from models.data_models import VocabularyEntry
from database import db_manager
from core import csv_manager


class ImportWorker(QObject):
    """背景執行緒 Worker：執行字幕下載 → 詞彙分類 → 批次翻譯"""

    ProgressUpdated = Signal(int, int, str)   # current, total, message
    Finished        = Signal(list)             # list[VocabularyEntry]
    ErrorOccurred   = Signal(str)             # error message

    def __init__(self, YoutubeUrl: str, SelectedLevels: list[str]):
        super().__init__()
        self._Url    = YoutubeUrl
        self._Levels = SelectedLevels

    def run(self):
        """執行三階段匯入流程"""
        try:
            # 階段一：下載字幕
            self.ProgressUpdated.emit(0, 0, "正在下載字幕...")
            from core.youtube_extractor import extractSubtitles, SubtitleNotFoundError
            try:
                Sentences = extractSubtitles(self._Url)
            except SubtitleNotFoundError as E:
                self.ErrorOccurred.emit(str(E))
                return
            except RuntimeError as E:
                self.ErrorOccurred.emit(str(E))
                return

            if not Sentences:
                self.ErrorOccurred.emit("未能擷取到任何字幕內容。")
                return

            # 階段二：詞彙分類
            self.ProgressUpdated.emit(0, 0, f"正在分析詞彙（共 {len(Sentences)} 句）...")
            from core.vocab_classifier import loadCefrWordlist, extractVocabulary, filterByLevel
            Wordlist = loadCefrWordlist()
            Entries  = extractVocabulary(Sentences, Wordlist)
            if self._Levels:
                Entries = filterByLevel(Entries, self._Levels)

            if not Entries:
                self.ErrorOccurred.emit("未從字幕中找到符合條件的詞彙。\n請確認影片有英文字幕，或嘗試降低等級篩選條件。")
                return

            # 階段三：批次翻譯
            self.ProgressUpdated.emit(0, len(Entries), f"正在翻譯 {len(Entries)} 個詞彙...")

            def OnProgress(Current, Total):
                self.ProgressUpdated.emit(Current, Total, f"翻譯中... ({Current}/{Total})")

            from core.translator import translateBatch
            Entries = translateBatch(Entries, OnProgress)

            self.Finished.emit(Entries)

        except Exception as E:
            self.ErrorOccurred.emit(f"匯入過程發生錯誤：{E}")


class ImportTab(QWidget):
    """Tab 1：YouTube 字幕匯入分頁"""

    VocabularySaved = Signal()   # 儲存完成時通知主視窗
    StatusMessage   = Signal(str)  # 轉發狀態訊息至主視窗狀態列

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._CurrentEntries: list[VocabularyEntry] = []
        self._Thread = None
        self._Worker = None
        self._setupUI()

    def _setupUI(self):
        """建立分頁 UI"""
        Layout = QVBoxLayout(self)
        Layout.setSpacing(10)
        Layout.setContentsMargins(16, 16, 16, 16)

        # ── URL 輸入區 ──
        UrlGroup = QGroupBox("YouTube 網址")
        UrlLayout = QHBoxLayout(UrlGroup)

        self._UrlInput = QLineEdit()
        self._UrlInput.setPlaceholderText("貼上 YouTube 網址，例如：https://www.youtube.com/watch?v=...")
        self._UrlInput.returnPressed.connect(self._onExtractClicked)

        self._ExtractBtn = QPushButton("擷取字幕")
        self._ExtractBtn.setFixedWidth(100)
        self._ExtractBtn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 6px; }")
        self._ExtractBtn.clicked.connect(self._onExtractClicked)

        UrlLayout.addWidget(self._UrlInput)
        UrlLayout.addWidget(self._ExtractBtn)
        Layout.addWidget(UrlGroup)

        # ── 進度條 & 狀態訊息 ──
        self._ProgressBar = QProgressBar()
        self._ProgressBar.setVisible(False)
        self._ProgressBar.setTextVisible(True)
        Layout.addWidget(self._ProgressBar)

        self._StatusLabel = QLabel("")
        self._StatusLabel.setStyleSheet("color: #666666;")
        Layout.addWidget(self._StatusLabel)

        # ── CEFR 篩選 ──
        FilterGroup = QGroupBox("篩選 CEFR 等級")
        FilterLayout = QHBoxLayout(FilterGroup)
        self._LevelCheckboxes = {}
        for Level, Color in [("B1", "#4CAF50"), ("B2", "#2196F3"), ("C1", "#FF9800"), ("C2", "#F44336")]:
            Cb = QCheckBox(Level)
            Cb.setChecked(True)
            Cb.setStyleSheet(f"QCheckBox {{ color: {Color}; font-weight: bold; }}")
            FilterLayout.addWidget(Cb)
            self._LevelCheckboxes[Level] = Cb
        FilterLayout.addStretch()
        Layout.addWidget(FilterGroup)

        # ── 預覽表格 ──
        self._PreviewLabel = QLabel("預覽結果（尚未擷取）")
        self._PreviewLabel.setStyleSheet("font-weight: bold;")
        Layout.addWidget(self._PreviewLabel)

        self._TableWidget = VocabTableWidget(ReadOnly=True)
        Layout.addWidget(self._TableWidget, stretch=1)

        # ── 底部操作按鈕 ──
        BtnLayout = QHBoxLayout()
        BtnLayout.addStretch()

        self._SaveBtn = QPushButton("儲存到資料庫")
        self._SaveBtn.setEnabled(False)
        self._SaveBtn.setStyleSheet("QPushButton:enabled { background-color: #4CAF50; color: white; padding: 6px 16px; }")
        self._SaveBtn.clicked.connect(self._onSaveClicked)

        self._ExportBtn = QPushButton("匯出 CSV")
        self._ExportBtn.setEnabled(False)
        self._ExportBtn.setStyleSheet("QPushButton:enabled { background-color: #FF9800; color: white; padding: 6px 16px; }")
        self._ExportBtn.clicked.connect(self._onExportClicked)

        BtnLayout.addWidget(self._SaveBtn)
        BtnLayout.addWidget(self._ExportBtn)
        Layout.addLayout(BtnLayout)

    def _getSelectedLevels(self) -> list[str]:
        return [Level for Level, Cb in self._LevelCheckboxes.items() if Cb.isChecked()]

    def _onExtractClicked(self):
        """點擊「擷取字幕」按鈕"""
        Url = self._UrlInput.text().strip()
        if not Url:
            QMessageBox.warning(self, "提示", "請先輸入 YouTube 網址。")
            return

        SelectedLevels = self._getSelectedLevels()
        if not SelectedLevels:
            QMessageBox.warning(self, "提示", "請至少選擇一個 CEFR 等級。")
            return

        self._setExtracting(True)
        self._CurrentEntries = []
        self._TableWidget.populate([])
        self._SaveBtn.setEnabled(False)
        self._ExportBtn.setEnabled(False)

        # 建立 Worker + Thread
        self._Thread = QThread()
        self._Worker = ImportWorker(Url, SelectedLevels)
        self._Worker.moveToThread(self._Thread)

        self._Thread.started.connect(self._Worker.run)
        self._Worker.ProgressUpdated.connect(self._onProgressUpdated)
        self._Worker.Finished.connect(self._onImportFinished)
        self._Worker.ErrorOccurred.connect(self._onImportError)
        self._Worker.Finished.connect(self._Thread.quit)
        self._Worker.ErrorOccurred.connect(self._Thread.quit)
        self._Thread.finished.connect(self._Worker.deleteLater)

        self._Thread.start()

    def _onProgressUpdated(self, Current: int, Total: int, Message: str):
        """更新進度條與狀態訊息"""
        self._StatusLabel.setText(Message)
        if Total > 0:
            self._ProgressBar.setRange(0, Total)
            self._ProgressBar.setValue(Current)
        else:
            self._ProgressBar.setRange(0, 0)  # 不確定進度

    def _onImportFinished(self, Entries: list):
        """匯入完成，顯示預覽"""
        self._setExtracting(False)
        self._CurrentEntries = Entries

        self._TableWidget.populate(Entries)
        self._PreviewLabel.setText(f"預覽結果（共 {len(Entries)} 個詞彙）")
        self._StatusLabel.setText(f"擷取完成！找到 {len(Entries)} 個 CEFR 詞彙。")
        self._SaveBtn.setEnabled(True)
        self._ExportBtn.setEnabled(True)
        self.StatusMessage.emit(f"擷取完成：{len(Entries)} 個詞彙")

    def _onImportError(self, ErrorMsg: str):
        """匯入失敗"""
        self._setExtracting(False)
        self._StatusLabel.setText(f"錯誤：{ErrorMsg}")
        QMessageBox.critical(self, "擷取失敗", ErrorMsg)

    def _onSaveClicked(self):
        """儲存詞彙到資料庫"""
        if not self._CurrentEntries:
            return
        try:
            SavedCount = db_manager.saveBatchVocabulary(self._CurrentEntries)
            QMessageBox.information(
                self, "儲存成功",
                f"成功新增 {SavedCount} 個新詞彙到資料庫。\n（重複的詞彙已自動略過）"
            )
            self.VocabularySaved.emit()
            self.StatusMessage.emit(f"已儲存 {SavedCount} 個詞彙")
        except RuntimeError as E:
            QMessageBox.critical(self, "儲存失敗", str(E))

    def _onExportClicked(self):
        """匯出詞彙為 CSV"""
        if not self._CurrentEntries:
            return
        FilePath, _ = QFileDialog.getSaveFileName(
            self, "儲存 CSV", "vocabulary_export.csv", "CSV 檔案 (*.csv)"
        )
        if not FilePath:
            return
        try:
            csv_manager.exportToCsv(self._CurrentEntries, FilePath)
            QMessageBox.information(self, "匯出成功", f"已匯出 {len(self._CurrentEntries)} 個詞彙到：\n{FilePath}")
        except RuntimeError as E:
            QMessageBox.critical(self, "匯出失敗", str(E))

    def _setExtracting(self, IsExtracting: bool):
        """切換擷取中/完成的 UI 狀態"""
        self._ExtractBtn.setEnabled(not IsExtracting)
        self._UrlInput.setEnabled(not IsExtracting)
        self._ProgressBar.setVisible(IsExtracting)
        if not IsExtracting:
            self._ProgressBar.setRange(0, 100)
            self._ProgressBar.setValue(0)
