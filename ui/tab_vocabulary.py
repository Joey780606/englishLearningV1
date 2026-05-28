from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QFileDialog,
    QDialog, QFormLayout, QDialogButtonBox,
    QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal

from ui.widgets.vocab_table_widget import VocabTableWidget
from models.data_models import VocabularyEntry, SentenceEntry
from database import db_manager
from core import csv_manager


class VocabEditDialog(QDialog):
    """詞彙編輯對話框（雙擊表格列時開啟）"""

    def __init__(self, Entry: VocabularyEntry, Parent=None):
        super().__init__(Parent)
        self.setWindowTitle(f"編輯詞彙：{Entry.Word}")
        self.setMinimumWidth(500)
        self._Entry = Entry
        self._setupUI()

    def _setupUI(self):
        Layout = QVBoxLayout(self)

        Form = QFormLayout()
        self._WordEdit   = QLineEdit(self._Entry.Word)
        self._WordEdit.setReadOnly(True)
        self._PosEdit    = QLineEdit(self._Entry.PartOfSpeech)
        self._ZhEdit     = QLineEdit(self._Entry.ChineseTranslation)
        self._LevelEdit  = QComboBox()
        self._LevelEdit.addItems(["B1", "B2", "C1", "C2"])
        self._LevelEdit.setCurrentText(self._Entry.CefrLevel)

        Form.addRow("英文單字：", self._WordEdit)
        Form.addRow("詞性：", self._PosEdit)
        Form.addRow("中文翻譯：", self._ZhEdit)
        Form.addRow("CEFR 等級：", self._LevelEdit)
        Layout.addLayout(Form)

        # 例句編輯區
        SentGroup = QGroupBox("例句（最多 3 個）")
        SentLayout = QVBoxLayout(SentGroup)
        self._SentEdits = []
        for I in range(3):
            Row = QHBoxLayout()
            EnEdit = QLineEdit()
            ZhEdit = QLineEdit()
            EnEdit.setPlaceholderText(f"例句 {I+1} 英文")
            ZhEdit.setPlaceholderText(f"例句 {I+1} 中文翻譯")
            if I < len(self._Entry.Sentences):
                EnEdit.setText(self._Entry.Sentences[I].EnglishSentence)
                ZhEdit.setText(self._Entry.Sentences[I].ChineseSentence)
            Row.addWidget(QLabel(f"{I+1}."))
            Row.addWidget(EnEdit)
            Row.addWidget(ZhEdit)
            SentLayout.addLayout(Row)
            self._SentEdits.append((EnEdit, ZhEdit))
        Layout.addWidget(SentGroup)

        # 確認/取消按鈕
        Buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        Buttons.accepted.connect(self.accept)
        Buttons.rejected.connect(self.reject)
        Layout.addWidget(Buttons)

    def getUpdatedEntry(self) -> VocabularyEntry:
        """回傳使用者編輯後的 VocabularyEntry"""
        Sentences = []
        for EnEdit, ZhEdit in self._SentEdits:
            EnText = EnEdit.text().strip()
            ZhText = ZhEdit.text().strip()
            if EnText:
                Sentences.append(SentenceEntry(EnglishSentence=EnText, ChineseSentence=ZhText))

        return VocabularyEntry(
            WordId=self._Entry.WordId,
            Word=self._Entry.Word,
            PartOfSpeech=self._PosEdit.text().strip(),
            ChineseTranslation=self._ZhEdit.text().strip(),
            CefrLevel=self._LevelEdit.currentText(),
            Sentences=Sentences,
            SourceUrl=self._Entry.SourceUrl,
        )


