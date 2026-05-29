from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from utils.config import CEFR_COLORS
from models.data_models import VocabularyEntry


class VocabTableWidget(QTableWidget):
    """
    可重用的詞彙表格元件。
    Tab 1 使用唯讀預覽模式；Tab 2 使用可互動管理模式。
    """

    # 欄位定義
    COL_ID      = 0   # word_id（隱藏）
    COL_WORD    = 1   # 英文單字
    COL_POS     = 2   # 詞性
    COL_ZH      = 3   # 中文翻譯
    COL_LEVEL   = 4   # CEFR 等級
    COL_SENT1   = 5   # 例句1

    HEADERS = ["ID", "英文單字", "詞性", "中文翻譯", "等級", "例句（第一句）"]

    def __init__(self, ReadOnly: bool = True, Parent=None):
        super().__init__(0, len(self.HEADERS), Parent)
        self._ReadOnly = ReadOnly
        self._setupUI()

    def _setupUI(self):
        """設定表格外觀"""
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.hideColumn(self.COL_ID)

        # 欄寬設定：Interactive 允許使用者拖拉調整，最後一欄 Stretch 填滿剩餘空間
        Header = self.horizontalHeader()
        Header.setSectionResizeMode(self.COL_WORD,  QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(self.COL_POS,   QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(self.COL_ZH,    QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(self.COL_LEVEL, QHeaderView.ResizeMode.Interactive)
        Header.setSectionResizeMode(self.COL_SENT1, QHeaderView.ResizeMode.Stretch)
        Header.setStretchLastSection(True)

        # 初始欄寬
        self.setColumnWidth(self.COL_WORD,  120)
        self.setColumnWidth(self.COL_POS,    60)
        self.setColumnWidth(self.COL_ZH,    160)
        self.setColumnWidth(self.COL_LEVEL,  60)

        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        if self._ReadOnly:
            self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        else:
            self.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)

    def populate(self, Entries: list[VocabularyEntry]) -> None:
        """清空並重新填入詞彙資料"""
        self.setSortingEnabled(False)
        self.setRowCount(0)

        for Entry in Entries:
            Row = self.rowCount()
            self.insertRow(Row)

            # word_id（隱藏，用於後續操作）
            IdItem = QTableWidgetItem(str(Entry.WordId or ""))
            IdItem.setData(Qt.ItemDataRole.UserRole, Entry.WordId)
            self.setItem(Row, self.COL_ID, IdItem)

            # 英文單字
            self.setItem(Row, self.COL_WORD, QTableWidgetItem(Entry.Word))

            # 詞性
            self.setItem(Row, self.COL_POS, QTableWidgetItem(Entry.PartOfSpeech))

            # 中文翻譯
            self.setItem(Row, self.COL_ZH, QTableWidgetItem(Entry.ChineseTranslation))

            # CEFR 等級（帶顏色）
            LevelItem = QTableWidgetItem(Entry.CefrLevel)
            LevelItem.setForeground(QColor("white"))
            BgColor = CEFR_COLORS.get(Entry.CefrLevel, "#999999")
            LevelItem.setBackground(QColor(BgColor))
            LevelItem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(Row, self.COL_LEVEL, LevelItem)

            # 第一個例句
            FirstSent = Entry.Sentences[0].EnglishSentence if Entry.Sentences else ""
            self.setItem(Row, self.COL_SENT1, QTableWidgetItem(FirstSent))

        self.setSortingEnabled(True)

    def getSelectedWordIds(self) -> list[int]:
        """回傳所有選取列的 word_id"""
        WordIds = []
        for Row in self.selectionModel().selectedRows():
            Item = self.item(Row.row(), self.COL_ID)
            if Item:
                WordId = Item.data(Qt.ItemDataRole.UserRole)
                if WordId is not None:
                    WordIds.append(int(WordId))
        return WordIds

    def setReadOnly(self, IsReadOnly: bool) -> None:
        """切換唯讀/可編輯模式"""
        self._ReadOnly = IsReadOnly
        if IsReadOnly:
            self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        else:
            self.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
