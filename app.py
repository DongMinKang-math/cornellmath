import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io
import os

# PDF 생성을 위한 부품 임포트
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 웹 페이지 설정
st.set_page_config(page_title="학원 성적표 변환 자동화", layout="centered")

st.title("📊 매쓰플랫 보고서 ➡️ 학원 성적표 변환기")
st.caption("A4 인쇄용 고품질 PDF 출력 시스템")
st.markdown("---")

# Secrets에서 안전하게 API Key 로드
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("❌ Streamlit Cloud Settings -> Secrets에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
    st.stop()

# PDF 성적표 생성 함수 정의
def create_academy_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # 깃허브에 업로드한 폰트 파일 연동 설정
    font_filename = "NANUMGOTHIC.TTF"
    
    if os.path.exists(font_filename):
        pdfmetrics.registerFont(TTFont('CustomFont', font_filename))
        font_name = 'CustomFont'
    else:
        st.warning(f"⚠️ 저장소에 {font_filename} 파일이 없어 한글이 공백으로 나올 수 있습니다. 폰트를 업로드해 주세요.")
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        font_name = 'HeiseiMin-W3'
        
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=24, leading=28, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName=font_name, fontSize=11, leading=14, alignment=2)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=11, leading=16)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName=font_name, fontSize=14, leading=18, textColor=colors.HexColor('#1E3A8A'))
    
    # 상단 학원 로고 배치
    logo_filename = "cornell.png"
    if os.path.exists(logo_filename):
        try:
            story.append(Image(logo_filename, width=120, height=40))
            story.append(Spacer(1, 10))
        except:
            pass
            
    story.append(Paragraph("수 학 학 원  정 기  성 적 표", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>분석 기준일:</b> {data.get('report_month', '이번 달')}", info_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=20))
    
    # [수정완료] 학생 기본 정보 표 가로 너비 (총 510)
    info_data = [
        [Paragraph('<b>학 생 명</b>', body_style), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>종합 점수</b>', body_style), Paragraph(f"{data.get('score', '')}점", body_style),
         Paragraph('<b>반 평 균</b>', body_style), Paragraph(f"{data.get('average_score', '')}점", body_style)]
    ]
    t_info = Table(info_data, colWidths=[80, 90, 80, 90, 80, 90])
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
    
    story.append(Paragraph("📈 단원별 세부 성취도", section_style))
    story.append(Spacer(1, 8))
    
    ch_rows = [[Paragraph('<b>분석 단원명</b>', body_style), Paragraph('<b>성취도 (%)</b>', body_style)]]
    for ch in data.get("chapters", []):
        ch_rows.append([Paragraph(ch['name'], body_style), Paragraph(f"{ch['achievement']}%", body_style)])
        
    # [수정완료] 단원 성취도 표 가로 너비 (총 510)
    t_ch = Table(ch_rows, colWidths=[380, 130])
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#E2E8F0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 25))
    
    story.append(Paragraph("🚨 집중 보완이 필요한 취약 유형", section_style))
    story.append(Spacer(1, 8))
    for i, weak in enumerate(data.get("weak_types", []), 1):
        story.append(Paragraph(f"<b>{i}.</b> {weak}", body_style))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 25))
    
    story.append(Paragraph("📝 학원 지도 및 종합 의견", section_style))
    story.append(Spacer(1, 8))
    
    # [수정완료] 코멘트 박스 가로 너비 (총 510)
    comment_box = [[Paragraph(data.get('teacher_comment', '내용 없음').replace('\n', '<br/>'), body_style)]]
    t_comment = Table(comment_box, colWidths=[510])
    t_comment.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (0,0), 1.5, colors.HexColor('#1E3A8A')),
        ('TOPPADDING', (0,0), (0,0), 12),
        ('BOTTOMPADDING', (0,0), (0,0), 12),
        ('LEFTPADDING', (0,0), (0,0), 12),
        ('RIGHTPADDING', (0,0), (0,0), 12),
    ]))
    story.append(t_comment)
    
    story.append(Spacer(1, 35))
    story.append(Paragraph("<b>수학전문학원 원장 드림</b>", ParagraphStyle('Footer', parent=body_style, alignment=1, fontSize=13)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# 파일 업로드 화면 구성
uploaded_file = st.file_uploader("매쓰플랫 보고서 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state:
            del st.session_state['parsed_data']

    if 'parsed_data' not in st.session_state:
        with st.spinner("PDF에서 성적 데이터를 분석하는 중입니다..."):
            try:
                reader = PdfReader(uploaded_file)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text: full_text += text + "\n"

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
                
                # [수정완료] 리스트 객체의 첫 번째 인덱스[0] 명시
                ai_content = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_content)
                st.success("AI 데이터 분석 완료!")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    if 'parsed_data' in st.session_state:
        res = st.session_state['parsed_data']
        
        st.markdown("---")
        st.subheader("🎯 AI 데이터 분석 수정")
        
        student_name = st.text_input("학생 이름", value=res.get("student_name", ""))
        score = st.text_input("종합 점수", value=str(res.get("score", "")))
        teacher_comment = st.text_area("종합 의견 코멘트 수정", value=res.get("teacher_comment", ""), height=120)
        
        res["student_name"] = student_name
        res["score"] = score
        res["teacher_comment"] = teacher_comment
        
        st.markdown("---")
        st.subheader("🖨️ 학원 성적표 PDF 인쇄 파일 생성")
        
        try:
            pdf_data = create_academy_report(res)
            st.download_button(
                label="📥 학원 성적표 PDF 다운로드 (A4 규격)",
                data=pdf_data,
                file_name=f"{student_name}_학원_성적표.pdf",
                mime="application/pdf"
            )
            st.info("💡 다운로드한 PDF 파일을 열어 인쇄하시면 A4 용지에 맞게 한글이 깨끗하게 출력됩니다.")
        except Exception as pdf_err:
            st.error(f"PDF 디자인 생성 중 오류 발생: {pdf_err}")
