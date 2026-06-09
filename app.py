import streamlit as st
import base64
import json
import io
import os
from pdf2image import convert_from_bytes
from openai import OpenAI

# PDF 생성 및 정밀 시각화 부품 임포트
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
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
        
        # 각 단원별 성취도 점수를 기반으로 알파벳 등급(A~F) 계산
        ch_level = calculate_math_level(ach_clean)
        
        ch_rows.append([
            Paragraph(ch.get('name', ''), body_style), 
            make_ch_bar_cell(ach_clean), 
            # 성취도 텍스트 오른쪽에 계산된 레벨 추가
            Paragraph(f"{ach_clean}% ({ch_level})", body_center) 
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

    
    # -------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("📊 난이도별 정답률 분석", section_style))
    story.append(Spacer(1, 15))

    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    
    # 1. 캔버스 높이를 160에서 240으로 1.5배 확대 (1페이지 하단 여백 채우기)
    drawing = Drawing(515, 240)
    drawing.add(Rect(0, 0, 515, 240, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))
    
    # 2. 그리드 간격 배율을 1.3에서 2.0으로 확대 (+ 하단 여백 20)
    for y_val in [25, 50, 75, 100]:
        y_pos = int(y_val * 2.0) + 20
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5, strokeDashArray=[2, 2]))
    
    levels = ["하", "중하", "중", "상", "최상"]
    x_coords = [45, 150, 257, 365, 470]
    
    # 회색 기준 성취도 배경선 처리 (배율 2.0 적용)
    baseline_vals = [90, 85, 75, 60, 30]
    for i in range(len(baseline_vals)):
        bx = x_coords[i]
        by = int(baseline_vals[i] * 2.0) + 20
        drawing.add(Circle(bx, by, 1.5, fillColor=colors.HexColor('#94A3B8'), strokeColor=None))
        if i > 0:
            pbx = x_coords[i-1]
            pby = int(baseline_vals[i-1] * 2.0) + 20
            drawing.add(Line(pbx, pby, bx, by, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=0.8, strokeDashArray=[3, 3]))
            
    # 학생 실제 데이터 매핑
    points = []
    for i, lvl in enumerate(levels):
        val_str = ''.join(filter(str.isdigit, str(st_diff.get(lvl, '0'))))
        val = int(val_str) if val_str else 0
        
        # ★ 핵심 오류 수정: AI가 추출한 숫자가 100을 초과하더라도 100으로 고정하여 그래프 이탈 원천 차단
        val = min(val, 100) 
        
        # 학생 점수 높이 계산 (배율 2.0 적용)
        y_pos = int(val * 2.0) + 20
        points.append((x_coords[i], y_pos, val))
        
        # 하단 난이도 라벨 (하, 중하, 중, 상, 최상)
        drawing.add(String(x_coords[i], 6, lvl, fontName=font_name, fontSize=10, textAnchor='middle', fillColor=colors.HexColor('#475569')))
        
    # 학생 점수 연결선 및 포인트 그리기
    for i in range(len(points)):
        cx, cy, cval = points[i]
        drawing.add(Circle(cx, cy, 3, fillColor=colors.HexColor('#2563EB'), strokeColor=colors.HexColor('#2563EB')))
        # 점수 텍스트 표시 위치 조정
        drawing.add(String(cx, cy + 8, f"{cval}%", fontName=font_name, fontSize=9, textAnchor='middle', fillColor=colors.HexColor('#1E293B')))
        if i > 0:
            px, py, _ = points[i-1]
            drawing.add(Line(px, py, cx, cy, strokeColor=colors.HexColor('#2563EB'), strokeWidth=2))
            
    story.append(drawing)
    story.append(Spacer(1, 20))
    # 코넬 분석 코멘트 단락
