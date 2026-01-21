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
print("✅ [1] 시스템 가동 (생중계 모드)")

# 선생님이 주신 아이디
TARGET_CHANNELS = ['darthacking'] 

ALERT_KEYWORDS = ['잠정실적', '영업이익', '매출액', '유상증자', '무상증자', '합병', '분할', '공개매수', '공급계약', '수주', '임상', '승인', '체결', '특허', '무상', '배당', '자사주', 'MOU', '협력', '속보', '특징주', '공시']

BLACKLIST_STOCKS = {'삼성증권', 'NH투자증권', '한국투자증권', '미래에셋증권', '키움증권', '신한투자증권', '신한지주', '하나증권', '하나금융지주', '메리츠증권', '메리츠금융지주', 'KB증권', 'KB금융', '대신증권', '한화투자증권', '유안타증권', '교보증권', '현대차증권', '하이투자증권', 'SK증권', '신영증권', 'IBK투자증권', '유진투자증권', '이베스트투자증권', 'LS증권', 'DB금융투자', '다올투자증권', '부국증권', '상상인증권', '케이프투자증권', 'BNK투자증권', 'DS투자증권', '한양증권', '흥국증권', '흥국화재', 'DB손해보험', 'DB', '상상인', '상상인저축은행', '한국금융지주', '우리금융지주', 'BNK금융지주', 'DGB금융지주', 'JB금융지주', '리서치', '금융투자', '투자증권', '스팩', '제호', '제호스팩', '기업인수목적'}

NOISE_STOCKS = {'전방', '대상', '지구', '신세계', '가스', '전선', '화재', '국보', '백산', '나노', '레이', '보물', '유진', '대원', '효성', '선진', '동방', '서원', '대성', '우진', '한화', '두산', '삼성', '현대', 'SK', 'LG', '부국', '국내', '미국', '중국', '일본', '해외', '시장', '금융', '증권', '투자', '매수', '매도', '추천', '비중', '전망', '분석', '이슈', '테마', '섹터', '코스피', '코스닥', '지수', '상한가', '하한가', '베뉴지', '홀딩스', '그룹', '우', '채널', '입장', '보기', '매매', '공부', '참여', '문의', '상담', '종목', '주식', '코리아', '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주', '흥국', '상상인', '다올', '케이프', '신영', '교보', '현대차', 'DB', '하이', '이베스트', '유안타', '메리츠', '하나', '신한', 'KB', 'NH', 'TP', 'Target', 'Price', 'EPS', 'PER', 'PBR', 'ROE', 'EBITDA'}

STOP_KEYWORDS = {'상승','하락','뉴스','종목','주가','특징','오후','오전','오늘','내일','이번','관련','검색','키워드','순위','링크','참고','공시','속보','예정','전망','개시','체결','확인','시간','대비','기준','달성','기록','규모','진행','제공','무료','증가','감소','영향','기대','우려','지속','유지','확대','축소','돌파','시작','엔터', '하이브', '보합', '매수', '매도', '목표', '리포트', '브리핑', '의견', '제시', '신규', '발표', '개최', '참여', '가능', '여부', '분기', '실적', '영업', '이익', '매출', '순이익', '흑자', '적자', '전년', '동기', '직전', '최대', '최저', '경신', '연속', '상장', '거래', '체결', '현황', '동향', '분석', '이유', '원인', '배경', '결과', '내용', '상황', '상태', '수준', '정도', '부분', '분야', '업계', '시장', '글로벌', '국내', '해외', '미국', '중국', '유럽', '일본', '한국', '정부', '정책', '지원', '육성', '강화', '추진', '계획', '방안', '마련', '도입', '시행', '적용', '운영', '관리', '감독', '규제', '완화', '개선', '개혁', '혁신', '성장', '발전', '확보', '유치', '체결', '협력', '제휴', '공동', '개발', '출시', '공개', '선보', '공급', '계약', '수주', '납품', '생산', '판매', '수출', '수입', '소비', '수요', '공급', 'TP', 'Target', 'Price', '목표가', '목표주가', '적정주가', '투자의견', '괴리율', '상향', '하향', '조정', '커버리지', '유지', '중립', '비중', '확대', '축소', 'Outperform', 'Buy', 'Hold', 'Sell', 'Neutral', 'Trading', 'Consensus', '컨센서스', '추정', '예상', '부합', '하회', '상회'}

