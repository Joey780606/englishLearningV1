from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QCheckBox, QButtonGroup, QFrame, QTextEdit,
    QGroupBox, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

from utils.config import CEFR_COLORS, FLASHCARD_ANIMATION_DURATION_MS
from models.data_models import VocabularyEntry
from database import db_manager
from core import audio_player


class AudioWorker(QObject):
    """背景播放語音的 Worker"""
    Finished = Signal(bool)

    def __init__(self, Text: str):
        super().__init__()
        self._Text = Text

    def run(self):
        Result = audio_player.playText(self._Text)
        self.Finished.emit(Result)


class FlashcardTab(QWidget):
    """Tab 3：字卡學習分頁"""

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._Entries: list[VocabularyEntry] = []
        self._CurrentIndex = 0
        self._IsFlipped     = False
        self._StudyStart    = None
        self._AudioThread   = None
        self._AudioWorker   = None
        self._setupUI()

    def _setupUI(self):
        Layout = QVBoxLayout(self)
        Layout.setSpacing(10)
        Layout.setContentsMargins(16, 16, 16, 16)

        # ── 頂部控制列 ──
        CtrlLayout = QHBoxLayout()

        # 學習模式
        ModeGroup = QGroupBox("學習模式")
        ModeLayout = QHBoxLayout(ModeGroup)
        self._BtnGroup = QButtonGroup(self)
        self._EnToZhBtn = QRadioButton("英文 → 中文")
        self._ZhToEnBtn = QRadioButton("中文 → 英文")
        self._EnToZhBtn.setChecked(True)
        self._BtnGroup.addButton(self._EnToZhBtn, 0)
        self._BtnGroup.addButton(self._ZhToEnBtn, 1)
        self._EnToZhBtn.toggled.connect(self._onModeChanged)
        ModeLayout.addWidget(self._EnToZhBtn)
        ModeLayout.addWidget(self._ZhToEnBtn)
        CtrlLayout.addWidget(ModeGroup)

        # 等級篩選
        LevelGroup = QGroupBox("等級篩選")
        LevelLayout = QHBoxLayout(LevelGroup)
        self._LevelCheckboxes = {}
        for Level, Color in [("B1", "#4CAF50"), ("B2", "#2196F3"), ("C1", "#FF9800"), ("C2", "#F44336")]:
            Cb = QCheckBox(Level)
            Cb.setChecked(True)
            Cb.setStyleSheet(f"QCheckBox {{ color: {Color}; font-weight: bold; }}")
            Cb.stateChanged.connect(self.reloadVocabulary)
            LevelLayout.addWidget(Cb)
            self._LevelCheckboxes[Level] = Cb
        CtrlLayout.addWidget(LevelGroup)

        # 進度顯示
        self._ProgressLabel = QLabel("第 0 / 0 張")
        self._ProgressLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._ProgressLabel.setStyleSheet("font-size: 14px; color: #666666;")
        CtrlLayout.addWidget(self._ProgressLabel)

        Layout.addLayout(CtrlLayout)

        # ── 字卡顯示區 ──
        self._CardFrame = QFrame()
        self._CardFrame.setFrameShape(QFrame.Shape.Box)
        self._CardFrame.setMinimumHeight(280)
        self._CardFrame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 12px;
            }
        """)

        CardLayout = QVBoxLayout(self._CardFrame)
        CardLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        CardLayout.setSpacing(8)

        # 正面文字（英文或中文，依模式而定）
        self._FrontLabel = QLabel("—")
        FrontFont = QFont()
        FrontFont.setPointSize(32)
        FrontFont.setBold(True)
        self._FrontLabel.setFont(FrontFont)
        self._FrontLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._FrontLabel.setWordWrap(True)
        CardLayout.addWidget(self._FrontLabel)

        # 詞性 & CEFR badge 列
        BadgeLayout = QHBoxLayout()
        BadgeLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._PosLabel = QLabel("")
        self._PosLabel.setStyleSheet("color: #888888; font-size: 13px;")
        self._LevelBadge = QLabel("")
        self._LevelBadge.setStyleSheet(
            "color: white; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 4px;"
        )
        BadgeLayout.addWidget(self._PosLabel)
        BadgeLayout.addSpacing(8)
        BadgeLayout.addWidget(self._LevelBadge)
        CardLayout.addLayout(BadgeLayout)

        # 分隔線
        self._Separator = QFrame()
        self._Separator.setFrameShape(QFrame.Shape.HLine)
        self._Separator.setStyleSheet("color: #DEE2E6;")
        self._Separator.setVisible(False)
        CardLayout.addWidget(self._Separator)

        # 翻面後顯示：翻譯文字
        self._BackLabel = QLabel("")
        BackFont = QFont()
        BackFont.setPointSize(20)
        self._BackLabel.setFont(BackFont)
        self._BackLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._BackLabel.setWordWrap(True)
        self._BackLabel.setVisible(False)
        CardLayout.addWidget(self._BackLabel)

        # 例句區（可切換顯示/隱藏）
        self._SentenceEdit = QTextEdit()
        self._SentenceEdit.setReadOnly(True)
        self._SentenceEdit.setMaximumHeight(100)
        self._SentenceEdit.setStyleSheet("background: transparent; border: none; font-size: 13px; color: #444444;")
        self._SentenceEdit.setVisible(False)
        CardLayout.addWidget(self._SentenceEdit)

        Layout.addWidget(self._CardFrame, stretch=1)

        # ── 例句切換 Checkbox ──
        self._ShowSentenceCheck = QCheckBox("顯示例句")
        self._ShowSentenceCheck.stateChanged.connect(self._onShowSentenceChanged)
        Layout.addWidget(self._ShowSentenceCheck)

        # ── 底部按鈕列 ──
        BtnLayout = QHBoxLayout()

        self._PrevBtn = QPushButton("◀ 上一張")
        self._PrevBtn.setFixedWidth(100)
        self._PrevBtn.clicked.connect(self._onPrevClicked)

        self._AudioBtn = QPushButton("🔊 播放")
        self._AudioBtn.setFixedWidth(80)
        self._AudioBtn.clicked.connect(self._onAudioClicked)

        self._FlipBtn = QPushButton("翻 面")
        self._FlipBtn.setFixedWidth(80)
        self._FlipBtn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 6px; }")
        self._FlipBtn.clicked.connect(self._onFlipClicked)

        self._NextBtn = QPushButton("▶ 下一張")
        self._NextBtn.setFixedWidth(100)
        self._NextBtn.clicked.connect(self._onNextClicked)

        self._MarkBtn = QPushButton("✓ 標記已學")
        self._MarkBtn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 6px 16px; }")
        self._MarkBtn.clicked.connect(self._onMarkLearned)

        BtnLayout.addWidget(self._PrevBtn)
        BtnLayout.addWidget(self._AudioBtn)
        BtnLayout.addWidget(self._FlipBtn)
        BtnLayout.addWidget(self._NextBtn)
        BtnLayout.addStretch()
        BtnLayout.addWidget(self._MarkBtn)
        Layout.addLayout(BtnLayout)

    def reloadVocabulary(self):
        """重新從資料庫載入符合等級篩選的詞彙"""
        try:
            SelectedLevels = [L for L, Cb in self._LevelCheckboxes.items() if Cb.isChecked()]
            if not SelectedLevels:
                self._Entries = []
            else:
                AllEntries = []
                for Level in SelectedLevels:
                    AllEntries.extend(db_manager.getAllVocabulary(Level))
                self._Entries = AllEntries

            self._CurrentIndex = 0
            self._IsFlipped    = False
            self._showCard()
        except RuntimeError as E:
            QMessageBox.critical(self, "載入失敗", str(E))

    def _showCard(self):
        """顯示目前索引的字卡"""
        if not self._Entries:
            self._FrontLabel.setText("沒有詞彙可學習\n請先到「詞彙列表」匯入或到「YouTube 匯入」擷取詞彙")
            self._BackLabel.setVisible(False)
            self._SentenceEdit.setVisible(False)
            self._Separator.setVisible(False)
            self._PosLabel.setText("")
            self._LevelBadge.setText("")
            self._ProgressLabel.setText("第 0 / 0 張")
            return

        Entry = self._Entries[self._CurrentIndex]
        IsEnToZh = self._EnToZhBtn.isChecked()
        self._IsFlipped = False

        # 正面：英文（英→中模式）或中文（中→英模式）
        if IsEnToZh:
            self._FrontLabel.setText(Entry.Word)
        else:
            self._FrontLabel.setText(Entry.ChineseTranslation or Entry.Word)

        # 詞性 & CEFR badge
        self._PosLabel.setText(Entry.PartOfSpeech)
        self._LevelBadge.setText(f"  {Entry.CefrLevel}  ")
        BgColor = CEFR_COLORS.get(Entry.CefrLevel, "#999999")
        self._LevelBadge.setStyleSheet(
            f"color: white; font-size: 12px; font-weight: bold; padding: 2px 8px; "
            f"border-radius: 4px; background-color: {BgColor};"
        )

        # 隱藏背面
        self._BackLabel.setText("")
        self._BackLabel.setVisible(False)
        self._Separator.setVisible(False)

        # 例句
        if self._ShowSentenceCheck.isChecked():
            self._updateSentenceText(Entry)
            self._SentenceEdit.setVisible(True)
        else:
            self._SentenceEdit.setVisible(False)

        self._ProgressLabel.setText(f"第 {self._CurrentIndex + 1} / {len(self._Entries)} 張")

    def _onFlipClicked(self):
        """翻面按鈕"""
        if not self._Entries:
            return

        Entry = self._Entries[self._CurrentIndex]
        IsEnToZh = self._EnToZhBtn.isChecked()

        if not self._IsFlipped:
            # 顯示翻面內容（答案）
            BackText = Entry.ChineseTranslation if IsEnToZh else Entry.Word
            self._BackLabel.setText(BackText)
            self._BackLabel.setVisible(True)
            self._Separator.setVisible(True)

            # 若未顯示例句，翻面後自動顯示
            if self._ShowSentenceCheck.isChecked():
                self._updateSentenceText(Entry)
                self._SentenceEdit.setVisible(True)
        else:
            self._BackLabel.setVisible(False)
            self._Separator.setVisible(False)
            if not self._ShowSentenceCheck.isChecked():
                self._SentenceEdit.setVisible(False)

        self._IsFlipped = not self._IsFlipped

        # 更新學習記錄（字卡翻閱次數）
        from datetime import date
        try:
            db_manager.upsertStudyRecord(date.today(), FlashcardDelta=1)
        except RuntimeError:
            pass

    def _onPrevClicked(self):
        if self._Entries and self._CurrentIndex > 0:
            self._CurrentIndex -= 1
            self._showCard()

    def _onNextClicked(self):
        if self._Entries and self._CurrentIndex < len(self._Entries) - 1:
            self._CurrentIndex += 1
            self._showCard()

    def _onAudioClicked(self):
        """播放目前字卡的英文發音"""
        if not self._Entries:
            return
        Entry = self._Entries[self._CurrentIndex]
        TextToPlay = Entry.Word  # 永遠播放英文單字

        if self._AudioThread and self._AudioThread.isRunning():
            return  # 正在播放中，忽略

        self._AudioThread = QThread()
        self._AudioWorker = AudioWorker(TextToPlay)
        self._AudioWorker.moveToThread(self._AudioThread)
        self._AudioThread.started.connect(self._AudioWorker.run)
        self._AudioWorker.Finished.connect(self._AudioThread.quit)
        self._AudioWorker.Finished.connect(self._AudioWorker.deleteLater)
        self._AudioThread.start()

    def _onMarkLearned(self):
        """標記目前字卡為已學習"""
        if not self._Entries:
            return
        from datetime import date
        try:
            db_manager.upsertStudyRecord(date.today(), WordsDelta=1)
            # 移到下一張
            if self._CurrentIndex < len(self._Entries) - 1:
                self._CurrentIndex += 1
                self._showCard()
            else:
                QMessageBox.information(self, "完成", "所有詞彙都學習完了！")
        except RuntimeError as E:
            QMessageBox.critical(self, "記錄失敗", str(E))

    def _onShowSentenceChanged(self, State: int):
        """切換例句顯示狀態"""
        if not self._Entries:
            return
        Entry = self._Entries[self._CurrentIndex]
        ShowSent = (State == Qt.CheckState.Checked.value)
        if ShowSent:
            self._updateSentenceText(Entry)
            self._SentenceEdit.setVisible(True)
        else:
            self._SentenceEdit.setVisible(False)

    def _onModeChanged(self):
        """學習模式切換時重新顯示字卡"""
        self._IsFlipped = False
        if self._Entries:
            self._showCard()

    def _updateSentenceText(self, Entry: VocabularyEntry):
        """更新例句文字區域的內容"""
        Lines = []
        for I, Sent in enumerate(Entry.Sentences, start=1):
            Lines.append(f"{I}. {Sent.EnglishSentence}")
            if Sent.ChineseSentence:
                Lines.append(f"   {Sent.ChineseSentence}")
        self._SentenceEdit.setPlainText("\n".join(Lines))
