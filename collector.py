import streamlit as st
import pandas as pd
import time
import altair as alt
import os
import configparser
from datetime import datetime

st.set_page_config(page_title="Awake Desk", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Awake 전용 마켓 스캐너 (KST)")

# ==========================================
# [수정] 검색창과 탭을 반복문 '밖'으로 뺐습니다 (에러 해결 핵심)
# ==========================================
with st.sidebar:
    st.header("📥 데이터 다운로드")
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button("🚨 공시 기록 받기", f, file_name="awake_history.csv", mime="text/csv")
        except: pass

# 탭과 검색창을 미리 한 번만 만듭니다.
tab1, tab2 = st.tabs(["📊 실시간 랭킹", "🚨 Awake 속보 누적"])
search_keyword = st.sidebar.text_input("🔍 종목 검색", key="sidebar_search")

# 화면을 계속 바꿔줄 빈 공간(Placeholder)을 만듭니다.
tab1_placeholder = tab1.empty()
tab2_placeholder = tab2.empty()

# 팝업 중복 방지
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
# [메인] 반복문 시작
# ==========================================
while True:
    df_rank, df_search, df_history = load_data()
    
    # 1. 긴급 팝업 (Toast)
    if not df_history.empty:
        recent_alerts = df_history.head(3)
        for i, row in recent_alerts.iterrows():
            unique_id = f"{row['Stock']}_{row['Keyword']}_{row['Time']}"
            if unique_id not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 [Awake] {row['Stock']} : {row['Keyword']}", icon="🔥")
                st.session_state['viewed_alerts'].add(unique_id)

    # 2. 탭 1 (랭킹) 내용 채우기
    with tab1_placeholder.container():
        if not df_rank.empty:
            # 검색 기능
            if search_keyword and not df_search.empty:
                filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
                if not filtered.empty:
                    row = filtered.iloc[0]
                    st.info(f"🔎 [검색] {row['Stock']} | {int(row['Price']):,}원 ({row['Change']:.2f}%) | 언급 {row['Buzz']}회")
                    st.caption(f"관련뉴스: {str(row['Context'])[:200]}...")

            c_chart, c_table = st.columns([1, 2])
            with c_chart:
                st.subheader("📊 언급량 Top 10")
                chart = alt.Chart(df_rank.head(10)).mark_bar().encode(
                    x=alt.X('Buzz', title=None), y=alt.Y('Stock', sort='-x', title=None),
                    color=alt.Color('Buzz', legend=None)
                ).properties(height=500)
                st.altair_chart(chart, use_container_width=True)
            
            with c_table:
                st.subheader("📋 실시간 랭킹")
                display_df = df_rank[['Rank', 'Stock', 'Price', 'Change', 'Buzz', 'Theme', 'Time']].copy()
                styled_df = display_df.style.map(color_change, subset=['Change']).format({
                    'Price': "{:,.0f}", 'Change': "{:+.2f}%"
                })
                st.dataframe(styled_df, use_container_width=True, height=500, hide_index=True)
        else:
            st.warning("데이터 수집 대기 중... (잠시만 기다려주세요)")

    # 3. 탭 2 (공시) 내용 채우기
    with tab2_placeholder.container():
        st.subheader("🚨 Awake 속보 / 공시 누적")
        if not df_history.empty:
            st.dataframe(
                df_history[['Time', 'Stock', 'Keyword', 'Content']],
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "Time": st.column_config.Column("시간(KST)", width="medium"),
                    "Stock": st.column_config.Column("종목", width="small"),
                    "Keyword": st.column_config.Column("재료", width="small"),
                    "Content": st.column_config.Column("내용", width="large"),
                }
            )
        else:
            st.info("아직 감지된 데이터가 없습니다.")

    time.sleep(1)
