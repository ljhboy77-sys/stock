import asyncio
import pandas as pd
import FinanceDataReader as fdr
import sys
import os
import configparser
import re
from telethon import TelegramClient
from kiwipiepy import Kiwi
from collections import Counter
from datetime import datetime, timedelta, timezone

# 한국 시간
KST = timezone(timedelta(hours=9))

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

try:
    API_ID = int(config['TELEGRAM']['api_id'])
    API_HASH = config['TELEGRAM']['api_hash']
except:
    API_ID = 35360614
    API_HASH = '36f413dbaa03648679d3a3db53d0cf76'

SESSION_NAME = 'streamlit_session'
print("✅ [1] 시스템 가동 (중복 제거 + DART 링크)")

# 공시 채널
DART_CHANNELS = ['rassiro_gongsi', 'dart_notify', 'kind_disclosure']

# 전체 감시 채널
TARGET_CHANNELS = [
    'rassiro_gongsi', 'dart_notify', 'kind_disclosure',
    'economy_trending', 'fast_economy_news', 'rassiro_channel', 'stock_breaking_news',
    'sentinel_main', 'real_time_news', 'korean_stock_news', 'news_check', 'issue_link'
]

BLACKLIST_STOCKS = {'삼성증권', 'NH투자증권', '한국투자증권', '미래에셋증권', '키움증권', '스팩', '리츠', '우B'}
NOISE_STOCKS = {'시장', '금융', '증권', '투자', '매수', '매도', '추천', '비중', '전망', '분석', '이슈', '테마', '섹터'}
ALERT_KEYWORDS = ['잠정실적', '영업이익', '매출액', '유상증자', '무상증자', '합병', '분할', '공개매수', '공급계약', '수주', '임상', '승인', '체결', '특허', '무상', '배당', '자사주']
STOP_KEYWORDS = {'상승','하락','뉴스','종목','주가','특징','오후','오전','오늘','내일','이번','관련'}
ABSOLUTE_IGNORE = ['광고', '무료', '입장', '클릭', '비트코인', '코인']

PRICE_MAP = {}
ALERT_HISTORY = []

def load_alert_history():
    global ALERT_HISTORY
    if os.path.exists("alert_history.csv"):
        try:
            df = pd.read_csv("alert_history.csv")
            ALERT_HISTORY = df.to_dict('records')
        except: ALERT_HISTORY = []

def get_krx_map():
    global PRICE_MAP
    try:
        df_krx = fdr.StockListing('KRX')
        for idx, row in df_krx.iterrows():
            name = row['Name']
            if any(x in name for x in BLACKLIST_STOCKS): continue
            price = row['Close'] if 'Close' in row else 0
            change = 0.0
            if 'ChagesRatio' in row: change = row['ChagesRatio']
            elif 'Change' in row: change = row['Change']
            PRICE_MAP[name] = {'Code': row['Code'], 'Price': price, 'Change': change}
        return set(PRICE_MAP.keys())
    except: return set()

def save_db(stock_map, kiwi):
    global PRICE_MAP, ALERT_HISTORY
    now_kst = datetime.now(KST).strftime('%H:%M:%S')

    if stock_map:
        sorted_stocks = sorted(stock_map.items(), key=lambda x: len(x[1]), reverse=True)
        final_rank = []
        final_search = []
        for rank, (s, ctx) in enumerate(sorted_stocks, 1):
            try:
                info = PRICE_MAP.get(s)
                price = info['Price'] if info else 0
                rate = info['Change'] if info else 0.0
                blob = " ".join(ctx)
                kws = [t.form for t in kiwi.tokenize(blob[:1000]) if t.tag.startswith('NN') or (t.tag=='SL' and len(t.form)>2)]
                valid_kws = [w for w in kws if len(w) >= 2 and w not in STOP_KEYWORDS]
                reason = ", ".join([w for w, _ in Counter(valid_kws).most_common(3)])
                if not reason: reason = "뉴스참조"
                
                data_row = {'Rank': rank, 'Stock': s, 'Buzz': len(ctx), 'Price': price, 'Change': rate, 'Trend': "-", 'Theme': reason, 'Context': " || ".join(ctx[:5]), 'Time': now_kst}
                final_search.append(data_row)
                if rank <= 30: final_rank.append(data_row)
            except: continue
        try:
            pd.DataFrame(final_rank).to_csv("market_data.csv", index=False, encoding='utf-8-sig')
            pd.DataFrame(final_search).to_csv("search_db.csv", index=False, encoding='utf-8-sig')
        except: pass

    if ALERT_HISTORY:
        df_hist = pd.DataFrame(ALERT_HISTORY).sort_values(by='Time', ascending=False).head(300)
        df_hist.to_csv("alert_history.csv", index=False, encoding='utf-8-sig')

async def collect():
    print("✅ 감시 중...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try: await client.connect()
    except: return
    if not await client.is_user_authorized(): return

    stock_names = get_krx_map()
    if not stock_names: return
    
    load_alert_history()
    kiwi = Kiwi()
    stock_map = {} 
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=3)
    
    for i, ch in enumerate(TARGET_CHANNELS):
        try:
            ent = await client.get_entity(ch)
            async for m in client.iter_messages(ent, limit=100):
                if m.text and len(m.text) > 2:
                    if m.date and m.date < cutoff_date: break 
                    if any(bad in m.text for bad in ABSOLUTE_IGNORE): continue
                    
                    msg_time_kst = m.date.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 링크 추출
                    url_match = re.search(r'(https?://\S+)', m.text)
                    link = url_match.group(0) if url_match else None

                    found_stocks_in_msg = []
                    for s in stock_names:
                        if s in m.text:
                            found_stocks_in_msg.append(s)
                            if s not in stock_map: stock_map[s] = []
                            if m.text not in stock_map[s]: stock_map[s].append(m.text)

                    # [핵심 수정] DART 공시 저장 로직 (중복 제거)
                    if any(dc in ch for dc in DART_CHANNELS):
                        for s in found_stocks_in_msg:
                            # 1. 키워드 찾기
                            found_kws = [k for k in ALERT_KEYWORDS if k in m.text]
                            if not found_kws: found_kws = ['공시'] # 키워드 없으면 기본값
                            
                            # 2. 키워드를 하나로 합침 (예: "매출액, 영업이익")
                            combined_keyword = ", ".join(found_kws)

                            # 3. 이미 저장된 '같은 시간 + 같은 종목'이 있는지 체크
                            is_exist = any(x['Stock'] == s and x['Time'] == msg_time_kst for x in ALERT_HISTORY)
                            
                            if not is_exist:
                                new_alert = {
                                    'Time': msg_time_kst, 
                                    'Stock': s, 
                                    'Keyword': combined_keyword, # 합쳐진 키워드 저장
                                    'Content': m.text[:100],
                                    'Link': link if link else "없음"
                                }
                                ALERT_HISTORY.append(new_alert)
                                print(f"🚨 [DART] {s} : {combined_keyword}")

        except: continue
        if (i+1) % 5 == 0: save_db(stock_map, kiwi)

    save_db(stock_map, kiwi)
    await client.disconnect()

async def main_loop():
    while True:
        try: await collect()
        except: pass
        print("💤 30초 대기...")
        await asyncio.sleep(30)

if __name__ == '__main__':
    try: asyncio.run(main_loop())
    except: pass
