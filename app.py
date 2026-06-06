import streamlit as st
from pypdf import PdfReader

# 1. 웹 페이지 기본 설정 (A4 레이아웃을 고려한 넓이 설정)
st.set_page_config(page_title="학원 성적표 변환 툴", layout="centered")

st.title("📊 매쓰플랫 보고서 ➡️ 학원 성적표 변환기")
st.caption("프로그램 설치 없이 PDF를 학원 양식 성적표로 변환합니다.")
st.markdown("---")

# 2. 파일 업로드 컴포넌트 (웹 브라우저에서 파일 선택)
uploaded_file = st.file_uploader("매쓰플랫 보고서 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    st.success("파일이 성공적으로 업로드되었습니다! 분석을 시작합니다.")
    
    # 로딩 애니메이션
    with st.spinner("PDF에서 텍스트 데이터를 추출하는 중..."):
        try:
            # 3. PDF 읽기 및 텍스트 추출 프로세스
            reader = PdfReader(uploaded_file)
            full_text = ""
            
            # 모든 페이지의 텍스트를 하나로 합침
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    full_text += f"\n--- [Page {page_num + 1}] ---\n" + text
            
            # 4. 추출된 결과 화면에 출력 (텍스트 데이터 확인용)
            st.subheader("📝 추출된 원본 데이터 데이터 (AI 입력용)")
            st.info("이 데이터가 다음 단계에서 AI(GPT/Claude)에게 전달되어 성적표 항목으로 가공됩니다.")
            
            # 스크롤 가능한 텍스트 박스로 출력하여 가독성 확보
            st.text_area(
                label="추출 완료된 텍스트 내용",
                value=full_text,
                height=400
            )
            
        except Exception as e:
            st.error(
                f"PDF를 읽는 중 오류가 발생했습니다. 파일이 손상되었거나 보안이 걸려있는지 확인해 주세요. 오차 내용: {e}"
            )
else:
    st.info("왼쪽 버튼이나 드래그 앤 드롭으로 매쓰플랫 PDF 파일을 올려주세요.")
