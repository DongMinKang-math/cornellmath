import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io
import os
import base64

# PDF 생성을 위한 부품 임포트
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 웹 페이지 설정
st.set_page_config(page_title="코넬수학 레벨테스트 결과지 시스템", layout="centered")

# [수정사항 1] 메인 홈페이지 상단에 로고 삽입
logo_filename = "cornell.png"
if os.path.exists(logo_filename):
    st.image(logo_filename, width=180)

st.title("🦅 코넬수학전문학원 레벨테스트 결과지 시스템")
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=60)
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
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=20, leading=26, alignment=1, textColor=colors.HexColor('#0F172A'))
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=14, alignment=2)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=15)
    body_center = ParagraphStyle('BodyCenter', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=15, alignment=1)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName=font_name, fontSize=13, leading=17, textColor=colors.HexColor('#1E3A8A'))
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>코넬수학전문학원 신규생 레벨테스트 결과지</b>", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>진단일:</b> {data.get('report_month', '최근')}", info_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=20))
    
    computed_level = calculate_math_level(data.get('score', '0'))
    
    info_data = [
        [Paragraph('<b>학 생 명</b>', body_center), Paragraph(data.get('student_name', ''), body_style),
         Paragraph('<b>학 교 명</b>', body_center), Paragraph(data.get('school_name', ''), body_style),
         Paragraph('<b>학 년</b>', body_center), Paragraph(data.get('student_grade', ''), body_style)],
        [Paragraph('<b>종합 점수</b>', body_center), Paragraph(f"<b>{data.get('score', '')} 점</b>", body_style),
         Paragraph('<b>진단 레벨</b>', body_center), Paragraph(f"<b>{computed_level} Level</b>", body_style),
         Paragraph('', body_style), Paragraph('', body_style)]
    ]
    
    t_info = Table(info_data, colWidths=[70, 100, 70, 100, 70, 100])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (2,0), (2,1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (4,0), (4,0), colors.HexColor('#F1F5F9')),
        ('SPAN', (3,1), (5,1)),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("📈 단원별 평가 분석", section_style))
    story.append(Spacer(1, 6))
    
    ch_rows = [[Paragraph('<b>평가 단원 영역</b>', body_center), Paragraph('<b>성취도 (%)</b>', body_center)]]
    for ch in data.get("chapters", []):
        ch_rows.append([Paragraph(ch['name'], body_style), Paragraph(f"{ch['achievement']}%", body_center)])
        
    t_ch = Table(ch_rows, colWidths=[380, 130])
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#E2E8F0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("📊 문항 난이도별 정답률 분석", section_style))
    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "하": "0"})
    
    diff_data = [
        [Paragraph('<b>난이도</b>', body_center), Paragraph('<b>정답률</b>', body_center), Paragraph('<b>취약도 진단</b>', body_center)],
        [Paragraph('최상 / 상', body_style), Paragraph(f"{st_diff.get('상', '0')}%", body_center), Paragraph('심화 개념 및 고난도 문제해결력 진단', body_style)],
        [Paragraph('중', body_style), Paragraph(f"{st_diff.get('중', '0')}%", body_center), Paragraph('응용 문제 및 핵심 유형 적용력 진단', body_style)],
        [Paragraph('하', body_style), Paragraph(f"{st_diff.get('하', '0')}%", body_center), Paragraph('기본 개념 및 기초 계산 능력 진단', body_style)]
    ]
    t_diff = Table(diff_data, colWidths=[90, 80, 340])
    t_diff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (2,0), colors.HexColor('#E2E8F0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_diff)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
    story.append(Spacer(1, 6))
    
    comment_box = [[Paragraph(data.get('teacher_comment', '').replace('\n', '<br/>'), body_style)]]
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
    
    def add_footer_logo(canvas, doc):
        canvas.saveState()
        if os.path.exists(logo_filename):
            try:
                canvas.drawImage(logo_filename, 237, 20, width=120, height=30, mask='auto')
            except:
                pass
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_footer_logo, onLaterPages=add_footer_logo)
    buffer.seek(0)
    return buffer
# 파일 업로드 화면 구성
uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"])

