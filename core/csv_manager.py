import os
from typing import Optional

from models.data_models import VocabularyEntry, CSV_COLUMNS


def exportToCsv(Entries: list[VocabularyEntry], FilePath: str) -> bool:
    """
    將詞彙列表匯出為 CSV 檔案。
    使用 UTF-8-BOM 編碼，確保 Excel 直接開啟不亂碼。
    """
    try:
        import pandas as pd

        Rows = [E.toCsvRow() for E in Entries]
        Df = pd.DataFrame(Rows, columns=CSV_COLUMNS)
        Df.to_csv(FilePath, index=False, encoding="utf-8-sig")
        return True
    except Exception as E:
        raise RuntimeError(f"匯出 CSV 失敗：{E}")


def importFromCsv(FilePath: str) -> list[VocabularyEntry]:
    """
    從 CSV 檔案匯入詞彙列表。
    支援 UTF-8-BOM 和一般 UTF-8 編碼。
    """
    try:
        import pandas as pd

        # 嘗試不同編碼
        for Encoding in ["utf-8-sig", "utf-8", "big5", "gbk"]:
            try:
                Df = pd.read_csv(FilePath, encoding=Encoding, dtype=str)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError("無法識別 CSV 檔案的編碼格式")

        # 填充 NaN 為空字串
        Df = Df.fillna("")

        # 驗證必要欄位
        IsValid, ErrorMsg = validateCsvFormat(FilePath)
        if not IsValid:
            raise ValueError(f"CSV 格式錯誤：{ErrorMsg}")

        Entries = []
        for _, Row in Df.iterrows():
            try:
                Entry = VocabularyEntry.fromCsvRow(Row.to_dict())
                if Entry.Word:
                    Entries.append(Entry)
            except Exception:
                continue  # 跳過格式錯誤的列

        return Entries
    except (RuntimeError, ValueError):
        raise
    except Exception as E:
        raise RuntimeError(f"匯入 CSV 失敗：{E}")


def validateCsvFormat(FilePath: str) -> tuple[bool, str]:
    """
    驗證 CSV 檔案是否包含必要欄位。
    回傳 (is_valid, error_message)。
    """
    try:
        import pandas as pd

        for Encoding in ["utf-8-sig", "utf-8", "big5", "gbk"]:
            try:
                Df = pd.read_csv(FilePath, encoding=Encoding, nrows=0)
                break
            except UnicodeDecodeError:
                continue
        else:
            return False, "無法識別檔案編碼"

        RequiredColumns = {"英文單字", "CEFR等級"}
        ExistingColumns = set(Df.columns.tolist())
        Missing = RequiredColumns - ExistingColumns

        if Missing:
            return False, f"缺少必要欄位：{', '.join(Missing)}"

        return True, ""
    except Exception as E:
        return False, str(E)
