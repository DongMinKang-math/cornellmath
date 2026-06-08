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

# [1] 기본 환경 설정 및 명품 액자 테두리 CSS 디자인 정의
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

# OpenAI 클라이언트 안전 초기화
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

# AI 맞춤 추출 프롬프트 고정 (내신끗, CMA 정기평가 완벽 분석 지침)
system_prompt = """
너는 코넬수학전문학원의 원장이야. 첨부된 매쓰플랫 리포트(특히 2페이지 및 4페이지)를 정밀 분석하여 오차 없는 데이터 JSON을 생성해라.

[추출 및 분석 핵심 지침]
1. 대표 우수 유형 & 대표 취약 유형: 리포트 4페이지에 표기된 대표 우수 유형 3개와 대표 취약 유형 3개를 텍스트 그대로 완벽하게 추출하여 리스트로 만들어라.
2. 난이도별 정답률 분석: 리포트 2페이지에 그래프나 텍스트로 표시된 최상, 상, 중, 중하, 하 각 난이도별 정답률(%) 수치를 정확하게 찾아내어 숫자로 매핑해라. 예: 57.1%, 6.5% 등을 절대 놓치지 말 것.
3. 단원별 정답률 분석: 리포트 2페이지 하단에 있는 단원별 정답률(%) 이름과 수치들을 전부 누락 없이 chapters 배열에 담아라.

[반드시 지켜야 할 응답 JSON 형식]:
{
  "student_name": "학생 이름",
  "school_name": "학교명",
  "student_grade": "학년",
  "report_month": "YYYY/MM/DD",
  "score": "종합 점수 (숫자만)",
  "chapters": [
    {"name": "단원명", "achievement": "성취도 숫자"}
  ],
  "difficulty_analysis": {
    "하": "하 정답률 숫자",
    "중하": "중하 정답률 숫자",
    "중": "중 정답률 숫자",
    "상": "상 정답률 숫자",
    "최상": "최상 정답률 숫자"
  },
  "mastery_types": [
    "우수 유형 1번째",
    "우수 유형 2번째",
    "우수 유형 3번째"
  ],
  "weakness_types": [
    "취약 유형 1번째",
    "취약 유형 2번째",
    "취약 유형 3번째"
  ],
  "teacher_comment": "학부모 상담용 정중하고 부드러운 종합 코멘트 (4~5문장)"
}
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
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#FFFFFF'))
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=12, alignment=2, textColor=colors.HexColor('#64748B'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BodyCenter', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, alignment=1, textColor=colors.HexColor('#1E293B'))
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor('#1E3A8A'))

    story.append(Spacer(1, 5))
    title_banner_data = [[Paragraph("<b>코넬수학전문학원 신규생 진단평가 결과 분석지</b>", title_style)]]
    t_banner = Table(title_banner_data, colWidths=515)
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1E3A8A')),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>시험 일자:</b> {data.get('report_month', '년/월/일')}", info_style))
    story.append(Spacer(1, 4))

    w_info = [515 / 6] * 6
    w_ch = [515 * 0.42, 515 * 0.45, 515 * 0.13]
    w_comment = 515

    info_data = [
        [Paragraph('<b>학 생 명</b>', body_center), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>학 교 명</b>', body_center), Paragraph(data.get('school_name', ''), body_style),
         Paragraph('<b>학 년</b>', body_center), Paragraph(data.get('student_grade', ''), body_style)],
        [Paragraph('<b>종합 점수</b>', body_center), Paragraph(f"<b>{data.get('score', '')} 점</b>", body_style),
         Paragraph('<b>진단 레벨</b>', body_center), Paragraph(f"<b>{calculate_math_level(data.get('score', '0'))} Level</b>", body_style),
         Paragraph('', body_style), Paragraph('', body_style)]
    ]
    t_info = Table(info_data, colWidths=w_info)
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (2,0), (2,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (4,0), (4,0), colors.HexColor('#F8FAFC')),
        ('SPAN', (3,1), (5,1)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 12))

    story.append(Paragraph("📈 단원별 성취 분석", section_style))
    story.append(Spacer(1, 4))

    def make_ch_bar_cell(pct_val):
        try: pct = min(100, max(0, int(pct_val)))
        except: pct = 0
        w_total_filled = max(1, int(pct * 2.0))
        w_empty = max(1, 200 - w_total_filled)
        seg1 = min(w_total_filled, 70)
        seg2 = min(max(0, w_total_filled - 70), 70)
        seg3 = max(0, w_total_filled - 140)
        bar_widths = [max(0.1, seg1), max(0.1, seg2), max(0.1, seg3), w_empty]
        bar_table = Table([['', '', '', '']], colWidths=bar_widths)
        bar_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#1E3A8A')),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor('#2563EB')),
            ('BACKGROUND', (2,0), (2,0), colors.HexColor('#60A5FA')),
            ('BACKGROUND', (3,0), (3,0), colors.HexColor('#E2E8F0')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
            ('TOPPADDING', (0,0), (-1,-1), 0.8),
        ]))
        return bar_table

    ch_rows = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>영역별 성취 수준 성장 지표</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ach_clean = ''.join(filter(str.isdigit, str(ch['achievement'])))
        ch_rows.append([Paragraph(ch['name'], body_style), make_ch_bar_cell(ach_clean), Paragraph(f"{ch['achievement']}%", body_center)])
    t_ch = Table(ch_rows, colWidths=w_ch)
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 12))

    story.append(Paragraph("📊 문항 진단 난이도별 정답률 분석", section_style))
    st_diff = data.get("difficulty_analysis", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    drawing = Drawing(515, 100)
    drawing.add(Rect(0, 0, 515, 100, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))

    for i in range(1, 5):
        y_pos = int((i * 25) * 0.8) + 10
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5, strokeDashArray=[2, 2]))

    levels = ["하", "중하", "중", "상", "최상"]
    points = []
    for i in range(5):
        lvl = levels[i]
        try: val = int(''.join(filter(str.isdigit, str(st_diff.get(lvl, '0')))))
        except: val = 0
        val = min(100, max(0, val))
        x_pos = int(40 + (i * 108))
        y_pos = int(val * 0.8) + 10
        points.append((x_pos, y_pos, val))

    for i in range(len(points)):
        x, y, v = points[i]
        drawing.add(String(x, 2, levels[i], fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#475569')))
        drawing.add(String(x, y + 5, f"{v}%", fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#1E3A8A')))
        drawing.add(Circle(x, y, 2.5, fillColor=colors.HexColor('#1E3A8A'), strokeColor=colors.HexColor('#FFFFFF'), strokeWidth=1))
        if i > 0:
            px, py, _ = points[i-1]
            drawing.add(Line(px, py, x, y, strokeColor=colors.HexColor('#1E3A8A'), strokeWidth=1.2))
    story.append(drawing)
    story.append(Spacer(1, 15))

    mastery_content = [Paragraph("<b>■ 대표 우수 유형</b>", section_style), Spacer(1, 6)]
    mastery_list = data.get("mastery_types", [])
    if not mastery_list:
        mastery_content.append(Paragraph("• 전반적으로 안정적인 성취를 보입니다.", body_style))
    else:
        for m_type in mastery_list[:3]:
            mastery_content.append(Paragraph(f"• {m_type}", body_style))
            mastery_content.append(Spacer(1, 4))

    section_style_red = ParagraphStyle('SectionRed', parent=section_style, textColor=colors.HexColor("#C53030"))
    weakness_content = [Paragraph("<b>■ 대표 취약 유형</b>", section_style_red), Spacer(1, 6)]
    weakness_list = data.get("weakness_types", [])
    if not weakness_list:
        weakness_content.append(Paragraph("• 특이 취약 유형이 검출되지 않았습니다.", body_style))
    else:
        for w_type in weakness_list[:3]:
            weakness_content.append(Paragraph(f"• {w_type}", body_style))
            weakness_content.append(Spacer(1, 4))

    type_data = [[mastery_content, weakness_content]]
    type_table = Table(type_data, colWidths=[w_comment / 2 - 10, w_comment / 2 - 10])
    type_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(type_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 4))
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=w_comment)
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')),
        ('TOPPADDING', (0,0), (0,0), 8),
        ('BOTTOMPADDING', (0,0), (0,0), 8),
        ('LEFTPADDING', (0,0), (0,0), 10),
        ('RIGHTPADDING', (0,0), (0,0), 10),
    ]))
    story.append(t_comment)

    def add_footer_logo(canvas, doc):
        canvas.saveState()
        logo_filename = "cornell.png"
        if os.path.exists(logo_filename):
            try: canvas.drawImage(logo_filename, 242, 10, width=110, height=42, mask='auto')
            except: pass
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer_logo, onLaterPages=add_footer_logo)
    buffer.seek(0)
    return buffer

# ====================================================================
# [엔진 개정 및 100% 렌더링 스코프 확보 영역]
# ====================================================================
st.title("📊 코넬수학 레벨테스트 결과지 시스템")
st.markdown("매쓰플랫 PDF를 정밀 분석하여 공식 신규생 진단 결과지를 발행합니다.")
st.markdown("---")

uploaded_file = st.file_uploader("📥 매쓰플랫 진단평가 결과 분석 리포트 PDF 업로드", type=["pdf"])

if uploaded_file is not None:
    if "ocr_result" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 리포트 파일 분석 중... (약 10~15초 소요)"):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                images_base64 = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    images_base64.append(base64.b64encode(img_data).decode('utf-8'))
                
                content = [{"type": "text", "text": system_prompt}]
                for img_b64 in images_base64:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                    })
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": content}],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                
                raw_text = response.choices[0].message.content
                st.session_state["ocr_result"] = json.loads(raw_text)
                st.session_state["file_name"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 중 에러 발생: {str(e)}")
                st.stop()

    # 안전하게 세션 딕셔너리 연동 확보
    res = st.session_state.get("ocr_result", {})

    # [UI 증발 철저 방어] 1단계 기본 학생 정보 수정 폼 강제 고정 렌더링
    st.markdown("### 📋 1단계: 기본 정보 검토 및 수정")
    col1, col2, col3 = st.columns(3)
    with col1:
        s_name = st.text_input("학생 이름", value=res.get("student_name", ""))
    with col2:
        sch_name = st.text_input("학교명", value=res.get("school_name", ""))
    with col3:
        s_grade = st.text_input("학년", value=res.get("student_grade", ""))

    col4, col5 = st.columns(2)
    with col4:
        r_month = st.text_input("평가 일자", value=res.get("report_month", ""))
    with col5:
        score_val = st.text_input("종합 점수", value=str(res.get("score", "")))

    # [UI 증발 철저 방어] 2단계 코넬 종합 평론 텍스트 상자 강제 고정 렌더링
    st.markdown("### 🦅 2단계: 종합 코멘트 관리")
    teacher_comment = st.text_area("코넬 분석 Comment", value=res.get("teacher_comment", ""), height=150)

    # 데이터 취합 동기화
    final_data = {
        "student_name": s_name,
        "school_name": sch_name,
        "student_grade": s_grade,
        "report_month": r_month,
        "score": score_val,
        "chapters": res.get("chapters", []),
        "difficulty_analysis": res.get("difficulty_analysis", {"하": "0", "중하": "0", "중": "0", "상": "0", "최상": "0"}),
        "mastery_types": res.get("mastery_types", []),
        "weakness_types": res.get("weakness_types", []),
        "teacher_comment": teacher_comment
    }

    st.markdown("---")
    
    # PDF 빌드 실행
    pdf_bin = create_academy_report(final_data)

    # 대시보드 2분할 가동
    left_col, right_col = st.columns([1, 1.2])
    
    with left_col:
        st.markdown("### 🖨️ 3단계: 성적표 결과지 발행")
        st.success("🎉 분석지 생성이 완료되었습니다. 아래 버튼을 눌러 소장하세요!")
        st.download_button(
            label="💾 코넬수학 진단평가 결과지 PDF 다운로드",
            data=pdf_bin,
            file_name=f"코넬수학_진단결과분석지_{s_name}.pdf",
            mime="application/pdf",
            type="primary"
        )
        
    with right_col:
        st.markdown("### 🔍 발급 예정 결과지 미리보기")
        
        # 라운드 디자인 테두리 명품 액자 컨테이너
        st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
        try:
            # 브라우저별 차단 규제를 100% 우회하는 고해상도 이미지 변환 프리뷰 기법 고정
            import fitz
            preview_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
            for page in preview_doc:
                pix = page.get_pixmap(dpi=180)
                st.image(pix.tobytes("png"), use_container_width=True)
        except Exception as display_err:
            st.info("💡 미리보기를 생성하는 중입니다.")
        st.markdown('</div>', unsafe_allow_html=True)
