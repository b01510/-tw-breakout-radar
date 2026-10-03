# 台股突破雷達

網站：https://b01510.github.io/-tw-breakout-radar/

已恢復公開 GitHub Pages。任何人都能瀏覽網站與掃描结果；不需要Cloudflare或Render。

GitHub Actions平日台北時間16:30（UTC08:30）每日掃描，啟動可能延遲。手動掃描按鈕連至GitHub Actions，登入並選Run workflow。完成後網站讀取最新結果。

策略v2.1：縮量收斂預警、一般放量突破（跳空另標籤）、前高確認及跌回平台淘汰。舊失敗事件不遮住新突破，原平台與前高固定追蹤。

進出場指南：網站guide.html。指引為操作範例，非已驗證最佳交易參數。先檢查行情日期、覆蓋率與失敗明細；評分不是獲利機率。

驗證：python -m unittest discover -s tests -v。運錩2069回放只使用截至2026/9/8資料，當日可篩出平台22.15、量能約4.74倍的突破。

Render、Cloudflare與私人報告相關檔案是未啟用的替代部署準備，現行daily-scan.yml不連接這些服務。
