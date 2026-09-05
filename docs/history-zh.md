# 開發歷史紀錄（中文）

> 這份文件是 `0.1.0` 公開發行之前的內部開發日誌（原 `tasks/todo.md`，後為
> `CHANGELOG.md`），內容維持原樣未重寫，僅作為歷史保存。
>
> 公開的版本紀錄請看 [CHANGELOG.md](../CHANGELOG.md)（Keep a Changelog 格式）。

---

# RUPS 增量改進整合

## S1: Issues CSV 增強（+Depends_On, +Owner）
- [x] 1.1 修改 `scripts/validate_paper_issues.py`（新欄位 + 依賴環偵測 + --legacy）
- [x] 1.2 更新 `assets/paper-issues-template.csv`
- [x] 1.3 更新 `assets/paper-issues-conference-template.csv`
- [x] 1.4 更新 `assets/paper-issues-codebase-template.csv`

## S2: Evidence Pack 階段
- [x] 2.1 新增 `scripts/evidence_pack.py`
- [x] 2.2 新增 `references/evidence-pack.md`

## S3: 多層 Selfloop 架構
- [x] 3.1 新增 `scripts/logic_selfloop.py`
- [x] 3.2 新增 `scripts/argument_selfloop.py`
- [x] 3.3 新增 `scripts/voice_selfloop.py`

## S4: Anti-Template 量化門控增強
- [x] 4.1 增強 `scripts/anti_ai_scan.py`（+--strict 模式）
- [x] 4.2 更新 `references/writing-style.md`

## S5: Refinement Markers
- [x] 5.1 `scripts/paper_utils.py` 新增 refinement marker 工具函式
- [x] 5.2 `scripts/claim_registry.py` 加入 refined guard
- [x] 5.3 `scripts/bibtex_audit.py` 加入 refined guard

## S6: Workspace Status
- [x] 6.1 新增 `scripts/workspace_status.py`

## 整合
- [x] 7.1 更新 `SKILL.md`
- [x] 7.2 新增/更新測試（修正 test_beamer_slides + test_conference_templates）
- [x] 7.3 執行全部測試（59/59 通過）

---

# Phase 4d: Video Synthesis 整合（Qwen3-TTS + Remotion）

## 新增腳本
- [x] 8.1 `scripts/generate_narration.py`（Beamer → narration-script.json）
- [x] 8.2 `scripts/synthesize_tts.py`（Qwen3-TTS 地端模型，支援 --api-url 遠端模式）
- [x] 8.3 `scripts/scaffold_video.py`（PDF→PNG + Remotion 專案搭建）
- [x] 8.4 `scripts/render_video.py`（npx remotion render 包裝）
- [x] 8.5 `scripts/validate_video.py`（ffprobe 影片驗證）

## 新增資產
- [x] 8.6 `assets/template/video/`（Remotion 模板：7 個檔案）
- [x] 8.7 `references/video-workflow.md`（Phase 4d 完整參考文件）

## 整合
- [x] 8.8 `SKILL.md` 新增 Phase 4d、Outputs、Issues CSV Schema
- [x] 8.9 三個 CSV 模板加入 VD1-VD5 Video 階段列
- [x] 8.10 `validate_paper_issues.py` ALLOWED_PHASES 加入 "Video"
- [x] 8.11 測試更新（VD 行斷言 + required phases + 59/59 通過）

---

## 審閱區塊
- 開始日期: 2026-03-13
- S1-S6 完成日期: 2026-03-13
- Phase 4d 完成日期: 2026-03-13
- 結果: 全部完成，59/59 測試通過
