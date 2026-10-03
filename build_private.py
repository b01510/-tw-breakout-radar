"""Package an offline dashboard; never publish this report to Pages."""
import json
from pathlib import Path
import shutil
out=Path('private-report');out.mkdir(exist_ok=True)
state=json.loads(Path('static/state.json').read_text())
payload=json.dumps(state,ensure_ascii=False).replace('<','\\u003c')
html=Path('static/index.html').read_text()
html=html.replace('<script>','<script>window.SCAN_SNAPSHOT='+payload+';</script><script>',1)
html=html.replace('async function api(url,body){',"async function api(url,body){if(url==='/api/state'&&window.SCAN_SNAPSHOT)return window.SCAN_SNAPSHOT;")
html=html.replace("$('scan').onclick=async()=>{try{await api('/api/scan',{});await refresh()}catch(e){$('notice').textContent=e.message}};", "$('scan').onclick=()=>window.open('https://github.com/b01510/-tw-breakout-radar/actions/workflows/daily-scan.yml','_blank','noopener');")
html=html.replace('<form method="post" action="/logout"><button>登出</button></form>','')
(out/'index.html').write_text(html)
shutil.copyfile('static/guide.html',out/'guide.html')
print('私人離線報告已產生；只能透過私人儲存庫 Actions 下載')
