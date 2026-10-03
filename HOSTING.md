# 登入保護的私人網站

本版本以私人單一密碼登入，不提供註冊；所有頁面、資料JSON與API皆由伺服器驗證。瀏覽器使用HttpOnly、Secure、SameSite Cookie，12小時到期。正式部署需 HTTPS；設定不足時拒絕啟動。

啟動命令：python serve_private.py（或 Dockerfile）。

必要秘密環境變數：
- APP_PASSWORD_HASH：auth.password_hash() 產生的 scrypt 雜湊。密碼不可放程式碼、儲存庫或對話。
- SESSION_SECRET：至少32字元的隨機簽章密鑰；更換會讓現有登入失效。

其他設定：DATA_DIR 指向主機持久磁碟，PORT 由主機提供，COOKIE_SECURE 預設1（正式網站不可設0）。設定雜湊可在可信本機使用 getpass 讀取密碼後呼叫 auth.password_hash；輸出雜湊僅填入主機的秘密設定，不提交 GitHub。

主機必須持續運行，才保證平日台北時間16:30的內建掃描；會休眠的方案不能保證這項排程。正式建立資源前應確認所選方案費用。資料來源仍可能限流，請查看日期與覆蓋率。

現有 GitHub 私人下載報告流程保留；新網站採 server.py 的 API，開啟後讀取最新已完成結果，掃描中保留上次結果。不保證即時行情，也不會因登入而自動完成首次全市場扫描。

部署前檢查：python -m unittest discover -s tests -v。部署後要重新驗證未登入資料URL回傳401或導向登入，並檢查HTTPS Cookie及排程。

## Render部署

render.yaml是部署設定範本，目前沒有建立Render資源。它選擇持續運行的Starter主機及1GB持久磁碟，兩者可能收費；套用前先核對Render最新費用。Render需要獲准讀取此私人GitHub儲存庫。

建立Blueprint時，APP_PASSWORD填入自己選擇的12–256字元密碼，只在Render秘密設定頁輸入。SESSION_SECRET由Render自動產生。網站首次登入使用該密碼，不要把密碼貼到聊天或提交GitHub。APP_PASSWORD_HASH可作為進階替代；程式優先使用雜湊設定。
