import streamlit as st
from pypdf import PdfReader
from openai import OpenAI
import json

st.set_page_config(page_title="학원 성적표 변환 툴", layout="centered")

st.title("📊 매쓰플랫 보고서 ➡️ 학원 성적표 변환기")
st.caption("AI를 활용해 PDF 데이터를 학원 성적표 포맷으로 가공합니다.")
st.markdown("---")

# [중요] 사용자가 웹 화면에서 직접 API Key를 입력할 수 있도록 안전하게 처리
api_key = st.sidebar.text_input("OpenAI API Key를 입력하세요", type="password")

uploaded_file = st.file_uploader("매쓰플랫 보고서 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("👈 왼쪽 사이드바에 OpenAI API Key를 먼저 입력해 주세요.")
    else:
        st.success("파일 업로드 완료! 분석을 시작합니다.")
        
        # 1단계: PDF 텍스트 추출
        with st.spinner("PDF에서 텍스트 데이터를 추출하는 중..."):
            reader = PdfReader(uploaded_file)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        # 2단계: GPT-4o를 이용한 데이터 가공
        with st.spinner("AI가 성적표 데이터를 분석하고 가공하는 중..."):
            try:
                # OpenAI 클라이언트 초기화
                client = OpenAI(api_key=api_key)
                
                # AI에게 줄 명확한 지침(프롬프트) 설정
                system_prompt = """
                너는 수학학원의 데이터 분석 전문가이자 베테랑 원장님이야.
                제공된 매쓰플랫 PDF 텍스트에서 학부모용 성적표에 들어갈 핵심 정보만 추출해서 반드시 아래의 'JSON 형식'으로만 응답해줘. 
                텍스트에 없는 정보라면 무리해서 지어내지 말고 빈칸이나 통계적 유추를 해줘.
                종합 코멘트는 학부모님이 읽었을 때 신뢰감이 가도록 정중하고 전문적인 학원 원장님의 어조로 작성해줘.

                [반드시 지켜야 할 응답 JSON 형식]:
                {
                    "student_name": "학생 이름",
                    "report_month": "해당 월 또는 회차 (예: 2026년 6월호)",
                    "score": "원점수 또는 종합 성취도 점수 (숫자만 또는 %)",
                    "average_score": "학원 또는 반 평균 점수",
                    "chapters": [
                        {"name": "단원명1", "achievement": "성취도 점수 또는 백분율"},
                        {"name": "단원명2", "achievement": "성취도 점수 또는 백분율"}
                    ],
                    "weak_types": ["가장 오답률이 높은 취약 유형 1", "취약 유형 2", "취약 유형 3"],
                    "teacher_comment": "이번 달 학생의 학습 태도, 성취도 분석, 그리고 향후 학원에서의 보완 및 지도 계획을 포함한 종합 코멘트 (3~4문장)"
                }
                """

                # API 호출 (GPT-4o 활용)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"여기 매쓰플랫 텍스트 데이터가 있어:\n\n{full_text}"}
                    ],
                    response_format={"type": "json_object"} # JSON 형태로만 답변하도록 강제
                )
                
                # 결과물 가공 및 로드
                result_json = json.loads(response.choices[0].message.content)
                
                # 3단계: 가공된 데이터를 화면에 깔끔하게 보여주기
                st.markdown("---")
                st.subheader("🎯 AI 데이터 가공 결과")
                
                # 보기 좋은 카드로 정보 배치
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("학생 이름", result_json.get("student_name"))
                with col2:
                    st.metric("종합 점수", f"{result_json.get('score')}점")
                with col3:
                    st.metric("반 평균", f"{result_json.get('average_score')}점")
                
                st.write("**📊 단원별 성취도**")
                for ch in result_json.get("chapters", []):
                    st.write(f"- {ch['name']}: {ch['achievement']}")
                
                st.write("**🚨 집중 보완이 필요한 취약 유형**")
                for i, weak in enumerate(result_json.get("weak_types", []), 1):
                    st.write(f"{i}. {weak}")
                
                st.write("**📝 학원 종합 의견 (수정 가능)**")
                # 원장님이 AI가 쓴 글을 마음에 들게 수정할 수 있도록 텍스트 입력창으로 배치
                final_comment = st.text_area("학부모 전송용 코멘트", value=result_json.get("teacher_comment"), height=150)
                
                # 추후 3단계에서 사용할 데이터를 세션에 저장
                st.session_state['parsed_data'] = result_json
                st.session_state['parsed_data']['teacher_comment'] = final_comment
                
                st.success("데이터 가공이 완료되었습니다! 3단계 성적표 인쇄 출력이 가능합니다.")

            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다. API 키나 크레딧을 확인해 주세요. 오류 내용: {e}")
