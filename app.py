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

# [1] 기본 화면 설정 및 크래시 방어 디자인
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="wide")

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("⚠️ OpenAI API Key 설정 상태를 확인해 주세요.")

# 레벨 자동 계산기
def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
        if score >= 90: return "S"
        elif score >= 80: return "A"
        elif score >= 70: return "B"
        elif score >= 60: return "C"
        else: return "D"
    except: return "D"

# AI 추출 전문 프롬프트 (정기평가 및 오답노트 2종 완벽 파싱 지침)
system_prompt = """
너는 코넬수학학원의 베테랑 원장이야. 매쓰플랫 PDF 리포트를 분석해서 학원 연동용 JSON을 생성해라.
반드시 리포트 2페이지의 단원별 정답률(chapters 배열)과 4페이지의 대표 우수 유형 3개, 대표 취약 유형 3개를 텍스트 그대로 정확히 추출해라.
만약 오답 리포트 양식이라 시험 점수가 없다면 리포트 내부 정답 현황을 기반으로 0~100 사이의 종합 점수를 추론하여 숫자로 출력해라.
"""

# [2] 명품 PDF 리포트 빌더 (그래프, 우수/취약 유형, 코멘트 상자 올인원 고정)
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

    # 메인 프리미엄 타이틀 배너
    t_banner = Table([[Paragraph("<b>코넬수학전문학원 진단평가 결과 분석지</b>", title_style)]], colWidths=515)
    t_banner.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')), ('TOPPADDING', (0,0), (-1,-1), 10), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(t_banner)
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>분석 발행일:</b> {data.get('report_month', '')}", info_style))
    story.append(Spacer(1, 5))

    # 12개 핵심 지표 연동 학생 정보 테이블
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

    # 단원별 성취 분석 시각화 표 (기능 완전 복구)
    story.append(Paragraph("📈 단원별 세부 성취 지표", section_style))
    story.append(Spacer(1, 5))
    ch_rows = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>성취도 수준 성장 그래프</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    
    chapters = data.get("chapters", [])
    if isinstance(chapters, list) and len(chapters) > 0:
        for ch in chapters:
            try: pct = int(ch.get('achievement', 0))
            except: pct = 0
            ch_rows.append([Paragraph(ch.get('name', '세부 단원'), body_style), "■"*(pct//10) + "□"*(10-(pct//10)), Paragraph(f"{pct}%", body_center)])
    else:
        ch_rows.append([Paragraph("추출된 세부 단원 성취 정보가 없습니다.", body_style), Paragraph("-", body_center), Paragraph("-", body_center)])
        
    t_ch = Table(ch_rows, colWidths=[180, 270, 65])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    # 대표 우수 / 취약 유형 듀얼 패널 (기능 완전 복구)
    u_style = ParagraphStyle('U', fontName=font_name, fontSize=11, textColor=colors.HexColor('#1E3A8A'))
    w_style = ParagraphStyle('W', fontName=font_name, fontSize=11, textColor=colors.HexColor('#C53030'))
    
    m_list = [Paragraph(f"• {t}", body_style) for t in data.get("mastery_types", []) if t]
    w_list = [Paragraph(f"• {t}", body_style) for t in data.get("weakness_types", []) if t]
    
    if not m_list: m_list = [Paragraph("• 전반적으로 성취 수준이 고르게 분포되어 있습니다.", body_style)]
    if not w_list: w_list = [Paragraph("• 특별히 검출된 취약 오답 유형이 없습니다.", body_style)]
    
    type_data = [[ [Paragraph("<b>■ 대표 우수 유형</b>", u_style), Spacer(1,5)] + m_list, [Paragraph("<b>■ 대표 취약 유형</b>", w_style), Spacer(1,5)] + w_list ]]
    t_type = Table(type_data, colWidths=[250, 250])
    t_type.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_type)
    story.append(Spacer(1, 15))

    # 독수리 눈 코넬 종합 코멘트 박스
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 5))
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (0,0), 10)]))
    story.append(t_comment)

    # 코넬 하단 시그니처 공식 로고 장착
    def add_logo(canvas, doc):
        canvas.saveState()
        if os.path.exists("cornell.png"):
            canvas.drawImage("cornell.png", 242, 12, width=110, height=42, mask='auto')
        canvas.restoreState()

    doc.build(story, onFirstPage=add_logo, onLaterPages=add_logo)
    buffer.seek(0)
    return buffer

# ====================================================================
# [3] 메인 웹 대시보드 스코프 컨트롤 영역
# ====================================================================

