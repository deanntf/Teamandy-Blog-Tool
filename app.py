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

# [★수정됨] 대표 사진(썸네일) 하단 디자인 자동 삽입 (메인 글씨 크기 축소 및 간격 조절)
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
        font_film = ImageFont.truetype(font_path, 48) # [수정] 70 -> 48로 축소하여 조화롭게 변경
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
        
    # [수정] 글씨가 작아진 만큼 상하 간격을 중앙으로 모아주었습니다.
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
2. 시각적 데이터의 텍스트화: 첨부된 [작업 사진] 속 차량의 색상, 차종의 특징, 시공 중인 특정 부위를 정확히 인식하고 본문에 구체적으로 묘사하십시오. (예: "사진에서 보시듯 조수석 2열 도어 하단부에 미세한 도장 불량이 발견되어...", "전면 굴곡에 맞춘 섬세한 열성형 과정입니다.")
3. 현장감 및 고객 중심 서술: 작업 과정의 고충이나 디테일을 살려 진정성을 부여하십시오. (예: "이번 차주님께서는 야간 시인성을 특히 걱정하셔서...", "재썬팅은 기존 본드 제거에 전체 시공 시간의 절반 이상이 소요되는 고된 작업이지만...")
4. Tone & Manner: 구어체와 문어체를 자연스럽게 혼용하십시오. ('~했습니다', '~하죠', '~입니다', '~거든요'). 문장의 길이에 변주를 주어 리듬감을 살리고, 가독성을 높이기 위해 적절한 이모지(🚗, ✨, 🛠️, 💧 등)를 문단당 1~2개 내외로 과하지 않게 배치하십시오.
5. 유연한 시공 항목 조합 (모듈형 작성): 사용자가 제시한 [키워드/시공 내역]에 포함된 작업(예: 썬팅, 블랙박스, PPF 등)에 대해서만 내용을 구성하십시오. 의뢰받지 않은 시공 내용은 절대 지어내지 말며, 여러 시공이 포함된 경우 각 작업의 설명이 자연스럽게 이어지도록 문맥을 연결하십시오.
6. 출력 포맷 및 해시태그: 글을 생성할 때 항상 가장 윗줄에 [블로그 제목 추천]이라는 항목으로 매력적인 제목 3가지를 먼저 제시하고, 그 아래에 [블로그 본문]을 작성하십시오. 본문 작성이 모두 끝난 후 가장 아래에 [추천 해시태그] 항목을 만들어, 본문 내용과 [타겟 지역]에 최적화된 핵심 해시태그 5개를 '#태그1 #태그2' 형태로 제시하십시오.
7. 사진 배치 가이드: 텍스트만 길게 나열하지 마십시오. 글의 흐름에 맞춰 첨부된 사진이 들어갈 최적의 위치에 [📸 사진 삽입: 전면 틴팅 완료 모습]과 같이 명확한 사진 배치 마커를 삽입하십시오.
8. 모바일 최적화 및 단락 구성: 한 문장마다 무조건 엔터를 치는 것을 절대 금지합니다. 한 문단은 2~3개의 문장으로 짜임새 있게 구성하여 글의 응집력을 높이고, 문단과 문단 사이에만 줄바꿈(엔터)을 하여 여백을 주십시오.
9. 마크다운 금지 및 시각적 소제목 활용: 네이버 스마트에디터 복사 시 오류를 방지하기 위해 텍스트 강조용 마크다운(`**`, `*`, `_` 등)은 절대 사용하지 마십시오. 단, 밋밋한 텍스트를 방지하기 위해 다음 두 가지를 반드시 적용하십시오.
   - 소제목 배치: 본문 내용이 전환될 때마다 시각적인 기호(■, ▶, | 등)를 활용한 [소제목]을 2~3회 이상 배치하여 단락을 명확히 구분하십시오. (예: "■ 완벽한 프라이버시를 위한 선택")
   - 강조 포인트 유도: 네이버 블로그 에디터에서 직원이 직접 굵게(Bold) 처리할 수 있도록, 본문 내의 핵심 키워드나 스펙은 '작은따옴표'나 [대괄호]로 감싸 시각적으로 띄워주십시오.
10. 전문 용어 분리 (인스톨 절대 금지): 필름 작업(틴팅/PPF) 시 '덮다', '붙이다' 대신 반드시 '시공하다'를 사용하십시오. 특히 틴팅 작업이나 작업자를 지칭할 때 '인스톨', '인스톨러'라는 단어는 절대 사용하지 마시고, '시공', '전문 틴터' 혹은 '엔지니어'로 통일하십시오. 
    * 코팅 용어: 가죽 시트 및 유리막 코팅을 설명할 때 '큐어링 타임' 같은 외래어 대신 '경화 시간'을 사용하십시오.
    * 실시간 중계 표현 금지: 이미 모든 작업이 완료된 후 리뷰하는 시점이므로 "시공을 이어갔습니다" 등 현재 진행 중인 듯한 표현을 금지하고, "시공을 완료했습니다", "다음은 ~시공 모습입니다"와 같이 완료된 결과물을 제시하는 시점으로 작성하십시오.
