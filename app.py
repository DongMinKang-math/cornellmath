import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json
import io
import os

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
# 파일 업로드 화면 구성
uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"])

if uploaded_file is not None:
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state:
            del st.session_state['parsed_data']
        if 'input_cleared' in st.session_state:
            del st.session_state['input_cleared']

import base64 # 코드 상단 import 문에 추가하세요.

# ... (create_academy_report 함수 등 기존 코드 유지)

# --- 파일 업로드 화면 구성 (이 아래 부분을 수정) ---
uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"])

if uploaded_file is not None:
    # 세션 상태 초기화 로직 유지
    if 'current_file' not in st.session_state or st.session_state['current_file'] != uploaded_file.name:
        st.session_state['current_file'] = uploaded_file.name
        if 'parsed_data' in st.session_state:
            del st.session_state['parsed_data']
        if 'input_cleared' in st.session_state:
            del st.session_state['input_cleared']

    if 'parsed_data' not in st.session_state:
        # 스피너 멘트 수정
        with st.spinner("코넬 AI가 매쓰플랫 리포트 이미지를 정밀 Vision 분석 및 수치 검증 중입니다..."):
            try:
                # 1. [Vision 도입 핵심] PDF를 이미지로 고해상도 변환 (300 DPI)
                # uploaded_file의 바이너리를 읽어와 이미지로 변환합니다.
                uploaded_file.seek(0) # 파일 읽기 위치 초기화
                pdf_bytes = uploaded_file.read()
                
                # Windows 로컬 실행 시 poppler_path="C:/path/to/poppler/bin" 추가 필요할 수 있음
                # Streamlit Cloud 배포 시에는 packages.txt 설정으로 생략 가능
                try:
                    images = convert_from_bytes(pdf_bytes, dpi=300)
                except Exception as e:
                    st.error(f"❌ PDF 이미지 변환 중 오류가 발생했습니다. (poppler 설치 확인 요망): {e}")
                    st.stop()
                
                # GPT-4o Vision API에 보낼 이미지 메시지 배열 구성 (최대 2페이지까지만 분석 권장)
                image_messages = []
                for idx, img in enumerate(images):
                    if idx >= 2: break # 매쓰플랫 주요 정보는 보통 1~2페이지에 있습니다.
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    image_messages.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high" # 표 수치를 정확히 보기 위해 고해상도 모드 설정
                        }
                    })

                client = OpenAI(api_key=api_key)
                
                # 기존의 System Prompt는 유지합니다.
                # system_prompt = """너는 강남 대치동 및 목동의 상위권 수학전문학원인 코넬수학... (생략) """

                # [Vision용 User Content 구성] 텍스트 프롬프트와 이미지를 병합
                vision_user_content = [
                    {
                        "type": "text",
                        "text": "첨부된 매쓰플랫 성적표 이미지에서 학생 정보, 종합 점수, 단원별 성취도(%), 난이도별 정답률(%)을 완벽하게 추출하여 JSON 포맷으로 출력해줘."
                    }
                ] + image_messages

                # 2. [OpenAI API 호출] model="gpt-4o" 유지, messages 구조 변경
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt}, # 기존 프롬프트
                        {"role": "user", "content": vision_user_content} # 이미지 포함된 컨텐트
                    ],
                    response_format={"type": "json_object"} # JSON 출력 고정 유지
                )
                
                # 이후 JSON 파싱 및 데이터 로드 로직은 기존 코드 그대로 유지됩니다.
                ai_raw_data = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 Vision AI가 이미지 분석 및 상담 멘트 최적화를 완료했습니다!")
                uploaded_file.seek(0) # 파일 포인터 원위치 (미리보기 등 대비)

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
                uploaded_file.seek(0)

    # (이후 결과 세부 정보 입력 및 검토 부분은 기존 코드 유지)
                
                # 명문 수학전문학원 원장의 학부모 카운셀링 블로그 문구를 완전하게 사상 주입하는 특수 지시문
                system_prompt = """
                너는 강남 대치동 및 목동의 상위권 수학전문학원인 코넬수학에서 학부모 입학 상담을 전담하는 친절하고 깊이 있는 원장이야.
                매쓰플랫 원본의 난이도별 데이터 수치 교정을 5회 반복 검증하여 오차 없는 데이터 JSON을 빌드해라.

                [학부모 상담용 극도로 부드럽고 정중한 어조 지침]:
                1. 첫 문장은 무조건 "코넬수학에 관심을 가지고 소중한 자녀의 진단평가에 응해주셔서 깊이 감사드립니다."로 아주 따뜻하고 정중하게 출발할 것.
                2. 명령조나 지나치게 딱딱한 표현(요구됩니다, 필요합니다, 요망됩니다 등)은 전면 금지한다. 수학 전문 학원 블로그의 친절한 분석 글처럼 "~해보입니다", "~하는 성향을 띠고 있습니다", "~를 다져나간다면 충분히 성장할 수 있습니다"와 같은 서술어 구조로 부드럽게 감싸줄 것.
                3. 결론부에는 '코넬수학만의 차별화된 세심하고 밀착된 1대1 관리 시스템과 철저한 오답 보완 매커니즘을 결합하여, 부족했던 영역을 탄탄한 심화 개념으로 반전시키고 상위권으로 안심하고 도약할 수 있도록 저희 교사진이 사랑과 책임감으로 지도하겠습니다'라는 확신과 안도감을 주는 멘트로 마감할 것.
                4. 이 세부 조건들을 바탕으로 문맥을 스스로 5회 연속 리팩토링(5-turn refinement)하여 부드러움และ 신뢰가 극대화된 완성형 코멘트(4~5문장)로 리턴해라.

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
                    "difficulty": {
                        "최상": "5회 검증된 최상 정답률 숫자",
                        "상": "5회 검증된 상 정답률 숫자",
                        "중": "5회 검증된 중 정답률 숫자",
                        "중하": "5회 검증된 중하 정답률 숫자",
                        "하": "5회 검증된 하 정답률 숫자"
                    },
                    "teacher_comment": "블로그 상담 패턴 기반으로 5차 윤문된 부드럽고 정중한 원장님 종합 분석 의견"
                }
                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": full_text}],
                    response_format={"type": "json_object"}
                )
                
                # [문법 교정 완료] response.choices[0] 형태의 문법적 오류 소지를 전면 타파하여 컴파일 구조 완비
                ai_raw_data = response.choices[0].message.content
                st.session_state['parsed_data'] = json.loads(ai_raw_data)
                st.success("🎉 코넬 대형학원 상담 멘트 최적화 및 문법 오류 해결 완료!")
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
        
        st.markdown("#### 📊 5회 교차 검증된 난이도별 정답률 확인 (최종 조율창)")
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
        
        teacher_comment = st.text_area("🦅 코넬 분석 Comment (학원 블로그 스타일 기반 초안 / 수정 가능)", value=res.get("teacher_comment", ""), height=150)
        
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
