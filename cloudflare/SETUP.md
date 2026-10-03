# Cloudflare 免費額度內的私人網站（尚未部署）

使用 Workers Static Assets + D1 + Access；不建立 Render 付費主機，不使用R2。Workers請求、CPU、D1儲存與讀寫、Access席次皆受免費額度限制；依Cloudflare最新方案檢查。GitHub私人儲存庫Actions也受免費分鐘數限制，全市場每日掃描需監看用量，不保證長期零費用。遇到額度不足先停用排程或降低頻率，不自動升級付費。

先註冊 https://dash.cloudflare.com/sign-up ，建立Zero Trust免費方案與team domain；依介面可能需付款方式驗證，選方案前看清楚0元及額度。尚未執行任何建立主機或付款操作。

1. Cloudflare建立D1資料庫 tw-breakout-results，記錄實際ID後填入 wrangler.jsonc；執行schema.sql建立state_chunks表。
2. 從私人GitHub部署 cloudflare/worker.mjs，設定Workers Static Assets為cloudflare/site；run_worker_first=true，D1 binding名稱RESULTS。部署前需填妥實際database_id。最初未設Access環境值時會拒絕服務503，不會公開資料。
3. Zero Trust建立Self-hosted Access應用，保護完整Worker主機名稱及所有路徑。啟用One-time PIN，Allow規則只能是使用者確認的單一電子郵件；不可使用Everyone、Bypass或公開資料路徑。Workers子網域若不允許此保護方式，需使用已擁有網域的Worker路由；沒有網域時先停下，不自行購買。
4. 為同一主機的/_update建立更精確的第二Access應用，僅允許Service Auth服務Token。複製兩個應用各自的AUD。Worker環境設定ACCESS_TEAM_DOMAIN、ACCESS_AUD、UPDATE_ACCESS_AUD、ALLOWED_EMAIL。ALLOWED_EMAIL必須先經使用者確認，不可猜測拼字。
5. Cloudflare秘密設定UPDATE_SECRET存入隨機更新密鑰；相同值存入GitHub Secret RADAR_UPDATE_SECRET。Service Token的Client ID與Secret存入GitHub Secrets CF_ACCESS_CLIENT_ID、CF_ACCESS_CLIENT_SECRET。不可提交任何密鑰到儲存庫或貼到聊天。
6. GitHub Variables設RADAR_URL為实际HTTPS網址；完成保護測試後才把CLOUDFLARE_SYNC_ENABLED設true。執行私人daily-scan.yml，確認上傳成功；原私人下載報告仍保留。

驗證：登出瀏覽器需看到Access登入而非App；直接/api/state、guide.html、icon.svg、manifest亦須受保護。Worker另驗JWT簽章、期限、issuer、aud與email，不能只依賴未驗證的header。錯誤email拒絕；未授權/_update拒絕。頁面及資料設定no-store。

網站登入後讀取最新已完成掃描，GitHub Actions平日台北16:30排程（可能延遲）。手動掃描連到私人GitHub Actions；完成後頁面每10秒讀取更新，無須重新下載檔案。

本地測試：node --test cloudflare/worker.test.mjs
