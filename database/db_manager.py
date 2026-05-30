import sqlite3
from datetime import date, datetime
from typing import Optional

from utils.config import DATABASE_PATH
from models.data_models import VocabularyEntry, SentenceEntry, StudyRecord, QuizRecord, ImportRecord


def initializeDatabase() -> None:
    """初始化資料庫，建立所有資料表（若不存在）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS vocabulary (
                word_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                word           TEXT NOT NULL,
                part_of_speech TEXT NOT NULL,
                chinese_trans  TEXT NOT NULL,
                cefr_level     TEXT NOT NULL,
                source_url     TEXT,
                created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(word, part_of_speech)
            );

            CREATE TABLE IF NOT EXISTS sentences (
                sentence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id          INTEGER NOT NULL
                    REFERENCES vocabulary(word_id) ON DELETE CASCADE,
                sentence_order   INTEGER NOT NULL,
                english_sentence TEXT NOT NULL,
                chinese_sentence TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS study_records (
                record_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                study_date       DATE NOT NULL UNIQUE,
                words_studied    INTEGER DEFAULT 0,
                flashcard_count  INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS quiz_records (
                quiz_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_date      DATETIME DEFAULT CURRENT_TIMESTAMP,
                word_id        INTEGER REFERENCES vocabulary(word_id) ON DELETE SET NULL,
                word           TEXT NOT NULL,
                quiz_mode      TEXT NOT NULL,
                is_correct     INTEGER NOT NULL,
                user_answer    TEXT,
                correct_answer TEXT
            );

            CREATE TABLE IF NOT EXISTS import_history (
                record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url  TEXT NOT NULL,
                video_title TEXT NOT NULL,
                word_count  INTEGER NOT NULL DEFAULT 0,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        Conn.commit()
    except sqlite3.Error as E:
        raise RuntimeError(f"資料庫初始化失敗：{E}")
    finally:
        Conn.close()


def saveVocabularyEntry(Entry: VocabularyEntry) -> Optional[int]:
    """儲存詞彙條目（INSERT OR IGNORE），回傳 word_id；重複時回傳現有 word_id"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.execute("PRAGMA foreign_keys = ON")
        Cursor = Conn.cursor()

        # 嘗試插入，重複時忽略
        Cursor.execute(
            """INSERT OR IGNORE INTO vocabulary
               (word, part_of_speech, chinese_trans, cefr_level, source_url)
               VALUES (?, ?, ?, ?, ?)""",
            (Entry.Word.lower(), Entry.PartOfSpeech, Entry.ChineseTranslation,
             Entry.CefrLevel, Entry.SourceUrl)
        )
        Conn.commit()

        # 查詢 word_id（無論是否新增）
        Cursor.execute(
            "SELECT word_id FROM vocabulary WHERE word=? AND part_of_speech=?",
            (Entry.Word.lower(), Entry.PartOfSpeech)
        )
        Row = Cursor.fetchone()
        if not Row:
            return None
        WordId = Row[0]

        # 如果是新增的，同時插入例句
        if Cursor.lastrowid:
            for I, Sentence in enumerate(Entry.Sentences[:3], start=1):
                Cursor.execute(
                    """INSERT INTO sentences
                       (word_id, sentence_order, english_sentence, chinese_sentence)
                       VALUES (?, ?, ?, ?)""",
                    (WordId, I, Sentence.EnglishSentence, Sentence.ChineseSentence)
                )
            Conn.commit()

        return WordId
    except sqlite3.Error as E:
        raise RuntimeError(f"儲存詞彙失敗：{E}")
    finally:
        Conn.close()


