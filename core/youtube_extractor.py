import os
import re
import tempfile
from typing import Optional

from utils.helpers import cleanText


class SubtitleNotFoundError(Exception):
    """找不到英文字幕時拋出"""
    pass


def extractSubtitles(YoutubeUrl: str) -> list[str]:
    """
    從 YouTube 網址下載英文字幕，回傳乾淨的句子列表。
    優先下載手動字幕，若無則下載自動生成字幕。
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp 尚未安裝，請執行 pip install yt-dlp")

    TmpDir = tempfile.mkdtemp()
    TmpBase = os.path.join(TmpDir, "subtitle")

    YdlOpts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "skip_download": True,
        "outtmpl": TmpBase,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(YdlOpts) as Ydl:
            Ydl.download([YoutubeUrl])
    except Exception as E:
        raise SubtitleNotFoundError(f"下載字幕失敗：{E}")

    # 尋找下載的 .vtt 檔案
    VttFile = _findSubtitleFile(TmpDir, ".vtt")
    if VttFile:
        try:
            Sentences = parseVttContent(VttFile)
        finally:
            _cleanupTmpDir(TmpDir)
        return Sentences

    # 備用：尋找 .srt 檔案
    SrtFile = _findSubtitleFile(TmpDir, ".srt")
    if SrtFile:
        try:
            Sentences = parseSrtContent(SrtFile)
        finally:
            _cleanupTmpDir(TmpDir)
        return Sentences

    _cleanupTmpDir(TmpDir)
    raise SubtitleNotFoundError("找不到英文字幕檔案，請確認此影片有提供英文字幕。")


def parseVttContent(VttFilePath: str) -> list[str]:
    """解析 .vtt 字幕檔，去除重複 cue，回傳乾淨句子列表"""
    try:
        import webvtt
    except ImportError:
        # 退回純文字解析
        return _parseVttFallback(VttFilePath)

    try:
        Sentences = []
        SeenTexts = set()
        for Caption in webvtt.read(VttFilePath):
            Text = cleanText(Caption.text)
            if Text and Text not in SeenTexts:
                SeenTexts.add(Text)
                Sentences.append(Text)
        return _mergeSentences(Sentences)
    except Exception as E:
        return _parseVttFallback(VttFilePath)


def parseSrtContent(SrtFilePath: str) -> list[str]:
    """解析 .srt 字幕檔，回傳乾淨句子列表"""
    try:
        with open(SrtFilePath, "r", encoding="utf-8", errors="ignore") as F:
            Content = F.read()
    except Exception as E:
        raise RuntimeError(f"讀取 SRT 檔失敗：{E}")

    # 移除序號和時間碼
    Content = re.sub(r"^\d+\s*$", "", Content, flags=re.MULTILINE)
    Content = re.sub(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}", "", Content)

    Lines = [cleanText(Line) for Line in Content.splitlines()]
    Sentences = list(dict.fromkeys(Line for Line in Lines if Line))  # 去重複
    return _mergeSentences(Sentences)


def getVideoTitle(YoutubeUrl: str) -> str:
    """取得 YouTube 影片標題（不下載影片）"""
    try:
        import yt_dlp
        YdlOpts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(YdlOpts) as Ydl:
            Info = Ydl.extract_info(YoutubeUrl, download=False)
            return Info.get("title", "未知標題")
    except Exception:
        return "未知標題"


def cleanSubtitleText(RawText: str) -> str:
    """去除字幕的 HTML tag、時間碼與特殊符號"""
    return cleanText(RawText)


def _parseVttFallback(VttFilePath: str) -> list[str]:
    """不依賴 webvtt 的純文字解析備用方案"""
    try:
        with open(VttFilePath, "r", encoding="utf-8", errors="ignore") as F:
            Content = F.read()
    except Exception:
        return []

    # 移除 WEBVTT header 和時間碼行
    Content = re.sub(r"WEBVTT.*?\n", "", Content)
    Content = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*", "", Content)
    Content = re.sub(r"NOTE.*?\n", "", Content)
    Content = re.sub(r"align:.*?\n", "", Content)

    Lines = [cleanText(Line) for Line in Content.splitlines()]
    Sentences = list(dict.fromkeys(Line for Line in Lines if Line))
    return _mergeSentences(Sentences)


def _mergeSentences(Lines: list[str]) -> list[str]:
    """
    將字幕行合併成完整句子（以句號/問號/驚嘆號判斷句尾）。
    短行（< 10 字元）不算獨立句子，嘗試合併到前一行。
    """
    Merged = []
    Buffer = ""

    for Line in Lines:
        if not Line:
            continue

        if Buffer:
            Buffer = Buffer + " " + Line
        else:
            Buffer = Line

        # 句子結尾判斷
        if re.search(r"[.!?]['\"]?\s*$", Buffer) or len(Buffer) > 200:
            Merged.append(Buffer.strip())
            Buffer = ""

    if Buffer.strip():
        Merged.append(Buffer.strip())

    return Merged


def _findSubtitleFile(Directory: str, Extension: str) -> Optional[str]:
    """在目錄中尋找指定副檔名的字幕檔，優先選擇 en 語言的檔案"""
    EnFiles = []
    OtherFiles = []
    for Filename in os.listdir(Directory):
        if Filename.endswith(Extension):
            FullPath = os.path.join(Directory, Filename)
            if ".en." in Filename or Filename.endswith(f".en{Extension}"):
                EnFiles.append(FullPath)
            else:
                OtherFiles.append(FullPath)
    return (EnFiles + OtherFiles)[0] if (EnFiles or OtherFiles) else None


def _cleanupTmpDir(TmpDir: str) -> None:
    """清除暫存目錄及其所有內容"""
    import shutil
    try:
        shutil.rmtree(TmpDir, ignore_errors=True)
    except Exception:
        pass
