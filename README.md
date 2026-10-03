# 台股突破雷達

手機網站： https://b01510.github.io/-tw-breakout-radar/

平日台北時間16:30（UTC 08:30）透過 GitHub Actions 掃描；實際啟動可能延遲，休市日顯示最近交易日。

手動更新：Actions → 每日台股掃描與網站部署 → Run workflow。頁面的手動掃描按鈕會開啟此頁，需 GitHub 登入並具儲存庫操作權。

初次 push 發佈已完成的歷史掃描快照（有資料日期與缺漏標記）；排程與手動執行會重新取得實際行情。

設定：Settings → Pages → Build and deployment → Source 選 GitHub Actions。掃描參數位於 server.py 的 CONFIG；修改後手動執行工作流程生效。

股票名單：TWSE、TPEx；日線：Yahoo Finance。非即時行情，外部來源可能限流或失敗，請查看資料日期、覆蓋率及缺漏明細。全部來源失敗時保留已發佈的歷史快照，不會假造今日結果。

型態：新高附近、上升趨勢、10–30日平台、波動收斂、開盤跳空、量能與收盤確認。突破後凍結原平台上緣，跌回即取消資格；評分不是獲利機率。

GitHub Pages 公開顯示行情與規則；不使用任何帳號密鑰。若儲存庫長期沒有活動，GitHub 可能停用排程，需在 Actions 重新啟用。