if uploaded_file is not None:
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state:
            del st.session_state['parsed_data']
        # 초기 공백 설정을 위한 세션 플래그 리셋
        if 'input_cleared' in st.session_state:
            del st.session_state['input_cleared']

    if 'parsed_data' not in st.session_state:
        with st.spinner("코넬 AI 엔진이 레벨테스트지를 분석하여 정밀 진단 데이터를 정제 중입니다..."):
            try:
                reader = PdfReader(uploaded_file)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text: full_text += text + "\n"

                client = OpenAI(api_key=api_key)
                system_prompt = """
                너는 코넬수학전문학원의 전문 입학상담 실장이자 교육 분석가야. 
                제공된 매쓰플랫 테스트 결과 텍스트에서 데이터를 추출하고, '새로 학원을 등록하려는 신규 학생과 학부모'를 타겟으로 정중하고 친절하면서도 학원의 전문성이 돋보이는 분석 JSON을 작성해줘.

                [분석 가이드라인]:
                - teacher_comment 작성 시: "코넬수학에 문을 두드려주어 감사하다"는 취약 극복 독려 인사를 할 것.
                - 학생이 어떤 대단원에서 강점과 약점을 보이는지 텍스트 기반으로 날카롭게 짚어줄 것.
                - 향후 코넬수학의 정밀 커리큘럼을 통해 어떻게 약점을 보완하고 레벨을 도약할 수 있는지 지도 계획을 제시할 것 (4~5문장 내외).

                [반드시 지켜야 할 응답 JSON 형식]:
                {
                    "student_name": "학생 이름",
                    "school_name": "학교명",
                    "student_grade": "학년",
                    "report_month": "오늘 날짜 또는 테스트 시행 월",
                    "score": "종합 성취 점수(숫자만)",
                    "chapters": [
                        {"name": "분석 단원명 1", "achievement": "성취도 숫자"},
                        {"name": "분석 단원명 2", "achievement": "성취도 숫자"}
                    ],
                    "difficulty": {
                        "상": "최상 및 상 난이도 문항 정답률 숫자",
                        "중": "중 난이도 문항 정답률 숫자",
                        "하": "하 난이도 문항 정답률 숫자"
                    },
                    "teacher_comment": "상담 코멘트 문구"
                }
                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_text}],
                    response_format={"type": "json_object"}
                )
                
                ai_content = response.choices.message.content
                st.session_state['parsed_data'] = json.loads(ai_content)
                st.success("🎉 코넬 정밀 분석 완료!")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    if 'parsed_data' in st.session_state:
        res = st.session_state['parsed_data']
        
        # [수정사항 2] 최초 1회만 학생 정보를 완전한 빈칸(공백)으로 강제 초기화 처리
        if 'input_cleared' not in st.session_state:
            res["student_name"] = ""
            res["school_name"] = ""
            res["student_grade"] = ""
            st.session_state['input_cleared'] = True
        
        st.markdown("---")
        st.subheader("🎯 입학 상담용 결과지 세부 정보 입력")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            student_name = st.text_input("학생 이름 (필수 입력)", value=res.get("student_name", ""))
        with col2:
            school_name = st.text_input("학교명 입력", value=res.get("school_name", ""))
        with col3:
            student_grade = st.text_input("학년 입력", value=res.get("student_grade", ""))
            
        # [수정사항 3] 종합 점수 화면 수정 불가능(disabled) 처리
        score = st.text_input("종합 점수 (원본 고정)", value=str(res.get("score", "0")), disabled=True)
        teacher_comment = st.text_area("🦅 코넬 분석 Comment (상담 방향에 맞게 편집 가능)", value=res.get("teacher_comment", ""), height=150)
        
        res["student_name"] = student_name
        res["school_name"] = school_name
        res["student_grade"] = student_grade
        res["score"] = score
        res["teacher_comment"] = teacher_comment
        
        # PDF 미리 빌드
        try:
            pdf_data = create_academy_report(res)
            
            # [수정사항 4] 실시간 미리보기 기능 구현 (PDF를 Base64 인코딩하여 iframe 뷰어로 화면 임베딩)
            st.markdown("---")
            st.subheader("👀 결과지 실시간 미리보기")
            
            base64_pdf = base64.b64encode(pdf_data.getvalue()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" style="border:1px solid #CBD5E1; border-radius:8px;"></iframe>'
            st.markdown(pdf_display, unsafe_with_html=True)
            
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
            st.error(f"PDF 렌더링 중 디자인 에러 발생: {pdf_err}")
