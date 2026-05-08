import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from prophet import Prophet
import io

st.set_page_config(page_title="전자상거래 수출입 예측", layout="wide")

def load_korea_customs_data(file):
    try:
        # 5행부터 데이터가 시작되므로 header=4 (0부터 시작하므로 5행은 4)
        df = pd.read_excel(file, header=4)
        
        # 엑셀의 실제 컬럼명인 '연월'을 '날짜'로 변환
        # '2024.01' 형식을 처리
        df['날짜'] = pd.to_datetime(df['연월'].astype(str).str.replace('.', '-'))
        
        # 천 단위 콤마(,) 제거 및 숫자 변환
        cols_to_fix = ['수출건수', '수출금액', '수입건수', '수입금액']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"엑셀을 읽는 중 오류 발생: {e}")
        return None

# --- UI 레이아웃 ---
st.title("📊 전자상거래 수출입 수요예측 시스템")

with st.sidebar:
    uploaded_file = st.file_uploader("관세청 '국가별 전자상거래 수출입' 엑셀 업로드", type=['xlsx'])
    pred_period = st.select_slider("예측 기간 (개월)", options=[3, 6, 12], value=12)

if uploaded_file:
    df = load_korea_customs_data(uploaded_file)
    
    if df is not None:
        # 1. 지표 요약 (Metric)
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("총 수출 금액", f"${df['수출금액'].sum():,.0f}")
        with col2: st.metric("총 수입 금액", f"${df['수입금액'].sum():,.0f}")
        with col3: st.metric("총 수출 건수", f"{df['수출건수'].sum():,.0f}건")
        with col4: st.metric("총 수입 건수", f"{df['수입건수'].sum():,.0f}건")

        # 2. 통합 그래프 (수입/수출 금액)
        st.subheader("📈 수출입 금액 추이 및 향후 1년 예측")
        
        fig = go.Figure()
        # 실제 데이터
        fig.add_trace(go.Scatter(x=df['날짜'], y=df['수출금액'], name="수출 실적 ($)", line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['날짜'], y=df['수입금액'], name="수입 실적 ($)", line=dict(color='red')))

        # Prophet 예측 (수출 금액 예시)
        m_exp = Prophet()
        m_exp.fit(df[['날짜', '수출금액']].rename(columns={'날짜': 'ds', '수출금액': 'y'}))
        future = m_exp.make_future_dataframe(periods=pred_period, freq='MS')
        forecast = m_exp.predict(future)
        
        # 예측 데이터 추가
        fig.add_trace(go.Scatter(x=forecast['ds'].iloc[-pred_period:], y=forecast['yhat'].iloc[-pred_period:], 
                                 name="수출 예측치", line=dict(dash='dot', color='cyan')))

        fig.update_layout(hovermode="x unified", template="plotly_white", xaxis_title="연월", yaxis_title="금액 ($)")
        st.plotly_chart(fig, use_container_width=True)

        # 3. 데이터 상세 보기
        with st.expander("🔍 업로드된 데이터 확인"):
            st.write(df.sort_values('날짜', ascending=False))