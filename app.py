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
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#FFFFFF'))
    info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=12, alignment=2, textColor=colors.HexColor('#64748B'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, textColor=colors.HexColor('#1E293B'))
    body_center = ParagraphStyle('BodyCenter', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=14, alignment=1, textColor=colors.HexColor('#1E293B'))
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor('#1E3A8A'))
    
    story.append(Spacer(1, 5))
    
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
    story.append(Paragraph(f"<b>시험 일자:</b> {data.get('report_month', '년/월/일')}", info_style))
    story.append(Spacer(1, 4))
    
    computed_level = calculate_math_level(data.get('score', '0'))
    
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
    
    story.append(Paragraph("📊 문항 진단 난이도별 정답률 분석", section_style))
    st_diff = data.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
    
    drawing = Drawing(515, 100)
    drawing.add(Rect(0, 0, 515, 100, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=0.5))
    
    for y_val in [25, 50, 75, 100]:
        y_pos = int(y_val * 0.8) + 10
        drawing.add(Line(0, y_pos, 515, y_pos, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=0.5, strokeDashArray=[2, 2]))
    
    levels = ["하", "중하", "중", "상", "최상"]
    points = []
    x_coords = [40, 150, 257, 365, 475]
    
    for i, lvl in enumerate(levels):
        try:
            val = int(''.join(filter(str.isdigit, str(st_diff.get(lvl, '0')))))
        except:
            val = 0
        val = min(100, max(0, val))
        y_pos = int(val * 0.8) + 10
        points.append((x_coords[i], y_pos, val))
        
    for i in range(len(points)):
        x, y, v = points[i]
        drawing.add(String(x, 2, levels[i], fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#475569')))
        drawing.add(String(x, y + 5, f"{v}%", fontName='CustomFont', fontSize=8, textAnchor='middle', fillColor=colors.HexColor('#1E3A8A')))
        drawing.add(Circle(x, y, 3, fillColor=colors.HexColor('#1E3A8A'), strokeColor=colors.HexColor('#FFFFFF'), strokeWidth=1))
        if i > 0:
            px, py, _ = points[i-1]
            drawing.add(Line(px, py, x, y, strokeColor=colors.HexColor('#1E3A8A'), strokeWidth=1.5))
            
    story.append(drawing)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("🚨 집중 보완 필요 대표 취약 유형 (매쓰플랫 발췌)", section_style))
    story.append(Spacer(1, 4))
    
    weak_list = data.get("weak_types", [])
    if not weak_list or len(weak_list) == 0:
        weak_list = ["원본 보고서의 취약 유형 단원을 검토해 주세요."]
        
    for i, weak in enumerate(weak_list, 1):
        story.append(Paragraph(f"• <b>{weak}</b> : 취약도가 발견된 대표적인 유형 영역입니다. 코넬만의 밀착 오답 메커니즘을 통한 오답 클리닉이 집중적으로 필요합니다.", body_style))
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
    
    def add_footer_logo(canvas, doc):
        canvas.saveState()
        logo_filename = "cornell.png"
        if os.path.exists(logo_filename):
            try:
                canvas.drawImage(logo_filename, 242, 12, width=110, height=38, mask='auto')
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
        with st.spinner("코넬 AI 진단 엔진이 매쓰플랫 구조 폰트를 역해석하고 데이터를 정밀 복원 중입니다..."):
            try:
                reader = PdfReader(uploaded_file)
                full_text = ""
                
                # 가독성이 무너진 외계어 상태의 데이터라도 매쓰플랫의 고유 배치 인덱스 구조를 유지하도록 페이지화 결합
                for idx, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- [PAGE {idx}] ---\n" + text

                client = OpenAI(api_key=api_key)
                
                # [해결 핵심] 깨진 인코딩 매커니즘을 복구하기 위해 LLM에게 폰트 복원 바인딩 임무 부여 및 3중 윤문 지침 적용
                system_prompt = """
                너는 매쓰플랫 시스템 보고서의 파일 구조와 특수 한글 암호화 폰트 체계를 완벽하게 지식으로 갖고 있는 인코딩 복구 AI 전문가이자 코넬수학의 입학상담 실장이야.

                [현상 정보 및 조치 지침]:
                1. 현재 입력으로 주어지는 텍스트 데이터는 매쓰플랫 내부 서체의 특수 암호화 배치 때문에 한글 자음/모음이 꼬이거나 외계어 형태로 깨져서 보일 수 있어.
                2. 너는 글자 자체에 매몰되지 말고, 매쓰플랫 레벨테스트지의 고유 데이터 정렬 패턴(점수, 단원 레이아웃, 난이도 테이블 배치 구조)을 해독하여 정상적인 한국어 정보로 변환(역인코딩)해야 해.
                3. 특히 [PAGE 4] 및 세부 영역에 표기된 '대표 취약 유형' 또는 '오답률이 높은 유형'의 깨진 단어 구조를 올바른 대한민국 교과과정 수학 단원명(예: 일차방정식의 활용, 삼각형의 성질 등)으로 복구하여 원문 발췌 가치와 동일하게 정제해줘.
                4. difficulty 수치 파싱: 난이도별 정답률은 임의 유추하지 말고, 배치 테이블에서 매칭된 값을 추출해줘.
                5. teacher_comment 고도화: '코넬수학에 관심을 가지고 진단에 응해주어 감사하다'는 첫인사 후, 약점을 보완하여 성적을 끌어올릴 수 있는 정중하고 매끄러운 코멘트를 3중 자체 검증하여 작성해줘.

                [반드시 지켜야 할 응답 JSON 형식]:
                {
                    "student_name": "복구된 학생 이름",
                    "school_name": "학교명",
                    "student_grade": "학년",
                    "report_month": "YYYY/MM/DD 형식의 시험 일자",
                    "score": "종합 점수 (숫자만)",
                    "chapters": [
                        {"name": "올바르게 교정된 단원명 1", "achievement": "성취도 숫자"},
                        {"name": "올바르게 교정된 단원명 2", "achievement": "성취도 숫자"}
                    ],
                    "difficulty": {
                        "최상": "최상 정답률 숫자",
                        "상": "상 정답률 숫자",
                        "중": "중 정답률 숫자",
                        "중하": "중하 정답률 숫자",
                        "하": "하 정답률 숫자"
                    },
                    "weak_types": ["PAGE 4 구조에서 완벽히 복원 발췌한 대표 취약 유형 1", "유형 2", "유형 3"],
                    "teacher_comment": "매끄럽게 보완된 상담 코멘트"
                }
                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_text}],
                    response_format={"type": "json_object"}
                )
                
                ai_raw_data = response.choices.message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 데이터 인코딩 보정 및 발췌 완료!")
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
            student_name = st.text_input("학생 이름 (필수)", value=res.get("student_name", ""))
        with col2:
            school_name = st.text_input("학교명 입력", value=res.get("school_name", ""))
        with col3:
            student_grade = st.text_input("학년 입력", value=res.get("student_grade", ""))
            
        report_month = st.text_input("시험 일자 (년/월/일)", value=res.get("report_month", ""))
        score = st.text_input("종합 점수 (원본 고정)", value=str(res.get("score", "0")), disabled=True)
        
        st.markdown("#### 📊 난이도별 정답률 수정 검토 (오차 발생 시 여기서 직접 수정하세요)")
        diff_obj = res.get("difficulty", {"최상": "0", "상": "0", "중": "0", "중하": "0", "하": "0"})
        
        d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns(5)
        with d_col1:
            d_ha = st.text_input("하 (%)", value=str(diff_obj.get("하", "0")))
        with d_col2:
            d_mid_ha = st.text_input("중하 (%)", value=str(diff_obj.get("중하", "0")))
        with d_col3:
            d_mid = st.text_input("중 (%)", value=str(diff_obj.get("중", "0")))
        with d_col4:
            d_sang = st.text_input("상 (%)", value=str(diff_obj.get("상", "0")))
        with d_col5:
            d_choi = st.text_input("최상 (%)", value=str(diff_obj.get("최상", "0")))
            
        res["difficulty"] = {
            "하": d_ha, "중하": d_mid_ha, "중": d_mid, "상": d_sang, "최상": d_choi
        }
        
        teacher_comment = st.text_area("🦅 코넬 분석 Comment (상담 방향에 맞게 편집 가능)", value=res.get("teacher_comment", ""), height=150)
        
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
            st.info("💡 위 미리보기를 검토하신 후 다운로드하여 바로 인쇄(A4 세로)하시면 됩니다.")
        except Exception as pdf_err:
            st.error(f"PDF 렌더링 중 디자인 에러 발생: {pdf_err}")
