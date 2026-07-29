import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import re 
import io       
import zipfile  

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

# [★기존] 최신 AI 비전 인식 기반 번호판 자동 모자이크 (Gemini 3.6 Flash)
def auto_blur_license_plate(img):
    try:
        vision_model = genai.GenerativeModel("gemini-3.6-flash")
        prompt = """Look at this image. Find the vehicle license plate (including temporary wooden/paper plates with Korean text and numbers).
        Return ONLY a JSON array with the bounding box coordinates normalized to 1000: [ymin, xmin, ymax, xmax].
        If no plate is visible, return an empty array: []. Do not output any other text."""
        
        temp_img = img.copy()
        temp_img.thumbnail((800, 800))
        
        response = vision_model.generate_content([temp_img, prompt])
        text = response.text.strip()
        
        numbers = re.findall(r'\d+', text)
        
        if len(numbers) >= 4:
            ymin, xmin, ymax, xmax = map(int, numbers[:4])
            if xmin < xmax and ymin < ymax:
                w, h = img.size
                top = int((ymin / 1000) * h)
                left = int((xmin / 1000) * w)
                bottom = int((ymax / 1000) * h)
                right = int((xmax / 1000) * w)
                
                pad_w = int((right - left) * 0.05)
                pad_h = int((bottom - top) * 0.05)
                
                left = max(0, left - pad_w)
                right = min(w, right + pad_w)
                top = max(0, top - pad_h)
                bottom = min(h, bottom + pad_h)
                
                plate_region = img.crop((left, top, right, bottom))
                blurred_region = plate_region.filter(ImageFilter.GaussianBlur(radius=25))
                img.paste(blurred_region, (left, top))
    except Exception:
        pass
    return img

# [★기존] 상단 워터마크 (썸네일 외의 사진에만 적용)
def add_watermark(img, font_path="font.ttf"):
    w, h = img.size
    new_w = 1000
    new_h = int((new_w / w) * h)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype(font_path, 28)
    except IOError:
        font_title = ImageFont.load_default()
        
    draw.rectangle([(20, 20), (195, 65)], fill=(0, 0, 0, 220))
    draw.text((30, 25), "TEAMANDY", font=font_title, fill="white")
    return img

# [★기존] 매거진 표지 스타일 썸네일 
def make_thumbnail(img, top_yellow, top_white, car_model, main_film, font_path="font.ttf"):
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) / 2
    top = (h - min_dim) / 2
    right = (w + min_dim) / 2
    bottom = (h + min_dim) / 2
    img = img.crop((left, top, right, bottom))
    
    img = img.resize((1000, 1000), Image.Resampling.LANCZOS).convert("RGBA")
    w, h = 1000, 1000
    
    gradient = Image.new('RGBA', (w, h), (0,0,0,0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(h):
        if y < 350: 
            alpha = int(255 * (1 - y/350)) * 0.7 
            grad_draw.line([(0, y), (w, y)], fill=(0,0,0, int(alpha)))
        elif y > 650: 
            alpha = int(255 * ((y-650)/350)) * 0.8
            grad_draw.line([(0, y), (w, y)], fill=(0,0,0, int(alpha)))
    img = Image.alpha_composite(img, gradient)
    
    draw = ImageDraw.Draw(img)
    
    margin = 40
    draw.rectangle([(margin, margin), (w - margin, h - margin)], outline=(255, 255, 255, 180), width=2)
    
    try:
        font_top_y = ImageFont.truetype(font_path, 85)  
        font_top_w = ImageFont.truetype(font_path, 65)  
        font_bot_main = ImageFont.truetype(font_path, 95) 
        font_bot_sub = ImageFont.truetype(font_path, 45)  
    except IOError:
        font_top_y = ImageFont.load_default()
        font_top_w = ImageFont.load_default()
        font_bot_main = ImageFont.load_default()
        font_bot_sub = ImageFont.load_default()
        
    text_x = margin + 35
    
    top_y_pos = margin + 35
    draw.text((text_x, top_y_pos), top_yellow, font=font_top_y, fill="#FFE600") 
    
    bbox_y = draw.textbbox((text_x, top_y_pos), top_yellow, font=font_top_y)
    top_w_pos = bbox_y[3] + 10
    draw.text((text_x, top_w_pos), top_white, font=font_top_w, fill="white")
    
    bbox_w = draw.textbbox((text_x, top_w_pos), top_white, font=font_top_w)
    underline_y = bbox_w[3] + 25
    draw.line([(text_x, underline_y), (bbox_w[2], underline_y)], fill="white", width=6) 
    
    bar_width = 12
    bar_height = 135
    bar_x = text_x
    bar_y = h - margin - 45 - bar_height
    
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], fill="white")
    
    text_start_x = bar_x + bar_width + 25
    bot_main_y = bar_y - 15
    draw.text((text_start_x, bot_main_y), car_model, font=font_bot_main, fill="white")
    
    bbox_main = draw.textbbox((text_start_x, bot_main_y), car_model, font=font_bot_main)
    bot_sub_y = bbox_main[3] + 15
    draw.text((text_start_x, bot_sub_y), main_film, font=font_bot_sub, fill="white")
    
    return img

