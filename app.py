import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import re 
import io       # [★신규] 파일을 메모리에 임시 저장하는 부품
import zipfile  # [★신규] 파일을 ZIP으로 압축하는 부품

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

# [★기존] 3.6 최신 AI 비전 인식 기반 번호판 자동 모자이크
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
    except Exception as e:
        pass
        
    return img

# [★기존] 상단 워터마크 자동 삽입
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
        st.warning("⚠️ 폰트 파일(font.ttf)이 없어 기본 글꼴로 표시됩니다.")
        
    draw.rectangle([(20, 20), (195, 65)], fill=(0, 0, 0, 220))
    draw.text((30, 25), "TEAMANDY", font=font_title, fill="white")
    
    return img

# [★기존] 대표 사진(썸네일) 하단 디자인 자동 삽입
def make_thumbnail(img, car_model, main_film, work_details, font_path="font.ttf"):
    w, h = img.size
    
    box_top = int(h * 0.55)
    box_bottom = int(h * 0.85)
    
    region = img.crop((0, box_top, w, box_bottom))
    region = region.filter(ImageFilter.GaussianBlur(radius=8))
    
    overlay = Image.new('RGBA', region.size, (0, 0, 0, 140))
    region = Image.alpha_composite(region, overlay)
    
    img.paste(region, (0, box_top), region)
    
    draw = ImageDraw.Draw(img)
    draw.line([(0, box_top), (w, box_top)], fill=(255, 255, 255, 200), width=2)
    draw.line([(0, box_bottom), (w, box_bottom)], fill=(255, 255, 255, 200), width=2)
    
    try:
        font_car = ImageFont.truetype(font_path, 35)
        font_film = ImageFont.truetype(font_path, 48) 
        font_detail = ImageFont.truetype(font_path, 22)
    except IOError:
        font_car = ImageFont.load_default()
        font_film = ImageFont.load_default()
        font_detail = ImageFont.load_default()
        
    def draw_centered_text(draw_obj, text, font, y_pos):
        bbox = draw_obj.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x_pos = (w - text_w) / 2
        draw_obj.text((x_pos, y_pos), text, font=font, fill="white")
        
    draw_centered_text(draw, f"'{car_model}'", font_car, box_top + 35)
    draw_centered_text(draw, main_film, font_film, box_top + 90)
    
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
4. Tone & Manner: 구어체와 문어체를 자연스럽게 혼용하십시오. ('~했습니다', '~하죠', '~입니다', '~거든요'). 문장의 길이에 변주를 주어 리듬감을 살리고, 가독성을 높이기 위해 적절한 이모지(🚗, ✨, 🛠️, 💧 등)를 문단당 1~2개 내외로 과하지 않게 배치하십시오.
5. 유연한 시공 항목 조합 (모듈형 작성): 사용자가 제시한 [키워드/시공 내역]에 포함된 작업에 대해서만 내용을 구성하십시오. 
6. 출력 포맷 및 해시태그: 가장 윗줄에 [블로그 제목 추천] 3가지 제시, 그 아래 [블로그 본문] 작성. 본문 끝에는 [추천 해시태그] 항목을 만들어 핵심 해시태그 5개를 '#태그1 #태그2' 형태로 제시하십시오.
7. 사진 배치 가이드: 텍스트만 길게 나열하지 마십시오. 글의 흐름에 맞춰 [📸 사진 삽입: 전면 틴팅 완료 모습]과 같이 사진 배치 마커를 삽입하십시오.
8. 모바일 최적화 및 단락 구성: 한 문장마다 무조건 엔터를 치는 것을 절대 금지합니다. 한 문단은 2~3개의 문장으로 짜임새 있게 구성하십시오.
9. 마크다운 금지 및 시각적 소제목 활용: 마크다운(`**`, `*` 등) 절대 금지. 대신 단락 구분을 위한 시각적 기호(■, ▶ 등)를 활용한 [소제목] 배치 및 '작은따옴표'나 [대괄호]를 활용한 강조 포인트 유도를 반드시 적용하십시오.
10. 전문 용어 분리 (인스톨 절대 금지): 틴팅/PPF는 '시공하다' 사용. 코팅은 '경화 시간' 사용. "시공을 이어갔습니다" 등 실시간 중계 표현 금지.
11. 사내 장비 어필 및 특정 장비 언급 금지: '썬프로(Sunpro)' 정밀 재단기 사용 명시. 연무기 가동 언급 금지.
12. 제품 스펙 임의 창작 방지: [팀앤디 오토센터 제품 사전] 최우선 참고.
13. 과장된 표현 및 비유 절대 금지.
14. 담백하고 전문적인 서술어 사용: "~을 도왔습니다" 금지, "시공을 완료했습니다", "적용했습니다" 사용.
15. 무관한 기술의 억지 연결 금지.
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
* 루마 버텍스 1100: '새로운 썬팅의 완성, 새로운 프리미엄의 시작'을 알리는 루마 최상위 하이엔드 비반사 필름입니다. 최신 나노 기술과 RC 코팅 등 첨단 기술이 집약되어 있으며, CV & NV ASSIST 기술로 주야간 모두 왜곡 없이 맑고 선명한 최고 수준의 시야를 제공하여 안전 드라이빙을 돕습니다. 전파 수신 간섭이 전혀 없으며, 10년의 넉넉한 품질 보증 기간을 제공하는 프리미엄 필름입니다.
* 루마 버텍스 900: '썬팅 기술의 결정체'라 불리는 첨단 신소재 나노융합 최고급 비반사 필름입니다. 어드밴스 나노 기술로 금속 성분이 없어 첨단 디바이스 전파 간섭이나 무아레 현상이 전혀 없으며, CV & NV ASSIST 기술 적용으로 주야간 모두 비교할 수 없는 선명한 시야를 제공합니다. 압도적인 열 차단 성능과 함께 10년의 품질 보증기간을 자랑하여 차량의 품격을 한 차원 높여줍니다.
* 루마 버텍스 700: '컴포트 밸런스 케어 나노테크'가 적용된 최고급 비금속 필름입니다. 금속 성분이 없어 터널 무아레 현상이나 하이패스, GPS 등 전파 수신 간섭이 전혀 없습니다. 내부 반사를 줄인 CVT 공법으로 주야간 선명한 시야를 제공하며, 색상은 고급스러운 '사파이어 블랙'입니다. 농도별 TSER 수치는 5%(67%), 15%(63%), 35%(59%), 50%(55%)이며 자외선은 99.9% 차단합니다.

