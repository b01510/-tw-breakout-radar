"""Run once in GitHub Actions and prepare a static Pages artifact."""
import json
from pathlib import Path
import server

server.scan()
data=server.read('results.json',None)
if not data:
    raise SystemExit('掃描失敗且沒有可保留的歷史結果：'+str(server.STATE['errors']))
out=Path('static/state.json')
out.write_text(json.dumps(dict(state=server.STATE,config=server.CONFIG,data=data),ensure_ascii=False))
print(f"行情 {data['date']}；完成 {data['coverage']}/{data['total']}；訊號 {len(data['results'])}；缺漏 {data['incomplete']}")