def saveBatchVocabulary(Entries: list[VocabularyEntry]) -> int:
    """批次儲存詞彙，回傳成功新增的筆數"""
    SavedCount = 0
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.execute("PRAGMA foreign_keys = ON")
        Cursor = Conn.cursor()

        for Entry in Entries:
            Cursor.execute(
                """INSERT OR IGNORE INTO vocabulary
                   (word, part_of_speech, chinese_trans, cefr_level, source_url)
                   VALUES (?, ?, ?, ?, ?)""",
                (Entry.Word.lower(), Entry.PartOfSpeech, Entry.ChineseTranslation,
                 Entry.CefrLevel, Entry.SourceUrl)
            )
            if Cursor.rowcount > 0:
                WordId = Cursor.lastrowid
                SavedCount += 1
                for I, Sentence in enumerate(Entry.Sentences[:3], start=1):
                    Cursor.execute(
                        """INSERT INTO sentences
                           (word_id, sentence_order, english_sentence, chinese_sentence)
                           VALUES (?, ?, ?, ?)""",
                        (WordId, I, Sentence.EnglishSentence, Sentence.ChineseSentence)
                    )

        Conn.commit()
        return SavedCount
    except sqlite3.Error as E:
        raise RuntimeError(f"批次儲存詞彙失敗：{E}")
    finally:
        Conn.close()


def getAllVocabulary(Level: Optional[str] = None) -> list[VocabularyEntry]:
    """取得所有詞彙（可依 CEFR 等級篩選），含例句"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.row_factory = sqlite3.Row
        Cursor = Conn.cursor()

        if Level and Level != "全部":
            Cursor.execute(
                "SELECT * FROM vocabulary WHERE cefr_level=? ORDER BY word",
                (Level,)
            )
        else:
            Cursor.execute("SELECT * FROM vocabulary ORDER BY word")

        Rows = Cursor.fetchall()
        Entries = []
        for Row in Rows:
            Entry = _rowToEntry(Row, Cursor)
            Entries.append(Entry)
        return Entries
    except sqlite3.Error as E:
        raise RuntimeError(f"取得詞彙失敗：{E}")
    finally:
        Conn.close()


def searchVocabulary(Keyword: str) -> list[VocabularyEntry]:
    """依關鍵字搜尋詞彙（英文單字或中文翻譯）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.row_factory = sqlite3.Row
        Cursor = Conn.cursor()
        SearchTerm = f"%{Keyword.lower()}%"
        Cursor.execute(
            """SELECT * FROM vocabulary
               WHERE LOWER(word) LIKE ? OR chinese_trans LIKE ?
               ORDER BY word""",
            (SearchTerm, SearchTerm)
        )
        Rows = Cursor.fetchall()
        return [_rowToEntry(Row, Cursor) for Row in Rows]
    except sqlite3.Error as E:
        raise RuntimeError(f"搜尋詞彙失敗：{E}")
    finally:
        Conn.close()


def deleteVocabulary(WordId: int) -> bool:
    """刪除指定 word_id 的詞彙（例句因 CASCADE 自動刪除）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.execute("PRAGMA foreign_keys = ON")
        Cursor = Conn.cursor()
        Cursor.execute("DELETE FROM vocabulary WHERE word_id=?", (WordId,))
        Conn.commit()
        return Cursor.rowcount > 0
    except sqlite3.Error as E:
        raise RuntimeError(f"刪除詞彙失敗：{E}")
    finally:
        Conn.close()


def updateVocabularyEntry(Entry: VocabularyEntry) -> bool:
    """更新詞彙資料（含例句）"""
    if Entry.WordId is None:
        return False
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.execute("PRAGMA foreign_keys = ON")
        Cursor = Conn.cursor()

        Cursor.execute(
            """UPDATE vocabulary
               SET part_of_speech=?, chinese_trans=?, cefr_level=?
               WHERE word_id=?""",
            (Entry.PartOfSpeech, Entry.ChineseTranslation, Entry.CefrLevel, Entry.WordId)
        )
        # 刪除舊例句後重新插入
        Cursor.execute("DELETE FROM sentences WHERE word_id=?", (Entry.WordId,))
        for I, Sentence in enumerate(Entry.Sentences[:3], start=1):
            Cursor.execute(
                """INSERT INTO sentences
                   (word_id, sentence_order, english_sentence, chinese_sentence)
                   VALUES (?, ?, ?, ?)""",
                (Entry.WordId, I, Sentence.EnglishSentence, Sentence.ChineseSentence)
            )
        Conn.commit()
        return True
    except sqlite3.Error as E:
        raise RuntimeError(f"更新詞彙失敗：{E}")
    finally:
        Conn.close()


def upsertStudyRecord(StudyDate: date, WordsDelta: int = 0,
                      FlashcardDelta: int = 0, DurationDelta: int = 0) -> None:
    """新增或更新當日學習記錄（累加方式）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            """INSERT INTO study_records (study_date, words_studied, flashcard_count, duration_seconds)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(study_date) DO UPDATE SET
                   words_studied    = words_studied    + excluded.words_studied,
                   flashcard_count  = flashcard_count  + excluded.flashcard_count,
                   duration_seconds = duration_seconds + excluded.duration_seconds""",
            (str(StudyDate), WordsDelta, FlashcardDelta, DurationDelta)
        )
        Conn.commit()
    except sqlite3.Error as E:
        raise RuntimeError(f"更新學習記錄失敗：{E}")
    finally:
        Conn.close()