---

[예시: 하이엔드 썬팅 시공 (장인정신 및 기술력 강조형)]

■ 써보지 않은 필름은 권하지 않습니다

저희 매장은 수많은 차량을 시공해왔지만, 기대 효과나 후기 면에서 특정 하이엔드 필름만 한 제품은 없더라고요. 고객님이 "제일 좋은 걸로 해주세요"라고 하시면, 저는 망설임 없이 이 제품을 말씀드립니다. 제가 직접 타보고 만족한 필름이라 자신 있게 권할 수 있거든요.

[📸 사진 삽입: 입고 및 마스킹 완료 모습]

■ 프라이버시와 열차단, 두 마리 토끼를 잡다

요즘 반사필름을 선호하시는 분들이 부쩍 많아졌는데, 가장 큰 이유는 프라이버시입니다. 외부 시선은 차단하면서도 내부 시야는 맑게 확보되도록 정밀하게 설계되어 있죠. 자연광을 받으면 차량이 한층 고급스러워지며 물론 열차단도 확실합니다. 

[📸 사진 삽입: 썬프로 재단 및 틴팅 시공 모습]

밝은 필름일수록 열차단이 약하다는 게 썬팅 시장의 일반적인 상식입니다. 농도를 높이면 열차단은 좋아지지만 시야가 어두워지고, 밝게 가면 열을 양보해야 하니까요. 이 필름은 이 두 가지를 동시에 충족한다는 점에서 '대체하기 어려운 강점'을 가집니다. 소비자분들이 흔히 오해하시는 지표가 바로 필름의 열차단율 수치인데, 측정 기준 자체가 다르기 때문에 과장된 스펙 광고에 눈이 가기 쉽습니다.

■ 압도적인 재구매율의 비밀

