import random
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QSpinBox, QComboBox, QCheckBox, QGroupBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from models.data_models import VocabularyEntry, QuizRecord
from database import db_manager


class QuizTab(QWidget):
    """Tab 4：測驗分頁（QStackedWidget 三頁：設定→測驗→結果）"""

    PAGE_SETUP  = 0
    PAGE_QUIZ   = 1
    PAGE_RESULT = 2

    def __init__(self, Parent=None):
        super().__init__(Parent)
        self._Questions: list[dict] = []   # [{entry, choices, correct_index}, ...]
        self._CurrentQuestion = 0
        self._CorrectCount    = 0
        self._Records: list[QuizRecord] = []
        self._AnswerTimer = QTimer()
        self._AnswerTimer.setSingleShot(True)
        self._AnswerTimer.timeout.connect(self._nextQuestion)
        self._setupUI()

    def _setupUI(self):
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(16, 16, 16, 16)

        self._Stack = QStackedWidget()
        Layout.addWidget(self._Stack)

        self._Stack.addWidget(self._buildSetupPage())
        self._Stack.addWidget(self._buildQuizPage())
        self._Stack.addWidget(self._buildResultPage())

    # ── 設定頁 ──────────────────────────────────────────────────────────────
    def _buildSetupPage(self) -> QWidget:
        Page = QWidget()
        Layout = QVBoxLayout(Page)
        Layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Layout.setSpacing(20)

        Title = QLabel("測驗設定")
        TitleFont = QFont()
        TitleFont.setPointSize(20)
        TitleFont.setBold(True)
        Title.setFont(TitleFont)
        Title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Layout.addWidget(Title)

        FormGroup = QGroupBox()
        FormGroup.setMaximumWidth(400)
        FormLayout = QVBoxLayout(FormGroup)
        FormLayout.setSpacing(12)

        # 題數
        CountRow = QHBoxLayout()
        CountRow.addWidget(QLabel("題數："))
        self._QuizCountSpin = QSpinBox()
        self._QuizCountSpin.setRange(5, 50)
        self._QuizCountSpin.setValue(10)
        self._QuizCountSpin.setSingleStep(5)
        CountRow.addWidget(self._QuizCountSpin)
        CountRow.addStretch()
        FormLayout.addLayout(CountRow)

        # 模式
        ModeRow = QHBoxLayout()
        ModeRow.addWidget(QLabel("模式："))
        self._ModeCombo = QComboBox()
        self._ModeCombo.addItems(["英文 → 中文（看英文選中文）", "中文 → 英文（看中文選英文）"])
        ModeRow.addWidget(self._ModeCombo)
        FormLayout.addLayout(ModeRow)

        # CEFR 等級
        LevelRow = QHBoxLayout()
        LevelRow.addWidget(QLabel("等級："))
        self._SetupLevelChecks = {}
        for Level, Color in [("B1","#4CAF50"), ("B2","#2196F3"), ("C1","#FF9800"), ("C2","#F44336")]:
            Cb = QCheckBox(Level)
            Cb.setChecked(True)
            Cb.setStyleSheet(f"QCheckBox {{ color: {Color}; font-weight: bold; }}")
            LevelRow.addWidget(Cb)
            self._SetupLevelChecks[Level] = Cb
        FormLayout.addLayout(LevelRow)

        Layout.addWidget(FormGroup, alignment=Qt.AlignmentFlag.AlignCenter)

        StartBtn = QPushButton("開始測驗")
        StartBtn.setFixedSize(160, 44)
        StartBtn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-size: 16px; border-radius: 6px; }")
        StartBtn.clicked.connect(self._startQuiz)
        Layout.addWidget(StartBtn, alignment=Qt.AlignmentFlag.AlignCenter)

        return Page

    # ── 測驗頁 ──────────────────────────────────────────────────────────────
    def _buildQuizPage(self) -> QWidget:
        Page = QWidget()
        Layout = QVBoxLayout(Page)
        Layout.setSpacing(12)
        Layout.setContentsMargins(20, 20, 20, 20)

        # 進度
        ProgressRow = QHBoxLayout()
        self._QuizProgressLabel = QLabel("第 1 / 10 題")
        self._QuizProgressLabel.setStyleSheet("color: #666666;")
        self._QuizProgressBar = QProgressBar()
        self._QuizProgressBar.setMaximumHeight(8)
        ProgressRow.addWidget(self._QuizProgressLabel)
        ProgressRow.addWidget(self._QuizProgressBar, stretch=1)
        Layout.addLayout(ProgressRow)

        # 題目
        self._QuestionLabel = QLabel("")
        QFont_ = QFont()
        QFont_.setPointSize(22)
        QFont_.setBold(True)
        self._QuestionLabel.setFont(QFont_)
        self._QuestionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._QuestionLabel.setWordWrap(True)
        self._QuestionLabel.setMinimumHeight(100)
        self._QuestionLabel.setStyleSheet("padding: 20px; background: #F8F9FA; border-radius: 8px;")
        Layout.addWidget(self._QuestionLabel)

        # 分數
        self._ScoreLabel = QLabel("得分：0")
        self._ScoreLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._ScoreLabel.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 14px;")
        Layout.addWidget(self._ScoreLabel)

        # 四個選項按鈕
        self._OptionBtns = []
        for I in range(4):
            Btn = QPushButton("")
            Btn.setMinimumHeight(48)
            Btn.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 8px 16px;
                    border: 1px solid #DEE2E6; border-radius: 6px;
                    font-size: 14px; background: white;
                }
                QPushButton:hover { background: #E3F2FD; }
            """)
            Btn.clicked.connect(lambda _, Idx=I: self._onOptionSelected(Idx))
            Layout.addWidget(Btn)
            self._OptionBtns.append(Btn)

        Layout.addStretch()

        # 退出測驗按鈕
        QuitBtn = QPushButton("退出測驗")
        QuitBtn.setStyleSheet("QPushButton { color: #F44336; border: none; }")
        QuitBtn.clicked.connect(lambda: self._Stack.setCurrentIndex(self.PAGE_SETUP))
        Layout.addWidget(QuitBtn, alignment=Qt.AlignmentFlag.AlignRight)

        return Page

    # ── 結果頁 ──────────────────────────────────────────────────────────────
    def _buildResultPage(self) -> QWidget:
        Page = QWidget()
        Layout = QVBoxLayout(Page)
        Layout.setSpacing(16)
        Layout.setContentsMargins(20, 20, 20, 20)

        self._ResultTitle = QLabel("測驗完成！")
        RFont = QFont()
        RFont.setPointSize(24)
        RFont.setBold(True)
        self._ResultTitle.setFont(RFont)
        self._ResultTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Layout.addWidget(self._ResultTitle)

        self._ResultScoreLabel = QLabel("")
        ScoreFont = QFont()
        ScoreFont.setPointSize(16)
        self._ResultScoreLabel.setFont(ScoreFont)
        self._ResultScoreLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        Layout.addWidget(self._ResultScoreLabel)

        # 答題明細
        self._ResultTable = QTableWidget(0, 5)
        self._ResultTable.setHorizontalHeaderLabels(["題號", "題目", "你的答案", "正確答案", "結果"])
        self._ResultTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._ResultTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        Layout.addWidget(self._ResultTable, stretch=1)

        BtnRow = QHBoxLayout()
        RetryBtn = QPushButton("再測一次")
        RetryBtn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px 20px; }")
        RetryBtn.clicked.connect(self._retryQuiz)

        BackBtn = QPushButton("返回設定")
        BackBtn.setStyleSheet("QPushButton { background-color: #9E9E9E; color: white; padding: 8px 20px; }")
        BackBtn.clicked.connect(lambda: self._Stack.setCurrentIndex(self.PAGE_SETUP))

        BtnRow.addStretch()
        BtnRow.addWidget(RetryBtn)
        BtnRow.addWidget(BackBtn)
        Layout.addLayout(BtnRow)

        return Page

    # ── 邏輯 ────────────────────────────────────────────────────────────────
    def _startQuiz(self):
        """準備題目並開始測驗"""
        SelectedLevels = [L for L, Cb in self._SetupLevelChecks.items() if Cb.isChecked()]
        if not SelectedLevels:
            QMessageBox.warning(self, "提示", "請至少選擇一個 CEFR 等級。")
            return

        Count = self._QuizCountSpin.value()
        try:
            Entries = db_manager.getWordsForQuiz(Count * 2, SelectedLevels)  # 多取一些作為干擾選項
        except RuntimeError as E:
            QMessageBox.critical(self, "錯誤", str(E))
            return

        if len(Entries) < 4:
            QMessageBox.warning(self, "詞彙不足", f"資料庫中符合條件的詞彙僅有 {len(Entries)} 個，至少需要 4 個才能測驗。\n請先匯入更多詞彙。")
            return

        # 建立題目列表
        QuizEntries = Entries[:Count]
        AllEntries  = Entries  # 用於生成干擾選項
        IsEnToZh = (self._ModeCombo.currentIndex() == 0)

        self._Questions = []
        for Entry in QuizEntries:
            # 生成四個選項（正確答案 + 三個干擾項）
            Distractors = [E for E in AllEntries if E.WordId != Entry.WordId]
            random.shuffle(Distractors)
            Distractors = Distractors[:3]

            if IsEnToZh:
                CorrectAns  = Entry.ChineseTranslation or Entry.Word
                WrongAns    = [E.ChineseTranslation or E.Word for E in Distractors]
                QuestionText = Entry.Word
            else:
                CorrectAns  = Entry.Word
                WrongAns    = [E.Word for E in Distractors]
                QuestionText = Entry.ChineseTranslation or Entry.Word

            Choices = [CorrectAns] + WrongAns
            random.shuffle(Choices)
            CorrectIndex = Choices.index(CorrectAns)

            self._Questions.append({
                "entry":         Entry,
                "question_text": QuestionText,
                "choices":       Choices,
                "correct_index": CorrectIndex,
                "correct_answer": CorrectAns,
                "mode":          "en_to_zh" if IsEnToZh else "zh_to_en",
            })

        self._CurrentQuestion = 0
        self._CorrectCount    = 0
        self._Records         = []
        self._Stack.setCurrentIndex(self.PAGE_QUIZ)
        self._showQuestion()

    def _showQuestion(self):
        """顯示目前題目"""
        if self._CurrentQuestion >= len(self._Questions):
            self._showResult()
            return

        Q = self._Questions[self._CurrentQuestion]
        Total = len(self._Questions)

        self._QuizProgressLabel.setText(f"第 {self._CurrentQuestion + 1} / {Total} 題")
        self._QuizProgressBar.setRange(0, Total)
        self._QuizProgressBar.setValue(self._CurrentQuestion)
        self._ScoreLabel.setText(f"得分：{self._CorrectCount}")
        self._QuestionLabel.setText(Q["question_text"])

        for I, Btn in enumerate(self._OptionBtns):
            Btn.setText(f"  {chr(65+I)}.  {Q['choices'][I]}")
            Btn.setEnabled(True)
            Btn.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 8px 16px;
                    border: 1px solid #DEE2E6; border-radius: 6px;
                    font-size: 14px; background: white;
                }
                QPushButton:hover { background: #E3F2FD; }
            """)

    def _onOptionSelected(self, SelectedIndex: int):
        """使用者選擇答案"""
        if self._AnswerTimer.isActive():
            return

        Q = self._Questions[self._CurrentQuestion]
        IsCorrect = (SelectedIndex == Q["correct_index"])
        if IsCorrect:
            self._CorrectCount += 1

        # 標記選項顏色
        for I, Btn in enumerate(self._OptionBtns):
            Btn.setEnabled(False)
            if I == Q["correct_index"]:
                Btn.setStyleSheet("QPushButton { text-align:left; padding:8px 16px; border-radius:6px; font-size:14px; background:#C8E6C9; border: 2px solid #4CAF50; }")
            elif I == SelectedIndex and not IsCorrect:
                Btn.setStyleSheet("QPushButton { text-align:left; padding:8px 16px; border-radius:6px; font-size:14px; background:#FFCDD2; border: 2px solid #F44336; }")

        # 記錄測驗結果
        Record = QuizRecord(
            WordId=Q["entry"].WordId or 0,
            Word=Q["entry"].Word,
            QuizMode=Q["mode"],
            IsCorrect=IsCorrect,
            UserAnswer=Q["choices"][SelectedIndex],
            CorrectAnswer=Q["correct_answer"],
        )
        self._Records.append(Record)
        try:
            db_manager.saveQuizRecord(Record)
        except RuntimeError:
            pass

        from utils.config import QUIZ_ANSWER_DELAY_MS
        self._AnswerTimer.start(QUIZ_ANSWER_DELAY_MS)

    def _nextQuestion(self):
        """跳至下一題"""
        self._CurrentQuestion += 1
        self._showQuestion()

    def _showResult(self):
        """顯示測驗結果頁"""
        Total    = len(self._Questions)
        Correct  = self._CorrectCount
        Rate     = round(Correct / Total * 100) if Total > 0 else 0

        self._ResultScoreLabel.setText(f"得分：{Correct} / {Total}　（{Rate}%）")

        # 更新學習記錄
        try:
            db_manager.upsertStudyRecord(date.today(), WordsDelta=Correct)
        except RuntimeError:
            pass

        # 填入明細表格
        self._ResultTable.setRowCount(0)
        for I, Rec in enumerate(self._Records):
            Row = self._ResultTable.rowCount()
            self._ResultTable.insertRow(Row)
            self._ResultTable.setItem(Row, 0, QTableWidgetItem(str(I + 1)))
            self._ResultTable.setItem(Row, 1, QTableWidgetItem(self._Questions[I]["question_text"]))
            self._ResultTable.setItem(Row, 2, QTableWidgetItem(Rec.UserAnswer))
            self._ResultTable.setItem(Row, 3, QTableWidgetItem(Rec.CorrectAnswer))
            ResultItem = QTableWidgetItem("✓" if Rec.IsCorrect else "✗")
            ResultItem.setForeground(QColor("#4CAF50") if Rec.IsCorrect else QColor("#F44336"))
            self._ResultTable.setItem(Row, 4, ResultItem)

        self._Stack.setCurrentIndex(self.PAGE_RESULT)

    def _retryQuiz(self):
        """保留相同設定重新測驗"""
        self._startQuiz()
