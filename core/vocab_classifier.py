import re
import csv
from typing import Optional

from utils.config import CEFR_WORDLIST_PATH, CEFR_LEVEL_ORDER, MAX_SENTENCES_PER_WORD
from models.data_models import VocabularyEntry, SentenceEntry

# 模組層快取，避免重複讀取 CSV
_CefrCache: Optional[dict] = None


def loadCefrWordlist(CsvPath: str = CEFR_WORDLIST_PATH) -> dict:
    """讀取 CEFR 詞彙表，回傳 {word: (cefr_level, part_of_speech)} 字典"""
    global _CefrCache
    if _CefrCache is not None:
        return _CefrCache

    Wordlist = {}
    try:
        with open(CsvPath, "r", encoding="utf-8-sig") as F:
            Reader = csv.DictReader(F)
            for Row in Reader:
                Word  = Row.get("word", "").strip().lower()
                Level = Row.get("cefr_level", "").strip()
                Pos   = Row.get("part_of_speech", "").strip()
                if Word and Level:
                    Wordlist[Word] = (Level, Pos)
    except FileNotFoundError:
        pass  # 若找不到詞彙表，回傳空字典（不中斷程式）

    _CefrCache = Wordlist
    return Wordlist


def classifyWord(Word: str, CefrWordlist: dict) -> Optional[tuple]:
    """
    查詢單字的 CEFR 等級與詞性。
    先查原形，找不到時嘗試常見詞形變化（去 -ing/-ed/-s/-es/-er/-est）。
    回傳 (cefr_level, part_of_speech) 或 None。
    """
    Lemma = Word.lower().strip()

    # 直接命中
    if Lemma in CefrWordlist:
        return CefrWordlist[Lemma]

    # 嘗試去除常見字尾後再查
    for Lemmatized in _getLemmas(Lemma):
        if Lemmatized in CefrWordlist:
            Level, Pos = CefrWordlist[Lemmatized]
            # 還原詞性標記（動詞變形 → 統一用原形詞性）
            return (Level, Pos)

    return None


def extractVocabulary(Sentences: list[str], CefrWordlist: dict,
                      MinLevel: str = "B1") -> list[VocabularyEntry]:
    """
    從句子列表中提取符合 MinLevel 以上的詞彙。
    每個單字最多保留 MAX_SENTENCES_PER_WORD 個例句。
    回傳 VocabularyEntry 列表（翻譯欄位為空，待後續填入）。
    """
    MinOrder = CEFR_LEVEL_ORDER.get(MinLevel, 2)

    # {word: (level, pos, [sentences])}
    WordMap: dict[str, tuple] = {}

    for Sentence in Sentences:
        CleanSentence = Sentence.strip()
        if not CleanSentence:
            continue

        # 提取句子中的英文單字
        Tokens = re.findall(r"[a-zA-Z]+(?:[-'][a-zA-Z]+)*", CleanSentence)

        for Token in Tokens:
            Word = Token.lower()
            # 過濾過短單字
            if len(Word) < 3:
                continue

            Result = classifyWord(Word, CefrWordlist)
            if Result is None:
                continue

            Level, Pos = Result
            LevelOrder = CEFR_LEVEL_ORDER.get(Level, 0)
            if LevelOrder < MinOrder:
                continue

            if Word not in WordMap:
                WordMap[Word] = (Level, Pos, [])

            # 每個單字最多收錄 MAX_SENTENCES_PER_WORD 個不重複句子
            _, _, SentenceList = WordMap[Word]
            if (len(SentenceList) < MAX_SENTENCES_PER_WORD
                    and CleanSentence not in SentenceList):
                SentenceList.append(CleanSentence)

    # 轉換成 VocabularyEntry 列表
    Entries = []
    for Word, (Level, Pos, SentenceTexts) in WordMap.items():
        Entry = VocabularyEntry(
            Word=Word,
            PartOfSpeech=Pos,
            ChineseTranslation="",   # 待翻譯
            CefrLevel=Level,
            Sentences=[
                SentenceEntry(EnglishSentence=S, ChineseSentence="")
                for S in SentenceTexts
            ],
        )
        Entries.append(Entry)

    # 依等級（由高到低）後按字母排序
    Entries.sort(key=lambda E: (
        -CEFR_LEVEL_ORDER.get(E.CefrLevel, 0),
        E.Word
    ))
    return Entries


def filterByLevel(Entries: list[VocabularyEntry],
                  Levels: list[str]) -> list[VocabularyEntry]:
    """依指定 CEFR 等級列表篩選詞彙"""
    LevelSet = set(Levels)
    return [E for E in Entries if E.CefrLevel in LevelSet]


def _getLemmas(Word: str) -> list[str]:
    """規則式詞形還原，回傳可能的原形列表（由最可能到最不可能）"""
    Candidates = []

    # -ing 結尾
    if Word.endswith("ing") and len(Word) > 5:
        Base = Word[:-3]
        Candidates.append(Base)          # running → run（若有雙子音）
        if len(Base) > 2 and Base[-1] == Base[-2]:
            Candidates.append(Base[:-1])  # running → runn → run
        Candidates.append(Base + "e")    # taking → tak → take

    # -ed 結尾
    elif Word.endswith("ed") and len(Word) > 4:
        Base = Word[:-2]
        Candidates.append(Base)          # looked → look
        Candidates.append(Base + "e")    # loved → lov → love
        if len(Base) > 2 and Base[-1] == Base[-2]:
            Candidates.append(Base[:-1])  # stopped → stopp → stop

    # -s / -es 結尾
    elif Word.endswith("ies") and len(Word) > 4:
        Candidates.append(Word[:-3] + "y")   # studies → study
    elif Word.endswith("es") and len(Word) > 4:
        Candidates.append(Word[:-2])          # boxes → box
        Candidates.append(Word[:-1])          # takes → take
    elif Word.endswith("s") and len(Word) > 3:
        Candidates.append(Word[:-1])          # runs → run

    # -er / -est 結尾（形容詞比較級）
    elif Word.endswith("est") and len(Word) > 5:
        Candidates.append(Word[:-3])          # fastest → fast
        Candidates.append(Word[:-2])          # greatest → great (via -er)
    elif Word.endswith("er") and len(Word) > 4:
        Candidates.append(Word[:-2])          # faster → fast
        Candidates.append(Word[:-1])          # larger → large

    # -ly 結尾（副詞 → 形容詞）
    elif Word.endswith("ly") and len(Word) > 4:
        Candidates.append(Word[:-2])          # quickly → quick
        Candidates.append(Word[:-1])          # extremely → extreme (rough)

    return Candidates
