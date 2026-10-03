import os, threading, time, urllib.parse
from collections import deque
from http.server import ThreadingHTTPServer
import server
from auth import COOKIE, TTL, valid_session, verify_password, issue_session

PASSWORD_HASH=os.environ.get('APP_PASSWORD_HASH','')
SESSION_SECRET=os.environ.get('SESSION_SECRET','')
COOKIE_SECURE=os.environ.get('COOKIE_SECURE','1')=='1'
ATTEMPTS=deque()
ATTEMPT_LOCK=threading.Lock()
LOGIN='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>登入｜台股突破雷達</title><style>body{background:#0b101a;color:#dfe8f5;font:16px/1.8 system-ui;max-width:420px;margin:10vh auto;padding:24px}input,button{font:inherit;box-sizing:border-box;width:100%;padding:12px;margin:12px 0;border:1px solid #34445d;border-radius:8px}button{background:#75edc7;color:#092b24;cursor:pointer}</style><h1>台股突破雷達</h1><p>私人網站，請輸入你的密碼。</p><form method="post" action="/login"><label for="password">密碼</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="256"><button>登入</button></form></html>'''

class PrivateHandler(server.Handler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        super().end_headers()
    def authenticated(self):return valid_session(self.headers.get('Cookie'),SESSION_SECRET)
    def html(self,body,status=200):
        content=body.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/healthz':return self.send_json({'ok':True})
        if path=='/login':return self.html(LOGIN)
        if not self.authenticated():
            if path.startswith('/api/'):return self.send_json({'error':'請先登入'},401)
            self.send_response(303);self.send_header('Location','/login');self.end_headers();return
        super().do_GET()
    def do_HEAD(self):
        if not self.authenticated():self.send_response(401);self.end_headers();return
        super().do_HEAD()
    def do_POST(self):
        origin=self.headers.get('Origin')
        scheme='https' if COOKIE_SECURE else 'http'
        if origin!=scheme+'://'+self.headers.get('Host',''):
            return self.send_json({'error':'請從本站操作'},403)
        path=urllib.parse.urlsplit(self.path).path
        if path=='/login':
            with ATTEMPT_LOCK:
                now=time.time()
                while ATTEMPTS and ATTEMPTS[0]<now-900:ATTEMPTS.popleft()
                if len(ATTEMPTS)>=10:return self.html(LOGIN+'<p>嘗試過多，請15分鐘後再試。</p>',429)
                ATTEMPTS.append(now)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2048:raise ValueError()
                fields=urllib.parse.parse_qs(self.rfile.read(length).decode())
                password=fields.get('password',[''])[0]
                if len(password)>256 or not verify_password(password,PASSWORD_HASH):
                    return self.html(LOGIN+'<p>登入失敗。</p>',401)
            except (ValueError,UnicodeDecodeError):return self.html(LOGIN+'<p>登入失敗。</p>',401)
            with ATTEMPT_LOCK:ATTEMPTS.clear()
            token=issue_session(SESSION_SECRET)
            self.send_response(303);self.send_header('Location','/')
            self.send_header('Set-Cookie',f'{COOKIE}={token}; Path=/; Max-Age={TTL}; HttpOnly; SameSite=Strict'+('; Secure' if COOKIE_SECURE else ''))
            self.end_headers();return
        if not self.authenticated():return self.send_json({'error':'請先登入'},401)
        if path=='/logout':
            self.send_response(303);self.send_header('Location','/login')
            self.send_header('Set-Cookie',f'{COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict'+('; Secure' if COOKIE_SECURE else ''))
            self.end_headers();return
        super().do_POST()

if __name__=='__main__':
    if not PASSWORD_HASH.startswith('scrypt$') or len(SESSION_SECRET)<32:
        raise SystemExit('拒絕啟動：需設定 APP_PASSWORD_HASH 與至少32字元的 SESSION_SECRET。')
    threading.Thread(target=server.scheduler,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),PrivateHandler).serve_forever()
