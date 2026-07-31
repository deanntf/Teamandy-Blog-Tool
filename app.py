import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import re 
import io       
import zipfile  
import time

import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

# ---------------------------------------------------------
# 1. 구글 시트 연동 및 학습 데이터(피드백) 관리 함수
# ---------------------------------------------------------
def save_to_gsheet(management_num, car_model, work_details):
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1JavBx0STp73mlTg8qNjeJ2lDHwwwwxCZvKAZAwANxd8/edit?gid=1200727784#gid=1200727784"
        doc = gc.open_by_url(sheet_url)
        worksheet = doc.sheet1
        KST = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        worksheet.append_row([now, management_num, car_model, work_details])
    except Exception:
        pass

def get_recent_history():
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
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

def save_final_feedback_to_gsheet(car_model, original_text, final_text):
    """★ [NEW] 대표님이 최종 수정한 완벽 원고를 Feedback 시트에 저장"""
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1JavBx0STp73mlTg8qNjeJ2lDHwwwwxCZvKAZAwANxd8/edit"
        doc = gc.open_by_url(sheet_url)
        
        # 'Feedback' 시트를 찾고, 없으면 새로 생성
        try:
            worksheet = doc.worksheet("Feedback")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = doc.add_worksheet(title="Feedback", rows="1000", cols="5")
            # 첫 줄 헤더 생성
            worksheet.append_row(["일시", "차종", "AI초안", "대표님최종수정본"])
            
        KST = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        worksheet.append_row([now, car_model, original_text, final_text])
        return True
    except Exception as e:
        st.error(f"피드백 저장 실패: {e}")
        return False

def get_fewshot_examples():
    """★ [NEW] AI가 글쓰기 전 참고할 최근 정답 원고 2건 로드"""
    try:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        creds = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1JavBx0STp73mlTg8qNjeJ2lDHwwwwxCZvKAZAwANxd8/edit"
        doc = gc.open_by_url(sheet_url)
        
        try:
            worksheet = doc.worksheet("Feedback")
        except gspread.exceptions.WorksheetNotFound:
            return "" # Feedback 시트가 아직 없으면 빈 값 반환
            
        records = worksheet.get_all_values()
        
        # 데이터가 헤더(1줄)밖에 없으면 빈 값 반환
        if len(records) <= 1:
            return ""

        # 대표님최종수정본(인덱스 3) 데이터만 추출
        valid_records = [row[3] for row in records[1:] if len(row) >= 4 and str(row[3]).strip() != ""]
        
        # 가장 최근에 저장된 2개의 수정본 추출
        recent_examples = valid_records[-2:]
        if not recent_examples:
            return ""
            
        fewshot_str = "\n\n".join([f"=== [대표님 직접 승인 완벽 원고 예시 {i+1}] ===\n{ex}" for i, ex in enumerate(recent_examples)])
        return fewshot_str
    except Exception:
        return ""

# ---------------------------------------------------------
# 2. 이미지 처리 함수
# ---------------------------------------------------------
def enhance_image_for_blog(img):
    img = ImageEnhance.Brightness(img).enhance(1.1)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(1.1)
    return img

def auto_blur_license_plate(img):
    try:
        vision_model = genai.GenerativeModel("gemini-3.6-flash")
        prompt = "Look at this image. Find the vehicle license plate. Return ONLY a JSON array with bounding box coordinates normalized to 1000: [ymin, xmin, ymax, xmax]."
        temp_img = img.copy()
        temp_img.thumbnail((800, 800))
        response = vision_model.generate_content([temp_img, prompt])
        numbers = re.findall(r'\d+', response.text.strip())
        if len(numbers) >= 4:
            ymin, xmin, ymax, xmax = map(int, numbers[:4])
            if xmin < xmax and ymin < ymax:
                w, h = img.size
                top, left = int((ymin / 1000) * h), int((xmin / 1000) * w)
                bottom, right = int((ymax / 1000) * h), int((xmax / 1000) * w)
                pad_w, pad_h = int((right - left) * 0.05), int((bottom - top) * 0.05)
                left, right = max(0, left - pad_w), min(w, right + pad_w)
                top, bottom = max(0, top - pad_h), min(h, bottom + pad_h)
                plate_region = img.crop((left, top, right, bottom))
                blurred_region = plate_region.filter(ImageFilter.GaussianBlur(radius=25))
                img.paste(blurred_region, (left, top))
    except Exception:
        pass
    return img

