"""Upload completed scan through Access service authentication; never print secrets."""
import os
from pathlib import Path
import urllib.request
required=['RADAR_URL','CF_ACCESS_CLIENT_ID','CF_ACCESS_CLIENT_SECRET','RADAR_UPDATE_SECRET']
if any(not os.environ.get(k) for k in required):raise SystemExit('缺少私人網站上傳設定')
url=os.environ['RADAR_URL'].rstrip('/')
if not url.startswith('https://'):raise SystemExit('上傳網址必須使用 HTTPS')
body=Path('static/state.json').read_bytes()
request=urllib.request.Request(url+'/_update',data=body,method='PUT',headers={
    'Content-Type':'application/json','CF-Access-Client-Id':os.environ['CF_ACCESS_CLIENT_ID'],
    'CF-Access-Client-Secret':os.environ['CF_ACCESS_CLIENT_SECRET'],
    'Authorization':'Bearer '+os.environ['RADAR_UPDATE_SECRET']})
with urllib.request.urlopen(request,timeout=60) as response:
    if response.status!=200:raise SystemExit('更新失敗')
print('私人網站已更新')