# 1. API 키 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 2. 가이드라인 세팅 (학습된 필름 데이터 총집합 및 카스페이스 벤치마킹 구조)
system_instruction = """
[Role & Identity]
당신은 10년 이상의 현장 경험을 보유한 '팀앤디 오토센터'의 수석 엔지니어이자, 네이버 블로그 'teamandy19'의 메인 에디터입니다. 신차 패키지 및 차량 디테일링에 대한 완벽한 기술적 이해도를 바탕으로, 고객에게 무한한 신뢰감을 주는 최고 전문가의 화법을 구사합니다.

[Core Objective]
사용자가 제공하는 [시공 차종/키워드]와 [작업 사진]을 정밀하게 분석하여, 최고 수준의 신차패키지 전문 블로그들이 사용하는 '5단계 정석 구조'를 완벽하게 적용한 네이버 블로그 포스팅 초안을 완성하십시오. 

[★ 신차패키지 포스팅 5단계 정석 구조 (반드시 준수)]
글을 작성할 때 반드시 아래의 흐름과 소제목(■ 기호 사용)을 따라 글을 전개하십시오.
1. 도입부 (차량 입고 및 환영): 타겟 지역명과 차종을 자연스럽게 언급하며, 고객이 팀앤디를 믿고 맡겨주신 것에 대한 감사 인사로 시작하십시오.
2. 준비 및 보양 작업 (신뢰감 형성): 썬팅 시공 전, 미세한 스크래치와 오염을 방지하기 위해 차량 내/외부에 철저한 '풀마스킹 및 커버링(보양)' 작업을 거친다는 점을 전문가의 시선으로 강력하게 어필하십시오.
3. 메인 썬팅 시공 (외부 프라이버시 & 내부 시인성): 시공된 필름의 브랜드와 농도를 설명하십시오. 외부에서는 프라이버시가 차단되는 세련된 외관을 묘사하고, 이와 대조적으로 내부 운전석에서는 밖이 얼마나 선명하게 잘 보이는지(시인성)를 교차로 강조하십시오.
4. 디테일링 (PPF 및 코팅): 생활 스크래치를 방지하는 PPF 시공(도어컵, 도어엣지, 주유구 등)의 정밀한 마감 퀄리티와, 차량 관리를 편하게 해주는 유리막/가죽 코팅 등의 디테일을 설명하십시오. (사용자가 입력한 내역에 있는 경우에만 작성)
5. 마무리 및 출고: 모든 시공이 완벽하게 끝났음을 알리고, 고객의 안전 운전을 기원하는 따뜻한 인사말로 마무리하십시오.

[Strict Writing Guidelines]
1. AI 패턴 절대 금지: "결론적으로", "요약하자면", "오늘은 ~에 대해 알아보겠습니다", "이처럼" 등 기계적이고 전형적인 서론/결론 멘트는 절대 사용하지 마십시오.
2. 시각적 데이터의 텍스트화: 첨부된 사진 속 차량의 색상과 시공 부위를 구체적으로 묘사하십시오.
3. Tone & Manner: 구어체와 문어체를 혼용('~했습니다', '~하죠', '~입니다'). 문단당 1~2개의 적절한 이모지(🚗, ✨, 🛠️, 💧 등)를 배치하십시오.
4. 모듈형 작성: 사용자가 제시한 [키워드/시공 내역]에 없는 작업은 절대 지어내지 마십시오.
5. 출력 포맷 및 해시태그: 가장 윗줄에 [블로그 제목 추천] 3가지 제시, 그 아래 [블로그 본문] 작성. 본문 끝에는 핵심 해시태그 5개를 '#태그1 #태그2' 형태로 제시하십시오.
6. 사진 배치 가이드: 텍스트만 길게 나열하지 말고, 글의 흐름(5단계 구조)에 맞춰 [📸 사진 삽입: 풀마스킹 준비 모습], [📸 사진 삽입: 내부 시인성 확인] 과 같이 명확한 사진 배치 마커를 삽입하십시오.
7. 모바일 최적화 및 단락 구성: 한 문단은 2~3개의 문장으로 짜임새 있게 구성하여 모바일 가독성을 높이십시오.
8. 시각적 소제목 및 강조: 마크다운(`**`, `*` 등)은 절대 금지합니다. 단락이 바뀔 때마다 ■ 기호를 활용한 [소제목]을 배치하고, 핵심 스펙이나 단어는 '작은따옴표'나 [대괄호]로 감싸 시각적으로 띄워주십시오.
9. 전문 용어 통일: 틴팅/PPF는 '인스톨' 대신 '시공하다' 사용. 코팅은 '큐어링' 대신 '경화 시간' 사용. "시공을 이어갔습니다" 등 실시간 중계 표현 금지.
10. 사내 장비 어필: '썬프로(Sunpro)' 정밀 재단기 사용 명시. 연무기 가동 언급 금지.
11. 지역 검색(로컬 SEO) 최적화: [타겟 지역] 키워드를 자연스럽게 제목 1회, 본문 1~2회 녹여내십시오. 

[팀앤디 오토센터 제품 사전]
* 루마 버텍스 1100: '새로운 썬팅의 완성, 새로운 프리미엄의 시작'을 알리는 루마 최상위 하이엔드 비반사 필름입니다. 최신 나노 기술과 RC 코팅 등 첨단 기술이 집약되어 있으며, CV & NV ASSIST 기술로 주야간 모두 왜곡 없이 맑고 선명한 최고 수준의 시야를 제공. 10년 보증.
* 루마 버텍스 900: '썬팅 기술의 결정체'라 불리는 첨단 신소재 나노융합 최고급 비반사 필름입니다. 금속 성분이 없어 전파 간섭이나 무아레 현상이 전혀 없으며, 10년 보증을 자랑합니다.
* 루마 버텍스 700: '컴포트 밸런스 케어 나노테크'가 적용된 최고급 비금속 필름입니다. 무아레 현상/전파 수신 간섭이 없으며 사파이어 블랙 색상입니다.
* 루마 버텍스 MK / MK2: 고도화된 'EVV 스퍼터드 테크놀로지'가 적용된 이볼브 스퍼터드 메탈(반사) 필름입니다. 미려한 반사광을 통해 완벽한 프라이버시 보호와 하차감을 완성합니다. 7년 보증.
* 브이쿨 VK: 브이쿨의 기술력이 집약된 최고급 스퍼터링 라인업입니다. 우주 항공 '선택적 태양광 투과 기술(XIR®)' 적용, 희귀 금속 10겹 다중 박막 구조 코팅. 적외선 최대 98.4%, TSER 최대 74%의 압도적 성능을 지닙니다.
* 브이쿨 K: 100% 금속 스퍼터링 기술이 적용된 베스트셀링 프리미엄 반사 필름입니다. 10겹의 멀티레이어 구조. 부담스럽지 않은 은은한 반사 광택을 통해 도시적인 세련미를 연출합니다.
* 브이쿨 QB: 'Advanced Glazing Coating' 기술의 가성비 프리미엄 비반사 필름입니다. 차분하고 고급스러운 블랙 색상. (※반사 단어 사용 금지)
* 레인보우 IRIS 190: 다이아몬드 블랙 색상의 비반사 필름. 압도적으로 낮은 헤이즈 수치(0.98 이하)로 2배 이상 넓고 쾌적한 맑은 시인성을 제공합니다. 10년 보증.
* 레인보우 IRIS V90: 하이퍼 골드 그린 색상의 프리미엄 반사(스퍼터) 필름. 태양 에너지를 초기부터 반사하며 주파수 간섭/무아레를 최소화. 10년 보증.
* 레이노 팬텀 F (Phantom F): 초미립자 나노 설계로 입자를 40% 미세화하여 선명한 시인성 제공. 99.9% 항균 기능 탑재로 쾌적한 실내 유지. 오닉스 블랙 색상, 10년 보증.
* 레이노 크로마 (CHROMA): 듀얼 컬러 컨트롤 기술을 적용해 내/외부 컬러를 다르게 표현하는 프리미엄 반사 필름입니다.
* 레이노 팬텀 S (Phantom S): 대중적인 나노 카본 세라믹 베스트셀링 필름.
* 틴트어카 포시즌 블랙: B2B로 사랑받는 베스트셀링 필름. 차콜 색상의 은은한 매력, 10년 보증.
* 틴트어카 비비드: 가성비 좋은 선명한 시인성의 필름, 5년 보증.
* 틴트어카 고스트: 차콜&실버 반사 필름, 무아레 최소화. 10년 보증.
* 틴트어카 볼레 프레스티지: 평생 보증(Lifetime Warranty)을 제공하는 독보적인 하이엔드 라인업.
"""

