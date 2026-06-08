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

# [1] 기본 설정 및 액자 테두리 CSS 디자인
st.set_page_config(page_title="코넬수학 레벨테스트 시스템", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    .pdf-preview-container {
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        background-color: #FFFFFF;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        text-align: center;
        min-height: 800px;
    }
    </style>
    """, unsafe_allow_html=True)

# OpenAI API 안전 연동
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error("⚠️ OpenAI API Key 설정이 필요합니다.")

# 레벨 자동 계산기
def calculate_math_level(score_str):
    try:
        s = int(''.join(filter(str.isdigit, str(score_str))))
        if s >= 90: return "S"
        elif s >= 80: return "A"
        elif s >= 70: return "B"
        elif s >= 60: return "C"
        else: return "D"
    except: return "D"

# [2] AI 데이터 추출 프롬프트 (내신끗 파일 특화)
system_prompt = """
너는 코넬수학전문학원의 데이터 분석가야. 매쓰플랫 진단 리포트를 분석해서 JSON을 생성해.
특히 4페이지의 유형별 정오답 데이터를 스캔해서 우수/취약 유형 3개씩을 무조건 찾아라.
난이도별(최상~하) 정답률 수치를 정확한 숫자로 추출해라. 
학생이름, 학교, 학년, 점수가 누락되지 않도록 할 것.
"""

# [3] 고품격 PDF 성적표 생성 함수 (코멘트 최하단 배치)
def create_academy_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=25, bottomMargin=40)
    story = []

    # 폰트 로드
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

    # 상단 배너
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
    t_banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')), ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_banner)
    story.append(Spacer(1, 10))

    # 학생 정보 표
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

    # 단원별 성취 그래프 (간략화된 막대 로직)
    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 5))
    ch_data = [[Paragraph('평가 영역', body_center), Paragraph('성취 수준', body_center), Paragraph('성취도', body_center)]]
    for ch in data.get("chapters", []):
        ch_data.append([Paragraph(ch['name'], body_style), "■"*int(int(ch['achievement'])/10), Paragraph(f"{ch['achievement']}%", body_center)])
    t_ch = Table(ch_data, colWidths=[200, 250, 65])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 20))

    # 유형 분석 (우수/취약)
    u_style = ParagraphStyle('U', fontName=font_name, fontSize=10, textColor=colors.HexColor('#1E3A8A'))
    c_style = ParagraphStyle('C', fontName=font_name, fontSize=10, textColor=colors.HexColor('#C53030'))
    
    m_types = [Paragraph(f"• {t}", body_style) for t in data.get("mastery_types", [])[:3]]
    w_types = [Paragraph(f"• {t}", body_style) for t in data.get("weakness_types", [])[:3]]
    
    type_table = Table([[ [Paragraph("<b>■ 우수 유형</b>", u_style), Spacer(1,5)] + m_types, [Paragraph("<b>■ 취약 유형</b>", c_style), Spacer(1,5)] + w_types ]], colWidths=[250, 250])
    story.append(type_table)
    story.append(Spacer(1, 20))

    # 원장님 코멘트 (최하단)
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    doc.build(story)
    buffer.seek(0)
    return buffer

# [4] 대시보드 화면 구성
st.title("📊 코넬수학 레벨테스트 결과지 시스템")
uploaded_file = st.file_uploader("📥 '[오답] 내신끗' 등 매쓰플랫 PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    if "ocr_result" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 리포트 정밀 분석 중..."):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                images = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    images.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
                
                content = [{"type": "text", "text": system_prompt}]
                for img in images:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
                
                resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": content}], response_format={"type": "json_object"})
                st.session_state["ocr_result"] = json.loads(resp.choices[0].message.content)
                st.session_state["file_name"] = uploaded_file.name
            except Exception as e:
                st.error(f"분석 에러: {e}")
                st.stop()

    res = st.session_state["ocr_result"]

    # 입력 폼
    st.markdown("### 📋 1단계: 기본 정보 검토")
    c1, c2, c3 = st.columns(3)
    s_name = c1.text_input("학생 이름", value=res.get("student_name", ""))
    sch_name = c2.text_input("학교명", value=res.get("school_name", ""))
    s_grade = c3.text_input("학년", value=res.get("student_grade", ""))
    
    score_val = st.text_input("종합 점수", value=str(res.get("score", "")))
    t_comment = st.text_area("코넬 분석 Comment", value=res.get("teacher_comment", ""), height=150)

    final_data = {**res, "student_name": s_name, "school_name": sch_name, "student_grade": s_grade, "score": score_val, "teacher_comment": t_comment}

    st.markdown("---")
    pdf_bin = create_academy_report(final_data)

    l_col, r_col = st.columns([1, 1.2])
    with l_col:
        st.markdown("### 🖨️ 성적표 발행")
        st.download_button("💾 PDF 다운로드", data=pdf_bin, file_name=f"코넬수학_{s_name}.pdf", mime="application/pdf", type="primary")
    
    with r_col:
        st.markdown("### 🔍 결과지 미리보기")
        st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
        # 보안 이슈를 우회하는 이미지 변환 렌더링
        import fitz
        preview_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in preview_doc:
            st.image(page.get_pixmap(dpi=180).tobytes("png"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
