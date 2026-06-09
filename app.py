import streamlit as st
import base64
import json
import io
import os
from pdf2image import convert_from_bytes
from openai import OpenAI

# PDF 생성 및 정밀 시각화 부품 임포트
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from streamlit_pdf_viewer import pdf_viewer

# 웹 페이지 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", page_icon="📊", layout="centered")
st.title("📊 코넬수학전문학원 레벨테스트 결과지 시스템")
st.caption("매쓰플랫 PDF를 정밀 시각 분석하여 공식 신규생 진단 결과지를 발행합니다.")
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

# PDF 성적표 생성 함수
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
    # 2. 제목 서식 굵고 선명하게 변경 (fontSize 및 두께감 강화)
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=19, leading=24, alignment=1, textColor=colors.HexColor('#FFFFFF'))
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
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 6))

    story.append(Paragraph(f"<b>시험 일자:</b> {data.get('report_month', '년/월/일')}", info_style))
    story.append(Spacer(1, 4))

    computed_level = calculate_math_level(data.get('score', '0'))

    w_info = [515 / 6] * 6
    w_ch = [515 * 0.42, 515 * 0.45, 515 * 0.13]
    w_comment = 515

    info_data = [
        [Paragraph('<b>학 생 명</b>', body_center), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>학 교 명</b>', body_center), Paragraph(data.get('school_name', ''), body_style),
         Paragraph('<b>학 년</b>', body_center), Paragraph(data.get('student_grade', ''), body_style)],
        [Paragraph('<b>종합 점수</b>', body_center), Paragraph(f"<b>{data.get('score', '')} 점</b>", body_style),
         Paragraph('<b>진단 레벨</b>', body_center), Paragraph(f"<b>{computed_level} Level</b>", body_style),
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

    # 1. '영역별 성취 수준 성장 지표' 막대그래프 슬림화 및 고급화 디자인 변경
    def make_ch_bar_cell(pct_val):
        try: pct = min(100, max(0, int(pct_val)))
        except: pct = 0
        
        # 높이 10px짜리 프리미엄 얇은 라운딩 바 드로잉 디자인
        d = Drawing(200, 10)
        # 연회색 백그라운드 트랙
        d.add(Rect(0, 2, 200, 6, fillColor=colors.HexColor('#E2E8F0'), strokeColor=None, rx=3, ry=3))
        # 활성화 성취도 바 (코넬 블루 메인컬러)
        if pct > 0:
            w_filled = max(2, int(pct * 2.0))
            d.add(Rect(0, 2, w_filled, 6, fillColor=colors.HexColor('#2563EB'), strokeColor=None, rx=3, ry=3))
        return d

    ch_rows = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>영역별 성취 수준 성장 지표</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ach_clean = ''.join(filter(str.isdigit, str(ch.get('achievement', '0'))))
        ch_rows.append([Paragraph(ch.get('name', ''), body_style), make_ch_bar_cell(ach_clean), Paragraph(f"{ach_clean}%", body_center)])
    
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
    story.append(Spacer(1, 4))

    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    drawing = Drawing(515, 100)
    drawing.add(Rect(0, 0, 515, 100, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))
    
    for y_val in [25, 50, 75, 100]:
        y_pos = int(y_val * 0.8) + 10
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5, strokeDashArray=[2, 2]))
    
    levels = ["하", "중하", "중", "상", "최상"]
    points = []
    x_coords = [45, 150, 257, 365, 470]
    
    for i, lvl in enumerate(levels):
        try: val = int(''.join(filter(str.isdigit, str(st_diff.get(lvl, '0')))))
        except: val = 0
        val = min(100, max(0, val))
        y_pos = int(val * 0.8) + 10
        points.append((x_coords[i], y_pos, val))
        
    for i in range(len(points)):
        x, y, v = points[i]
        drawing.add(String(x, 2, levels[i], fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#475569')))
        drawing.add(String(x, y + 5, f"{v}%", fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#1E3A8A')))
        drawing.add(Circle(x, y, 2.5, fillColor=colors.HexColor('#1E3A8A'), strokeColor=colors.HexColor('#FFFFFF'), strokeWidth=1))
        if i > 0:
            px, py, _ = points[i-1]
            drawing.add(Line(px, py, x, y, strokeColor=colors.HexColor('#1E3A8A'), strokeWidth=1.2))
            
    story.append(drawing)
    story.append(Spacer(1, 14))

    # 3. 대표 우수 유형 / 대표 취약 유형 섹션 추가 (코멘트 위쪽 삽입)
    story.append(Paragraph("🎯 핵심 유형별 상세 진단 결과", section_style))
    story.append(Spacer(1, 4))
    
    strong_list = data.get("strong_types", [])
    weak_list = data.get("weak_types", [])
    
    strong_text = "<br/>".join([f"• {t}" for t in strong_list]) if strong_list else "• 분석된 우수 유형 정보가 없습니다."
    weak_text = "<br/>".join([f"• {t}" for t in weak_list]) if weak_list else "• 분석된 취약 유형 정보가 없습니다."
    
    type_table_data = [
        [Paragraph('<b>🦅 대표 우수 유형 (Strengths)</b>', body_style), Paragraph('<b>⚠️ 대표 취약 유형 (Weaknesses)</b>', body_style)],
        [Paragraph(strong_text, body_style), Paragraph(weak_text, body_style)]
    ]
    t_types = Table(type_table_data, colWidths=[255, 260])
    t_types.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#EFF6FF')), # 연한 우수 블루
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FEF2F2')), # 연한 취약 레드
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_types)
    story.append(Spacer(1, 14))

    # 코넬 분석 코멘트 단락
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
            try: canvas.drawImage(logo_filename, 242, 12, width=110, height=38, mask='auto')
            except: pass
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer_logo, onLaterPages=add_footer_logo)
    buffer.seek(0)
    return buffer

# 메인 UI 로직
uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"])

if uploaded_file is not None:
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state: del st.session_state['parsed_data']
        if 'input_cleared' in st.session_state: del st.session_state['input_cleared']

    if 'parsed_data' not in st.session_state:
        with st.spinner("코넬 AI가 비전(Vision) 기술로 리포트를 정밀 판독하고 프리미엄 코멘트를 작성 중입니다..."):
            try:
                # 1. PDF를 이미지로 변환
                pdf_bytes = uploaded_file.getvalue()
                images = convert_from_bytes(pdf_bytes, dpi=200)
                
                base64_images = []
                for img in images:
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    base64_images.append(img_str)

                client = OpenAI(api_key=api_key)

                # 3. 우수유형/취약유형 추출 조건이 고도화된 프롬프트
# 3. 4페이지 타겟팅 및 프리미엄 톤앤매너 프롬프트 개정
                system_prompt = """
                당신은 강남 대치동 및 목동의 최상위권 수학전문학원에서 신규생 입학 상담을 전담하는 '수석 교육 팀장(컨설턴트)'입니다.
                제공된 매쓰플랫 PDF 이미지들(1페이지부터 순서대로 입력됨)을 정밀하게 분석하여 오차 없는 데이터를 추출하고 JSON으로 응답하세요.

                [★ 중요: 4페이지 집중 분석 가이드라인]
                1. 입력된 이미지 중 **4번째 이미지(PDF의 4페이지)**를 집중적으로 판독하십시오.
                2. 4페이지에 명시된 **'대표 우수 유형'** 단락에서 문항 유형명(예: 대단원/소단원명 또는 구체적인 유형 텍스트)들을 찾아내어 `strong_types` 배열에 담으십시오.
                3. 4페이지에 명시된 **'대표 취약 유형'** 단락에서 문항 유형명들을 찾아내어 `weak_types` 배열에 담으십시오.
                4. 만약 해당 페이지에서 유형명이 텍스트로 보인다면 번호나 핵심 키워드를 생략하지 말고 명확하게 배열에 담아야 합니다.

                [프리미엄 상담 코멘트 가이드라인]
                1. 가벼운 칭찬이나 어색한 번역투("참 잘했습니다", "좋은 결과입니다")는 절대 금지합니다.
                2. 객관적이고 무게감 있는 학술적 어휘를 사용하세요. (예: "기본 개념의 뼈대가 견고하게 형성되어 있음", "특정 유형에서 조건 분석의 누수가 관찰됨", "학습 임계점 돌파가 필요함" 등)
                3. 학생의 취약점을 날카롭게 분석한 뒤, 반드시 본원(코넬수학)의 '타이트한 밀착 개별 클리닉' 및 '무한 오답 제어 메커니즘'을 해결책으로 제시하세요.
                4. 문체는 정중하면서도 확신에 찬 전문가의 어조(단정적인 문어체 혹은 하십시오체)로 총 4~5문장 작성하세요.

                [반드시 지켜야 할 응답 JSON 형식]
                {
                  "student_name": "학생 이름",
                  "school_name": "학교명",
                  "student_grade": "학년",
                  "report_month": "YYYY/MM/DD",
                  "score": "숫자만",
                  "chapters": [
                    {"name": "단원명", "achievement": "숫자만"}
                  ],
                  "difficulty": {
                    "최상": "숫자만",
                    "상": "숫자만",
                    "중": "숫자만",
                    "중하": "숫자만",
                    "하": "숫자만"
                  },
                  "strong_types": ["4페이지에서 추출한 우수 유형 1", "4페이지에서 추출한 우수 유형 2"],
                  "weak_types": ["4페이지에서 추출한 취약 유형 1", "4페이지에서 추출한 취약 유형 2"],
                  "teacher_comment": "교정된 프리미엄 상담 코멘트"
                }
                """

                messages_content = [{"type": "text", "text": system_prompt}]
                for b64_img in base64_images:
                    messages_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                    })

                # API 호출 (GPT-4o Vision 활용)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a highly skilled data extraction AI. You must output valid JSON only."},
                        {"role": "user", "content": messages_content}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=2000,
                    temperature=0.2  # 데이터 추출의 정확도를 높이기 위해 온도를 0.3에서 0.2로 소폭 하향
                )
                
                ai_raw_data = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 대형학원 비전 판독 및 코멘트 최적화 완료!")
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    if 'parsed_data' in st.session_state:
        res = st.session_state['parsed_data']
        
        if 'input_cleared' not in st.session_state:
            res["student_name"] = res.get("student_name", "")
            res["school_name"] = res.get("school_name", "")
            res["student_grade"] = res.get("student_grade", "")
            st.session_state['input_cleared'] = True

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
        
        # UI 영역에 검토 및 수정이 가능하도록 추출된 유형 칸 배치
        col_str, col_wek = st.columns(2)
        with col_str:
            strong_input = st.text_area("🦅 추출된 대표 우수 유형 (줄바꿈 구분)", value="\n".join(res.get("strong_types", [])), height=100)
        with col_wek:
            weak_input = st.text_area("⚠️ 추출된 대표 취약 유형 (줄바꿈 구분)", value="\n".join(res.get("weak_types", [])), height=100)

        teacher_comment = st.text_area("🦅 코넬 분석 Comment (프리미엄 컨설팅 스타일 초안 / 수정 가능)", value=res.get("teacher_comment", ""), height=150)
        
        # 변경값 다시 매핑
        res["student_name"] = student_name
        res["school_name"] = school_name
        res["student_grade"] = student_grade
        res["report_month"] = report_month
        res["strong_types"] = [x.strip() for x in strong_input.split("\n") if x.strip()]
        res["weak_types"] = [x.strip() for x in weak_input.split("\n") if x.strip()]
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
            st.info("💡 위 미리보기를 검토하신 후 다운로드하여 바로 인쇄(A4 세로)하시면 됩니다.")
            
        except Exception as pdf_err:
            st.error(f"PDF 렌더링 중 에러 발생: {pdf_err}")
