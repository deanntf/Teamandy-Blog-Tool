import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont

import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

# [★기존] 엑셀 자동 저장
def save_to_gsheet(management_num, car_model, work_details):
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(
            creds_json, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        
        sheet_url = "https://docs.google.com/spreadsheets/d/1JavBx0STp73mlTg8qNjeJ2lDHwwwwxCZvKAZAwANxd8/edit?gid=1200727784#gid=1200727784"
        doc = gc.open_by_url(sheet_url)
        worksheet = doc.sheet1
        
        KST = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        
        worksheet.append_row([now, management_num, car_model, work_details])
    except Exception as e:
        st.warning(f"⚠️ 엑셀 저장에 실패했습니다. (오류: {e})")

# [★기존] 최근 이력 불러오기
def get_recent_history():
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(
            creds_json, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        
        sheet_url = "https://docs.google.com/spreadsheets/d/1JavBx0STp73mlTg8qNjeJ2lDHwwwwxCZvKAZAwANxd8/edit?gid=1200727784#gid=1200727784"
        doc = gc.open_by_url(sheet_url)
        worksheet = doc.sheet1 
        
        records = worksheet.get_all_values()
        valid_records = [row for row in records if len(row) >= 4 and str(row[0]).strip() != ""]
        
        recent_records = valid_records[-5:]
        recent_records.reverse()
        return recent_records
    except Exception:
        return []

# [★기존] 색감 자동 보정
def enhance_image_for_blog(img):
    enhancer_bright = ImageEnhance.Brightness(img)
    img = enhancer_bright.enhance(1.1)
    enhancer_sharp = ImageEnhance.Sharpness(img)
    img = enhancer_sharp.enhance(1.2)
    enhancer_color = ImageEnhance.Color(img)
    img = enhancer_color.enhance(1.1)
    return img

# [★수정됨] 상단 워터마크 자동 삽입 (전화번호 제거 및 박스 크기 조절)
def add_watermark(img, font_path="font.ttf"):
    # 사진 크기를 가로 1000px로 통일하여 글씨 크기 편차 방지
    w, h = img.size
    new_w = 1000
    new_h = int((new_w / w) * h)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype(font_path, 28)
    except IOError:
        font_title = ImageFont.load_default()
        st.warning("⚠️ 폰트 파일(font.ttf)이 없어 기본 글꼴로 표시됩니다.")
        
    # 검은색 반투명 배경 박스 그리기 (전화번호가 빠졌으므로 세로 높이 축소)
    draw.rectangle([(20, 20), (195, 65)], fill=(0, 0, 0, 220))
    
    # 텍스트 삽입 (TEAMANDY만 남김)
    draw.text((30, 25), "TEAMANDY", font=font_title, fill="white")
    
    return img

# [★신규] 대표 사진(썸네일) 하단 디자인 자동 삽입
def make_thumbnail(img, car_model, main_film, work_details, font_path="font.ttf"):
    w, h = img.size
    
    # 하단 텍스트가 들어갈 블러(흐림) 영역 지정 (세로 기준 55% ~ 85% 지점)
    box_top = int(h * 0.55)
    box_bottom = int(h * 0.85)
    
    # 해당 영역만 잘라내서 블러 처리 및 어둡게 만들기
    region = img.crop((0, box_top, w, box_bottom))
    region = region.filter(ImageFilter.GaussianBlur(radius=8))
    
    overlay = Image.new('RGBA', region.size, (0, 0, 0, 140)) # 반투명 검은색 덮기
    region = Image.alpha_composite(region, overlay)
    
    # 원본 이미지에 다시 붙여넣기
    img.paste(region, (0, box_top), region)
    
    # 위아래 하얀색 얇은 테두리 선 그리기
    draw = ImageDraw.Draw(img)
    draw.line([(0, box_top), (w, box_top)], fill=(255, 255, 255, 200), width=2)
    draw.line([(0, box_bottom), (w, box_bottom)], fill=(255, 255, 255, 200), width=2)
    
    try:
        font_car = ImageFont.truetype(font_path, 35)
        font_film = ImageFont.truetype(font_path, 70) # 메인 필름명은 아주 크게
        font_detail = ImageFont.truetype(font_path, 22)
    except IOError:
        font_car = ImageFont.load_default()
        font_film = ImageFont.load_default()
        font_detail = ImageFont.load_default()
        
    # 가운데 정렬하여 텍스트 넣는 헬퍼 함수
    def draw_centered_text(draw_obj, text, font, y_pos):
        bbox = draw_obj.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x_pos = (w - text_w) / 2
        draw_obj.text((x_pos, y_pos), text, font=font, fill="white")
        
    # 텍스트 삽입
    draw_centered_text(draw, f"'{car_model}'", font_car, box_top + 25)
    draw_centered_text(draw, main_film, font_film, box_top + 70)
    
    # 상세 내역이 너무 길면 잘리므로 줄임말 처리
    display_detail = f"[ {work_details[:40]}... ]" if len(work_details) > 40 else f"[ {work_details} ]"
    draw_centered_text(draw, display_detail, font_detail, box_top + 160)
    
    return img

# 1. API 키 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 2. 가이드라인 세팅
system_instruction = """
[Role & Identity]
당신은 10년 이상의 현장 경험을 보유한 '팀앤디 오토센터'의 수석 엔지니어이자, 네이버 블로그 'teamandy19'의 메인 에디터입니다. 신차 패키지 및 차량 디테일링에 대한 완벽한 기술적 이해도를 바탕으로, 고객에게 무한한 신뢰감을 주는 최고 전문가의 화법을 구사합니다.

[Core Objective]
사용자가 제공하는 [시공 차종/키워드]와 [작업 사진]을 정밀하게 분석하여, 실제 시공자가 현장에서 땀 흘려 작업하며 직접 작성한 듯한 생생하고 전문적인 네이버 블로그 포스팅 초안을 완성하십시오. 제공된 우수 포스팅 레퍼런스의 문체와 단락 구조를 완벽하게 모방해야 합니다.

[Strict Writing Guidelines]
1. AI 패턴 절대 금지: "결론적으로", "요약하자면", "오늘은 ~에 대해 알아보겠습니다", "이처럼" 등 기계적이고 전형적인 서론 및 결론 멘트는 절대 사용하지 마십시오.
2. 시각적 데이터의 텍스트화: 첨부된 [작업 사진] 속 차량의 색상, 차종의 특징, 시공 중인 특정 부위를 정확히 인식하고 본문에 구체적으로 묘사하십시오.
3. 현장감 및 고객 중심 서술: 작업 과정의 고충이나 디테일을 살려 진정성을 부여하십시오. 
4. Tone & Manner: 구어체와 문어체를 자연스럽게 혼용하십시오. ('~했습니다', '~하죠', '~입니다', '~거든요'). 문단당 적절한 이모지 배치.
5. 유연한 시공 항목 조합 (모듈형 작성): 의뢰받지 않은 시공 내용은 절대 지어내지 마십시오.
6. 출력 포맷 및 해시태그: 가장 윗줄에 [블로그 제목 추천] 3가지 제시, 그 아래 [블로그 본문] 작성. 본문 끝에는 [추천 해시태그] 5개를 '#태그1 #태그2' 형태로 제시하십시오.
7. 사진 배치 가이드: [📸 사진 삽입: 전면 틴팅 완료 모습]과 같이 명확한 사진 배치 마커를 삽입하십시오.
8. 모바일 최적화 호흡: 한 문단은 최대 2~3문장을 넘지 않도록 잦은 줄바꿈 사용.
9. 마크다운 기호(`**`) 사용 절대 금지.
10. 전문 용어 분리 (인스톨 절대 금지): 틴팅/PPF는 '시공하다' 사용. 코팅은 '경화 시간' 사용. 실시간 중계 표현 금지.
11. 사내 장비 어필: '썬프로(Sunpro)' 정밀 재단기 사용 명시. 연무기 가동 언급 금지.
12. 제품 스펙 창작 금지: 팀앤디 오토센터 제품 사전 기반으로 작성.
13. 과장된 표현 금지.
14. 담백한 서술어 사용: "~을 도왔습니다" 대신 "시공을 완료했습니다" 사용.
15. 억지 기술 연결 금지.
16. 지역 검색(로컬 SEO) 최적화: [타겟 지역] 키워드를 자연스럽게 녹여내십시오.

[네이버 검색 품질 가이드라인 (어뷰징 엄격 금지)]
1. 키워드 남용 및 반복 금지
2. 기계적인 템플릿 탈피 (저품질 대량 생산 방지)
3. 낚시성 제목 및 과장 금지
4. '생생한 1인칭 경험' 중심 서술 (E-E-A-T 충족)

[팀앤디 오토센터 제품 사전]
* 브이쿨 QB: 프리미엄 비반사 필름. 열반사/반사 단어 사용 금지. TSER 최대 63%.
* 브이쿨 VK: 최상위 프리미엄 라인업. TSER 최고 74%.
* 브이쿨 K: 베스트셀링 메탈 반사 필름. TSER 최고 70%.
"""

model = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    system_instruction=system_instruction
)

# 3. 팀앤디 직원 전용 UI 구성
st.set_page_config(page_title="팀앤디 오토센터 블로그 매니저", page_icon="🚗", layout="wide")

left_col, right_col = st.columns([7, 3], gap="large")

with left_col:
    st.markdown("<h1 style='text-align: center;'>🚗 팀앤디 오토센터 블로그 매니저</h1>", unsafe_allow_html=True)
    st.info("💡 썸네일 자동 생성 기능 탑재! 폰트 파일(font.ttf)이 꼭 필요합니다.")
    
    st.divider()

    with st.form("my_form"):
        # UI 레이아웃 조정
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            management_num = st.text_input("🔢 번호", placeholder="예: 229")
        with col2:
            target_location = st.text_input("📍 타겟 지역", placeholder="예: 구리, 다산")
        with col3:
            car_model = st.text_input("🚙 차종", placeholder="예: GV70")
            
        # 썸네일용 아주 큰 글씨 필름명 입력칸 추가
        main_film = st.text_input("👑 메인 시공명 (썸네일 대표 글씨)", placeholder="예: 루마 버텍스 900")
        work_details = st.text_area("🛠️ 상세 작업 내역", placeholder="예: 전면 30%, 측후면 15% + PPF(4종)...")

        st.subheader("📸 작업 사진 업로드")
        st.caption("첫 번째로 올린 사진이 '썸네일(대표 사진)'이 되어 글씨가 합성됩니다. 나머지 사진은 워터마크만 찍힙니다.")
        uploaded_files = st.file_uploader("", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

        st.divider()
        submitted = st.form_submit_button("✨ 블로그 원고 & 썸네일 자동 생성기 실행 ✨", type="primary", use_container_width=True)

    # 4. 블로그 원고 생성 실행
    if submitted:
        if management_num and target_location and car_model and main_film and work_details and uploaded_files:
            with st.spinner("전문가 톤앤매너 원고 작성 및 사진을 합성 중입니다... (약 20초 소요)"):
                try:
                    save_to_gsheet(management_num, car_model, work_details)

                    images_for_ai = []
                    
                    st.markdown("### 📸 썸네일 및 보정 완료된 사진")
                    st.caption("우클릭하여 '이미지를 다른 이름으로 저장' 하신 후 블로그에 바로 사용하세요!")
                    
                    img_cols = st.columns(len(uploaded_files))
                    
                    for idx, file in enumerate(uploaded_files):
                        img = Image.open(file).convert("RGBA")
                        
                        # 1단계: 색감 보정
                        img = enhance_image_for_blog(img)
                        
                        # 2단계: 워터마크 합성 (모든 사진 적용)
                        img = add_watermark(img, "font.ttf")
                        
                        # 3단계: 썸네일 합성 (첫 번째 사진만 적용)
                        if idx == 0:
                            img = make_thumbnail(img, car_model, main_film, work_details, "font.ttf")
                        
                        # 화면 출력을 위해 다시 RGB 변환 (투명도 제거)
                        final_img = img.convert("RGB")
                        
                        with img_cols[idx]:
                            if idx == 0:
                                st.markdown("**[대표 사진]**")
                            st.image(final_img, use_column_width=True)
                        
                        # AI 전달용 축소 이미지
                        final_img.thumbnail((800, 800))  
                        images_for_ai.append(final_img)
                    
                    st.divider()
                    
                    user_prompt = f"[키워드/시공 내역]\n타겟 지역: {target_location}\n차종: {car_model}\n메인시공: {main_film}\n상세내역: {work_details}\n\n위 시공 내역과 사진들을 바탕으로 블로그 원고를 작성해 주세요."
                    response = model.generate_content(images_for_ai + [user_prompt])
                    
                    st.success("✅ 완벽한 세팅이 완료되었습니다! (엑셀 자동 저장 완료)")
                    st.text_area("📋 완성된 블로그 본문 (복사해서 사용하세요)", value=response.text, height=500)
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
        else:
            st.warning("⚠️ 모든 빈칸을 채우고 사진을 업로드해 주세요.")

with right_col:
    recent_data = get_recent_history()
    
    history_html = """<h3 style="margin-top: 0; margin-bottom: 8px;">🕒 최근 생성 이력</h3>
<div style="font-size: 14px; color: #888888; margin-bottom: 12px;">가장 최근에 작업이 완료된 5개의 목록입니다.</div>
<hr style="margin: 0; border: none; border-top: 1px solid rgba(0,0,0,0.1);" />"""
    
    if recent_data:
        for row in recent_data:
            work_summary = row[3]
            history_html += f"""
<div style="padding: 12px 0px; border-bottom: 1px solid rgba(0,0,0,0.1);">
<div style="font-size: 16px; font-weight: bold; margin-bottom: 4px;">[{row[1]}] {row[2]}</div>
<div style="font-size: 13px; color: #888888; margin-bottom: 8px;">🗓️ {row[0]}</div>
<div style="font-size: 14px; color: #555555; white-space: pre-wrap;">🛠️ {work_summary}</div>
</div>"""
        
        st.markdown(history_html, unsafe_allow_html=True)
    else:
        st.markdown(history_html, unsafe_allow_html=True)
        st.info("아직 생성된 이력이 없습니다.")
