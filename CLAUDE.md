# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

我的英文單字能力約中高等級,想設計程式,輸入Youtube網址,如網址有英文翻譯,幫我把中高級的單字,與對應的句子,整理成一個.csv檔並存下來. 並幫我設計學習的UI,每天我可以點開程式做英文的學習. 並設計測驗小程式,讓我可以從測驗中學習單字.最後要記錄我每天學習的狀況.

## Code Specification

1. 開發語言：Python 3.13 
2. UI library：pyside6
3. 註解請用中文
4. Variable Naming：CamelCase 一致使用
5. Error Handling：所有 API 呼叫必須包含 try-except
6. Function 名稱使用英文，不要用中文

## Design Decisions

1. 單字分級,我覺得適用CEFR的B1、B2、C1、C2, 片語則是B1以上都可以記錄.
2. csv檔要考慮方便匯入到excel裡. 欄位可分為英文,中文翻譯(要含詞性,像n., vt.,等),英文例句,例句中文翻譯
3. 一個單字最多記錄三個句子即可.
3. 要能匯入/匯出csv檔.
4. 測驗小程式可以像中英文單字選擇題.
5. 學習時可以像字卡一樣,可選從英文單字學中文單字,或從中文單字來學英文單字,例句可先隱藏,有按鍵可以選顯示或不顯示,若英文句子能夠發音更好.

## UI

1. 由你先幫我規劃,畫面儘量簡潔,不同的功能可以用不同的分頁呈現.等你設計好後我們再來討論.
