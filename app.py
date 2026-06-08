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

# [1] 기본 화면 설정 (중앙 정렬로 더 깔끔하게)
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

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("⚠️ OpenAI API Key가 설정되지 않았습니다. Streamlit Secrets를 확인해 주세요.")

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
너는 코넬수학학원 원장이야. 업로드된 PDF 리포트(정기평가 혹은 오답노트)를 분석해라.
학생명, 학교명, 학년, 평가일자, 종합점수, 단원별 성취도(chapters 배열), 대표 우수 유형 3개, 대표 취약 유형 3개를 JSON으로 출력해라.
만약 오답노트라 점수가 없다면 리포트의 전반적인 정답률을 기반으로 0~100 사이의 점수를 추론하여 생성해라.
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
    chapters = data.get("chapters", [])
    if isinstance(chapters, list):
        for ch in chapters:
            ch_data.append([Paragraph(ch.get('name', '미지'), body_style), Paragraph(f"{ch.get('achievement', '0')}%", body_center)])
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
# [메인 로직] 고정형 UI 설계 (학생 정보 수정 시 창이 사라지는 버그 해결)
# ====================================================================
st.markdown("# 📊 코넬수학 레벨테스트 결과지 시스템")

# 세션 키 강제 고정
for k in ["s_name", "s_school", "s_grade", "s_month", "s_score", "s_comment"]:
    if k not in st.session_state: st.session_state[k] = ""
if "s_chapters" not in st.session_state: st.session_state["s_chapters"] = []
if "s_mastery" not in st.session_state: st.session_state["s_mastery"] = []
if "s_weakness" not in st.session_state: st.session_state["s_weakness"] = []

uploaded_file = st.file_uploader("📥 PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    if st.session_state.get("last_file") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 새로운 리포트 분석 중..."):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                images_base64 = []
                for page in doc:
                    images_base64.append(base64.b64encode(page.get_pixmap(dpi=130).tobytes("png")).decode('utf-8'))
                
                content = [{"type": "text", "text": system_prompt}]
                for img in images_base64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
                
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": content}], response_format={"type": "json_object"})
                res = json.loads(resp.choices[0].message.content)
                
                st.session_state["s_name"] = res.get("student_name", "")
                st.session_state["s_school"] = res.get("school_name", "")
                st.session_state["s_grade"] = res.get("student_grade", "")
                st.session_state["s_month"] = res.get("report_month", "")
                st.session_state["s_score"] = str(res.get("score", ""))
                st.session_state["s_comment"] = res.get("teacher_comment", "")
                st.session_state["s_chapters"] = res.get("chapters", [])
                st.session_state["s_mastery"] = res.get("mastery_types", [])
                st.session_state["s_weakness"] = res.get("weakness_types", [])
                st.session_state["last_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"분석 실패: {e}")

# [핵심 수술] 파일 유무와 관계없이 UI는 항상 고정 노출
st.markdown("### 📋 1단계: 기본 정보 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=st.session_state["s_name"])
sch_name = col2.text_input("학교명", value=st.session_state["s_school"])
s_grade = col3.text_input("학년", value=st.session_state["s_grade"])

col4, col5 = st.columns(2)
r_month = col4.text_input("평가 일자", value=st.session_state["s_month"])
score_val = col5.text_input("종합 점수", value=st.session_state["s_score"])

st.markdown("### 🦅 2단계: 코넬 분석 코멘트")
teacher_comment = st.text_area("분석 코멘트", value=st.session_state["s_comment"], height=150)

final_data = {
    "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
    "report_month": r_month, "score": score_val, "teacher_comment": teacher_comment,
    "chapters": st.session_state["s_chapters"],
    "mastery_types": st.session_state["s_mastery"], "weakness_types": st.session_state["s_weakness"]
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### 🖨️ 3단계: 결과지 발행")
    st.download_button("💾 PDF 다운로드", data=pdf_bin, file_name=f"코넬수학_{s_name}.pdf", mime="application/pdf", type="primary")

with right_col:
    st.markdown("### 🔍 결과지 미리보기")
    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
    try:
        # 보안 차단을 100% 우회하는 고해상도 이미지 프리뷰 방식 적용
        import fitz
        preview_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in preview_doc:
            st.image(page.get_pixmap(dpi=180).tobytes("png"), use_container_width=True)
    except:
        st.info("파일을 업로드하면 미리보기가 생성됩니다.")
    st.markdown('</div>', unsafe_allow_html=True)

이번 업데이트를 통해 **어떤 브라우저를 쓰시더라도 미리보기가 완벽하게 나오고**, 학생 이름을 수정해도 **입력창이 절대 사라지지 않는** 쾌적한 환경을 구축했습니다. 바로 반영하여 테스트해 보세요!
