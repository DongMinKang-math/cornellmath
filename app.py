import streamlit as st
import json
import os
import io
import base64
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle

# 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="wide")
st.markdown("""<style>.pdf-preview-container { border: 2px solid #E2E8F0; border-radius: 12px; padding: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }</style>""", unsafe_allow_html=True)

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("API Key 확인 필요")

def calculate_math_level(score):
    try: s = int(''.join(filter(str.isdigit, str(score)))); return "S" if s >= 90 else "A" if s >= 80 else "B" if s >= 70 else "C" if s >= 60 else "D"
    except: return "D"

def create_academy_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=25, bottomMargin=40)
    story = []
    
    # 폰트 설정 (생략된 부분은 기존과 동일하게 유지)
    styles = getSampleStyleSheet()
    # [리포트 구성 로직은 기존 함수와 동일]
    # (여기 함수 내용은 원장님 깃허브 코드에 있던 기존 함수를 그대로 쓰시면 됩니다)
    doc.build(story)
    buffer.seek(0)
    return buffer

st.title("📊 코넬수학 레벨테스트 결과지 시스템")
uploaded_file = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    # 1. AI 분석
    if "ocr_result" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.spinner("분석 중..."):
            import fitz
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            # ... (기존 분석 로직 동일)
            st.session_state["ocr_result"] = {"student_name": "강주원", "chapters": [], "teacher_comment": "코멘트"}
            st.session_state["file_name"] = uploaded_file.name
    
    res = st.session_state["ocr_result"]
    
    # 2. 정보 입력
    col1, col2, col3 = st.columns(3)
    s_name = col1.text_input("학생 이름", value=res.get("student_name", ""))
    # ... (나머지 입력창)
    
    st.markdown("---")
    final_data = {"student_name": s_name, "teacher_comment": "코멘트 내용"}
    pdf_bin = create_academy_report(final_data)
    
    # 3. 레이아웃 (오류 없는 버전)
    left, right = st.columns([1, 1.2])
    with left:
        st.download_button("💾 PDF 다운로드", data=pdf_bin, file_name="result.pdf", mime="application/pdf")
    with right:
        st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
        b64 = base64.b64encode(pdf_bin.getvalue()).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="800px"></iframe>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
