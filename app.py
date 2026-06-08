import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io
import os
import base64
from pdf2image import convert_from_bytes
# PDF 생성 및 정밀 시각화 부품 임포트
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from streamlit_pdf_viewer import pdf_viewer

# 웹 페이지 설정 (브라우저 탭 아이콘을 📊 모양으로 고정)
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="centered")

st.title("📊 코넬수학전문학원 레벨테스트 결과지 시스템")
st.caption("매쓰플랫 PDF를 정밀 분석하여 공식 신규생 진단 결과지를 발행합니다.")
st.markdown("---")

# Secrets에서 안전하게 API Key 로드
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("❌ Streamlit Cloud Settings -> Secrets에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
    st.stop()

# 점수에 따라 알파벳 레벨을 자동으로 계산하는 함수
def calculate_math_level(score_str):
    try:
        score = int(''.join(filter(str.isdigit, str(score_str))))
        if score >= 88: return "A"
        elif score >= 72: return "B"
        elif score >= 48: return "C"
        elif score >= 20: return "D"
        else: return "F"
    except:
        return "C"

# PDF 성적표 생성 함수 정의
def create_academy_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=25, bottomMargin=40)
    story = []

    font_filename = "NANUMGOTHIC.TTF"
    if os.path.exists(font_filename):
        pdfmetrics.registerFont(TTFont('CustomFont', font_filename))
        font_name = 'CustomFont'
    else:
        st.warning(f"⚠️ 저장소에 {font_filename} 파일이 발견되지 않았습니다. 한글 폰트를 업로드해 주세요.")
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
        try:
            pct = min(100, max(0, int(pct_val)))
        except:
            pct = 0
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

    ch_rows = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>영역별 성취 수준 성장 지표 (선형 그라데이션)</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ach_clean = ''.join(filter(str.isdigit, str(ch['achievement'])))
        ch_rows.append([
            Paragraph(ch['name'], body_style),
            make_ch_bar_cell(ach_clean),
            Paragraph(f"{ch['achievement']}%", body_center)
        ])
    t_ch = Table(ch_rows, colWidths=w_ch)
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,1), (1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 12))

    story.append(Paragraph("📊 문항 진단 난이도별 정답률 분석", section_style))
    
    # [오류 해결] 0% 매핑 에러 방지를 위해 확장된 difficulty_analysis 키 연동
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
        try:
            val = int(''.join(filter(str.isdigit, str(st_diff.get(lvl, '0')))))
        except:
            val = 0
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

    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 4))
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=w_comment)
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')),
        ('TOPPADDING', (0,0), (0,0), 8),
        ('BOTTOMPADDING', (0,0),
# ====================================================================
# [교정 완료] 라인 208번 이후의 파일 업로드 및 AI 호출 전체 로직
# ====================================================================

import base64
from pdf2image import convert_from_bytes

# 명문 수학전문학원 원장의 학부모 카운셀링 블로그 문구를 사상 주입하는 특수 지시문
system_prompt = """
너는 코넬수학전문학원의 원장이야. 첨부된 매쓰플랫 리포트(특히 4페이지)를 정밀 분석하여 오차 없는 데이터 JSON을 생성해라.

[추출 및 분석 핵심 지침]
1. 대표 우수 유형 & 대표 취약 유형: 4페이지 데이터에서 가장 두드러지는 문항/유형을 '각각 정확히 3가지씩' 추출하여 리스트로 만들어라. (예: "8번 명제가 참이 되도록 하는 미지수 구하기")
2. 난이도별 정답률 분석: 리포트에 표시된 최상, 상, 중, 중하, 하 각 난이도별 정답률(%) 수치를 정확하게 찾아내어 숫자로 매핑해라. 절대로 0%로 누락시키지 말고 정밀하게 스캔할 것.

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
    "우수 유형 1번째 (예시)",
    "우수 유형 2번째 (예시)",
    "우수 유형 3번째 (예시)"
  ],
  "weakness_types": [
    "취약 유형 1번째 (예시)",
    "취약 유형 2번째 (예시)",
    "취약 유형 3번째 (예시)"
  ],
  "teacher_comment": "학부모 상담용 정중하고 부드러운 종합 코멘트 (4~5문장)"
}
"""

# 파일 업로드 화면 구성
uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"], key="mathflat_uploader")

if uploaded_file is not None:
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state:
            del st.session_state['parsed_data']
        if 'input_cleared' in st.session_state:
            del st.session_state['input_cleared']

    if 'parsed_data' not in st.session_state:
        with st.spinner("코넬 AI가 매쓰플랫 리포트 전체 페이지(우수/취약 유형 포함)를 정밀 Vision 분석 중입니다..."):
            try:
                uploaded_file.seek(0)
                pdf_bytes = uploaded_file.read()
                
                # 4페이지 데이터까지 안정적으로 읽기 위해 전체 페이지 이미지 변환
                images = convert_from_bytes(pdf_bytes, dpi=300)
                
                # 4페이지 분석을 위해 최대 5페이지까지 GPT-4o로 전송
                image_messages = []
                for idx, img in enumerate(images):
                    if idx >= 5: 
                        break
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    image_messages.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high"
                        }
                    })

                vision_user_content = [
                    {
                        "type": "text",
                        "text": "첨부된 매쓰플랫 성적표 이미지에서 학생 정보, 종합 점수, 단원별 성취도(%)를 추출하고, 특히 4페이지에 있는 '대표 우수 유형'과 '대표 취약 유형'의 문항 번호와 내용을 정확히 추출해서 지정된 JSON 포맷으로 응답해줘."
                    }
                ] + image_messages

                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": vision_user_content}
                    ],
                    response_format={"type": "json_object"}
                )
                
                ai_raw_data = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 Vision AI가 4페이지 상세 유형 분석 및 상담 멘트 최적화를 완료했습니다!")
                uploaded_file.seek(0)

            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
                uploaded_file.seek(0)
                st.stop()

    # 데이터 바인딩 및 화면 검토 영역
    res = st.session_state['parsed_data']
    
    st.markdown("---")
    st.subheader("🎯 입학 상담용 결과지 세부 정보 입력 및 검토")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        student_name = st.text_input("학생 이름 (필수 입력)", value=res.get("student_name", ""))
    with col2:
        school_name = st.text_input("학교명 입력", value=res.get("school_name", ""))
    with col3:
        student_grade = st.text_input("학년 입력", value=res.get("student_grade", ""))
        
    report_month = st.text_input("시험 일자 (년/월/일)", value=res.get("report_month", ""))
    score = st.text_input("종합 점수 (원본 고정)", value=str(res.get("score", "0")), disabled=True)
    
      # --------------------------------------------------------------------
    # [교정] 4페이지 유형 자동 연동 및 난이도별 정답률 분석 오류 수정
    # --------------------------------------------------------------------
    # 1. AI가 추출한 유형 데이터를 최대 3개까지만 칼같이 슬라이싱하여 고정
    res["mastery_types"] = res.get("mastery_types", [])[:3]
    res["weakness_types"] = res.get("weakness_types", [])[:3]

    # 2. 난이도별 정답률 분석 0% 오류 해결 (AI 분석 원본 difficulty_analysis 구조 매핑)
    diff_data = res.get("difficulty_analysis", {})
    if isinstance(diff_data, dict):
        # 파싱 딕셔너리에 수치가 문자로 들어올 경우를 대비해 안정적으로 변환 처리
        res["difficulty_analysis"] = {
            "하": diff_data.get("하", "0"),
            "중하": diff_data.get("중하", "0"),
            "중": diff_data.get("중", "0"),
            "상": diff_data.get("상", "0"),
            "최상": diff_data.get("최상", "0")
        } 
    teacher_comment = st.text_area("🦅 코넬 분석 Comment", value=res.get("teacher_comment", ""), height=150)
    
    res["student_name"] = student_name
    res["school_name"] = school_name
    res["student_grade"] = student_grade
    res["report_month"] = report_month
    res["score"] = score
    res["teacher_comment"] = teacher_comment
    
    try:
        pdf_data = create_academy_report(res)
        st.markdown("---")
        st.subheader("👀 결과지 실시간 미리보기")
        pdf_viewer(input=pdf_data.getvalue(), width=700)
        
        st.markdown("---")
        st.subheader("🖨️ 최종 결과지 인쇄 발행")
        st.download_button(
            label="📥 코넬수학 레벨테스트 결과지 PDF 다운로드",
            data=pdf_data,
            file_name=f"{student_name if student_name else '신규생'}_코넬수학_레벨테스트_결과지.pdf",
            mime="application/pdf"
        )
    except Exception as pdf_err:
        st.error(f"PDF 렌더링 중 디자인 에러 발생: {pdf_err}")