def getStudyHistory(Days: int = 30) -> list[StudyRecord]:
    """取得最近 N 天的學習記錄"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.row_factory = sqlite3.Row
        Cursor = Conn.cursor()
        Cursor.execute(
            """SELECT * FROM study_records
               WHERE study_date >= date('now', ?)
               ORDER BY study_date DESC""",
            (f"-{Days} days",)
        )
        return [
            StudyRecord(
                RecordId=Row["record_id"],
                StudyDate=date.fromisoformat(Row["study_date"]),
                WordsStudied=Row["words_studied"],
                FlashcardCount=Row["flashcard_count"],
                DurationSeconds=Row["duration_seconds"],
            )
            for Row in Cursor.fetchall()
        ]
    except sqlite3.Error as E:
        raise RuntimeError(f"取得學習記錄失敗：{E}")
    finally:
        Conn.close()


def saveQuizRecord(Record: QuizRecord) -> None:
    """儲存單一測驗題目記錄"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            """INSERT INTO quiz_records
               (word_id, word, quiz_mode, is_correct, user_answer, correct_answer)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (Record.WordId, Record.Word, Record.QuizMode,
             1 if Record.IsCorrect else 0,
             Record.UserAnswer, Record.CorrectAnswer)
        )
        Conn.commit()
    except sqlite3.Error as E:
        raise RuntimeError(f"儲存測驗記錄失敗：{E}")
    finally:
        Conn.close()


def getQuizStats(Days: int = 7) -> dict:
    """取得最近 N 天的測驗統計資料"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            """SELECT COUNT(*) as Total,
                      SUM(is_correct) as Correct
               FROM quiz_records
               WHERE quiz_date >= datetime('now', ?)""",
            (f"-{Days} days",)
        )
        Row = Cursor.fetchone()
        Total   = Row[0] or 0
        Correct = Row[1] or 0
        Rate    = round(Correct / Total * 100, 1) if Total > 0 else 0.0
        return {"Total": Total, "Correct": Correct, "Rate": Rate}
    except sqlite3.Error as E:
        raise RuntimeError(f"取得測驗統計失敗：{E}")
    finally:
        Conn.close()


def getWordsForQuiz(Count: int = 10, Levels: Optional[list] = None) -> list[VocabularyEntry]:
    """隨機取得測驗用詞彙（可依等級篩選）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.row_factory = sqlite3.Row
        Cursor = Conn.cursor()

        if Levels:
            Placeholders = ",".join("?" * len(Levels))
            Cursor.execute(
                f"""SELECT * FROM vocabulary WHERE cefr_level IN ({Placeholders})
                    ORDER BY RANDOM() LIMIT ?""",
                (*Levels, Count)
            )
        else:
            Cursor.execute(
                "SELECT * FROM vocabulary ORDER BY RANDOM() LIMIT ?",
                (Count,)
            )

        return [_rowToEntry(Row, Cursor) for Row in Cursor.fetchall()]
    except sqlite3.Error as E:
        raise RuntimeError(f"取得測驗詞彙失敗：{E}")
    finally:
        Conn.close()


