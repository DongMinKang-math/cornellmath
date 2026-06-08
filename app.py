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
    
    # 컴파일 오류를 유실을 원천 차단하기 위해 대괄호 고정값을 수식형 비율로 선언 (A4 내부 가로폭 515 완벽 매핑)
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
    
    # [디자인 완성] 1.5pt 극초슬림 실선 바 레이아웃 및 3색 그라데이션 선형 매핑 적용
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
        
        # 글자 수 유실 방지 가변 연산 패치
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
    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    
    drawing = Drawing(515, 100)
    drawing.add(Rect(0, 0, 515, 100, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))
    
    # [수정완료] 잘려나가기 쉽던 대괄호 묶음 대신 수식 루프로 Y 가이드라인 배정 처리
    for i in range(1, 5):
        y_pos = int((i * 25) * 0.8) + 10
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5, strokeDashArray=[2, 2]))
    
    levels = ["하", "중하", "중", "상", "최상"]
    points = []
    
    # [수정완료] 잘려나가기 쉽던 X축 좌표 대괄호를 수식형 연산 루프로 복구 완료 (5등분)
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
        ('BOTTOMPADDING', (0,0), (0,0), 8),
        ('LEFTPADDING', (0,0), (0,0), 10),
        ('RIGHTPADDING', (0,0), (0,0), 10),
    ]))
    story.append(t_comment)
    # ====================================================================
    # [4단계 신설] 매쓰플랫 4페이지 기반 대표 우수/취약 유형 PDF 드로잉 로직
    # ====================================================================
  # ====================================================================
    # [교정 완료] 대표 우수 유형 / 대표 취약 유형 2분할(좌우) 배치 레이아웃
    # ====================================================================
    story.append(Spacer(1, 15))

    # 좌측 열: 대표 우수 유형 콘텐츠 생성
    mastery_content = [Paragraph("<b>■ 대표 우수 유형</b>", section_style), Spacer(1, 6)]
    mastery_list = data.get("mastery_types", [])
    if not mastery_list:
        mastery_content.append(Paragraph("• 해당 사항 없음 (단원별 성취도 안정적)", body_style))
    else:
        for m_type in mastery_list:
            mastery_content.append(Paragraph(f"• {m_type}", body_style))
            mastery_content.append(Spacer(1, 4))

    # 우측 열: 대표 취약 유형 콘텐츠 생성 (강조용 다크레드 스타일 적용)
    section_style_red = ParagraphStyle('SectionRed', parent=section_style, textColor=colors.HexColor("#C53030"))
    weakness_content = [Paragraph("<b>■ 대표 취약 유형</b>", section_style_red), Spacer(1, 6)]
    weakness_list = data.get("weakness_types", [])
    if not weakness_list:
        weakness_content.append(Paragraph("• 해당 사항 없음 (특이 취약 유형 미검출)", body_style))
    else:
        for w_type in weakness_list:
            weakness_content.append(Paragraph(f"• {w_type}", body_style))
            weakness_content.append(Spacer(1, 4))

    # 두 콘텐츠를 묶어 한 줄에 나오도록 Table로 배치 (가로 폭을 정확히 반씩 분할)
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
    # ====================================================================
    # ====================================================================
    
    def add_footer_logo(canvas, doc):
        canvas.saveState()
        logo_filename = "cornell.png"
        if os.path.exists(logo_filename):
            try:
                canvas.drawImage(logo_filename, 242, 10, width=110, height=42, mask='auto')
            except:
                pass
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_footer_logo, onLaterPages=add_footer_logo)
    buffer.seek(0)
    return buffer
# ====================================================================
# [교정 완료] 라인 208번 이후의 파일 업로드 및 AI 호출 전체 로직
# ====================================================================

import base64
from pdf2image import convert_from_bytes

# 명문 수학전문학원 원장의 학부모 카운셀링 블로그 문구를 사상 주입하는 특수 지시문
system_prompt = """
너는 강남 대치동 및 목동의 상위권 수학전문학원인 코넬수학에서 학부모 입학 상담을 전담하는 친절하고 깊이 있는 원장이야.
매쓰플랫 원본 리포트를 정밀하게 확인하여 오차 없는 데이터 JSON을 빌드해라.
특히 4페이지에 존재하는 '대표 우수 유형'과 '대표 취약 유형' 섹션의 문항 번호와 유형명을 완벽하게 추출해야 한다.

[학부모 상담용 극도로 부드럽고 정중한 어조 지침]:
1. 첫 문장은 무조건 "코넬수학에 관심을 가지고 소중한 자녀의 진단평가에 응해주셔서 깊이 감사드립니다."로 아주 따뜻하고 정중하게 출발할 것.
2. 명령조나 지나치게 딱딱한 표현(요구됩니다, 필요합니다, 요망됩니다 등)은 전면 금지한다. 수학 전문 학원 블로그의 친절한 분석 글처럼 "~해보입니다", "~하는 성향을 띠고 있습니다", "~를 다져나간다면 충분히 성장할 수 있습니다"와 같은 서술어 구조로 부드럽게 감싸줄 것.
3. 결론부에는 '코넬수학만의 차별화된 세심하고 밀착된 1대1 관리 시스템과 철저한 오답 보완 매커니즘을 결합하여, 부족했던 영역을 탄탄한 심화 개념으로 반전시키고 상위권으로 안심하고 도약할 수 있도록 저희 교사진이 사랑과 책임감으로 지도하겠습니다'라는 확신과 안도감을 주는 멘트로 마감할 것.
4. 이 세부 조건들을 바탕으로 문맥을 스스로 5회 연속 리팩토링(5-turn refinement)하여 부드러움과 신뢰가 극대화된 완성형 코멘트(4~5문장)로 리턴해라.

[반드시 지켜야 할 응답 JSON 형식]:
{
  "student_name": "교정된 학생 이름",
  "school_name": "학교명",
  "student_grade": "학년",
  "report_month": "YYYY/MM/DD 형식의 시험 일자",
  "score": "종합 점수 (숫자만)",
  "chapters": [
    {"name": "올바른 단원명 1", "achievement": "성취도 숫자"},
    {"name": "올바른 단원명 2", "achievement": "성취도 숫자"}
  ],
  "mastery_types": [
    "8번 명제가 참이 되도록 하는 미지수 구하기"
  ],
  "weakness_types": [
    "11번 절댓값 기호를 포함한 절대부등식"
  ],
  "teacher_comment": "블로그 상담 패턴 기반으로 윤문된 부드럽고 정중한 원장님 종합 분석 의견"
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
    
    # 🌟 [난이도 칸 제거 후 신설] 4페이지 대표 우수 유형 및 대표 취약 유형 수정/검토 UI
    st.markdown("#### 🔍 매쓰플랫 4페이지 심층 유형 분석 결과")
    
    default_mastery = "\n".join(res.get("mastery_types", [])) if isinstance(res.get("mastery_types"), list) else ""
    default_weakness = "\n".join(res.get("weakness_types", [])) if isinstance(res.get("weakness_types"), list) else ""
    
    col_m, col_w = st.columns(2)
    with col_m:
        mastery_input = st.text_area("🏆 대표 우수 유형 (줄바꿈으로 구분)", value=default_mastery, height=120)
    with col_w:
        weakness_input = st.text_area("⚠️ 대표 취약 유형 (줄바꿈으로 구분)", value=default_weakness, height=120)
    
    # 수정 반영
    res["mastery_types"] = [line.strip() for line in mastery_input.split("\n") if line.strip()]
    res["weakness_types"] = [line.strip() for line in weakness_input.split("\n") if line.strip()]
    
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
