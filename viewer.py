import streamlit as st
import pandas as pd
import time
import altair as alt
import os
import configparser
from datetime import datetime

st.set_page_config(page_title="DART Scanner", layout="wide")

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ DART/KIND 공시 속보 (Link)")

with st.sidebar:
    st.header("📥 데이터 다운로드")
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button("🚨 공시 파일 받기", f, file_name="dart_history.csv", mime="text/csv")
        except: pass

tab1, tab2 = st.tabs(["📊 실시간 랭킹", "🚨 DART 공시 (Clickable)"])
search_keyword = st.sidebar.text_input("🔍 종목 검색", key="unique_search")

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

while True:
    df_rank, df_search, df_history = load_data()
    
    # 1. 팝업
    if not df_history.empty:
        recent_alerts = df_history.head(3)
        for i, row in recent_alerts.iterrows():
            unique_id = f"{row['Stock']}_{row['Time']}"
            if unique_id not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 [공시] {row['Stock']}", icon="📢")
                st.session_state['viewed_alerts'].add(unique_id)

    # 2. 랭킹 탭
    with tab1_placeholder.container():
        if not df_rank.empty:
            if search_keyword and not df_search.empty:
                filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
                if not filtered.empty:
                    row = filtered.iloc[0]
                    st.info(f"🔎 [검색] {row['Stock']} | {int(row['Price']):,}원 ({row['Change']:.2f}%)")
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
            st.warning("데이터 수집 대기 중...")

    # 3. 공시 탭 (링크 기능 추가)
    with tab2_placeholder.container():
        st.subheader("🚨 DART/KIND 실시간 공시")
        if not df_history.empty:
            # [핵심] LinkColumn 사용
            st.data_editor(
                df_history[['Time', 'Stock', 'Content', 'Link']],
                use_container_width=True,
                height=800,
                hide_index=True,
                column_config={
                    "Time": st.column_config.Column("시간(KST)", width="medium"),
                    "Stock": st.column_config.Column("종목", width="small"),
                    "Content": st.column_config.Column("공시 내용", width="large"),
                    "Link": st.column_config.LinkColumn(
                        "원문 링크", 
                        display_text="🔗 바로가기", # 링크 대신 이 글자가 보임
                        width="small"
                    ),
                },
                disabled=True # 편집 불가, 클릭만 가능
            )
        else:
            st.info("아직 감지된 공시가 없습니다.")

    time.sleep(1)
