import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io
import os

# PDF 생성 및 정밀 드로잉을 위한 부품 임포트
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
    # 1페이지 최적화 여백 세팅 (상하 25pt, 좌우 40pt)
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=25, bottomMargin=45)
    story = []
    
    font_filename = "NANUMGOTHIC.TTF" 
    if os.path.exists(font_filename):
        pdfmetrics.registerFont(TTFont('CustomFont', font_filename))
        font_name = 'CustomFont'
    else:
        st.warning(f"⚠️ 저장소에 {font_filename} 파일이 발견되지 않았습니다.")
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        font_name = 'HeiseiMin-W3'
        
    styles = getSampleStyleSheet()
    
    # [디자인 개선 4] 타이틀 가독성을 최고 등급으로 올린 굵은 백색 서체 스타일 정의
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#FFFFFF'))
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=12, alignment=2, textColor=colors.HexColor('#64748B'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BodyCenter', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, alignment=1, textColor=colors.HexColor('#1E293B'))
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor('#1E3A8A'))
    
    story.append(Spacer(1, 5))
    
    # [디자인 개선 4] 상단 제목을 고품격 네이비 배너 박스 레이아웃으로 변경
    title_banner_data = [[Paragraph("<b>코넬수학전문학원 신규생 진단평가 결과 분석지</b>", title_style)]]
    t_banner = Table(title_banner_data, colWidths=[515])
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
    story.append(Paragraph(f"<b>진단일자:</b> {data.get('report_month', '최근')}", info_style))
    story.append(Spacer(1, 4))
    
    computed_level = calculate_math_level(data.get('score', '0'))
    
    # 코드 잘림 유실을 원천 차단하기 위한 폭 고정 자동 분할 연산
    w_info = [515 / 6] * 6
    w_ch = [515 * 0.75, 515 * 0.25]
    w_comment = [515]
    
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
    
    ch_rows = [[Paragraph('<b>평가 진단 영역</b>', body_center), Paragraph('<b>성취도</b>', body_center)]]
    for ch in data.get("chapters", []):
        ch_rows.append([Paragraph(ch['name'], body_style), Paragraph(f"{ch['achievement']}%", body_center)])
        
    t_ch = Table(ch_rows, colWidths=w_ch)
    t_ch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_ch)
    story.append(Spacer(1, 12))
    
    # [수정사항 1] 하, 중하, 중, 상, 최상 기준의 꺾은선 그래프 정밀 그리기 구현
    story.append(Paragraph("📊 문항 진단 난이도별 정답률 분석", section_style))
    story.append(Spacer(1, 4))
    
    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    
    # 꺾은선 캔버스 생성 (가로 515, 세로 100)
    drawing = Drawing(515, 100)
    drawing.add(Rect(0, 0, 515, 100, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))
    
    # Y축 가이드 점선 그리기 (25%, 50%, 75%, 100% 라인)
    for y_val in [25, 50, 75]:
        y_pos = int(y_val * 0.8) + 10
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=0.5, strokeDashArray=[2,2]))
    
    # 하, 중하, 중, 상, 최상 수치 정수화 연산
    levels = ["하", "중하", "중", "상", "최상"]
    points = []
    
    # 가로폭 515pt를 5개 영역으로 등분하여 X좌표 설정
    x_coords = [45, 150, 257, 365, 470]
    
    for i, lvl in enumerate(levels):
        try:
            val = int(''.join(filter(str.isdigit, str(st_diff.get(lvl, '0')))))
        except:
            val = 0
        val = min(100, max(0, val))
        y_pos = int(val * 0.8) + 10 # Y축 스케일링 가중치
        points.append((x_coords[i], y_pos, val))
        
    # 꺾은선 및 데이터 마커 그리기
    for i in range(len(points)):
        x, y, v = points[i]
        # 텍스트 라벨 (하, 중하...)
        drawing.add(String(x, 2, levels[i], fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#475569')))
        # 데이터 점수 마커 수치 출력
        drawing.add(String(x, y + 5, f"{v}%", fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#1E3A8A')))
        # 파란색 도트 좌표 그리기
        drawing.add(Circle(x, y, 3, fillColor=colors.HexColor('#1E3A8A'), strokeColor=colors.HexColor('#FFFFFF'), strokeWidth=1))
        # 선 잇기
        if i > 0:
            px, py, _ = points[i-1]
            drawing.add(Line(px, py, x, y, strokeColor=colors.HexColor('#1E3A8A'), strokeWidth=1.5))
            
    story.append(drawing)
    story.append(Spacer(1, 12))
    
    # [수정사항 2] 집중 보완 취약 유형 섹션 동적 삽입
    story.append(Paragraph("🚨 집중 보완 필요 취약 유형", section_style))
    story.append(Spacer(1, 4))
    for i, weak in enumerate(data.get("weak_types", []), 1):
        story.append(Paragraph(f"• <b>{weak}</b> : 해당 유형의 오답 원인을 파악하고 클리닉 강좌를 통해 우선 보완이 요구됩니다.", body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("🦅 코넬 분석 Comment", section_style))
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
    
    # [수정사항 3] 위아래로 찌그러졌던 로고의 종횡비를 높여서 정상으로 보정 (가로 100, 세로 45)
    def add_footer_logo(canvas, doc):
        canvas.saveState()
        logo_filename = "cornell.png"
        if os.path.exists(logo_filename):
            try:
                canvas.drawImage(logo_filename, 247, 10, width=100, height=45, mask='auto')
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
                너는 코넬수학전문학원의 전문 입학상담 실장이야. 
                매쓰플랫 결과 데이터에서 성적 정보와 함께 학생의 오답률이 가장 높은 취약 유형 3가지를 가공해줘.
                종합 코멘트는 "코넬수학에 문을 두드려주어 감사하다"는 환영 인사로 정중하게 시작하고, 단원별 상태 진단 점검 및 코넬의 밀착 솔루션을 담아 4~5문장으로 채워줘.

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
                        "최상": "최상 난이도 정답률 숫자",
                        "상": "상 난이도 정답률 숫자",
                        "중": "중 난이도 정답률 숫자",
                        "중하": "중하 난이도 정답률 숫자",
                        "하": "하 난이도 정답률 숫자"
                    },
                    "weak_types": ["가장 취약한 세부 수학 유형명 1", "유형명 2", "유형명 3"],
                    "teacher_comment": "상담 코멘트 문구"
                }
                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_text}],
                    response_format={"type": "json_object"}
                )
                
                ai_raw_data = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 정밀 분석 완료!")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    if 'parsed_data' in st.session_state:
        res = st.session_state['parsed_data']
        
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
            
        score = st.text_input("종합 점수 (원본 고정)", value=str(res.get("score", "0")), disabled=True)
        teacher_comment = st.text_area("🦅 코넬 분석 Comment (상담 방향에 맞게 편집 가능)", value=res.get("teacher_comment", ""), height=150)
        
        res["student_name"] = student_name
        res["school_name"] = school_name
        res["student_grade"] = student_grade
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
            st.info("💡 위 미리보기를 검토하신 후 다운로드하여 바로 인쇄(A4 세로)하시면 됩니다.")
        except Exception as pdf_err:
            st.error(f"PDF 렌더링 중 디자인 에러 발생: {pdf_err}")
