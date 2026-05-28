import re
import hashlib
from datetime import date, timedelta


def cleanText(RawText: str) -> str:
    """清理字幕原始文字：去除 HTML tag、多餘空白、特殊符號"""
    # 去除 HTML tag（如 <c>, <font>, <b> 等）
    Text = re.sub(r"<[^>]+>", "", RawText)
    # 去除方括號內容（如 [Music], [Applause]）
    Text = re.sub(r"\[[^\]]*\]", "", Text)
    # 去除多餘空白
    Text = re.sub(r"\s+", " ", Text).strip()
    return Text


def getMd5Hash(Text: str) -> str:
    """取得字串的 MD5 hash（用於音訊快取檔名）"""
    return hashlib.md5(Text.lower().strip().encode("utf-8")).hexdigest()


def formatDuration(Seconds: int) -> str:
    """將秒數格式化為可讀字串，例如 '2分30秒'"""
    if Seconds < 60:
        return f"{Seconds}秒"
    Minutes = Seconds // 60
    Secs = Seconds % 60
    if Secs == 0:
        return f"{Minutes}分鐘"
    return f"{Minutes}分{Secs}秒"


def getDateRange(Days: int) -> list[date]:
    """回傳最近 N 天的日期列表（含今天）"""
    Today = date.today()
    return [Today - timedelta(days=I) for I in range(Days - 1, -1, -1)]


def truncateText(Text: str, MaxLength: int = 50) -> str:
    """截斷過長字串，末尾加 '...'"""
    if len(Text) <= MaxLength:
        return Text
    return Text[:MaxLength - 3] + "..."


def normalizePOS(Pos: str) -> str:
    """標準化詞性標記格式（確保有句點結尾）"""
    PosMap = {
        "noun": "n.", "verb": "v.", "adjective": "adj.", "adverb": "adv.",
        "transitive verb": "vt.", "intransitive verb": "vi.",
        "preposition": "prep.", "conjunction": "conj.", "pronoun": "pron.",
        "n": "n.", "v": "v.", "adj": "adj.", "adv": "adv.",
        "vt": "vt.", "vi": "vi.", "prep": "prep.",
        "phrase": "phrase", "idiom": "phrase",
    }
    Normalized = Pos.lower().strip().rstrip(".")
    return PosMap.get(Normalized, Pos if Pos.endswith(".") else Pos + ".")
