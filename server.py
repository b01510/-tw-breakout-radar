import json, os, threading, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from engine import evaluate, DEFAULTS, VERSION

ROOT=Path(__file__).parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
TW=timezone(timedelta(hours=8))
LOCK=threading.Lock()
STATE={'running':False,'done':0,'total':0,'errors':[]}
CONFIG=DEFAULTS.copy()
def read(name, fallback):
    try: return json.loads((DATA/name).read_text())
    except (FileNotFoundError,json.JSONDecodeError): return fallback
def save(name,value):
    p=DATA/(name+'.tmp');p.write_text(json.dumps(value,ensure_ascii=False));p.replace(DATA/name)
CONFIG.update(read('config.json',{}))
def get(url):
    import gzip
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                content=r.read()
                if r.headers.get('Content-Encoding')=='gzip': content=gzip.decompress(content)
                return json.loads(content)
        except Exception:
            if attempt==2: raise
            time.sleep(1+attempt)
def universe():
    sources=[('上市','TW','https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'),
             ('上櫃','TWO','https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes')]
    stocks=[]
    for market,suffix,url in sources:
        try:
            rows=get(url)
            save('universe-'+suffix+'.json',rows)
        except Exception as e:
            STATE['errors'].append(dict(code=market+'名單',message=str(e)))
            rows=read('universe-'+suffix+'.json',[])
        for x in rows:
            code=x.get('Code') or x.get('SecuritiesCompanyCode')
            name=x.get('Name') or x.get('CompanyName')
            if code and len(code)==4 and code.isdigit() and not code.startswith('0'):
                stocks.append(dict(code=code,name=name,market=market,symbol=f'{code}.{suffix}'))
    if not stocks: raise RuntimeError('官方名單為空，請檢查來源格式')
    return list({s['symbol']:s for s in stocks}.values())
def history(stock):
    p=DATA/(stock['symbol']+'.json')
    today=datetime.now(TW).strftime('%Y-%m-%d')
    cached=read(p.name,{})
    complete=datetime.now(TW).hour>=14
    if cached.get('fetchedDate')==today and cached.get('complete')==complete: return cached['bars']
    raw=get('https://query1.finance.yahoo.com/v8/finance/chart/'+stock['symbol']+'?range=1y&interval=1d')
    r=raw['chart']['result'][0]; q=r['indicators']['quote'][0];bars=[]
    for i,ts in enumerate(r.get('timestamp',[])):
        d=datetime.fromtimestamp(ts,TW).strftime('%Y-%m-%d')
        if d==today and datetime.now(TW).hour<14: continue
        vals={k:q[k][i] for k in ['open','high','low','close','volume']}
        if any(v is None for v in vals.values()) or vals['low']<=0: continue
        bars.append(dict(date=d,**vals))
    save(p.name,dict(fetchedDate=today,complete=complete,bars=bars))
    return bars
def scan():
    global STATE
    with LOCK:
        if STATE['running']: return
        STATE={'running':True,'done':0,'total':0,'errors':[]}
    config=CONFIG.copy(); results=[]; dates=[]; successful=0
    try:
        stocks=universe();STATE['total']=len(stocks)
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures={pool.submit(history,s):s for s in stocks}
            for future in as_completed(futures):
                stock=futures[future]
                try:
                    bars=future.result()
                    if len(bars)<125: raise ValueError('有效日線不足125根')
                    successful+=1;dates.append(bars[-1]['date'])
                    signal=evaluate(bars,config)
                    if signal: results.append(dict(**stock,**signal))
                except Exception as e: STATE['errors'].append(dict(code=stock['code'],message=str(e)[:180]))
                STATE['done']+=1
        if not successful: raise RuntimeError('全部歷史行情讀取失敗；保留上次結果')
        result=dict(strategyVersion=VERSION,updatedAt=datetime.now(TW).isoformat(),date=max(dates),oldestDate=min(dates),
                    incomplete=successful<len(stocks) or bool(STATE['errors']),
                    coverage=successful,total=len(stocks),errors=STATE['errors'],config=config,
                    source='TWSE / TPEx 股票名單；Yahoo Finance 日線（非即時）',
                    results=sorted(results,key=lambda x:x['score'],reverse=True))
        save('results.json',result)
        save('last-run.json',{'day':datetime.now(TW).strftime('%Y-%m-%d')})
    except Exception as e: STATE['errors'].append(dict(code='掃描',message=str(e)))
    finally: STATE['running']=False
def scheduler():
    while True:
        now=datetime.now(TW);day=now.strftime('%Y-%m-%d')
        if now.weekday()<5 and (now.hour,now.minute)>=(16,30) and read('last-run.json',{}).get('day')!=day:
            # Record attempts to avoid retrying a failed source every minute.
            save('last-run.json',{'day':day});scan()
        time.sleep(30)
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'static'),**kwargs)
    def send_json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)))
        self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=='/api/state':return self.send_json(dict(state=STATE,config=CONFIG,data=read('results.json',None)))
        super().do_GET()
    def do_POST(self):
        if self.path=='/api/scan':
            threading.Thread(target=scan,daemon=True).start();return self.send_json({'started':True})
        if self.path=='/api/config':
            if STATE['running']:return self.send_json({'error':'掃描中無法變更設定'},409)
            try:
                c=json.loads(self.rfile.read(min(int(self.headers.get('Content-Length',0)),4096)))
                bounds={'width':(.01,.5),'gap':(0,.1),'volume':(1,10),'near':(.01,.2),'monitor':(1,60)}
                for k,(lo,hi) in bounds.items():
                    if k in c and (not isinstance(c[k],(int,float)) or not lo<=c[k]<=hi): raise ValueError('參數超出範圍')
                CONFIG.update({k:c[k] for k in bounds if k in c});CONFIG['monitor']=int(CONFIG['monitor'])
                save('config.json',CONFIG);return self.send_json(CONFIG)
            except Exception as e:return self.send_json({'error':str(e)},400)
        self.send_json({'error':'找不到操作'},404)
if __name__=='__main__':
    threading.Thread(target=scheduler,daemon=True).start()
    port=int(os.environ.get('PORT',8080))
    print(f'台股突破雷達：http://localhost:{port}（台北時間平日16:30掃描）',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