def getVocabularyCount(Level: Optional[str] = None) -> dict:
    """取得詞彙數量統計（依 CEFR 等級分組）"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            "SELECT cefr_level, COUNT(*) FROM vocabulary GROUP BY cefr_level"
        )
        Result = {Row[0]: Row[1] for Row in Cursor.fetchall()}
        Result["total"] = sum(Result.values())
        return Result
    except sqlite3.Error as E:
        raise RuntimeError(f"取得詞彙統計失敗：{E}")
    finally:
        Conn.close()


def getStudyStreakDays() -> int:
    """計算連續學習天數（從今天往回數）"""
    try:
        from datetime import timedelta
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            "SELECT study_date FROM study_records ORDER BY study_date DESC"
        )
        Rows = Cursor.fetchall()
        if not Rows:
            return 0

        StreakCount = 0
        CheckDate = date.today()
        for Row in Rows:
            RecordDate = date.fromisoformat(Row[0])
            if RecordDate == CheckDate:
                StreakCount += 1
                CheckDate -= timedelta(days=1)
            elif RecordDate < CheckDate:
                break
        return StreakCount
    except sqlite3.Error as E:
        raise RuntimeError(f"計算連續天數失敗：{E}")
    finally:
        Conn.close()


def saveImportRecord(Record: ImportRecord) -> int:
    """儲存匯入歷史記錄，回傳新增的 record_id"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Cursor = Conn.cursor()
        Cursor.execute(
            """INSERT INTO import_history (source_url, video_title, word_count)
               VALUES (?, ?, ?)""",
            (Record.SourceUrl, Record.VideoTitle, Record.WordCount)
        )
        Conn.commit()
        return Cursor.lastrowid
    except sqlite3.Error as E:
        raise RuntimeError(f"儲存匯入記錄失敗：{E}")
    finally:
        Conn.close()


def getImportHistory() -> list[ImportRecord]:
    """取得所有匯入歷史，依時間倒序"""
    try:
        Conn = sqlite3.connect(DATABASE_PATH)
        Conn.row_factory = sqlite3.Row
        Cursor = Conn.cursor()
        Cursor.execute(
            "SELECT * FROM import_history ORDER BY imported_at DESC"
        )
        return [
            ImportRecord(
                RecordId=Row["record_id"],
                SourceUrl=Row["source_url"],
                VideoTitle=Row["video_title"],
                WordCount=Row["word_count"],
                ImportedAt=datetime.fromisoformat(Row["imported_at"]),
            )
            for Row in Cursor.fetchall()
        ]
    except sqlite3.Error as E:
        raise RuntimeError(f"取得匯入歷史失敗：{E}")
    finally:
        Conn.close()


def _rowToEntry(Row: sqlite3.Row, Cursor: sqlite3.Cursor) -> VocabularyEntry:
    """將 vocabulary 資料列轉換成 VocabularyEntry（含例句查詢）"""
    Cursor.execute(
        """SELECT english_sentence, chinese_sentence
           FROM sentences WHERE word_id=?
           ORDER BY sentence_order""",
        (Row["word_id"],)
    )
    SentenceRows = Cursor.fetchall()
    Sentences = [
        SentenceEntry(
            EnglishSentence=S["english_sentence"] if isinstance(S, sqlite3.Row) else S[0],
            ChineseSentence=S["chinese_sentence"] if isinstance(S, sqlite3.Row) else S[1],
        )
        for S in SentenceRows
    ]
    return VocabularyEntry(
        WordId=Row["word_id"],
        Word=Row["word"],
        PartOfSpeech=Row["part_of_speech"],
        ChineseTranslation=Row["chinese_trans"],
        CefrLevel=Row["cefr_level"],
        SourceUrl=Row["source_url"],
        Sentences=Sentences,
    )
