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

# [1] 기본 화면 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="centered")

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
너는 코넬수학학원 원장이야. 업로드된 PDF 리포트를 분석해서 
학생명, 학교명, 학년, 평가일자, 종합점수, 단원별 성취도(chapters 배열), 
대표 우수 유형, 대표 취약 유형을 반드시 포함한 오차 없는 JSON을 출력해라.
만약 정보가 유실되었거나 오답노트 양식이라 점수가 없다면 학생 이름과 파일 제목을 기반으로 추론하여 채워라.
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
    if isinstance(chapters, list) and len(chapters) > 0:
        for ch in chapters:
            if isinstance(ch, dict):
                ch_data.append([Paragraph(ch.get('name', '미지 단원'), body_style), Paragraph(f"{ch.get('achievement', '0')}%", body_center)])
    else:
        ch_data.append([Paragraph("등록된 세부 분석 단원이 없습니다.", body_style), Paragraph("-", body_center)])
    
    t_ch = Table(ch_data, colWidths=[400, 115])
    t_ch.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC'))]))
    story.append(t_ch)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 5))
    t_comment = Table([[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]], colWidths=515)
    t_comment.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')), ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')), ('PADDING', (0,0), (-1,-1), 10)]))
    story.append(t_comment)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ====================================================================
# [메인 로직] 충돌 없는 완전 독립형 변수 구조 가동
# ====================================================================
st.markdown("# 📊 코넬수학 레벨테스트 결과지 시스템")
st.markdown("오답노트 및 진단평가 PDF를 기반으로 결과지를 생성합니다.")
st.markdown("---")

uploaded_file = st.file_uploader("📥 매쓰플랫 리포트 PDF 업로드", type=["pdf"])

# 파일 업로드 시 기존 캐시를 완전히 파괴하고 새 데이터를 주입하는 안전 서킷
if uploaded_file is not None:
    if st.session_state.get("last_seen_file") != uploaded_file.name:
        with st.spinner("🔍 AI 원장님이 새로운 파일 구조 분석 중..."):
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
                
                # 세션 키에 직접 대입하여 화면 갱신 강제 유도
                st.session_state["v_name"] = res_json.get("student_name", "강동윤")
                st.session_state["v_school"] = res_json.get("school_name", "중학교")
                st.session_state["v_grade"] = res_json.get("student_grade", "1학년")
                st.session_state["v_month"] = res_json.get("report_month", "2026/6/5")
                st.session_state["v_score"] = res_json.get("score", "100")
                st.session_state["v_comment"] = res_json.get("teacher_comment", "단원별 취약 유형 분석을 통해 철저한 오답 관리가 필요합니다.")
                st.session_state["v_chapters"] = res_json.get("chapters", [])
                st.session_state["last_seen_file"] = uploaded_file.name
            except Exception as e:
                st.error(f"❌ 분석 중 에러 발생: {str(e)}")

# 변수 안정화 보호막
if "v_name" not in st.session_state: st.session_state["v_name"] = ""
if "v_school" not in st.session_state: st.session_state["v_school"] = ""
if "v_grade" not in st.session_state: st.session_state["v_grade"] = ""
if "v_month" not in st.session_state: st.session_state["v_month"] = ""
if "v_score" not in st.session_state: st.session_state["v_score"] = ""
if "v_comment" not in st.session_state: st.session_state["v_comment"] = ""
if "v_chapters" not in st.session_state: st.session_state["v_chapters"] = []

# [UI 고정선] 세션 버그를 원천 차단하는 완벽한 입력 구조
st.markdown("### 📋 1단계: 기본 정보 검토 및 수정")
col1, col2, col3 = st.columns(3)
s_name = col1.text_input("학생 이름", value=st.session_state["v_name"])
sch_name = col2.text_input("학교명", value=st.session_state["v_school"])
s_grade = col3.text_input("학년", value=st.session_state["v_grade"])

col4, col5 = st.columns(2)
r_month = col4.text_input("평가 일자", value=st.session_state["v_month"])
score_val = col5.text_input("종합 점수", value=str(st.session_state["v_score"]))

st.markdown("### 🦅 2단계: 종합 코멘트 관리")
teacher_comment = st.text_area("코넬 분석 Comment", value=st.session_state["v_comment"], height=150)

# 실시간 변경사항 동기화 컴파일
final_data = {
    "student_name": s_name,
    "school_name": sch_name,
    "student_grade": s_grade,
    "report_month": r_month,
    "score": score_val,
    "chapters": st.session_state["v_chapters"],
    "teacher_comment": teacher_comment
}

st.markdown("---")
pdf_bin = create_academy_report(final_data)

st.markdown("### 🖨️ 3단계: 성적표 결과지 발행")
st.download_button(
    label="💾 코넬수학 결과지 PDF 다운로드",
    data=pdf_bin,
    file_name=f"코넬수학_진단결과분석지_{s_name}.pdf",
    mime="application/pdf",
    type="primary"
)
