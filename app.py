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
너는 코넬수학학원 원장이야. 매쓰플랫 PDF 리포트를 분석해서 
학생명, 학교명, 학년, 평가일자, 종합점수, 단원별 성취도(chapters 배열), 
대표 우수 유형 3개, 대표 취약 유형 3개를 반드시 포함한 오차 없는 JSON을 출력해라.
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

    # 단원별 테이블 가공 복구
    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 5))
    ch_data = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ch_data.append([Paragraph(ch.get('name', ''), body_style), Paragraph(f"{ch.get('achievement', '0')}%", body_center)])
    t_ch = Table(ch_data, colWidths=[400, 115])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    # 우수/취약 유형 복구
    m_types = [Paragraph(f"• {t}", body_style) for t in data.get("mastery_types", [])[:3]]
    w_types = [Paragraph(f"• {t}", body_style) for t in data.get("weakness_types", [])[:3]]
    type_table = Table([[ [Paragraph("<b>■ 대표 우수 유형</b>", section_style), Spacer(1,5)] + m_types, [Paragraph("<b>■ 대표 취약 유형</b>", section_style), Spacer(1,5)] + w_types ]], colWidths=[250, 250])
    story.append(type_table)
    story.append(Spacer(1, 20))

    # 코멘트 박스 최하단 배치 고정
    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ====================================================================
# [메인 로직] 강제 캐시 클리닝 시스템 가동
# ====================================================================
st.markdown("# 📊 코넬수학 레벨테스트 결과지 시스템")

uploaded_file = st.file_uploader("📥 매쓰플랫 진단평가 결과 분석 리포트 PDF 업로드", type=["pdf"])

# 고착화된 과거 강주원 데이터 강제 청소 알고리즘
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
                
                # 강제 덮어쓰기로 구세대 캐시 파괴
                st.session_state["active_data"] = res_json
                st.session_state["current_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 실패: {str(e)}")

if "active_data" in st.session_state:
    res = st.session_state["active_data"]

    st.markdown("### 📋 1단계: 기본 정보 검토 및 수정")
    col1, col2, col3 = st.columns(3)
    s_name = col1.text_input("학생 이름", value=res.get("student_name", ""))
    sch_name = col2.text_input("학교명", value=res.get("school_name", ""))
    s_grade = col3.text_input("학년", value=res.get("student_grade", ""))

    col4, col5 = st.columns(2)
    r_month = col4.text_input("평가 일자", value=res.get("report_month", ""))
    score_val = col5.text_input("종합 점수", value=str(res.get("score", "")))

    st.markdown("### 🦅 2단계: 종합 코멘트 관리")
    teacher_comment = st.text_area("코넬 분석 Comment", value=res.get("teacher_comment", ""), height=150)

    final_data = {
        **res, "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
        "report_month": r_month, "score": score_val, "teacher_comment": teacher_comment
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
            # 크롬 보안 우회를 보장하는 정석 이미지 스트림 방식 변환 호출
            import fitz
            preview_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
            for page in preview_doc:
                st.image(page.get_pixmap(dpi=150).tobytes("png"), use_container_width=True)
        except Exception as display_err:
            st.info("💡 미리보기를 실시간 렌더링 중입니다.")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("📥 분석을 위해 매쓰플랫 PDF 결과 분석 리포트 파일을 업로드해 주세요.")
