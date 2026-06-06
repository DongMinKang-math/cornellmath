import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io

# 3단계 PDF 생성을 위한 부품 임포트
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 웹 페이지 설정
st.set_page_config(page_title="학원 성적표 변환 완성형", layout="centered")

st.title("📊 매쓰플랫 보고서 ➡️ 학원 성적표 변환기")
st.caption("AI 가공 데이터 기반 A4 인쇄용 PDF 출력 기능이 포함되어 있습니다.")
st.markdown("---")

# API Key 입력
api_key = st.sidebar.text_input("OpenAI API Key를 입력하세요", type="password")

# PDF 성적표 생성 함수 정의
def create_academy_report(data):
    buffer = io.BytesIO()
    # A4 사이즈 세로형 문서 설정
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # 한국어 폰트 등록 (스트림릿 클라우드에서 별도 다운로드 없이 쓸 수 있는 표준 아시아 폰트인 바탕/돋움체 계열 사용)
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3')) # 한글 출력을 위한 인코딩 매핑용
    
    # 기본 스타일 세트 로드 및 한글 스타일 생성
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontName='HeiseiMin-W3', fontSize=24, leading=28, alignment=1, textColor=colors.HexColor('#1E3A8A')
    )
    info_style = ParagraphStyle(
        'InfoStyle', parent=styles['Normal'], fontName='HeiseiMin-W3', fontSize=11, leading=14, alignment=2
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'], fontName='HeiseiMin-W3', fontSize=11, leading=16
    )
    section_style = ParagraphStyle(
        'SectionStyle', parent=styles['Heading2'], fontName='HeiseiMin-W3', fontSize=14, leading=18, textColor=colors.HexColor('#0F172A')
    )
    
    # 1. 상단 타이틀 및 날짜
    story.append(Spacer(1, 10))
    story.append(Paragraph("📊 수 학 학 원  성 적 표", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>분석 기준일:</b> {data.get('report_month', '이번 달')}", info_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=20))
    
    # 2. 학생 기본 정보 표
    info_data = [
        [Paragraph('<b>학 생 명</b>', body_style), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>종합 점수</b>', body_style), Paragraph(f"{data.get('score', '')}점", body_style),
         Paragraph('<b>반 평 균</b>', body_style), Paragraph(f"{data.get('average_score', '')}점", body_style)]
    ]
    t_info = Table(info_data, colWidths=[70, 90, 70, 90, 70, 90])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (2,0), (2,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (4,0), (4,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 25))
    
    # 3. 단원별 성취도 분석
    story.append(Paragraph("📈 단원별 세부 성취도", section_style))
    story.append(Spacer(1, 5))
    
    ch_rows = [[Paragraph('<b>단 원 명</b>', body_style), Paragraph('<b>성취도 (%)</b>', body_style)]]
    for ch in data.get("chapters", []):
        ch_rows.append([Paragraph(ch['name'], body_style), Paragraph(str(ch['achievement']), body_style)])
        
    t_ch = Table(ch_rows, colWidths=[360, 120])
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#E2E8F0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 25))
    
    # 4. 취약 유형 항목
    story.append(Paragraph("🚨 집중 보완이 필요한 취약 유형", section_style))
    story.append(Spacer(1, 5))
    for i, weak in enumerate(data.get("weak_types", []), 1):
        story.append(Paragraph(f"{i}. {weak}", body_style))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 20))
    
    # 5. 원장님 종합 의견
    story.append(Paragraph("📝 학원 지도 및 종합 의견", section_style))
    story.append(Spacer(1, 5))
    
    comment_box = [[Paragraph(data.get('teacher_comment', '내용 없음'), body_style)]]
    t_comment = Table(comment_box, colWidths=[480])
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0,0), (0,0), 12),
        ('BOTTOMPADDING', (0,0), (0,0), 12),
        ('LEFTPADDING', (0,0), (0,0), 12),
        ('RIGHTPADDING', (0,0), (0,0), 12),
    ]))
    story.append(t_comment)
    
    # 하단 학원 안내
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>○○ 수학전문학원 원장 드림</b>", ParagraphStyle('Footer', parent=body_style, alignment=1, fontSize=12)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# 파일 업로드 화면 구성
uploaded_file = st.file_uploader("매쓰플랫 보고서 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("👈 왼쪽 사이드바에 OpenAI API Key를 먼저 입력해 주세요.")
    else:
        st.success("파일 업로드 완료! 분석을 시작합니다.")
        
        # [데이터 추출 및 AI 가공 트리거 확인]
        if 'parsed_data' not in st.session_state:
            with st.spinner("PDF 추출 및 AI 분석을 최초 1회 실행합니다..."):
                try:
                    # 1단계
                    reader = PdfReader(uploaded_file)
                    full_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text: full_text += text + "\n"

                    # 2단계
                    client = OpenAI(api_key=api_key)
                    system_prompt = """
                    너는 수학학원의 데이터 분석 전문가야. 제공된 매쓰플랫 PDF 텍스트에서 학부모용 성적표에 들어갈 핵심 정보만 추출해서 JSON으로 응답해줘.
                    [반드시 지켜야 할 응답 JSON 형식]:
                    {
                        "student_name": "학생 이름",
                        "report_month": "해당 월/회차 (예: 2026년 6월분)",
                        "score": "종합 성취 점수(숫자만)",
                        "average_score": "반 평균 점수(숫자만)",
                        "chapters": [
                            {"name": "단원명1", "achievement": "성취도(숫자)"},
                            {"name": "단원명2", "achievement": "성취도(숫자)"}
                        ],
                        "weak_types": ["오답률 높은 취약 유형 1", "유형 2", "유형 3"],
                        "teacher_comment": "학습 태도 및 향후 보완 계획 코멘트 (3~4문장)"
                    }
                    """
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_text}],
                        response_format={"type": "json_object"}
                    )
                    st.session_state['parsed_data'] = json.loads(response.choices.message.content)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

        # AI 결과가 세션에 존재할 때 화면 렌더링
        if 'parsed_data' in st.session_state:
            res = st.session_state['parsed_data']
            
            st.markdown("---")
            st.subheader("🎯 AI 데이터 분석 완료")
            
            # 입력 폼 형태로 원장님이 최종 수정 가능하도록 매핑
            student_name = st.text_input("학생 이름", value=res.get("student_name"))
            score = st.text_input("종합 점수", value=str(res.get("score")))
            teacher_comment = st.text_area("종합 의견 코멘트 수정", value=res.get("teacher_comment"), height=120)
            
            # 수정한 값으로 갱신
            res["student_name"] = student_name
            res["score"] = score
            res["teacher_comment"] = teacher_comment
            
            st.markdown("---")
            st.subheader("🖨️ 학원 성적표 PDF 인쇄 파일 생성")
            
            # 3단계: 버튼 클릭 시 PDF 생성 및 다운로드 활성화
            pdf_data = create_academy_report(res)
            
            st.download_button(
                label="📥 학원 성적표 PDF 다운로드 (A4 규격)",
                data=pdf_data,
                file_name=f"{student_name}_학원_성적표.pdf",
                mime="application/pdf"
            )
            st.info("💡 다운로드한 PDF 파일을 열어 [인쇄] 버튼을 누르시면 A4 용지에 꽉 차게 출력됩니다.")
