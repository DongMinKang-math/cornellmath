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

# [1] 기본 페이지 설정 및 명품 액자 테두리 CSS
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
    }
    </style>
    """, unsafe_allow_html=True)

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("⚠️ OpenAI API Key가 설정되지 않았습니다.")

def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
        if score >= 90: return "S"
        elif score >= 80: return "A"
        elif score >= 70: return "B"
        elif score >= 60: return "C"
        else: return "D"
    except: return "D"

system_prompt = """
너는 코넬수학학원 원장이야. 매쓰플랫 PDF 리포트를 분석해서 학생명, 학교명, 학년, 평가일자, 종합점수, 단원별 성취도(chapters 배열), 대표 우수 유형 3개, 대표 취약 유형 3개를 반드시 포함한 오차 없는 JSON을 출력해라.
"""

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
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
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

    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 5))
    ch_data = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ch_data.append([Paragraph(ch.get('name', ''), body_style), Paragraph(f"{ch.get('achievement', '0')}%", body_center)])
    t_ch = Table(ch_data, colWidths=[400, 115])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    m_types = [Paragraph(f"• {t}", body_style) for t in data.get("mastery_types", [])[:3]]
    w_types = [Paragraph(f"• {t}", body_style) for t in data.get("weakness_types", [])[:3]]
    type_table = Table([[ [Paragraph("<b>■ 대표 우수 유형</b>", section_style), Spacer(1,5)] + m_types, [Paragraph("<b>■ 대표 취약 유형</b>", section_style), Spacer(1,5)] + w_types ]], colWidths=[250, 250])
    story.append(type_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ====================================================================
# [구조 개혁] 1, 2단계 입력창을 최상단 스코프로 영구 고정
# ====================================================================
st.markdown("# 📊 코넬수학 레벨테스트 결과지 시스템")

# 안전한 전역 세션 보관소 초기화
if "saved_name" not in st.session_state: st.session_state["saved_name"] = ""
if "saved_school" not in st.session_state: st.session_state["saved_school"] = ""
if "saved_grade" not in st.session_state: st.session_state["saved_grade"] = ""
if "saved_month" not in st.session_state: st.session_state["saved_month"] = ""
if "saved_score" not in st.session_state: st.session_state["saved_score"] = ""
if "saved_comment" not in st.session_state: st.session_state["saved_comment"] = ""
if "saved_chapters" not in st.session_state: st.session_state["saved_chapters"] = []
if "saved_mastery" not in st.session_state: st.session_state["saved_mastery"] = []
if "saved_weakness" not in st.session_state: st.session_state["saved_weakness"] = []

uploaded_file = st.file_uploader("📥 매쓰플랫 진단평가 결과 분석 리포트 PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    if st.session_state.get("current_file") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 리포트 파일 새롭게 정밀 분석 중..."):
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
                
                st.session_state["saved_name"] = res_json.get("student_name", "")
                st.session_state["saved_school"] = res_json.get("school_name", "")
                st.session_state["saved_grade"] = res_json.get("student_grade", "")
                st.session_state["saved_month"] = res_json.get("report_month", "")
                st.session_state["saved_score"] = res_json.get("score", "")
                st.session_state["saved_comment"] = res_json.get("teacher_comment", "")
                st.session_state["saved_chapters"] = res_json.get("chapters", [])
                st.session_state["saved_mastery"] = res_json.get("mastery_types", [])
                st.session_state["saved_weakness"] = res_json.get("weakness_types", [])
                st.session_state["current_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 실패: {str(e)}")

# [핵심 수술] 조건문 바깥에 배치하여 글자를 고쳐도 절대로 사라지지 않는 영구 고정 UI 영역
st.markdown("### 📋 1단계: 기본 정보 검토 및 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=st.session_state["saved_name"])
sch_name = col2.text_input("학교명", value=st.session_state["saved_school"])
s_grade = col3.text_input("학년", value=st.session_state["saved_grade"])

col4, col5 = st.columns(2)
r_month = col4.text_input("평가 일자", value=st.session_state["saved_month"])
score_val = col5.text_input("종합 점수", value=str(st.session_state["saved_score"]))

st.markdown("### 🦅 2단계: 종합 코멘트 관리")
teacher_comment = st.text_area("코넬 분석 Comment", value=st.session_state["saved_comment"], height=150)

# 최종 컴파일 데이터 패키징
final_data = {
    "student_name": s_name,
    "school_name": sch_name,
    "student_grade": s_grade,
    "report_month": r_month,
    "score": score_val,
    "chapters": st.session_state["saved_chapters"],
    "mastery_types": st.session_state["saved_mastery"],
    "weakness_types": st.session_state["saved_weakness"],
    "teacher_comment": teacher_comment
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### 🖨️ 3단계: 성적표 결과지 발행")
    st.download_button(
        label="💾 PDF 다운로드",
        data=pdf_bin,
        file_name=f"코넬수학_진단결과분석지_{s_name}.pdf",
        mime="application/pdf",
        type="primary"
    )
    
with right_col:
    st.markdown("### 🔍 발급 예정 결과지 미리보기")
    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
    try:
        import fitz
        preview_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in preview_doc:
            st.image(page.get_pixmap(dpi=150).tobytes("png"), use_container_width=True)
    except Exception as display_err:
        st.info("💡 미리보기를 실시간 렌더링 중입니다.")
    st.markdown('</div>', unsafe_allow_html=True)
