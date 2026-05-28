import os

from utils.config import AUDIO_CACHE_DIR
from utils.helpers import getMd5Hash

# 記錄 pygame.mixer 是否成功初始化
_PlayerInitialized = False


def initializePlayer() -> bool:
    """初始化 pygame.mixer。若音訊裝置不可用回傳 False。"""
    global _PlayerInitialized
    try:
        import pygame
        pygame.mixer.init()
        _PlayerInitialized = True
        return True
    except Exception:
        _PlayerInitialized = False
        return False


def getAudioCachePath(Text: str) -> str:
    """根據文字內容的 MD5 hash 回傳快取檔案路徑"""
    Filename = getMd5Hash(Text) + ".mp3"
    return os.path.join(AUDIO_CACHE_DIR, Filename)


def playText(Text: str, Language: str = "en") -> bool:
    """
    將文字轉成語音並播放。
    流程：查快取 → 若無快取則呼叫 gTTS 生成 → 播放。
    回傳 True 表示播放成功，False 表示失敗。
    """
    if not _PlayerInitialized:
        return False

    CachePath = getAudioCachePath(Text)

    # 若快取不存在，呼叫 gTTS 生成
    if not os.path.exists(CachePath):
        Success = _generateAudio(Text, Language, CachePath)
        if not Success:
            return False

    # 播放音訊
    try:
        import pygame
        pygame.mixer.music.load(CachePath)
        pygame.mixer.music.play()
        return True
    except Exception:
        return False


def stopPlayback() -> None:
    """停止目前的語音播放"""
    try:
        import pygame
        if _PlayerInitialized:
            pygame.mixer.music.stop()
    except Exception:
        pass


def isPlaying() -> bool:
    """回傳目前是否正在播放語音"""
    try:
        import pygame
        if _PlayerInitialized:
            return pygame.mixer.music.get_busy()
    except Exception:
        pass
    return False


def _generateAudio(Text: str, Language: str, OutputPath: str) -> bool:
    """呼叫 gTTS 生成語音檔案並存至快取路徑"""
    try:
        from gtts import gTTS
        Tts = gTTS(text=Text, lang=Language, slow=False)
        Tts.save(OutputPath)
        return True
    except Exception:
        return False
