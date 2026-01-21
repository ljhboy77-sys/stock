import streamlit as st
import pandas as pd
import time
import altair as alt
import os
from datetime import datetime

# 1. 페이지 설정 (가장 먼저!)
st.set_page_config(page_title="HedgeFund Desk", layout="wide")

# 2. 스타일
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ 기관용 마켓 스캐너 (DART & KST)")

# ==========================================
# [핵심] 검색창과 버튼을 '반복문 밖'에 배치 (에러 원천 차단)
# ==========================================
with st.sidebar:
    st.header("📥 데이터 추출")
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button("🚨 공시 파일 받기", f, "dart_history.csv", "text/csv")
        except: pass
    
    st.markdown("---")
    # 검색창을 여기에 한 번만 만듭니다.
    search_keyword = st.text_input("🔍 종목 검색", key="sidebar_search_final")

# 탭도 밖에서 한 번만 만듭니다.
tab1, tab2 = st.tabs(["📊 실시간 랭킹", "🚨 DART 공시 (Link)"])

# 내용이 들어갈 빈 공간 만들기
tab1_placeholder = tab1.empty()
tab2_placeholder = tab2.empty()

if 'viewed_alerts' not in st.session_state:
    st.session_state['viewed_alerts'] = set()

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

# ==========================================
# [반복문 시작] 데이터만 계속 갈아끼움
# ==========================================
while True:
    df_rank, df_search, df_history = load_data()
    
    # 1. 팝업 알림
    if not df_history.empty:
        recent = df_history.head(3)
        for i, row in recent.iterrows():
            uid = f"{row['Stock']}_{row['Time']}"
            if uid not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 {row['Stock']} 공시 발생!", icon="📢")
                st.session_state['viewed_alerts'].add(uid)

    # 2. 랭킹 탭 채우기
    with tab1_placeholder.container():
        # 검색 결과 표시용
        if search_keyword and not df_search.empty:
            filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
            if not filtered.empty:
                row = filtered.iloc[0]
                st.info(f"🔎 {row['Stock']} | {int(row['Price']):,}원 | {row['Theme']}")

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

    # 3. DART 탭 채우기 (링크 기능 포함)
    with tab2_placeholder.container():
        st.subheader("🚨 DART 실시간 공시")
        if not df_history.empty:
            # 링크 컬럼 설정
            st.data_editor(
                df_history[['Time', 'Stock', 'Content', 'Link']],
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "Time": st.column_config.Column("시간(KST)", width="medium"),
                    "Stock": st.column_config.Column("종목", width="small"),
                    "Content": st.column_config.Column("공시 내용", width="large"),
                    "Link": st.column_config.LinkColumn(
                        "원문", display_text="🔗 바로가기", width="small"
                    ),
                },
                disabled=True
            )
        else:
            st.info("아직 공시가 없습니다. (수집기는 작동 중)")

    time.sleep(1)
