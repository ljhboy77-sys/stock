import streamlit as st
import pandas as pd
import time
import altair as alt
import os
import configparser
from datetime import datetime

st.set_page_config(page_title="HedgeFund Desk", layout="wide")

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ 기관용 마켓 스캐너 (DART & KST)")

# 사이드바 (다운로드)
with st.sidebar:
    st.header("📥 데이터 추출 (Excel)")
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button("🚨 공시/속보 기록 받기", f, file_name=f"공시기록_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        except: pass
    
    if os.path.exists("market_data.csv"):
        try:
            with open("market_data.csv", "rb") as f:
                st.download_button("📊 실시간 랭킹 받기", f, file_name=f"실시간랭킹_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        except: pass

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
# [핵심 수정] UI 요소를 반복문 밖으로 이동!
# ==========================================
tab1, tab2 = st.tabs(["📊 실시간 랭킹 (Main)", "🚨 DART 공시 (Link)"])

# 검색창도 밖으로!
search_keyword = st.sidebar.text_input("🔍 종목 검색 (랭킹 탭)", key="unique_sidebar_search")

# 탭 안의 내용을 바꿀 '빈 공간(Container)' 미리 만들기
tab1_placeholder = tab1.empty()
tab2_placeholder = tab2.empty()

if 'viewed_alerts' not in st.session_state:
    st.session_state['viewed_alerts'] = set()

# ==========================================
# 반복문 시작 (내용만 업데이트)
# ==========================================
while True:
    df_rank, df_search, df_history = load_data()
    
    # 팝업 알림
    if not df_history.empty:
        recent_alerts = df_history.head(5)
        for i, row in recent_alerts.iterrows():
            unique_id = f"{row['Stock']}_{row['Time']}"
            if unique_id not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 [DART] {row['Stock']} 공시 발생!", icon="📢")
                st.session_state['viewed_alerts'].add(unique_id)

    # 탭 1 업데이트 (랭킹)
    with tab1_placeholder.container():
        # 상세 분석 표시용 컨테이너
        detail_container = st.container()

        if not df_rank.empty:
            # 검색 로직
            target_row = None
            if search_keyword and not df_search.empty:
                filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
                if not filtered.empty: target_row = filtered.iloc[0]
            
            # 상세 내용 표시 함수
            def show_details(row):
                with detail_container:
                    st.markdown("---")
                    st.markdown(f"### 📄 {row['Stock']} 상세분석")
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("현재가", f"{int(row['Price']):,}원", f"{row['Change']:.2f}%")
                        c2.metric("언급량", f"{row['Buzz']}회")
                        c3.metric("키워드", row['Theme'])
                        c4.metric("갱신(KST)", row['Time'])
                        st.info(f"📰 뉴스: {str(row['Context'])[:300]}...")
                    st.markdown("---")
            
            if target_row is not None:
                show_details(target_row)

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
                display_df = df_rank[['Rank', 'Stock', 'Price', 'Change', 'Buzz', 'Theme']].copy()
                styled_df = display_df.style.map(color_change, subset=['Change']).format({
                    'Price': "{:,.0f}", 'Change': "{:+.2f}%"
                })
                # 데이터프레임 클릭 이벤트
                event = st.dataframe(
                    styled_df, use_container_width=True, height=500, hide_index=True,
                    on_select="rerun", selection_mode="single-row", key="rank_table_tab1"
                )
                if len(event.selection.rows) > 0:
                    show_details(df_rank.iloc[event.selection.rows[0]])
        else:
            st.info("데이터 수집 중... (잠시만 기다려주세요)")

    # 탭 2 업데이트 (공시 & 링크)
    with tab2_placeholder.container():
        st.subheader("🚨 DART/KIND 실시간 공시 (Only DART)")
        if not df_history.empty:
            # [핵심] LinkColumn을 사용하여 클릭 가능한 링크 만들기
            st.data_editor(
                df_history[['Time', 'Stock', 'Content', 'Link']],
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "Time": st.column_config.Column("시간(KST)", width="medium"),
                    "Stock": st.column_config.Column("종목명", width="small"),
                    "Content": st.column_config.Column("공시 내용", width="large"),
                    "Link": st.column_config.LinkColumn(
                        "원문 링크", 
                        display_text="🔗 바로가기", # 주소 대신 이 글자가 보임
                        width="small"
                    ),
                },
                disabled=True # 편집 불가, 클릭만 가능
            )
        else:
            st.info("아직 감지된 DART 공시가 없습니다.")

    time.sleep(1)
