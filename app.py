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

# [1] 기본 페이지 설정 및 명품 액자 테두리 CSS
st.set_page_config(page_title="코넬수학 결과지 시스템", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .report-container {
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 15px;
        background-color: #FFFFFF;
        box-shadow: 0 10px 25px rgba(0,0,0,0.06);
        text-align: center;
        min-height: 800px;
    }
    </style>
    """, unsafe_allow_html=True)

# OpenAI 클라이언트 초기화
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("⚠️ OpenAI API Key가 설정되지 않았습니다. Streamlit Secrets를 확인해 주세요.")

# 레벨 계산 함수
def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
    except: score = 0
    if score >= 90: return "S"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    else: return "D"

# AI 데이터 추출 프롬프트 (정기평가 & 오답노트 완벽 대응)
system_prompt = """
너는 코넬수학전문학원 원장이야. 매쓰플랫 리포트 PDF를 분석해서 JSON 데이터를 생성해.
파일이 '정기평가'라면 점수를 그대로 추출하고, '내신끗(오답노트)'이라서 점수가 없다면 정답률을 기반으로 0~100 사이의 점수를 추론해라.
[반드시 포함할 JSON 필드]:
{
  "student_name": "이름", "school_name": "학교", "student_grade": "학년", "report_month": "YYYY/MM/DD",
  "score": "점수(숫자)", "chapters": [{"name": "단원명", "achievement": "성취도숫자"}],
  "mastery_types": ["우수유형1", "2", "3"], "weakness_types": ["취약유형1", "2", "3"],
  "teacher_comment": "학부모 상담용 전문 코멘트(5문장 내외)"
}
"""

# PDF 결과지 생성 함수 (디자인 강화)
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
    body_style = ParagraphStyle('B', fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BC', fontName=font_name, fontSize=9, alignment=1)
    section_style = ParagraphStyle('S', fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor('#1E3A8A'))

    # 상단 배너
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
    t_banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')), ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_banner)
    story.append(Spacer(1, 10))

    # 학생 정보 섹션
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

    # 단원 성취도 테이블
    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 5))
    ch_rows = [[Paragraph('평가 진단 영역', body_center), Paragraph('성취도 지표', body_center), Paragraph('성취도', body_center)]]
    for ch in data.get("chapters", []):
        pct = int(ch.get('achievement', 0))
        ch_rows.append([Paragraph(ch.get('name', ''), body_style), "■"*(pct//10), Paragraph(f"{pct}%", body_center)])
    t_ch = Table(ch_rows, colWidths=[200, 250, 65])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    # 코멘트 섹션 (최하단)
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    # 로고 추가
    def add_logo(canvas, doc):
        canvas.saveState()
        if os.path.exists("cornell.png"):
            canvas.drawImage("cornell.png", 242, 10, width=110, height=42, mask='auto')
        canvas.restoreState()

    doc.build(story, onFirstPage=add_logo, onLaterPages=add_logo)
    buffer.seek(0)
    return buffer

# ====================================================================
# [메인 화면] 12개 필드 및 입력창 사라짐 현상 완전 해결
# ====================================================================

# 세션 상태 고정 (수정 시 창 사라짐 방지 핵심)
if "ocr_result" not in st.session_state: st.session_state["ocr_result"] = {}
if "last_file_name" not in st.session_state: st.session_state["last_file_name"] = None

uploaded_file = st.file_uploader("📥 매쓰플랫 PDF 결과 리포트 업로드", type=["pdf"])

if uploaded_file and uploaded_file.name != st.session_state["last_file_name"]:
    with st.spinner("🔍 AI 원장님이 리포트 분석 중..."):
        try:
            import fitz
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            imgs = []
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                imgs.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
            
            content = [{"type": "text", "text": system_prompt}]
            for img in imgs:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": content}], response_format={"type": "json_object"})
            st.session_state["ocr_result"] = json.loads(resp.choices[0].message.content)
            st.session_state["last_file_name"] = uploaded_file.name
        except Exception as e:
            st.error(f"분석 실패: {e}")

# [핵심 수술] 입력창을 세션 데이터와 직접 연동하여 항시 고정
res = st.session_state["ocr_result"]

st.markdown("### 📋 1단계: 학생 정보 등록 및 수정")
c1, c2, c3 = st.columns(3)
s_name = c1.text_input("학생 이름", value=res.get("student_name", ""), key="name_input")
sch_name = c2.text_input("학교명", value=res.get("school_name", ""), key="school_input")
s_grade = c3.text_input("학년", value=res.get("student_grade", ""), key="grade_input")

c4, c5 = st.columns(2)
r_date = c4.text_input("평가 일자", value=res.get("report_month", ""), key="date_input")
s_score = c5.text_input("종합 점수", value=str(res.get("score", "")), key="score_input")

st.markdown("### 🦅 2단계: 코넬 분석 코멘트")
t_comment = st.text_area("학부모 상담용 코멘트 (수정 가능)", value=res.get("teacher_comment", ""), height=150, key="comment_input")

# 실시간 데이터 병합
final_data = {
    **res, "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
    "report_month": r_date, "score": s_score, "teacher_comment": t_comment
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left, right = st.columns([1, 1.2])

with left:
    st.markdown("### 🖨️ 3단계: 결과지 발행")
    st.download_button("💾 PDF 결과지 다운로드", data=pdf_bin, file_name=f"코넬수학_{s_name}.pdf", mime="application/pdf", type="primary")

with right:
    st.markdown("### 🔍 결과지 미리보기")
    st.markdown('<div class="report-container">', unsafe_allow_html=True)
    # [핵심 수술] iFrame 대신 이미지 스트림으로 깨짐 현상 완전 해결
    try:
        import fitz
        p_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in p_doc:
            st.image(page.get_pixmap(dpi=150).tobytes("png"), use_container_width=True)
    except:
        st.info("파일을 업로드하면 미리보기가 생성됩니다.")
    st.markdown('</div>', unsafe_allow_html=True)
