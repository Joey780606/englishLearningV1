import time
from typing import Optional, Callable

from utils.config import TRANSLATE_DELAY_SECONDS, MAX_RETRY_COUNT, RETRY_DELAY_SECONDS
from models.data_models import VocabularyEntry


def translateWord(EnglishWord: str) -> str:
    """翻譯單一英文單字為繁體中文，失敗時回傳空字串"""
    try:
        from deep_translator import GoogleTranslator
        Translator = GoogleTranslator(source="en", target="zh-TW")
        Result = Translator.translate(EnglishWord.strip())
        return Result if Result else ""
    except Exception:
        return ""


def translateSentence(EnglishSentence: str) -> str:
    """翻譯單一英文句子為繁體中文，失敗時回傳空字串"""
    try:
        from deep_translator import GoogleTranslator
        Translator = GoogleTranslator(source="en", target="zh-TW")
        Result = Translator.translate(EnglishSentence.strip())
        return Result if Result else ""
    except Exception:
        return ""


def translateWithRetry(Text: str, Retries: int = MAX_RETRY_COUNT) -> str:
    """帶重試機制的翻譯函式"""
    for Attempt in range(Retries):
        try:
            from deep_translator import GoogleTranslator
            Translator = GoogleTranslator(source="en", target="zh-TW")
            Result = Translator.translate(Text.strip())
            if Result:
                return Result
        except Exception as E:
            if Attempt < Retries - 1:
                time.sleep(RETRY_DELAY_SECONDS)
    return ""


def translateBatch(Entries: list[VocabularyEntry],
                   ProgressCallback: Optional[Callable[[int, int], None]] = None
                   ) -> list[VocabularyEntry]:
    """
    批次翻譯所有 VocabularyEntry 的單字與例句。
    ProgressCallback(current, total) 在每次翻譯後呼叫（用於更新 UI 進度條）。
    """
    # 計算總翻譯次數（單字 + 各例句）
    TotalItems = sum(1 + len(E.Sentences) for E in Entries)
    CurrentItem = 0

    for Entry in Entries:
        # 翻譯單字
        if not Entry.ChineseTranslation:
            Entry.ChineseTranslation = translateWithRetry(Entry.Word)
        CurrentItem += 1
        if ProgressCallback:
            ProgressCallback(CurrentItem, TotalItems)
        time.sleep(TRANSLATE_DELAY_SECONDS)

        # 翻譯各例句
        for Sentence in Entry.Sentences:
            if not Sentence.ChineseSentence and Sentence.EnglishSentence:
                Sentence.ChineseSentence = translateWithRetry(Sentence.EnglishSentence)
            CurrentItem += 1
            if ProgressCallback:
                ProgressCallback(CurrentItem, TotalItems)
            time.sleep(TRANSLATE_DELAY_SECONDS)

    return Entries