ABSOLUTE_IGNORE = ['검색', '키워드', '순위', '랭킹', '인기글', '실시간', '링크', '모음', '정리', '광고', '무료', '입장', '클릭', 'Touch', '비트코인', '코인']

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
            if name in NOISE_STOCKS or name in BLACKLIST_STOCKS: continue
            if '스팩' in name or '리츠' in name or '우B' in name: continue
            price = row['Close'] if 'Close' in row else 0
            change = 0.0
            for col in ['ChagesRatio', 'ChangesRatio', 'Change']:
                if col in row:
                    change = row[col]
                    break
            PRICE_MAP[name] = {'Code': row['Code'], 'Price': price, 'Change': change}
        print(f"✅ KRX 다운로드 성공! ({len(PRICE_MAP)}개)")
        return set(PRICE_MAP.keys())
    except Exception as e:
        print(f"⚠️ KRX 다운로드 실패: {e}")
        return set()

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
                valid_kws = []
                for w in kws:
                    if len(w) < 2: continue
                    if w in STOP_KEYWORDS or w in ABSOLUTE_IGNORE or w in BLACKLIST_STOCKS: continue
                    if re.match(r'^[a-zA-Z]+$', w) and w.upper() in [x.upper() for x in STOP_KEYWORDS]: continue
                    valid_kws.append(w)
                reason = ", ".join([w for w, _ in Counter(valid_kws).most_common(3)])
                if not reason: reason = "뉴스참조"
                news_context = " || ".join(ctx[:5]) 
                data_row = {'Rank': rank, 'Stock': s, 'Buzz': len(ctx), 'Price': price, 'Change': rate, 'Trend': "-", 'Theme': reason, 'Context': news_context, 'Time': now_kst}
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
    print("\n✅ 텔레그램 서버 접속 중...")
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
        print(f"👉 [진입 시도] 채널: {ch}") # [수정] 진입 확인
        try:
            ent = await client.get_entity(ch)
            print(f"   🔓 {ch} 접속 성공! 메시지 읽는 중...") # [수정] 접속 성공 확인
            
            msg_count = 0
            async for m in client.iter_messages(ent, limit=10): # [수정] 일단 10개만 테스트로 읽어봄
                if m.text:
                    msg_count += 1
                    # [핵심] 봇이 읽고 있는 실제 메시지를 화면에 뿌림
                    print(f"   📩 [읽음] {m.text[:30].replace('\n', ' ')}...") 

                    msg_time_kst = m.date.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S')
                    found_stocks_in_msg = []
                    for s in stock_names:
                        if s in m.text:
                            if '증권' in s or '스팩' in s or '리츠' in s: continue 
                            found_stocks_in_msg.append(s)
                            if s not in stock_map: stock_map[s] = []
                            if m.text not in stock_map[s]: stock_map[s].append(m.text)
                    
                    for s in found_stocks_in_msg:
                        for keyword in ALERT_KEYWORDS:
                            if keyword in m.text:
                                is_exist = any(x['Stock'] == s and x['Keyword'] == keyword and x['Time'] == msg_time_kst for x in ALERT_HISTORY)
                                if not is_exist:
                                    new_alert = {'Time': msg_time_kst, 'Stock': s, 'Keyword': keyword, 'Content': m.text[:150]}
                                    ALERT_HISTORY.append(new_alert)
                                    print(f"🚨 [발견!] {s}:{keyword}")
            
            if msg_count == 0:
                print(f"   ⚠️ 경고: {ch} 채널에 글이 하나도 없습니다! (혹시 아이디 틀림?)")
                
        except Exception as e: 
            print(f"   ❌ 접속 실패 ({ch}): {e}") # [수정] 접속 실패 시 에러 출력
            continue
        save_db(stock_map, kiwi)

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
