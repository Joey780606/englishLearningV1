from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from ui.widgets.stat_card_widget import StatCardWidget
from utils.config import CEFR_LEVELS, CEFR_COLORS
from utils.helpers import formatDuration
from database import db_manager


class ProgressTab(QWidget):
    """Tab 5：學習進度分頁"""

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._setupUI()

    def _setupUI(self):
        Layout = QVBoxLayout(self)
        Layout.setSpacing(16)
        Layout.setContentsMargins(16, 16, 16, 16)

        # ── 頂部統計卡片列 ──
        CardLayout = QHBoxLayout()
        self._TotalCard   = StatCardWidget("詞彙總數")
        self._TodayCard   = StatCardWidget("今日學習")
        self._StreakCard  = StatCardWidget("連續天數")
        self._AccuracyCard = StatCardWidget("測驗正確率")

        for Card in [self._TotalCard, self._TodayCard, self._StreakCard, self._AccuracyCard]:
            CardLayout.addWidget(Card)
        Layout.addLayout(CardLayout)

        # ── CEFR 等級分佈 ──
        DistGroup = QGroupBox("詞彙等級分佈")
        DistLayout = QVBoxLayout(DistGroup)
        self._LevelBars: dict[str, tuple] = {}  # {level: (QProgressBar, QLabel)}

        for Level in CEFR_LEVELS:
            Row = QHBoxLayout()
            LevelLabel = QLabel(Level)
            LevelLabel.setFixedWidth(30)
            LevelLabel.setStyleSheet(
                f"color: {CEFR_COLORS.get(Level, '#999999')}; font-weight: bold;"
            )
            Bar = QProgressBar()
            Bar.setMaximumHeight(14)
            Bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {CEFR_COLORS.get(Level, '#999999')}; }}"
                "QProgressBar { border: 1px solid #DEE2E6; border-radius: 4px; text-align: right; }"
            )
            CountLabel = QLabel("0 個")
            CountLabel.setFixedWidth(60)
            CountLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
            Row.addWidget(LevelLabel)
            Row.addWidget(Bar, stretch=1)
            Row.addWidget(CountLabel)
            DistLayout.addLayout(Row)
            self._LevelBars[Level] = (Bar, CountLabel)

        Layout.addWidget(DistGroup)

        # ── 學習記錄表格 ──
        HistoryGroup = QGroupBox("最近學習記錄（近 30 天）")
        HistoryLayout = QVBoxLayout(HistoryGroup)

        self._HistoryTable = QTableWidget(0, 4)
        self._HistoryTable.setHorizontalHeaderLabels(["日期", "學習單字數", "字卡翻閱次數", "學習時長"])
        Header = self._HistoryTable.horizontalHeader()
        Header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        Header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        Header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        Header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._HistoryTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._HistoryTable.verticalHeader().setVisible(False)
        self._HistoryTable.setAlternatingRowColors(True)

        HistoryLayout.addWidget(self._HistoryTable)
        Layout.addWidget(HistoryGroup, stretch=1)

    def refreshStats(self):
        """從資料庫取得最新統計資料並更新 UI（切換到此 Tab 時呼叫）"""
        try:
            # 詞彙統計
            VocabCount = db_manager.getVocabularyCount()
            self._TotalCard.setValue(str(VocabCount.get("total", 0)))

            # 更新等級分佈
            MaxCount = max((VocabCount.get(L, 0) for L in CEFR_LEVELS), default=1)
            for Level in CEFR_LEVELS:
                Count = VocabCount.get(Level, 0)
                Bar, CountLabel = self._LevelBars[Level]
                Bar.setRange(0, max(MaxCount, 1))
                Bar.setValue(Count)
                Bar.setFormat(f"{Count}")
                CountLabel.setText(f"{Count} 個")

            # 今日學習
            Records = db_manager.getStudyHistory(1)
            TodayStudied = Records[0].WordsStudied if Records else 0
            self._TodayCard.setValue(str(TodayStudied))

            # 連續天數
            Streak = db_manager.getStudyStreakDays()
            self._StreakCard.setValue(f"{Streak} 天")

            # 測驗正確率（近 7 天）
            QuizStats = db_manager.getQuizStats(7)
            Rate = QuizStats.get("Rate", 0.0)
            self._AccuracyCard.setValue(f"{Rate}%")

            # 歷史記錄
            self._refreshHistoryTable()

        except RuntimeError:
            pass  # 資料庫尚無資料時靜默忽略

    def _refreshHistoryTable(self):
        """更新學習記錄表格"""
        try:
            Records = db_manager.getStudyHistory(30)
            self._HistoryTable.setRowCount(0)
            for Rec in Records:
                Row = self._HistoryTable.rowCount()
                self._HistoryTable.insertRow(Row)
                self._HistoryTable.setItem(Row, 0, QTableWidgetItem(str(Rec.StudyDate)))
                self._HistoryTable.setItem(Row, 1, QTableWidgetItem(str(Rec.WordsStudied)))
                self._HistoryTable.setItem(Row, 2, QTableWidgetItem(str(Rec.FlashcardCount)))
                self._HistoryTable.setItem(Row, 3, QTableWidgetItem(formatDuration(Rec.DurationSeconds)))
        except RuntimeError:
            pass
