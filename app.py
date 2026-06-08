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

# [1] 화면 레이아웃 및 기본 액자 스타일 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .pdf-preview-container {
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px;
        background-color: #F8FAFC;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("⚠️ OpenAI API Key를 확인해 주세요.")

def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
    except: score = 0
    if score >= 90: return "S"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    else: return "D"

system_prompt = "매쓰플랫 리포트를 분석하여 학생명, 학교, 학년, 평가일자, 종합점수, 단원별성취도, 우수/취약유형 3개씩을 JSON으로 추출해라."

def create_academy_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=25, bottomMargin=40)
    story = []

    font_filename = "NANUMGOTHIC.TTF"
    if os.path.exists(font_filename):
        pdfmetrics.registerFont(TTFont('CustomFont', font_filename))
        font_name = 'CustomFont'
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        font_name = 'HeiseiMin-W3'

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T', fontName=font_name, fontSize=18, alignment=1, textColor=colors.white)
    body_style = ParagraphStyle('B', fontName=font_name, fontSize=9, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BC', fontName=font_name, fontSize=9, alignment=1)
    section_style = ParagraphStyle('S', fontName=font_name, fontSize=12, textColor=colors.HexColor('#1E3A8A'))

    story.append(Spacer(1, 5))
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 신규생 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
    t_banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')), ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_banner)
    story.append(Spacer(1, 10))

    info_data = [
        [Paragraph('<b>학 생 명</b>', body_center), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>학 교 명</b>', body_center), Paragraph(data.get('school_name', ''), body_style),
         Paragraph('<b>학 년</b>', body_center), Paragraph(data.get('student_grade', ''), body_style)],
        [Paragraph('<b>종합 점수</b>', body_center), Paragraph(f"<b>{data.get('score', '')} 점</b>", body_style),
         Paragraph('<b>진단 레벨</b>', body_center), Paragraph(f"<b>{calculate_math_level(data.get('score', '0'))} Level</b>", body_style),
         Paragraph('', body_style), Paragraph('', body_style)]
    ]
    t_info = Table(info_data, colWidths=[515/6]*6)
    t_info.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (0,1), colors.HexColor('#F8FAFC')), ('SPAN', (3,1), (5,1))]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ====================================================================
# [핵심 수술] 세션 상태 초기화 및 입력창/코멘트 영역을 조건문 밖으로 완전히 분리
# ====================================================================
st.title("📊 코넬수학 레벨테스트 결과지 시스템")

# 세션 초기 가동화
if "student_name" not in st.session_state: st.session_state["student_name"] = ""
if "school_name" not in st.session_state: st.session_state["school_name"] = ""
if "student_grade" not in st.session_state: st.session_state["student_grade"] = ""
if "report_month" not in st.session_state: st.session_state["report_month"] = ""
if "score" not in st.session_state: st.session_state["score"] = ""
if "teacher_comment" not in st.session_state: st.session_state["teacher_comment"] = ""

uploaded_file = st.file_uploader("📥 매쓰플랫 진단평가 리포트 PDF 업로드", type=["pdf"])

# 파일이 처음 올라왔을 때 딱 한 번만 세션 값을 새로고침하는 안전 장치
if uploaded_file is not None:
    if st.session_state.get("last_uploaded_file") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 리포트 파일 분석 중..."):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                images_base64 = []
                for page in doc:
                    pix = page.get_pixmap(dpi=130)
                    images_base64.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
                
                content = [{"type": "text", "text": system_prompt}]
                for img_b64 in images_base64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": content}],
                    response_format={"type": "json_object"}
                )
                res_json = json.loads(response.choices[0].message.content)
                
                # 분석 결과를 세션에 즉시 안전하게 박제
                st.session_state["student_name"] = res_json.get("student_name", "")
                st.session_state["school_name"] = res_json.get("school_name", "")
                st.session_state["student_grade"] = res_json.get("student_grade", "")
                st.session_state["report_month"] = res_json.get("report_month", "")
                st.session_state["score"] = res_json.get("score", "")
                st.session_state["teacher_comment"] = res_json.get("teacher_comment", "")
                st.session_state["last_uploaded_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 실패: {str(e)}")

# [조건문 외부 배치] 파일 유무와 상관없이 화면에 무조건 항시 고정되는 1·2단계 수정 패널
st.markdown("### 📋 1단계: 기본 정보 검토 및 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=st.session_state["student_name"])
sch_name = col2.text_input("학교명", value=st.session_state["school_name"])
s_grade = col3.text_input("학년", value=st.session_state["student_grade"])

col4, col5 = st.columns(2)
r_month = col4.text_input("평가 일자", value=st.session_state["report_month"])
score_val = col5.text_input("종합 점수", value=str(st.session_state["score"]))

st.markdown("### 🦅 2단계: 종합 코멘트 관리")
teacher_comment = st.text_area("코넬 분석 Comment", value=st.session_state["teacher_comment"], height=150)

# 실시간 갱신 데이터 바인딩
final_data = {
    "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
    "report_month": r_month, "score": score_val, "teacher_comment": teacher_comment
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### 🖨️ 3단계: 성적표 결과지 발행")
    st.download_button(
        label="💾 코넬수학 진단평가 결과지 PDF 다운로드",
        data=pdf_bin,
        file_name=f"코넬수학_진단결과분석지_{s_name}.pdf",
        mime="application/pdf",
        type="primary"
    )

with right_col:
    st.markdown("### 🔍 발급 예정 결과지 미리보기")
    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
    # 크롬 및 웨일 브라우저 차단 정책을 뚫어내는 우회 임베딩 스크립트 고정
    base64_pdf = base64.b64encode(pdf_bin.getvalue()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0" width="100%" height="800px" style="border:none;"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
