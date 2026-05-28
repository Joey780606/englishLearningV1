from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QStatusBar
)
from PySide6.QtCore import Qt

from utils.config import APP_NAME, APP_MIN_WIDTH, APP_MIN_HEIGHT
from ui.tab_import import ImportTab
from ui.tab_vocabulary import VocabularyTab
from ui.tab_flashcard import FlashcardTab
from ui.tab_quiz import QuizTab
from ui.tab_progress import ProgressTab


class MainWindow(QMainWindow):
    """主視窗：包含五個功能分頁"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        self.resize(1200, 760)

        self._setupUI()
        self._connectSignals()

    def _setupUI(self):
        """建立 UI 元件"""
        # 主分頁元件
        self._TabWidget = QTabWidget()
        self._TabWidget.setDocumentMode(True)
        self.setCentralWidget(self._TabWidget)

        # 建立各分頁
        self._ImportTab     = ImportTab()
        self._VocabTab      = VocabularyTab()
        self._FlashcardTab  = FlashcardTab()
        self._QuizTab       = QuizTab()
        self._ProgressTab   = ProgressTab()

        self._TabWidget.addTab(self._ImportTab,    "📥 YouTube 匯入")
        self._TabWidget.addTab(self._VocabTab,     "📚 詞彙列表")
        self._TabWidget.addTab(self._FlashcardTab, "🎴 字卡學習")
        self._TabWidget.addTab(self._QuizTab,      "✏️ 測驗")
        self._TabWidget.addTab(self._ProgressTab,  "📊 學習進度")

        # 狀態列
        self._StatusBar = QStatusBar()
        self.setStatusBar(self._StatusBar)
        self._StatusBar.showMessage("就緒")

    def _connectSignals(self):
        """連接跨分頁信號"""
        # Tab 1 完成儲存後，自動刷新 Tab 2 詞彙列表
        self._ImportTab.VocabularySaved.connect(self._VocabTab.refreshTable)
        # Tab 1 狀態訊息轉發到狀態列
        self._ImportTab.StatusMessage.connect(self._StatusBar.showMessage)
        # 切換到 Tab 5 時自動刷新進度資料
        self._TabWidget.currentChanged.connect(self._onTabChanged)

    def _onTabChanged(self, Index: int):
        """切換分頁時的處理（Tab 5 自動刷新）"""
        if Index == 4:
            self._ProgressTab.refreshStats()
        elif Index == 2:
            self._FlashcardTab.reloadVocabulary()