def add_watermark(img, font_path="font.ttf"):
    w, h = img.size
    new_w = 1000
    new_h = int((new_w / w) * h)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGBA")
    draw = ImageDraw.Draw(img)
    try: font_title = ImageFont.truetype(font_path, 28)
    except IOError: font_title = ImageFont.load_default()
    draw.rectangle([(20, 20), (195, 65)], fill=(0, 0, 0, 220))
    draw.text((30, 25), "TEAMANDY", font=font_title, fill="white")
    return img

def make_thumbnail(img, top_yellow, top_white, car_model, main_film, font_path="font.ttf"):
    w, h = img.size
    min_dim = min(w, h)
    left, top = (w - min_dim) / 2, (h - min_dim) / 2
    right, bottom = (w + min_dim) / 2, (h + min_dim) / 2
    img = img.crop((left, top, right, bottom))
    img = img.resize((1000, 1000), Image.Resampling.LANCZOS).convert("RGBA")
    
    gradient = Image.new('RGBA', (1000, 1000), (0,0,0,0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(1000):
        if y < 350: grad_draw.line([(0, y), (1000, y)], fill=(0,0,0, int(255 * (1 - y/350) * 0.7)))
        elif y > 650: grad_draw.line([(0, y), (1000, y)], fill=(0,0,0, int(255 * ((y-650)/350) * 0.8)))
    img = Image.alpha_composite(img, gradient)
    
    draw = ImageDraw.Draw(img)
    margin = 40
    draw.rectangle([(margin, margin), (1000 - margin, 1000 - margin)], outline=(255, 255, 255, 180), width=2)
    
    try:
        f_y, f_w, f_m, f_s = ImageFont.truetype(font_path, 85), ImageFont.truetype(font_path, 65), ImageFont.truetype(font_path, 95), ImageFont.truetype(font_path, 45)
    except:
        f_y = f_w = f_m = f_s = ImageFont.load_default()
        
    text_x = margin + 35
    draw.text((text_x, margin + 35), top_yellow, font=f_y, fill="#FFE600") 
    top_w_pos = draw.textbbox((text_x, margin + 35), top_yellow, font=f_y)[3] + 10
    draw.text((text_x, top_w_pos), top_white, font=f_w, fill="white")
    bbox_w = draw.textbbox((text_x, top_w_pos), top_white, font=f_w)
    draw.line([(text_x, bbox_w[3] + 25), (bbox_w[2], bbox_w[3] + 25)], fill="white", width=6) 
    
    bar_y = 1000 - margin - 45 - 135
    draw.rectangle([(text_x, bar_y), (text_x + 12, bar_y + 135)], fill="white")
    draw.text((text_x + 37, bar_y - 15), car_model, font=f_m, fill="white")
    bot_sub_y = draw.textbbox((text_x + 37, bar_y - 15), car_model, font=f_m)[3] + 15
    draw.text((text_x + 37, bot_sub_y), main_film, font=f_s, fill="white")
    
    return img

# ---------------------------------------------------------
# 3. AI 모델 및 시스템 프롬프트
# ---------------------------------------------------------
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

system_instruction = """
[Role & Identity]
당신은 10년 이상의 현장 경험을 보유한 '팀앤디 오토센터'의 수석 엔지니어이자, 네이버 블로그 'teamandy19'의 메인 에디터입니다. 신차 패키지 및 차량 디테일링에 대한 완벽한 기술적 이해도를 바탕으로, 고객에게 무한한 신뢰감을 주는 최고 전문가의 화법을 구사합니다.

[★ 신차패키지 포스팅 5단계 정석 구조 (반드시 준수)]
1. 제목: 검색 노출에 최적화된 [지역명 + 차종 + 필름/작업명] 조합 포함.
2. 도입부: 타겟 지역명과 차종 자연스럽게 언급, 감사 인사.
3. 준비/보양 작업: 풀마스킹 및 커버링 작업의 중요성 어필.
4. 메인 썬팅 시공: 외부 프라이버시 차단 효과 & 내부 맑은 시인성 교차 강조.
5. 디테일링 (PPF/코팅): 생활 스크래치 방지, 정밀한 마감 어필.
6. 마무리 및 출고: 안전 운전 기원 인사말.

[Strict Writing Guidelines]
1. 전형적인 AI 멘트("결론적으로", "오늘은~", "안녕하세요 여러분") 금지.
2. 구어체/문어체 혼용, 적절한 이모지 사용.
3. 소제목(■) 및 핵심 단어 따옴표(' ') 강조 적용. 마크다운(**) 금지.
4. '시공하다', '경화 시간', '썬프로 정밀 재단기' 용어 사용. '인스톨'/'연무기' 언급 금지.
5. 타겟 지역 키워드를 로컬 SEO에 맞게 자연스럽게 배치.
6. [중요] 아래에 제시되는 '대표님 직접 승인 완벽 원고 예시'가 있다면, 해당 예시의 어조, 줄바꿈 간격, 문장 길이, 스타일을 100% 동일하게 복제하여 작성할 것.

[팀앤디 오토센터 제품 사전 (Knowledge Base)]
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

model = genai.GenerativeModel(model_name="gemini-3.6-flash", system_instruction=system_instruction)

# ---------------------------------------------------------
# 4. Streamlit 화면 구성 (UI)
# ---------------------------------------------------------
st.set_page_config(page_title="팀앤디 오토센터 블로그 매니저", page_icon="🚗", layout="wide")
left_col, right_col = st.columns([7, 3], gap="large")

with left_col:
    with st.form("my_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1: management_num = st.text_input("🔢 번호")
        with col2: target_location = st.text_input("📍 타겟 지역")
        with col3: car_model = st.text_input("🚙 차종 (하단 큰글씨)")
            
        col4, col5 = st.columns([1, 1])
        with col4: thumb_keyword = st.text_input("💛 썸네일 상단 노란글씨", value="버텍스썬팅")
        with col5: thumb_brand = st.text_input("🤍 썸네일 상단 흰글씨", value="팀앤디오토센터")
            
        main_film = st.text_input("👑 메인 시공명 (하단 작은글씨)")
        work_details = st.text_area("🛠️ 상세 작업 내역")
        use_auto_blur = st.checkbox("🔍 AI 번호판 자동 모자이크 적용", value=True)
        uploaded_files = st.file_uploader("", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        # 버튼 클릭 여부
        submitted = st.form_submit_button("✨ 블로그 원고 & 썸네일 자동 생성기 실행 ✨", type="primary", use_container_width=True)

    if submitted and uploaded_files:
        try:
            # 상태 초기화 (재실행 시 이전 피드백 창 리셋)
            if "generated_text" in st.session_state:
                del st.session_state["generated_text"]
                
            save_to_gsheet(management_num, car_model, work_details)
            images_for_ai, processed_display_images = [], []
            zip_buffer = io.BytesIO()
            my_bar = st.progress(0, text=f"사진 처리 중... (0/{len(uploaded_files)})")
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file).convert("RGBA")
                    img = enhance_image_for_blog(img)
                    if use_auto_blur:
                        img = auto_blur_license_plate(img)
                        time.sleep(1) 
                    
                    if idx == 0: img = make_thumbnail(img, thumb_keyword, thumb_brand, car_model, main_film, "font.ttf")
                    else: img = add_watermark(img, "font.ttf")
                    
                    final_img = img.convert("RGB")
                    processed_display_images.append(final_img) 
                    
                    img_for_ai = final_img.copy()
                    img_for_ai.thumbnail((800, 800))  
                    images_for_ai.append(img_for_ai)
                    
                    img_byte_arr = io.BytesIO()
                    final_img.save(img_byte_arr, format='JPEG', quality=95)
                    zip_file.writestr(f"{idx+1:02d}_{file.name}" if idx > 0 else f"01_썸네일_{file.name}", img_byte_arr.getvalue())
                    my_bar.progress((idx + 1) / len(uploaded_files), text=f"사진 처리 중... ({idx+1}/{len(uploaded_files)})")
            
            my_bar.progress(1.0, text="✨ 블로그 원고 작성 중... (이전 원고 스타일을 분석하여 작성합니다)")
            
            st.markdown("##### 🌟 대표 표지 사진 (1:1 비율)")
            _, col_m, _ = st.columns([1, 2, 1])
            with col_m: st.image(processed_display_images[0], use_column_width=True)
            
            if len(processed_display_images) > 1:
                st.markdown("##### 🎞️ 일반 작업 사진")
                grid_cols = st.columns(5)
                for i in range(1, len(processed_display_images)):
                    with grid_cols[(i - 1) % 5]: st.image(processed_display_images[i], use_column_width=True)

            st.download_button(label="📦 ZIP 다운로드", data=zip_buffer.getvalue(), file_name="팀앤디_블로그사진.zip", mime="application/zip")
            
            # ★ 동적 퓨샷: 구글 시트에서 대표님의 최근 완벽 수정본 로드
            fewshot_examples = get_fewshot_examples()
            user_prompt = f"[시공내역] 타겟: {target_location}, 차종: {car_model}, 필름: {main_film}, 내역: {work_details}\n\n"
            
            # 과거 데이터가 있으면 프롬프트에 추가해서 명령 내림
            if fewshot_examples:
                user_prompt += f"[참고: 대표님이 승인한 최고의 원고 예시]\n{fewshot_examples}\n\n위 예시 원고의 문체, 구성, 어조, 줄바꿈 방식을 완벽하게 분석하고 100% 동일한 스타일로 작성해 주세요."
            
            response = model.generate_content(images_for_ai + [user_prompt])
            my_bar.empty() 
            
            # 세션 상태에 저장 (새로고침해도 날아가지 않게 보존)
            st.session_state["generated_text"] = response.text
            st.session_state["current_car_model"] = car_model

        except Exception as e:
            st.error(f"오류: {e}")

    # ---------------------------------------------------------
    # 5. [NEW] AI 원고 표시 & 피드백 저장 UI
    # ---------------------------------------------------------
    if "generated_text" in st.session_state:
        st.markdown("---")
        st.subheader("📋 생성된 블로그 본문 초안")
        ai_draft = st.text_area("AI 초안 (복사해서 네이버 블로그로 가져가세요)", value=st.session_state["generated_text"], height=400)
        
        st.markdown("### 🎓 (중요) AI 학습용 최종본 등록")
        st.info("네이버 블로그에서 글을 최종적으로 예쁘게 다듬으셨나요? **발행 버튼을 누르기 전, 그 완성된 텍스트를 아래 빈칸에 붙여넣고 [저장]을 눌러주세요.** AI가 대표님의 스타일을 기억하고 다음번 글쓰기부터 똑같이 따라 합니다!")
        
        edited_final_text = st.text_area("✏️ 대표님이 수정을 완료한 '최종 완벽 원고'", value=ai_draft, height=400)
        
        if st.button("💾 대표님 수정본 저장 (AI 학습 반영)", type="secondary", use_container_width=True):
            with st.spinner("구글 시트에 대표님의 스타일을 저장 중입니다..."):
                if save_final_feedback_to_gsheet(st.session_state.get("current_car_model", "차종미상"), ai_draft, edited_final_text):
                    st.success("🎉 성공적으로 학습 데이터가 저장되었습니다! 다음 작업부터는 대표님의 수정 스타일(문체, 간격 등)이 자동 반영됩니다.")
                    # 피드백 완료 시 중복 저장 방지를 위해 상태 초기화
                    del st.session_state["generated_text"]
                    
with right_col:
    # 기존 코드에서 우측 컬럼에 보여주던 항목이 있다면 이곳에 위치 (현재 비워둠 또는 기존 상태 유지)
    st.markdown("#### 📝 최근 작업 이력")
    history = get_recent_history()
    if history:
        for row in history:
            # row = [일시, 관리번호, 차종, 작업내역]
            st.caption(f"{row[0]} | {row[1]} | {row[2]}")
    else:
        st.caption("최근 내역이 없습니다.")
