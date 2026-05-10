# Redundancy Prevention Patterns

本文件記錄了確保代理人行為一致、不重複廢話的核心設計模式。

## 1. 物理身分錨點 (Physical Identity Anchor)
不要依賴狀態檔或日誌來記住自己是誰。
*   **模式**：發送時必加 `[Hermes]` 前綴。
*   **優勢**：即使 Log 被刪除、進程崩潰，重啟後只需掃描 DOM 就能立即認回「哪些是我說過的」。

## 2. 自適應自介 (Adaptive Introduction)
自動判斷是否需要自我介紹。
*   **邏輯**：
    ```python
    intro_needed = True
    for line in history:
        if "Hermes" in line and "AI代理" in line:
            intro_needed = False; break
    ```
*   **指令**：若 `intro_needed` 為 False，在 Prompt 中明確禁止模型使用任何介紹性開場白。

## 3. 問題去重 (Question Deduplication)
任務描述（Task Description）往往是靜態的，但對話是動態的。
*   **規則**：若任務中要求詢問的事情（如停車位），在對話歷史中已被回答（如店家說「沒車位」），則在重啟或後續回覆中自動跳過該詢問。

## 4. 默契退場 (Tacit Exit)
處理「好的/了解/謝謝」等短回覆。
*   **指令**：若任務目標已初步達成，且對方回覆是簡短的確認語，代理人應直接進入 `accomplished` 守候狀態，嚴禁回覆「不客氣/再見」等冗餘文字。
*   **優勢**：讓 AI 代理人感覺更像一個有默契的真人助理，而非死板的腳本。

## 5. 聚焦回答 (Focused Response)
針對店員的重複提問進行優化。
*   **邏輯**：如果店員問的是歷史中已提過的單一資訊，代理人應「只給該項答案」，不應重新輸出完整的預約詳情。
*   **範例**：
    *   *店員*：「幾位兒童？」
    *   *Hermes*：「總共 2 位，謝謝。」 (而非重講一次日期人數姓名)