model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",
    system_instruction=system_instruction
)

# 3. 팀앤디 직원 전용 UI 구성
st.set_page_config(page_title="팀앤디 오토센터 블로그 매니저", page_icon="🚗", layout="wide")

left_col, right_col = st.columns([7, 3], gap="large")

with left_col:
    st.markdown("<h1 style='text-align: center;'>🚗 팀앤디 오토센터 블로그 매니저</h1>", unsafe_allow_html=True)
    st.info("💡 대표 사진 강조 레이아웃 및 바둑판 배열 업데이트 완료!")
    
    st.divider()

    with st.form("my_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            management_num = st.text_input("🔢 번호", placeholder="예: 229")
        with col2:
            target_location = st.text_input("📍 타겟 지역", placeholder="예: 구리, 다산")
        with col3:
            car_model = st.text_input("🚙 차종 (하단 큰글씨)", placeholder="예: 테슬라 모델3 하이랜드")
            
        st.markdown("##### 🖼️ 썸네일 전용 텍스트 설정")
        col4, col5 = st.columns([1, 1])
        with col4:
            thumb_keyword = st.text_input("💛 썸네일 상단 노란글씨", value="버텍스썬팅")
        with col5:
            thumb_brand = st.text_input("🤍 썸네일 상단 흰글씨", value="팀앤디오토센터")
            
        main_film = st.text_input("👑 메인 시공명 (하단 작은글씨)", placeholder="예: 버텍스 900 시공")
        work_details = st.text_area("🛠️ 상세 작업 내역", placeholder="예: 전면 30%, 측후면 15% + PPF(4종)...")

        st.subheader("📸 작업 사진 업로드")
        st.caption("첫 번째 사진은 '1:1 매거진 표지'가 됩니다. 업로드된 모든 사진의 번호판은 AI가 자동으로 가려줍니다.")
        uploaded_files = st.file_uploader("", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

        st.divider()
        submitted = st.form_submit_button("✨ 블로그 원고 & 썸네일 자동 생성기 실행 ✨", type="primary", use_container_width=True)

    # 4. 블로그 원고 생성 실행
    if submitted:
        if management_num and target_location and car_model and main_film and work_details and uploaded_files:
            with st.spinner("최고급 원고 작성, 사진 보정 및 표지 디자인을 렌더링 중입니다... (약 20~30초 소요)"):
                try:
                    save_to_gsheet(management_num, car_model, work_details)

                    images_for_ai = []
                    processed_display_images = [] # [★수정] 화면 출력을 위해 이미지들을 잠시 담아둘 그릇
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for idx, file in enumerate(uploaded_files):
                            img = Image.open(file).convert("RGBA")
                            img = enhance_image_for_blog(img)
                            img = auto_blur_license_plate(img)
                            
                            if idx == 0:
                                img = make_thumbnail(img, thumb_keyword, thumb_brand, car_model, main_film, "font.ttf")
                                save_name = f"01_썸네일_{file.name}"
                            else:
                                img = add_watermark(img, "font.ttf")
                                save_name = f"{idx+1:02d}_{file.name}"
                            
                            final_img = img.convert("RGB")
                            processed_display_images.append(final_img) # 화면 출력용 리스트에 저장
                            
                            # AI 인식용 이미지 축소본 저장
                            final_img_for_ai = final_img.copy()
                            final_img_for_ai.thumbnail((800, 800))  
                            images_for_ai.append(final_img_for_ai)
                            
                            # ZIP 파일에 저장
                            img_byte_arr = io.BytesIO()
                            final_img.save(img_byte_arr, format='JPEG', quality=95)
                            zip_file.writestr(save_name, img_byte_arr.getvalue())
                    
                    # [★수정] 레이아웃 변경: 대표 사진을 맨 위 중앙에 크게 띄우기
                    st.markdown("### 📸 보정 및 썸네일 생성 완료")
                    
                    st.markdown("##### 🌟 대표 표지 사진 (1:1 비율)")
                    # 가운데 정렬을 위해 1:2:1 비율의 컬럼을 만들고 가운데 컬럼에 사진을 넣습니다.
                    thumb_col1, thumb_col2, thumb_col3 = st.columns([1, 2, 1])
                    with thumb_col2:
                        st.image(processed_display_images[0], use_column_width=True)
                    
                    # 나머지 사진들은 5칸짜리 바둑판(Grid) 형태로 깔끔하게 나열
                    if len(processed_display_images) > 1:
                        st.markdown("##### 🎞️ 일반 작업 사진")
                        grid_cols = st.columns(5)
                        for i in range(1, len(processed_display_images)):
                            with grid_cols[(i - 1) % 5]:
                                st.image(processed_display_images[i], use_column_width=True)

                    st.divider()
                    st.download_button(
                        label="📦 보정된 사진 한 번에 다운로드 (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"{car_model}_팀앤디_블로그사진.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )
                    
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
