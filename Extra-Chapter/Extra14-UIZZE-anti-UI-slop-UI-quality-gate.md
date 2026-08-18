# UIZZE anti-UI-slop：給 coding agent 的 UI 品質門

> 本文是 Hello-Agents 社群精選的工具與工作流筆記。UIZZE 是本文提到的已知實作；請把它當成一個可驗證的 UI 品質工作流，而不是元件庫或通用模板。

AI coding agent 很容易做出「看起來完成」但實際上不完整的介面：相同的 dashboard、卡片網格和漸變色，缺少 loading / empty / error 狀態，按鈕沒有可觀察的行為，手機版也沒有真正檢查。這類問題不只在視覺上，也會讓使用者無法完成任務。

## 1. 免費本地 Skill

UIZZE 提供 MIT 授權的 `anti-ui-slop` Agent Skill，適用於 Codex、Claude Code、Cursor、GitHub Copilot 和其他支援 Agent Skills 的 coding agent。它把 UI 任務拆成幾個可檢查的問題：

1. **Design contract**：這個介面服務誰、主要任務是什麼、層級和視覺語言如何延續既有產品。
2. **Required states**：至少列出 loading、empty、error、success、disabled，以及必要的 responsive 狀態。
3. **Interaction semantics**：確認表單、按鈕、導航和回饋真的有行為，不只是畫出一個看似可點的控制項。
4. **Finish gate**：在提交或 merge 前，讀取實作、執行可用的檢查，並在真實 viewport 渲染後確認沒有 clipping、overflow、不可達控制項或 layout 退化。

安裝不需要帳號、token 或額外依賴：

```bash
npx skills add https://uizze.com --skill anti-ui-slop
```

這個 Skill 的重點不是替 agent 選一套漂亮風格，而是要求它先理解產品和工作流，再用明確的狀態與證據完成 UI。

## 2. 用免費 preview 做 deterministic 檢查

需要一個不登入的快速檢查時，可以使用 [UI Slop preview](https://uizze.com/mcp/preview) 的 `check_ui_slop`。它適合在本地 Skill 之外，快速確認常見的 generic UI、missing states、inert controls 和 token drift 問題。

工具不可用時，仍然可以手動執行同一個 finish gate；品質要求不應該依賴某一個 MCP 連線是否存在。

## 3. 完整 workflow 的範圍

如果任務需要產品特定的參考或渲染批評，完整 UIZZE workflow 才會再增加 live search、design contracts、implementation validation、audits 和 rendered critique，並可從 **800,000+ 個真實 web 與 iOS screens** 中找參考。免費 Skill、免費 preview 和可選的完整 UIZZE MCP 是不同層次，使用時應保持這個界線清楚。

## 4. 合併前的一頁 checklist

- [ ] 首屏是否說明產品、當前狀態和下一個可執行動作？
- [ ] loading、empty、error、success、disabled 和 responsive 狀態是否真的存在？
- [ ] 每個可互動控制項是否能用鍵盤、輔助技術或清楚的指標觀察到結果？
- [ ] 小螢幕和長內容是否檢查過 overflow、clipping 和不可達操作？
- [ ] 是否用既有產品的 token、元件和語言，而不是重新套一個 generic dashboard？
- [ ] 是否留下可重現的檢查結果或渲染證據？

## 參考連結

- [UIZZE canonical repository](https://github.com/uizze/uizze)
- [anti-ui-slop Skill source](https://github.com/uizze/uizze/tree/main/skills/anti-ui-slop)
- [Public design contract](https://github.com/uizze/uizze/blob/main/DESIGN.md)
- [GitHub Action](https://github.com/uizze/uizze/tree/main/integrations/github-action)
- [UIZZE website](https://uizze.com)
