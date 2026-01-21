import streamlit as st
import pandas as pd
import time
import altair as alt
import os
from datetime import datetime

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="HedgeFund Desk", layout="wide")

# 2. 스타일 설정
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ 기관용 마켓 스캐너 (DART & KST)")

# =========================================================
# [핵심 수정] 위젯(검색창, 버튼, 탭)은 반복문 '밖'에서 딱 한 번만 생성
# =========================================================

# 사이드바 설정
with st.sidebar:
    st.header("📥 데이터")
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button("🚨 공시 파일", f, "dart_history.csv", "text/csv")
        except: pass
    
    st.markdown("---")
    # [중요] 검색창을 여기서 만듭니다. (에러 원인 해결)
    search_keyword = st.text_input("🔍 종목 검색", key="sidebar_search_fixed_unique")

# 탭 생성 (반복문 밖)
tab1, tab2 = st.tabs(["📊 실시간 랭킹", "🚨 DART 공시 (Link)"])

# 내용이 채워질 빈 공간(Placeholder) 미리 확보
tab1_placeholder = tab1.empty()
tab2_placeholder = tab2.empty()

# 팝업 알림 상태 저장
if 'viewed_alerts' not in st.session_state:
    st.session_state['viewed_alerts'] = set()

# 데이터 로드 함수
def load_data():
    df_rank = pd.DataFrame()
    df_search = pd.DataFrame()
    df_history = pd.DataFrame()
    if os.path.exists("market_data.csv"):
        try: df_rank = pd.read_csv("market_data.csv")
        except: pass
    if os.path.exists("search_db.csv"):
        try: df_search = pd.read_csv("search_db.csv")
        except: pass
    if os.path.exists("alert_history.csv"): 
        try: df_history = pd.read_csv("alert_history.csv")
        except: pass
    return df_rank, df_search, df_history

def color_change(val):
    if isinstance(val, str): return ''
    color = '#ff4b4b' if val > 0 else '#4b88ff' if val < 0 else 'white'
    return f'color: {color}; font-weight: bold;'

# =========================================================
# [반복문 시작] 이제 데이터만 갱신합니다 (위젯 생성 X)
# =========================================================
while True:
    df_rank, df_search, df_history = load_data()
    
    # 1. 팝업 알림
    if not df_history.empty:
        recent = df_history.head(3)
        for i, row in recent.iterrows():
            uid = f"{row['Stock']}_{row['Time']}"
            if uid not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 {row['Stock']} : {row['Keyword']}", icon="📢")
                st.session_state['viewed_alerts'].add(uid)

    # 2. 랭킹 탭 업데이트
    with tab1_placeholder.container():
        # 검색 결과 표시
        if search_keyword and not df_search.empty:
            filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
            if not filtered.empty:
                r = filtered.iloc[0]
                st.info(f"🔎 {r['Stock']} | {int(r['Price']):,}원 | {r['Theme']}")

        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("📊 언급량 Top 10")
            if not df_rank.empty:
                chart = alt.Chart(df_rank.head(10)).mark_bar().encode(
                    x=alt.X('Buzz', title=None), y=alt.Y('Stock', sort='-x', title=None),
                    color=alt.Color('Buzz', legend=None)
                ).properties(height=500)
                st.altair_chart(chart, use_container_width=True)
        
        with c2:
            st.subheader("📋 실시간 랭킹")
            if not df_rank.empty:
                display = df_rank[['Rank', 'Stock', 'Price', 'Change', 'Buzz', 'Theme']].style.map(color_change, subset=['Change']).format({'Price':"{:,.0f}", 'Change':"{:+.2f}%"})
                st.dataframe(display, use_container_width=True, height=500, hide_index=True)
            else:
                st.warning("데이터 수집 대기 중...")

    # 3. DART 탭 업데이트 (링크 기능)
    with tab2_placeholder.container():
        st.subheader("🚨 DART 실시간 공시")
        if not df_history.empty:
            st.data_editor(
                df_history[['Time', 'Stock', 'Keyword', 'Content', 'Link']],
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "Time": st.column_config.Column("시간(KST)", width="medium"),
                    "Stock": st.column_config.Column("종목", width="small"),
                    "Keyword": st.column_config.Column("재료", width="medium"),
                    "Content": st.column_config.Column("요약", width="large"),
                    "Link": st.column_config.LinkColumn("링크", display_text="🔗 이동", width="small"),
                },
                disabled=True
            )
        else:
            st.info("아직 공시가 없습니다.")

    time.sleep(1)
