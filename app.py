import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="매쓰플랫 데이터 텍스트 검증기", page_icon="📊", layout="centered")

st.title("📊 매쓰플랫 PDF 텍스트 추출 검증기")
st.caption("AI 연동 전, PDF 내부 글자가 정상적으로 추출되는지 확인하는 단계입니다.")
st.markdown("---")

uploaded_file = st.file_uploader("매쓰플랫 레벨테스트 결과 PDF 파일을 선택하세요", type=["pdf"])

if uploaded_file is not None:
    st.success("파일 업로드 성공! 텍스트를 추출합니다.")
    
    try:
        reader = PdfReader(uploaded_file)
        full_text = ""
        
        # 각 페이지별로 글자를 긁어모아 화면에 구분해서 보여줍니다.
        for idx, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text:
                full_text += f"\n\n================ [PAGE {idx}] ================\n" + text
            else:
                full_text += f"\n\n================ [PAGE {idx}] ================\n[글자를 읽을 수 없는 페이지(이미지 형태)]\n"
        
        st.markdown("### 📝 추출된 원본 텍스트 데이터")
        st.info("아래 상자 안에서 'Ctrl + F'를 눌러 '대표 취약 유형' 단어가 실제로 존재하는지 검색해 보세요.")
        
        # 큰 스크롤 박스로 추출된 텍스트 전체 노출
        st.text_area(label="PDF 원문 내용", value=full_text, height=500)
        
    except Exception as e:
        st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