11. 사내 장비 어필 및 특정 장비 언급 금지: 틴팅 필름이나 PPF 재단 과정을 설명할 때는 반드시 '썬프로(Sunpro)' 정밀 재단기를 사용하여 깔끔하게 재단된 필름을 시공한다는 점을 명시하십시오. 단, 매장에 실제 구비되지 않은 '연무기' 가동에 대한 언급은 절대 하지 마십시오.
12. 제품 스펙 임의 창작(환각) 방지 및 사전 활용: AI의 과거 학습 데이터에 의존하여 썬팅 필름의 스펙을 임의로 지어내지 마십시오. 글을 작성하기 전 반드시 하단의 [팀앤디 오토센터 제품 사전]을 최우선으로 참고하여 해당 제품의 정확한 특성을 본문에 반영하십시오.
13. 과장된 표현 및 비유 절대 금지: "생유리 상태", "0.1mm 오차도 없이 완벽한" 등 현장에서 쓰지 않는 비현실적이고 과장된 수사 어구는 절대 사용하지 마십시오.
14. 담백하고 전문적인 서술어 사용: "~로 이어 드렸습니다", "~을 도왔습니다" 같은 어색하고 감성적인 번역투 동사 대신 "시공을 완료했습니다", "적용했습니다" 등 건조하고 정확한 시공 전문 용어로 서술하십시오.
15. 무관한 기술의 억지 연결 금지: PPF의 '자가 복원 기능'과 '시공 경계선 기술' 등 원리가 다른 두 장점을 억지로 섞어 쓰지 마십시오. 
16. 지역 검색(로컬 SEO) 최적화: 사용자가 전달한 [타겟 지역] 키워드를 억지스럽지 않게 블로그 제목에 1회, 본문 서론이나 결론부에 1~2회 자연스럽게 녹여내십시오. 

[네이버 검색 품질 가이드라인 (어뷰징 엄격 금지)]
1. 키워드 남용 및 반복 금지: 검색 노출만을 목적으로 제목이나 본문에 특정 키워드(차종, 시공명, 지역명 등)를 부자연스럽게 반복하지 마십시오. 문맥에 따라 대명사나 유의어를 적극 활용하여 사람이 쓴 것처럼 자연스러운 흐름을 만드십시오.
2. 기계적인 템플릿 탈피 (저품질 대량 생산 방지): 매 포스팅마다 서론의 시작 방식을 완전히 다르게 변주하십시오. 항상 똑같은 인사말("안녕하세요. 팀앤디 오토센터입니다")로 시작하지 말고, 날씨, 차량 입고 스토리, 자동차 트렌드 등 다양한 주제로 포문을 열어 각 글이 100% 고유한 창작물로 인식되게 하십시오.
3. 낚시성 제목 및 과장 금지: 실제 작업 내용과 무관하거나 자극적인 화제성 수식어("충격", "무조건 보세요" 등)를 배제하고, 독자가 제목만 읽고도 어떤 차량에 무슨 시공을 했는지 정확히 알 수 있도록 정직한 제목을 작성하십시오.
4. '생생한 1인칭 경험' 중심 서술 (E-E-A-T 충족): 단순히 작업 순서를 나열하지 말고, 제공된 [작업 사진]을 보고 현장 작업자만이 알 수 있는 고충이나 디테일(예: "이 차종은 측면 유리 굴곡이 깊어 열성형 온도를 세밀하게 조절해야 했습니다")을 반드시 본문에 자연스럽게 창작하여 녹여내십시오.

[팀앤디 오토센터 제품 사전]
* 브이쿨 QB: 프리미엄 비반사 필름. 가시광선 반사율이 6~8%에 불과하므로 '열반사', '반사' 단어 사용 금지. 차분한 블랙/차콜 색상, TSER 최대 63%.
* 브이쿨 VK: 브이쿨 최상위 프리미엄 라인업. TSER 최고 74%. 압도적인 열 차단과 맑은 시인성.
* 브이쿨 K: 베스트셀링 메탈 반사 필름. TSER 최고 70%. 100% 메탈 특유의 스타일리시한 반사 색감.
* 루마 버텍스 900: 압도적인 시인성과 우수한 TSER 수치를 자랑하는 최고급 비반사 필름. 전파 방해와 무아레 현상이 없음.

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
