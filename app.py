import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. API 키 설정
genai.configure(api_key="여기에_발급받은_API_KEY를_입력하세요")

# 2. 팀앤디 오토센터 전용 1~12번 가이드라인 세팅
system_instruction = """
[이곳에 앞서 완성한 1번~11번 작성 규칙과 12번 제품 사전 전체를 복사해서 넣습니다.]
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro", 
    system_instruction=system_instruction
)

# 3. 팀앤디 직원 전용 UI 구성
st.set_page_config(page_title="팀앤디 오토센터 블로그 매니저", page_icon="🚗", layout="centered")

st.title("🚗 팀앤디 오토센터 블로그 매니저")
st.markdown("#### 고객관리명단(2026)의 내용을 그대로 복사해서 붙여넣어 주세요.")

st.divider()

# 레이아웃 나누기 (차종과 작업내역을 나란히 배치)
col1, col2 = st.columns([1, 2])

with col1:
    car_model = st.text_input("🚙 차종", placeholder="예: GV70")

with col2:
    work_details = st.text_area("🛠️ 작업 내역 (복사/붙여넣기)", placeholder="예: 브이쿨 VK/K 전면 30% 측후면 14% + PPF(4종) + 유리막코팅...")

st.divider()

# 사진 업로드 영역
st.markdown("#### 📸 작업 사진 업로드")
uploaded_files = st.file_uploader("스마트폰 앨범 또는 PC에서 사진을 여러 장 선택하세요 (jpg, png)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

st.divider()

# 4. 블로그 원고 생성 실행
if st.button("✨ 블로그 원고 자동 생성기 실행 ✨", use_container_width=True):
    if car_model and work_details and uploaded_files:
        with st.spinner("전문가 톤앤매너로 원고를 작성 중입니다... (약 10~15초 소요)"):
            try:
                # 업로드된 이미지 처리
                images = [Image.open(file) for file in uploaded_files]
                
                # AI에게 전달할 프롬프트 조합
                user_prompt = f"[키워드/시공 내역]\n차종: {car_model}\n작업내역: {work_details}\n\n위 시공 내역과 첨부된 사진들을 바탕으로 블로그 원고를 작성해 주세요."
                
                # API 호출 및 결과 출력
                response = model.generate_content(images + [user_prompt])
                
                st.success("✅ 원고 생성이 완료되었습니다! 내용을 복사하여 블로그에 등록해 주세요.")
                st.text_area("📋 완성된 블로그 본문 (복사해서 사용하세요)", value=response.text, height=500)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
    else:
        st.warning("⚠️ 차종, 작업 내역, 그리고 사진을 모두 입력해 주세요.")
