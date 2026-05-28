from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class SentenceEntry:
    """單一例句資料結構"""
    EnglishSentence: str   # 英文例句
    ChineseSentence: str   # 中文翻譯


@dataclass
class VocabularyEntry:
    """詞彙核心資料結構，對應 CSV 欄位與 SQLite vocabulary 表"""
    Word: str                                      # 英文單字
    PartOfSpeech: str                              # 詞性（n./vt./adj./phrase 等）
    ChineseTranslation: str                        # 中文翻譯
    CefrLevel: str                                 # CEFR 等級（B1/B2/C1/C2）
    Sentences: list[SentenceEntry] = field(default_factory=list)  # 最多三個例句
    WordId: Optional[int] = None                   # SQLite 主鍵（儲存後填入）
    SourceUrl: Optional[str] = None                # 來源 YouTube URL
    CreatedAt: Optional[datetime] = None           # 新增時間

    def toCsvRow(self) -> dict:
        """轉換成 CSV 匯出用的 flat dict"""
        Row = {
            "英文單字": self.Word,
            "詞性": self.PartOfSpeech,
            "中文翻譯": self.ChineseTranslation,
            "CEFR等級": self.CefrLevel,
        }
        for I in range(3):
            if I < len(self.Sentences):
                Row[f"例句{I+1}_英文"] = self.Sentences[I].EnglishSentence
                Row[f"例句{I+1}_中文"] = self.Sentences[I].ChineseSentence
            else:
                Row[f"例句{I+1}_英文"] = ""
                Row[f"例句{I+1}_中文"] = ""
        return Row

    @classmethod
    def fromCsvRow(cls, Row: dict) -> "VocabularyEntry":
        """從 CSV 列建立 VocabularyEntry 物件"""
        Sentences = []
        for I in range(1, 4):
            EnKey = f"例句{I}_英文"
            ZhKey = f"例句{I}_中文"
            EnText = str(Row.get(EnKey, "")).strip()
            ZhText = str(Row.get(ZhKey, "")).strip()
            if EnText:
                Sentences.append(SentenceEntry(EnglishSentence=EnText, ChineseSentence=ZhText))
        return cls(
            Word=str(Row.get("英文單字", "")).strip().lower(),
            PartOfSpeech=str(Row.get("詞性", "")).strip(),
            ChineseTranslation=str(Row.get("中文翻譯", "")).strip(),
            CefrLevel=str(Row.get("CEFR等級", "")).strip(),
            Sentences=Sentences,
        )


@dataclass
class StudyRecord:
    """每日學習記錄"""
    StudyDate: date                  # 學習日期
    WordsStudied: int = 0            # 當日學習單字數
    FlashcardCount: int = 0          # 字卡翻閱次數
    DurationSeconds: int = 0         # 學習時長（秒）
    RecordId: Optional[int] = None   # SQLite 主鍵


@dataclass
class QuizRecord:
    """單次測驗題目記錄"""
    WordId: int                      # 對應 vocabulary 表的 word_id
    Word: str                        # 英文單字（冗餘儲存）
    QuizMode: str                    # 'en_to_zh' 或 'zh_to_en'
    IsCorrect: bool                  # 是否答對
    UserAnswer: str                  # 使用者選擇的答案
    CorrectAnswer: str               # 正確答案
    RecordId: Optional[int] = None   # SQLite 主鍵


# CSV 欄位定義（固定順序，供 csv_manager 使用）
CSV_COLUMNS = [
    "英文單字", "詞性", "中文翻譯", "CEFR等級",
    "例句1_英文", "例句1_中文",
    "例句2_英文", "例句2_中文",
    "例句3_英文", "例句3_中文",
]
