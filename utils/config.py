import os

# 專案根目錄
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 資料路徑
ASSETS_DIR       = os.path.join(BASE_DIR, "assets")
CACHE_DIR        = os.path.join(BASE_DIR, "cache")
AUDIO_CACHE_DIR  = os.path.join(CACHE_DIR, "audio")
DATABASE_DIR     = os.path.join(BASE_DIR, "database")

CEFR_WORDLIST_PATH = os.path.join(ASSETS_DIR, "cefr_wordlist.csv")
DATABASE_PATH      = os.path.join(DATABASE_DIR, "english_learning.db")

# 確保必要目錄存在
for _Dir in [ASSETS_DIR, AUDIO_CACHE_DIR, DATABASE_DIR]:
    os.makedirs(_Dir, exist_ok=True)

# CEFR 等級定義
CEFR_LEVELS = ["B1", "B2", "C1", "C2"]
CEFR_LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4, "C2": 5}

# CEFR badge 顏色（用於 UI StyleSheet）
CEFR_COLORS = {
    "B1": "#4CAF50",
    "B2": "#2196F3",
    "C1": "#FF9800",
    "C2": "#F44336",
}

# 應用程式設定
APP_NAME    = "英文單字學習系統"
APP_MIN_WIDTH  = 1024
APP_MIN_HEIGHT = 700

# 每個單字最多記錄幾個例句
MAX_SENTENCES_PER_WORD = 3

# 翻譯 API 設定
TRANSLATE_DELAY_SECONDS = 0.5
MAX_RETRY_COUNT         = 3
RETRY_DELAY_SECONDS     = 2.0

# 測驗設定預設值
QUIZ_DEFAULT_COUNT = 10
QUIZ_MIN_COUNT     = 5
QUIZ_MAX_COUNT     = 50
QUIZ_ANSWER_DELAY_MS = 1500   # 顯示對錯後自動跳下一題的毫秒數

# 字卡動畫時長（毫秒）
FLASHCARD_ANIMATION_DURATION_MS = 200