class VocabularyTab(QWidget):
    """Tab 2：詞彙列表管理分頁"""

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._SearchTimer = QTimer()
        self._SearchTimer.setSingleShot(True)
        self._SearchTimer.setInterval(300)  # debounce 300ms
        self._SearchTimer.timeout.connect(self._doSearch)
        self._setupUI()
        self.refreshTable()

    def _setupUI(self):
        Layout = QVBoxLayout(self)
        Layout.setSpacing(8)
        Layout.setContentsMargins(16, 16, 16, 16)

        # ── 搜尋與篩選列 ──
        FilterLayout = QHBoxLayout()
        FilterLayout.addWidget(QLabel("搜尋："))
        self._SearchEdit = QLineEdit()
        self._SearchEdit.setPlaceholderText("輸入英文或中文關鍵字...")
        self._SearchEdit.textChanged.connect(self._onSearchTextChanged)
        FilterLayout.addWidget(self._SearchEdit)

        FilterLayout.addWidget(QLabel("等級："))
        self._LevelCombo = QComboBox()
        self._LevelCombo.addItems(["全部", "B1", "B2", "C1", "C2"])
        self._LevelCombo.currentTextChanged.connect(self._doSearch)
        FilterLayout.addWidget(self._LevelCombo)

        self._CountLabel = QLabel("共 0 筆")
        self._CountLabel.setStyleSheet("color: #666666;")
        FilterLayout.addWidget(self._CountLabel)
        Layout.addLayout(FilterLayout)

        # ── 主表格 ──
        self._TableWidget = VocabTableWidget(ReadOnly=False)
        self._TableWidget.itemDoubleClicked.connect(self._onRowDoubleClicked)
        Layout.addWidget(self._TableWidget, stretch=1)

        # ── 操作按鈕列 ──
        BtnLayout = QHBoxLayout()

        self._DeleteBtn = QPushButton("刪除選取")
        self._DeleteBtn.setStyleSheet("QPushButton { background-color: #F44336; color: white; padding: 5px 12px; }")
        self._DeleteBtn.clicked.connect(self._onDeleteClicked)

        self._ImportBtn = QPushButton("匯入 CSV")
        self._ImportBtn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 5px 12px; }")
        self._ImportBtn.clicked.connect(self._onImportClicked)

        self._ExportBtn = QPushButton("匯出 CSV")
        self._ExportBtn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; padding: 5px 12px; }")
        self._ExportBtn.clicked.connect(self._onExportClicked)

        BtnLayout.addWidget(self._DeleteBtn)
        BtnLayout.addStretch()
        BtnLayout.addWidget(self._ImportBtn)
        BtnLayout.addWidget(self._ExportBtn)
        Layout.addLayout(BtnLayout)

    def refreshTable(self):
        """從資料庫重新載入詞彙（供外部呼叫）"""
        self._doSearch()

    def _onSearchTextChanged(self):
        """搜尋文字改變時啟動 debounce 計時器"""
        self._SearchTimer.start()

    def _doSearch(self):
        """執行搜尋並刷新表格"""
        try:
            Keyword = self._SearchEdit.text().strip()
            Level   = self._LevelCombo.currentText()

            if Keyword:
                Entries = db_manager.searchVocabulary(Keyword)
                if Level != "全部":
                    Entries = [E for E in Entries if E.CefrLevel == Level]
            else:
                Entries = db_manager.getAllVocabulary(Level)

            self._TableWidget.populate(Entries)
            self._CountLabel.setText(f"共 {len(Entries)} 筆")
        except RuntimeError as E:
            QMessageBox.critical(self, "載入失敗", str(E))

    def _onRowDoubleClicked(self, Item):
        """雙擊列開啟編輯對話框"""
        Row = Item.row()
        IdItem = self._TableWidget.item(Row, VocabTableWidget.COL_ID)
        if not IdItem:
            return
        WordId = IdItem.data(Qt.ItemDataRole.UserRole)
        if WordId is None:
            return

        # 從資料庫取得完整資料
        try:
            AllEntries = db_manager.getAllVocabulary()
            Entry = next((E for E in AllEntries if E.WordId == WordId), None)
            if not Entry:
                return
        except RuntimeError:
            return

        Dialog = VocabEditDialog(Entry, self)
        if Dialog.exec() == QDialog.DialogCode.Accepted:
            UpdatedEntry = Dialog.getUpdatedEntry()
            try:
                db_manager.updateVocabularyEntry(UpdatedEntry)
                self._doSearch()
            except RuntimeError as E:
                QMessageBox.critical(self, "更新失敗", str(E))

    def _onDeleteClicked(self):
        """刪除選取的詞彙"""
        WordIds = self._TableWidget.getSelectedWordIds()
        if not WordIds:
            QMessageBox.information(self, "提示", "請先選取要刪除的詞彙。")
            return

        Reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除選取的 {len(WordIds)} 個詞彙嗎？\n此操作無法復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if Reply != QMessageBox.StandardButton.Yes:
            return

        try:
            for WordId in WordIds:
                db_manager.deleteVocabulary(WordId)
            self._doSearch()
        except RuntimeError as E:
            QMessageBox.critical(self, "刪除失敗", str(E))

    def _onImportClicked(self):
        """從 CSV 匯入詞彙"""
        FilePath, _ = QFileDialog.getOpenFileName(
            self, "選擇 CSV 檔案", "", "CSV 檔案 (*.csv)"
        )
        if not FilePath:
            return
        try:
            Entries = csv_manager.importFromCsv(FilePath)
            SavedCount = db_manager.saveBatchVocabulary(Entries)
            QMessageBox.information(
                self, "匯入成功",
                f"從 CSV 讀取 {len(Entries)} 筆，成功新增 {SavedCount} 個新詞彙。"
            )
            self._doSearch()
        except (RuntimeError, ValueError) as E:
            QMessageBox.critical(self, "匯入失敗", str(E))

    def _onExportClicked(self):
        """匯出目前顯示的詞彙為 CSV"""
        FilePath, _ = QFileDialog.getSaveFileName(
            self, "匯出 CSV", "vocabulary.csv", "CSV 檔案 (*.csv)"
        )
        if not FilePath:
            return
        try:
            Keyword = self._SearchEdit.text().strip()
            Level   = self._LevelCombo.currentText()
            Entries = db_manager.searchVocabulary(Keyword) if Keyword else db_manager.getAllVocabulary(Level)
            csv_manager.exportToCsv(Entries, FilePath)
            QMessageBox.information(self, "匯出成功", f"已匯出 {len(Entries)} 個詞彙。")
        except RuntimeError as E:
            QMessageBox.critical(self, "匯出失敗", str(E))