# 세션 상태 꼬임 방지 버퍼 하우스웨어 구축
if "buf_name" not in st.session_state: st.session_state["buf_name"] = ""
if "buf_school" not in st.session_state: st.session_state["buf_school"] = ""
if "buf_grade" not in st.session_state: st.session_state["buf_grade"] = ""
if "buf_month" not in st.session_state: st.session_state["buf_month"] = ""
if "buf_score" not in st.session_state: st.session_state["buf_score"] = ""
if "buf_comment" not in st.session_state: st.session_state["buf_comment"] = ""
if "buf_chapters" not in st.session_state: st.session_state["buf_chapters"] = []
if "buf_mastery" not in st.session_state: st.session_state["buf_mastery"] = []
if "buf_weakness" not in st.session_state: st.session_state["buf_weakness"] = []
if "tracking_file" not in st.session_state: st.session_state["tracking_file"] = None

uploaded_file = st.file_uploader("📥 매쓰플랫 PDF 결과 리포트 파일 업로드", type=["pdf"])

if uploaded_file and uploaded_file.name != st.session_state["tracking_file"]:
    with st.spinner("🔍 AI 원장님이 리포트 패키지 분석 중..."):
        try:
            import fitz
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            imgs = []
            for page in doc:
                pix = page.get_pixmap(dpi=140)
                imgs.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
            
            content = [{"type": "text", "text": system_prompt}]
            for img in imgs:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": content}], response_format={"type": "json_object"})
            parsed = json.loads(resp.choices[0].message.content)
            
            # 업로드 즉시 격리 버퍼 세션에 바인딩 유도
            st.session_state["buf_name"] = parsed.get("student_name", "")
            st.session_state["buf_school"] = parsed.get("school_name", "")
            st.session_state["buf_grade"] = parsed.get("student_grade", "")
            st.session_state["buf_month"] = parsed.get("report_month", "")
            st.session_state["buf_score"] = str(parsed.get("score", ""))
            st.session_state["buf_comment"] = parsed.get("teacher_comment", "")
            st.session_state["buf_chapters"] = parsed.get("chapters", [])
            st.session_state["buf_mastery"] = parsed.get("mastery_types", [])
            st.session_state["buf_weakness"] = parsed.get("weakness_types", [])
            st.session_state["tracking_file"] = uploaded_file.name
        except Exception as e:
            st.error(f"데이터 파싱에 실패했습니다: {e}")

# [오류 해결] 꼬임 현상을 제거한 독립 폼 레이아웃 가동
st.markdown("### 📋 1단계: 학생 정보 등록 및 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=st.session_state["buf_name"])
sch_name = col2.text_input("학교명", value=st.session_state["buf_school"])
s_grade = col3.text_input("학년", value=st.session_state["buf_grade"])

col4, col5 = st.columns(2)
r_date = col4.text_input("평가 일자", value=st.session_state["buf_month"])
s_score = col5.text_input("종합 점수", value=st.session_state["buf_score"])

st.markdown("### 🦅 2단계: 코넬 분석 코멘트 수정")
teacher_comment = st.text_area("학부모 전송용 종합 코멘트 (실시간 편집 가능)", value=st.session_state["buf_comment"], height=160)

# 가공 데이터 결합
final_data = {
    "student_name": s_name, "school_name": sch_name, "student_grade": s_grade,
    "report_month": r_date, "score": s_score, "teacher_comment": teacher_comment,
    "chapters": st.session_state["buf_chapters"],
    "mastery_types": st.session_state["buf_mastery"], "weakness_types": st.session_state["buf_weakness"]
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### 🖨️ 3단계: 결과지 최종 발행")
    st.download_button(label="💾 코넬수학 결과지 PDF 다운로드", data=pdf_bin, file_name=f"코넬수학_진단리포트_{s_name}.pdf", mime="application/pdf", type="primary")

with right_col:
    st.markdown("### 🔍 결과지 실시간 미리보기")
    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
    # [크롬 차단 무력화] iFrame을 버리고 이미지 객체 다이렉트 드로잉 기법 전환
    try:
        import fitz
        p_doc = fitz.open(stream=pdf_bin.getvalue(), filetype="pdf")
        for page in p_doc:
            st.image(page.get_pixmap(dpi=140).tobytes("png"), use_container_width=True)
    except:
        st.info("매쓰플랫 PDF 결과 파일을 업로드하시면 우측에 실시간 결과 분석지가 투영됩니다.")
    st.markdown('</div>', unsafe_allow_html=True)
