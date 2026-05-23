# genecr-gui

Windows-friendly GUI wrapper for the genecr pipeline. Designed for non-CLI users.

## Run (development)

```powershell
python C:\Projects\genecr\gui\genecr-gui.pyw
```

或雙擊 `.pyw` 檔（Windows 會用 `pythonw.exe` 執行，不會開 console 視窗）。

## 前置

依賴 genecr runtime 已安裝在 `~/.gemini/skills/genecr`（或 `.claude` / `.codex` / `.copilot`）。
GUI 會自動偵測已安裝 host，並切到對應的 genecr runtime。

## 功能

- 大型文字框輸入 brief
- 自動偵測 host（Gemini / Claude / Codex / Copilot）+ 對應 runtime
- 7 step 即時進度（⬜ → ⏳ → ✅）
- 完成後列出產出檔案，按鈕可直接開啟（HTML 走瀏覽器、MD 走系統預設）
- 「資料夾」按鈕開 Explorer 並選中該檔

## 後續

- Phase 2：PyInstaller 打包 → `genecr-gui.exe`（免裝 Python）
- Phase 3：bootstrap 腳本（winget 裝 Node/Python/Git + clone genecr + 引導 Gemini 登入）
- Phase 4：Inno Setup 包成 `genecr-installer.exe`
