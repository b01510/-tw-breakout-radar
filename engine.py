"""Daily-bar platform breakout scanner. All signal calculations use past bars only."""
from statistics import mean

LABELS = ['準備突破', '今日突破', '突破成功續強', '疑似假突破']

def evaluate(bars, config=None):
    c = {'width': .18, 'gap': .005, 'volume': 1.5, 'near': .05, 'monitor': 20}
    c.update(config or {})
    if len(bars) < 125:
        return None
    def candidate(i):
        past, b = bars[:i], bars[i]
        if len(past) < 120: return None
        closes = [x['close'] for x in past] + [b['close']]
        ma20, ma60 = mean(closes[-20:]), mean(closes[-60:])
        slope20 = ma20 > mean(closes[-25:-5])
        slope60 = ma60 > mean(closes[-65:-5])
        trend = b['close'] > ma20 > ma60 and slope20
        high120 = max(x['high'] for x in past[-119:] + [b])
        near = b['close'] >= high120 * (1-c['near'])
        if not (trend and near): return None
        platforms = []
        for days in range(10,31):
            p = past[-days:]
            hi, lo = max(x['high'] for x in p), min(x['low'] for x in p)
            width = (hi-lo)/lo
            drift = abs(mean(x['close'] for x in p[-5:])/mean(x['close'] for x in p[:5])-1)
            touches = sum(x['high'] >= hi*.98 for x in p)
            if width <= c['width'] and drift <= .05 and touches >= 2:
                platforms.append((days,hi,lo,width))
        if not platforms: return None
        days,hi,lo,width = platforms[-1]
        v = b['volume']/max(1,mean(x['volume'] for x in past[-20:]))
        strong = (b['close']-b['low'])/(b['high']-b['low']) if b['high']>b['low'] else .5
        gap = b['open']/hi-1
        checks = [
            ('多頭排列',15,b['close']>ma20>ma60),
            ('均線向上',10,slope20 and slope60),
            ('距60日高點小於3%',15,b['close']>=max(x['high'] for x in past[-59:]+[b])*.97),
            ('10–30日整理',10,True),('平台振幅小於15%',10,width<.15),
            ('收盤突破平台',15,b['close']>hi),('開盤跳空大於1%',5,gap>.01),
            ('突破量達1.5倍',10,v>1.5),('收盤位置達65%',10,strong>=.65)]
        breakout = b['close']>hi and gap>c['gap'] and v>c['volume'] and strong>=.65
        ready = not breakout and hi*.97<=b['close']<=hi
        if not (breakout or ready): return None
        return dict(status=LABELS[1] if breakout else LABELS[0], score=sum(w for _,w,ok in checks if ok),
                    platformHigh=hi,platformLow=lo,days=days,width=width,volumeRatio=v,gap=gap,
                    close=b['close'],date=b['date'],breakoutDate=b['date'] if breakout else None,
                    fullGap=b['low']>hi,checks=[dict(label=n,points=w,passed=ok) for n,w,ok in checks])
    latest = bars[-1]
    # Freeze the first breakout's platform; any later close below it invalidates it.
    for i in range(max(120,len(bars)-c['monitor']-1),len(bars)):
        s = candidate(i)
        if not s or s['status'] != LABELS[1]: continue
        after = bars[i+1:]
        failed = next((b for b in after if b['close']<s['platformHigh']),None)
        s.update(close=latest['close'],date=latest['date'],bars=bars[-70:])
        if failed:
            s.update(status=LABELS[3],failedDate=failed['date'],eligible=False)
        elif after:
            s.update(status=LABELS[2] if latest['close']>max(b['high'] for b in bars[i:-1]) else '突破後守穩',eligible=True)
        else: s['eligible']=True
        return s
    s = candidate(len(bars)-1)
    if s: s.update(bars=bars[-70:],eligible=True)
    return s
