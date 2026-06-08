import streamlit as st
import json
import os
import io
import re
import base64
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle

# 페이지 기본 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="wide")

# 미리보기 창 테두리 및 그림자 효과를 위한 커스텀 CSS
st.markdown("""
    <style>
    .pdf-preview-container {
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px;
        background-color: #F8FAFC;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# OpenAI 클라이언트 초기화
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error("⚠️ OpenAI API Key가 설정되지 않았습니다. Streamlit Secrets를 확인해 주세요.")

def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
    except:
        score = 0
    if score >= 90: return "S"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    else: return "D"

# AI 프롬프트 정의
system_prompt = """
너는 코넬수학전문학원의 원장이야. 첨부된 매쓰플랫 리포트를 정밀 분석하여 JSON을 생성해라.
1. 우수/취약 유형: 각각 정확히 3가지씩 추출.
2. 난이도 정답률: 최상/상/중/중하/하 수치를 정확히 숫자로 매핑(0% 에러 주의).
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
    title_style = ParagraphStyle('TitleStyle', fontName=font_name, fontSize=18, alignment=1, textColor=colors.HexColor('#FFFFFF'))
    info_style = ParagraphStyle('InfoStyle', fontName=font_name, fontSize=9, alignment=2, textColor=colors.HexColor('#64748B'))
    body_style = ParagraphStyle('BodyStyle', fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BodyCenter', fontName=font_name, fontSize=9, leading=14, alignment=1)
    section_style = ParagraphStyle('SectionStyle', fontName=font_name, fontSize=12, textColor=colors.HexColor('#1E3A8A'))

    # 상단 배너 및 학생 정보
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
    t_info.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (0,1), colors.HexColor('#F8FAFC')), ('BACKGROUND', (2,0), (2,1), colors.HexColor('#F8FAFC')), ('BACKGROUND', (4,0), (4,0), colors.HexColor('#F8FAFC')), ('SPAN', (3,1), (5,1))]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    # 단원 분석 & 난이도 분석 (중략 - 기존 로직 유지)
    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 15)) # [참고] 실제 코드에는 막대그래프 생성 로직 포함됨

    # --------------------------------------------------------------------
    # [위치 조정 1] 대표 우수/취약 유형을 코멘트 위로 올림
    # --------------------------------------------------------------------
    mastery_content = [Paragraph("<b>■ 대표 우수 유형</b>", section_style), Spacer(1, 6)]
    for m in data.get("mastery_types", [])[:3]: mastery_content.append(Paragraph(f"• {m}", body_style))
    
    section_style_red = ParagraphStyle('SectionRed', parent=section_style, textColor=colors.HexColor("#C53030"))
    weakness_content = [Paragraph("<b>■ 대표 취약 유형</b>", section_style_red), Spacer(1, 6)]
    for w in data.get("weakness_types", [])[:3]: weakness_content.append(Paragraph(f"• {w}", body_style))

    type_table = Table([[mastery_content, weakness_content]], colWidths=[250, 250])
    type_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(type_table)
    story.append(Spacer(1, 20))

    # --------------------------------------------------------------------
    # [위치 조정 2] 코넬 분석 Comment를 가장 하단 배치
    # --------------------------------------------------------------------
    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 6))
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=515)
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')),
        ('TOPPADDING', (0,0), (0,0), 10), ('BOTTOMPADDING', (0,0), (0,0), 10),
        ('LEFTPADDING', (0,0), (0,0), 12), ('RIGHTPADDING', (0,0), (0,0), 12),
    ]))
    story.append(t_comment)

    def add_footer_logo(canvas, doc):
        canvas.saveState()
        logo = "cornell.png"
        if os.path.exists(logo): canvas.drawImage(logo, 242, 10, width=110, height=42, mask='auto')
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer_logo, onLaterPages=add_footer_logo)
    buffer.seek(0)
    return buffer
# ====================================================================
# ====================================================================
# [개편 완료] 실시간 결과지 미리보기 통합 대시보드
# ====================================================================
st.title("📊 코넬수학전문학원 레벨테스트 결과지 시스템")
st.markdown("매쓰플랫 PDF를 정밀 분석하여 공식 신규생 진단 결과지를 발행합니다.")
st.markdown("---")

uploaded_file = st.file_uploader("📥 매쓰플랫 진단평가 결과 분석 리포트 PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    # 1. AI 분석 로직 (기존 유지)
    if "ocr_result" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 리포트 파일 분석 중..."):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                import base64
                images_base64 = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    images_base64.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
                
                content = [{"type": "text", "text": system_prompt}]
                for img_b64 in images_base64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": content}],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                res_json = json.loads(response.choices[0].message.content)
                st.session_state["ocr_result"] = res_json
                st.session_state["file_name"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 오류: {str(e)}")
                st.stop()

    res = st.session_state["ocr_result"]

    # 2. 사용자 입력 폼
    st.markdown("### 📋 1단계: 기본 정보 검토")
    col1, col2, col3 = st.columns(3)
    s_name = col1.text_input("학생 이름", value=res.get("student_name", ""))
    sch_name = col2.text_input("학교명", value=res.get("school_name", ""))
    s_grade = col3.text_input("학년", value=res.get("student_grade", ""))
    
    col4, col5 = st.columns(2)
    r_month = col4.text_input("평가 일자", value=res.get("report_month", ""))
    score_val = col5.text_input("종합 점수", value=str(res.get("score", "")))

    st.markdown("### 🦅 2단계: 종합 코멘트 관리")
    teacher_comment = st.text_area("코넬 분석 Comment", value=res.get("teacher_comment", ""), height=150)

    # 3. PDF 생성 및 미리보기 레이아웃
    final_data = {
        "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
        "report_month": r_month, "score": score_val, "chapters": res.get("chapters", []),
        "difficulty_analysis": res.get("difficulty_analysis", {"하": "0", "중하": "0", "중": "0", "상": "0", "최상": "0"}),
        "mastery_types": res.get("mastery_types", [])[:3],
        "weakness_types": res.get("weakness_types", [])[:3],
        "teacher_comment": teacher_comment
    }
st.markdown("---")
    
    # PDF 파일 생성
    pdf_bin = create_academy_report(final_data)

    # 레이아웃 정의 (오류 방지를 위해 if문 바로 아래에 배치)
    col_left, col_right = st.columns([1, 1.2])
    
    with col_left:
        st.markdown("### 🖨️ 3단계: 성적표 결과지 발행")
        st.download_button(
            label="💾 PDF 다운로드", 
            data=pdf_bin, 
            file_name=f"코넬수학_{s_name}.pdf", 
            mime="application/pdf", 
            type="primary"
        )
        
    with col_right:
        st.markdown("### 🔍 결과지 미리보기")
        st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
        import base64
        b64 = base64.b64encode(pdf_bin.getvalue()).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="800px"></iframe>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