이 필름은 일반적인 제품보다 시공에 더 많은 시간과 정성이 들어갑니다. 두껍고 견고한 구조를 지녔기 때문에, 곡면이 많은 유리에 밀착시키는 과정이 무척 까다롭습니다. 저 역시 이 필름을 제 손으로 완벽히 익히겠다는 생각 하나로, 끊임없이 반복하며 연습했습니다.

[📸 사진 삽입: 시공 완료 후 출고 모습]

한 번 경험해 보신 분들은 다음 차량을 받으실 때도 변함없이 저희 오토센터를 찾으십니다. 심지어 동종 업계 사장님들도 정작 본인 차에는 저희 쪽에 시공해 달라며 찾아오시곤 합니다. 저희 팀앤디 오토센터는 단 한 대를 시공하더라도 완성도 하나만큼은 타협하지 않습니다. 
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
    st.info("💡 썸네일 생성 및 번호판 자동 블러, 압축 다운로드(ZIP) 기능 탑재 완료!")
    
    st.divider()

    with st.form("my_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            management_num = st.text_input("🔢 번호", placeholder="예: 229")
        with col2:
            target_location = st.text_input("📍 타겟 지역", placeholder="예: 구리, 다산")
        with col3:
            car_model = st.text_input("🚙 차종", placeholder="예: GV70")
            
        main_film = st.text_input("👑 메인 시공명 (썸네일 대표 글씨)", placeholder="예: 루마 버텍스 900")
        work_details = st.text_area("🛠️ 상세 작업 내역", placeholder="예: 전면 30%, 측후면 15% + PPF(4종)...")

        st.subheader("📸 작업 사진 업로드")
        st.caption("첫 번째 사진은 '썸네일'이 됩니다. 업로드된 모든 사진의 번호판은 AI가 자동으로 가려줍니다.")
        uploaded_files = st.file_uploader("", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

        st.divider()
        submitted = st.form_submit_button("✨ 블로그 원고 & 썸네일 자동 생성기 실행 ✨", type="primary", use_container_width=True)

    # 4. 블로그 원고 생성 실행
    if submitted:
        if management_num and target_location and car_model and main_film and work_details and uploaded_files:
            with st.spinner("전문가 톤앤매너 원고 작성, 사진 보정 및 번호판을 처리 중입니다... (약 20~30초 소요)"):
                try:
                    save_to_gsheet(management_num, car_model, work_details)

                    images_for_ai = []
                    
                    # [★신규] 압축파일(ZIP) 생성을 위한 메모리 그릇 준비
                    zip_buffer = io.BytesIO()
                    
                    # ZIP 파일 생성 모드 시작
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        
                        st.markdown("### 📸 썸네일 및 보정(번호판 블러) 완료된 사진")
                        
                        # 사진 개수만큼 컬럼 분할 (Streamlit은 많아도 알아서 가로로 배치해 줍니다)
                        img_cols = st.columns(len(uploaded_files))
                        
                        for idx, file in enumerate(uploaded_files):
                            img = Image.open(file).convert("RGBA")
                            
                            img = enhance_image_for_blog(img)
                            img = auto_blur_license_plate(img)
                            img = add_watermark(img, "font.ttf")
                            
                            if idx == 0:
                                img = make_thumbnail(img, car_model, main_film, work_details, "font.ttf")
                                save_name = f"01_썸네일_{file.name}"
                            else:
                                save_name = f"{idx+1:02d}_{file.name}"
                            
                            final_img = img.convert("RGB")
                            
                            with img_cols[idx]:
                                if idx == 0:
                                    st.markdown("**[대표]**")
                                st.image(final_img, use_column_width=True)
                            
                            final_img.thumbnail((800, 800))  
                            images_for_ai.append(final_img)
                            
                            # [★신규] 보정된 이미지를 바이트로 변환해서 바로 ZIP 파일 안에 담기
                            img_byte_arr = io.BytesIO()
                            final_img.save(img_byte_arr, format='JPEG', quality=95)
                            zip_file.writestr(save_name, img_byte_arr.getvalue())
                    
                    st.divider()
                    
                    # [★신규] 방금 묶어둔 ZIP 파일을 통째로 다운로드할 수 있는 대형 버튼 생성
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