# -------------------------------------------------------------------------
    # [수정] 코멘트 글자 크기(fontSize) 및 줄 간격(leading) 확대 적용
    # -------------------------------------------------------------------------
    story.append(Paragraph("<b>🦅 코넬 분석 Comment</b>", section_style))
    story.append(Spacer(1, 8))
    
    # 학부모 가독성을 극대화하기 위한 전용 고품격 스타일 생성
    premium_comment_style = ParagraphStyle(
        'PremiumComment',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,       # 기존 9에서 11로 확대
        leading=17,          # 글씨가 커진 만큼 줄 간격도 여유 있게 조정
        textColor=colors.HexColor('#1E293B'),
        alignment=4          # 양쪽 정렬(Justify)로 서류의 깔끔함 유지
    )
    
    w_comment = [515]
    # 위에서 정의한 premium_comment_style을 Paragraph에 적용
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), premium_comment_style)]]
    
    t_comment = Table(comment_box, colWidths=w_comment)
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BORDER', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_comment)

    # === [신규 추가] 레벨 안내 표 생성 로직 ===
    from reportlab.lib.styles import ParagraphStyle
    try:
        score_val = int(''.join(filter(str.isdigit, str(data.get('종합 점수', '0')))))
    except:
        score_val = 0

    # 점수에 따른 행 강조 번호 설정 (A=1, B=2, C=3, D=4, F=5)
    target_row = 5
    if score_val >= 88: target_row = 1
    elif score_val >= 72: target_row = 2
    elif score_val >= 48: target_row = 3
    elif score_val >= 20: target_row = 4

    cell_style = ParagraphStyle('LvlC', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=13)
    cell_style_bold = ParagraphStyle('LvlCB', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=13, alignment=1)

    level_table_data = [
        [Paragraph("<b>레벨</b>", cell_style_bold), Paragraph("<b>점수 구간</b>", cell_style_bold), Paragraph("<b>설명</b>", cell_style_bold)],
        [Paragraph("A 레벨", cell_style_bold), Paragraph("100점 ~ 88점", cell_style_bold), Paragraph("고교 내신 1등급을 독점할 수 있는 실력이며, 서울대·연세대·고려대 및 의치한약수 합격을 정조준할 수 있는 최상위권입니다.", cell_style)],
        [Paragraph("B 레벨", cell_style_bold), Paragraph("87점 ~ 72점", cell_style_bold), Paragraph("개념은 완벽하나 준킬러/킬러 문항에서 오답이 발생하는 단계로, 심화 유형만 정복하면 상위권으로 도약 가능합니다.", cell_style)],
        [Paragraph("C 레벨", cell_style_bold), Paragraph("71점 ~ 48점", cell_style_bold), Paragraph("기본 유형은 해결하지만 응용·변형이 어려운 단계로, 무리한 고난도 문제 풀이보다는 기출 핵심 문항 분석에 집중하여 전략적 학습이 필요합니다.", cell_style)],
        [Paragraph("D 레벨", cell_style_bold), Paragraph("47점 ~ 20점", cell_style_bold), Paragraph("개념을 응용하는 과정에서 벽에 부딪혔을 뿐이니, 교과서 개념과 필수 연산부터 재정비하여 '작은 성공'을 쌓아가며 자신감을 회복할 때입니다.", cell_style)],
        [Paragraph("F 레벨", cell_style_bold), Paragraph("19점 이하", cell_style_bold), Paragraph("오늘 배운 개념 익히기, 예제 3개 스스로 풀기처럼 실현 가능한 하루 목표를 달성하며 수학과의 거리감을 좁혀가는 것이 최우선입니다.", cell_style)]
    ]

    level_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F0DF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    # 학생 점수 레벨에만 하늘색 하이라이트 배경색 칠하기
    level_table_style.add('BACKGROUND', (0, target_row), (-1, target_row), colors.HexColor('#D1E8FF'))

    lvl_table = Table(level_table_data, colWidths=[60, 80, 375])
    lvl_table.setStyle(level_table_style)

    story.append(Spacer(1, 15))
    story.append(lvl_table)

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
# 3. 데이터 유기적 분석 및 향후 공부 방향 제시가 강화된 프리미엄 프롬프트
                system_prompt = """
                당신은 강남 대치동 및 목동의 최상위권 수학전문학원에서 신규생 입학 상담을 전담하는 '수석 교육 팀장(컨설턴트)'입니다.
                제공된 매쓰플랫 PDF 이미지들을 정밀 분석하여 오차 없는 데이터를 추출하고, 학부모가 압도적인 전문성과 깊은 신뢰감을 느낄 수 있는 고품격 '코넬 분석 Comment'를 작성하여 JSON으로 응답하세요.

                [★ 중요: 4페이지 집중 분석 가이드라인]
                1. 입력된 이미지 중 **4번째 이미지(PDF의 4페이지)**를 집중적으로 판독하십시오.
                2. 4페이지에 명시된 **'대표 우수 유형'** 단락에서 문항 유형명들을 찾아내어 `strong_types` 배열에 담으십시오.
                3. 4페이지에 명시된 **'대표 취약 유형'** 단락에서 문항 유형명들을 찾아내어 `weak_types` 배열에 담으십시오.

                [★ 핵심: 프리미엄 상담 코멘트(teacher_comment) 작성 고도화 지침]
                1. **데이터의 유기적 상관관계 분석**: 단편적인 총평은 절대 금지합니다. 상단의 '단원별 성취 분석(chapters)' 데이터와 '문항 진단 난이도별 정답률 분석(difficulty)' 그래프의 흐름을 연계하여 분석해야 합니다. 
                   *(예: 기본 정답률은 높으나 특정 단원의 성취도가 낮다면 개념 누수를, 단원별 점수는 평이하나 상/최상 난이도에서 정답률 낙폭이 크다면 심화 추론력의 공백을 짚어내야 함)*
                2. **본질적 원인 진단**: 가벼운 칭찬이나 모호한 조언 대신, 학생의 현재 학습 상태를 학술적이고 무거운 입시 어휘를 사용하여 날카롭게 진단하십시오.
                   - 권장 어휘: [대수적 구조화 능력, 사고의 임계점 돌파, 조건 제시어 분석의 누수, 개념의 골조, 연산의 완결성, 심화 추론 메커니즘, 직관적 직시와 엄밀한 증명 등]
                3. **향후 공부 방법 및 구체적 방향성 제시**: 진단에 그치지 않고, 이 약점을 타파하기 위해 '앞으로 어떤 방식으로 오답을 관리하고 실전 사고력을 확장해야 하는지' 명확한 학습 지침을 제시하십시오.
                4. **본원(코넬수학) 솔루션과의 연계**: 앞서 제시한 공부 방향을 완벽하게 실현할 본원의 핵심 시스템인 '타이트한 1:1 밀착 개별 클리닉' 및 '망각 곡선을 제어하는 무한 오답 제어 메커니즘'을 해결책으로 자연스럽게 녹여내십시오.
                5. **문체 및 분량**: 대치동 특유의 냉철하면서도 확신에 찬 전문가의 어조(~입니다, ~하십시오)로 **총 5~6문장 내외**로 밀도 높게 작성하십시오.

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
                  "teacher_comment": "유기적 데이터 분석과 향후 공부 방향이 담긴 프리미엄 코멘트"
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
                    temperature=0.2
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
