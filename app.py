import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from prophet import Prophet
from docx import Document
import io

# 1. 페이지 설정 및 다크모드 대응
st.set_page_config(page_title="전자상거래 수출입 예측", layout="wide")

# 2. 모델 상세 설명 (커서/클릭 대응)
with st.expander("ℹ️ [설명] 각 예측 모형에 대한 상세 안내 (클릭하여 확인)"):
    st.markdown("""
    * **Exponential Smoothing (지수평활법):** 과거 데이터에 가중치를 두어 평균을 내는 방식. 최근 데이터가 중요할 때 유리합니다.
    * **ARIMA / SARIMA:** 시계열 데이터의 자기상관관계를 분석하는 정석 모델. 계절성 분석에 강합니다.
    * **Facebook Prophet:** 휴일, 이벤트, 시계열의 급격한 변화를 자동으로 감지하는 비즈니스 최적화 모델.
    * **XGBoost / Random Forest:** 머신러닝 기법으로, 복잡한 비선형 패턴을 학습하는 데 탁월합니다.
    """)

# 3. 사이드바 설정
with st.sidebar:
    st.header("📂 설정 및 업로드")
    uploaded_file = st.file_uploader("관세청 엑셀 파일 업로드", type=['xlsx'])
    
    st.subheader("⏱️ 기간 설정")
    pred_period = st.select_slider("향후 예측 기간", options=[3, 6, 12], value=12)
    
    st.subheader("🤖 모델 선택")
    selected_models = st.multiselect("예측 모형 (복수 선택 가능)", 
                                    ["Prophet", "Exponential Smoothing"], 
                                    default=["Prophet"])

# 4. 데이터 로드 함수 (에러 해결 핵심)
def load_data(file):
    # 관세청 엑셀은 '전자상거래 수출', '전자상거래 수입' 시트명을 가짐
    try:
        exp_df = pd.read_excel(file, sheet_name='전자상거래 수출')
        imp_df = pd.read_excel(file, sheet_name='전자상거래 수입')
        
        for df in [exp_df, imp_df]:
            # '기간' 컬럼을 '날짜'로 인식 (2024.01 -> 2024-01-01)
            df['날짜'] = pd.to_datetime(df['기간'].astype(str).str.replace('.', '-'))
            # 금액 데이터 숫자 변환 (콤마 제거)
            if '금액' in df.columns:
                df['금액'] = df['금액'].replace({',': ''}, regex=True).astype(float)
            if '건수' in df.columns:
                df['건수'] = df['건수'].replace({',': ''}, regex=True).astype(float)
        return exp_df, imp_df
    except Exception as e:
        st.error(f"엑셀 구조가 예상과 다릅니다: {e}")
        return None, None

# 5. 메인 분석 및 그래프
if uploaded_file:
    exp_df, imp_df = load_data(uploaded_file)
    
    if exp_df is not None:
        st.subheader("📈 수출입 금액 추이 및 예측 ($)")
        
        fig = go.Figure()
        
        # 실제 데이터 그래프
        fig.add_trace(go.Scatter(x=exp_df['날짜'], y=exp_df['금액'], name="수출 실적 ($)", line=dict(color='#1f77b4')))
        fig.add_trace(go.Scatter(x=imp_df['날짜'], y=imp_df['금액'], name="수입 실적 ($)", line=dict(color='#ff7f0e')))
        
        # 간단한 Prophet 예측 예시 (수출 기준)
        if "Prophet" in selected_models:
            m = Prophet()
            m.fit(exp_df[['날짜', '금액']].rename(columns={'날짜': 'ds', '금액': 'y'}))
            future = m.make_future_dataframe(periods=pred_period, freq='MS')
            forecast = m.predict(future)
            
            fig.add_trace(go.Scatter(x=forecast['ds'].iloc[-pred_period:], y=forecast['yhat'].iloc[-pred_period:], 
                                     name="수출 예측치", line=dict(dash='dot')))
            # 신뢰 구간 범위 표시
            fig.add_trace(go.Scatter(x=forecast['ds'].iloc[-pred_period:], y=forecast['yhat_upper'].iloc[-pred_period:],
                                     fill=None, mode='lines', line_color='rgba(0,0,0,0)', showlegend=False))
            fig.add_trace(go.Scatter(x=forecast['ds'].iloc[-pred_period:], y=forecast['yhat_lower'].iloc[-pred_period:],
                                     fill='tonexty', mode='lines', line_color='rgba(0,0,0,0)', fillcolor='rgba(100,100,100,0.2)', name="예측 범위"))

        fig.update_layout(hovermode="x unified", template="plotly_white", xaxis_title="연월", yaxis_title="금액 (USD)")
        st.plotly_chart(fig, use_container_width=True)

        # 6. Word 보고서 저장 버튼
        if st.button("📥 Word 보고서 저장"):
            doc = Document()
            doc.add_heading('전자상거래 수출입 분석 보고서', 0)
            doc.add_paragraph(f'분석 기간: {exp_df["날짜"].min()} ~ {exp_df["날짜"].max()}')
            doc.add_paragraph(f'총 수출 금액: ${exp_df["금액"].sum():,.0f}')
            
            buffer = io.BytesIO()
            doc.save(buffer)
            st.download_button(label="파일 다운로드", data=buffer.getvalue(), file_name="Report.docx")
else:
    st.info("좌측 사이드바에서 관세청 엑셀 파일을 업로드해 주세요.")