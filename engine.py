"""Causal daily-bar scanner: frozen platform and resistance, no future bars."""
from statistics import mean

VERSION = '2.0'
DEFAULTS = dict(width=.18, gap=.005, volume=1.5, near=.10, monitor=20,
                dry=.7, contraction=.8, convergence=.03, closePosition=.75)

def evaluate(bars, config=None):
    c = {**DEFAULTS, **(config or {})}
    if len(bars) < 125:
        return None
    def tr(i):
        b = bars[i]
        prev = bars[i-1]['close'] if i else b['close']
        return max(b['high']-b['low'], abs(b['high']-prev), abs(b['low']-prev))
    def candidate(i):
        if i < 124: return None
        past, b = bars[:i], bars[i]
        closes = [x['close'] for x in bars[:i+1]]
        ma5, ma10, ma20, ma60 = [mean(closes[-n:]) for n in (5,10,20,60)]
        slope20 = ma20 > mean(closes[-25:-5])
        slope60 = ma60 >= mean(closes[-65:-5])
        if not (b['close'] > ma20 > ma60 and slope20 and slope60): return None
        high120 = max(x['high'] for x in bars[max(0,i-119):i+1])
        if b['close'] < high120*(1-c['near']): return None
        platforms=[]
        for days in range(10,41):
            p=past[-days:]
            hi,lo=max(x['high'] for x in p),min(x['low'] for x in p)
            width=(hi-lo)/lo
            drift=abs(mean(x['close'] for x in p[-5:])/mean(x['close'] for x in p[:5])-1)
            touches=sum(x['high']>=hi*.98 for x in p)
            if width<=c['width'] and drift<=.05 and touches>=2:
                platforms.append((days,hi,lo,width))
        if not platforms: return None
        days,hi,lo,width=platforms[-1]
        dry=mean(x['volume'] for x in past[-5:])/max(1,mean(x['volume'] for x in past[-25:-5]))
        contraction=mean(tr(j) for j in range(i-10,i))/max(1e-9,mean(tr(j) for j in range(i-30,i-10)))
        # Pre-breakout convergence; today's expanded candle must not disqualify a breakout.
        precloses=closes[:-1]
        premas=[mean(precloses[-n:]) for n in (5,10,20)]
        convergence=(max(premas)-min(premas))/precloses[-1]
        v=b['volume']/max(1,mean(x['volume'] for x in past[-20:]))
        strong=(b['close']-b['low'])/(b['high']-b['low']) if b['high']>b['low'] else .5
        upper=(b['high']-max(b['open'],b['close']))/(b['high']-b['low']) if b['high']>b['low'] else .5
        gap=b['open']/hi-1
        setup=dry<=c['dry'] and contraction<=c['contraction'] and convergence<=c['convergence']
        breakout=b['close']>hi and v>=c['volume'] and strong>=c['closePosition'] and b['close']>b['open'] and upper<=.25
        ready=hi*.97<=b['close']<=hi and setup
        if not (breakout or ready): return None
        # Resistance is the historical high BEFORE the platform, frozen at detection.
        before=bars[max(0,i-250):i-days]
        resistance=max((x['high'] for x in before),default=hi)
        resistance=max(resistance,hi)
        checks=[('多頭排列與均線向上',20,True),('接近120日高點3%',10,b['close']>=high120*.97),
                ('10–40日平台、振幅≤15%',10,width<=.15),('整理縮量比≤0.7',15,dry<=c['dry']),
                ('波動收斂比≤0.8',10,contraction<=c['contraction']),('突破前均線差距≤3%',10,convergence<=c['convergence']),
                ('收盤突破平台',10,b['close']>hi),('突破量達設定倍數',10,v>=c['volume']),
                ('紅K、收盤位置≥75%',5,b['close']>b['open'] and strong>=c['closePosition'])]
        return dict(status='今日突破' if breakout else '準備突破',score=sum(w for _,w,ok in checks if ok),
            platformHigh=hi,platformLow=lo,days=days,width=width,volumeRatio=v,gap=gap,
            dryRatio=dry,contractionRatio=contraction,convergence=convergence,closePosition=strong,
            resistance=resistance,close=b['close'],date=b['date'],breakoutDate=b['date'] if breakout else None,
            fullGap=b['low']>hi,gapBreakout=gap>c['gap'],setupConfirmed=setup,
            checks=[dict(label=n,points=w,passed=ok) for n,w,ok in checks])
    latest=bars[-1]
    for i in range(max(124,len(bars)-int(c['monitor'])-1),len(bars)):
        s=candidate(i)
        if not s or not s['breakoutDate']: continue
        after=bars[i+1:]
        failed=next((b for b in after if b['close']<s['platformHigh']),None)
        s.update(close=latest['close'],date=latest['date'],bars=bars[-70:],eligible=not bool(failed))
        s['resistanceDistance']=s['resistance']/latest['close']-1
        if failed:
            s.update(status='疑似假突破',failedDate=failed['date'])
        else:
            confirmations=[]
            for j in range(i,len(bars)):
                b=bars[j]
                ratio=b['volume']/max(1,mean(x['volume'] for x in bars[j-20:j]))
                if b['close']>s['resistance'] and ratio>=c['volume']:
                    confirmations.append(b['date'])
            confirmed=bool(confirmations) and latest['close']>s['resistance']
            if confirmed:
                s.update(status='前高突破',resistanceBreakoutDate=confirmations[0])
            elif after:
                s['status']='前高確認中'
        s['grade']='失效' if failed else ('A級' if s['status']=='前高突破' and s['score']>=80 else '觀察')
        return s
    s=candidate(len(bars)-1)
    if s:
        s.update(bars=bars[-70:],eligible=True,grade='預警',resistanceDistance=s['resistance']/latest['close']-1)
    return s
