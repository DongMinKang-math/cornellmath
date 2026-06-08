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

# [1] 기본 설정 및 액자 스타일
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .pdf-preview-container {
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
    st.error("⚠️ OpenAI API Key가 설정되지 않았습니다.")

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

# [2] AI 데이터 추출 프롬프트 (정기평가 & 오답노트 모두 대응)
system_prompt = """
너는 코넬수학전문학원의 원장이야. 매쓰플랫 리포트를 정밀 분석하여 JSON 데이터를 생성해라.
특히 4페이지의 유형별 정오답 데이터를 스캔해서 우수/취약 유형 3개씩을 리스트로 추출해라.
내신끗(오답노트) 파일일 경우 점수가 없을 수 있으니, 정답률을 기반으로 0~100 사이의 점수를 추론해라.
[JSON 형식]:
{
  "student_name": "이름", "school_name": "학교", "student_grade": "학년",
  "report_month": "YYYY/MM/DD", "score": "점수(숫자만)",
  "chapters": [{"name": "단원명", "achievement": "성취도숫자"}],
  "difficulty_analysis": {"하": "숫자", "중하": "숫자", "중": "숫자", "상": "숫자", "최상": "숫자"},
  "mastery_types": ["우수유형1", "2", "3"],
  "weakness_types": ["취약유형1", "2", "3"],
  "teacher_comment": "학부모 상담용 전문 코멘트(5문장)"
}
"""

# [3] PDF 리포트 생성 함수 (로고, 그래프 포함)
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
    info_style = ParagraphStyle('I', fontName=font_name, fontSize=9, alignment=2, textColor=colors.HexColor('#64748B'))
    body_style = ParagraphStyle('B', fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BC', fontName=font_name, fontSize=9, alignment=1)
    section_style = ParagraphStyle('S', fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor('#1E3A8A'))

    # 배너
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 신규생 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
    t_banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')), ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_banner)
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>시험 일자:</b> {data.get('report_month', '')}", info_style))
    story.append(Spacer(1, 5))

    # 학생 정보 (1단계 복구 데이터)
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

    # 단원별 성취 분석 (막대 그래프)
    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 5))
    ch_rows = [[Paragraph('평가 진단 영역', body_center), Paragraph('성취도 성장 지표', body_center), Paragraph('성취도', body_center)]]
    for ch in data.get("chapters", []):
        pct = int(ch['achievement'])
        ch_rows.append([Paragraph(ch['name'], body_style), "■"*(pct//10), Paragraph(f"{pct}%", body_center)])
    t_ch = Table(ch_rows, colWidths=[200, 250, 65])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    # 우수/취약 유형
    u_style = ParagraphStyle('U', fontName=font_name, fontSize=11, textColor=colors.HexColor('#1E3A8A'))
    w_style = ParagraphStyle('W', fontName=font_name, fontSize=11, textColor=colors.HexColor('#C53030'))
    
    m_list = [Paragraph(f"• {t}", body_style) for t in data.get("mastery_types", [])]
    w_list = [Paragraph(f"• {t}", body_style) for t in data.get("weakness_types", [])]
    
    type_data = [[ [Paragraph("<b>■ 대표 우수 유형</b>", u_style), Spacer(1,5)] + m_list, [Paragraph("<b>■ 대표 취약 유형</b>", w_style), Spacer(1,5)] + w_list ]]
    t_type = Table(type_data, colWidths=[250, 250])
    story.append(t_type)
    story.append(Spacer(1, 15))

    # 코멘트 박스 (최하단)
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 5))
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (0,0), 10)]))
    story.append(t_comment)

    # 로고 추가 함수
    def add_logo(canvas, doc):
        canvas.saveState()
        if os.path.exists("cornell.png"):
            canvas.drawImage("cornell.png", 242, 10, width=110, height=42, mask='auto')
        canvas.restoreState()

    doc.build(story, onFirstPage=add_logo, onLaterPages=add_logo)
    buffer.seek(0)
    return buffer

# ====================================================================
# [4] 메인 UI (1단계 학생정보, 2단계 코멘트 완벽 복구)
# ====================================================================
st.title("📊 코넬수학 레벨테스트 결과지 시스템")
st.markdown("매쓰플랫 PDF를 업로드하여 고품격 학원 전용 결과지를 생성하세요.")

# 세션 관리 (데이터 보존)
if "ocr_data" not in st.session_state: st.session_state["ocr_data"] = {}
if "last_file" not in st.session_state: st.session_state["last_file"] = None

uploaded_file = st.file_uploader("📥 매쓰플랫 PDF 리포트 업로드", type=["pdf"])

if uploaded_file and uploaded_file != st.session_state["last_file"]:
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
            st.session_state["ocr_data"] = json.loads(resp.choices[0].message.content)
            st.session_state["last_file"] = uploaded_file
        except Exception as e:
            st.error(f"분석 실패: {e}")

# [핵심 수술] 입력창 무조건 노출 및 데이터 고정
res = st.session_state["ocr_data"]

st.markdown("### 📋 1단계: 학생 정보 등록 및 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=res.get("student_name", ""), key="sn")
sch_name = col2.text_input("학교명", value=res.get("school_name", ""), key="sc")
s_grade = col3.text_input("학년", value=res.get("student_grade", ""), key="sg")

col4, col5 = st.columns(2)
r_date = col4.text_input("평가 일자", value=res.get("report_month", ""), key="rd")
s_score = col5.text_input("종합 점수", value=str(res.get("score", "")), key="ss")

st.markdown("### 🦅 2단계: 코넬 분석 코멘트 수정")
teacher_comment = st.text_area("분석 Comment (자유롭게 수정 가능)", value=res.get("teacher_comment", ""), height=150, key="tc")

# 실시간 변경 데이터 취합
final_data = {
    **res, "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
    "report_month": r_date, "score": s_score, "teacher_comment": teacher_comment
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### 🖨️ 3단계: 결과지 발행")
    st.download_button(label="💾 코넬수학 결과지 PDF 다운로드", data=pdf_bin, file_name=f"코넬수학_{s_name}.pdf", mime="application/pdf", type="primary")

with right_col:
    st.markdown("### 🔍 결과지 미리보기")
    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
    # 보안 차단을 우회하는 이미지 스트림 방식 프리뷰
    try:
        import fitz
        p_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in p_doc:
            st.image(page.get_pixmap(dpi=150).tobytes("png"), use_container_width=True)
    except:
        st.info("파일을 업로드하면 미리보기가 생성됩니다.")
    st.markdown('</div>', unsafe_allow_html=True)
