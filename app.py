import streamlit as st
import requests
import time
import base64
import zipfile
import io
import os

st.set_page_config(page_title="AI 영상 일괄 생성기", page_icon="🎬", layout="wide")

st.title("🎬 AI 영상 일괄 생성기")

# API 키 안내
with st.expander("🔑 API 키 발급 방법 (처음 사용자는 클릭)", expanded=False):
    st.markdown("""
    ### Replicate API 키 발급 (1분)
    
    1. **회원가입**: [Replicate 가입하기](https://replicate.com/signin) (Google/GitHub 계정으로 10초 완료)
    2. **API 키 복사**: [API 토큰 페이지](https://replicate.com/account/api-tokens)에서 키 복사 (`r8_`로 시작)
    3. **결제 등록** (선택): [결제 페이지](https://replicate.com/account/billing)에서 $5 충전 → 약 50개 영상 생성 가능
    
    💡 **비용**: 모델별로 다름 (아래 비용 비교표 참고)
    """)

api_key = st.text_input("🔑 Replicate API 키", type="password", placeholder="r8_...")

# 모델 정보
MODELS = {
    "🚀 LTX-2 Distilled ($0.02/초) - 가장 저렴, 빠름": {
        "id": "lightricks/ltx-2-distilled",
        "cost": 0.02,
        "audio": True,
        "image_support": True
    },
    "🎯 Grok Imagine ($0.05/초) - 가성비 최고": {
        "id": "xai/grok-imagine-video",
        "cost": 0.05,
        "audio": True,
        "image_support": True
    },
    "🎬 Kling 2.6 ($0.07/초) - 안정적 품질": {
        "id": "kwaivgi/kling-v2.6",
        "cost": 0.07,
        "audio": True,
        "image_support": True
    },
    "✨ Sora 2 Standard ($0.10/초) - 고품질": {
        "id": "openai/sora-2",
        "cost": 0.10,
        "audio": True,
        "image_support": True
    },
    "🎤 Seedance 1.5 Pro ($0.15/초) - 립싱크+다국어": {
        "id": "bytedance/seedance-1.5-pro",
        "cost": 0.15,
        "audio": True,
        "image_support": True
    },
    "🌟 Veo 3 Fast ($0.15/초) - 립싱크 강점": {
        "id": "google/veo-3-fast",
        "cost": 0.15,
        "audio": True,
        "image_support": False
    },
    "💎 Sora 2 Pro ($0.30/초) - 최고 품질": {
        "id": "openai/sora-2-pro",
        "cost": 0.30,
        "audio": True,
        "image_support": True
    },
    "👑 Veo 3 Standard ($0.40/초) - 프리미엄": {
        "id": "google/veo-3",
        "cost": 0.40,
        "audio": True,
        "image_support": False
    }
}

# 모델 선택
selected_model = st.selectbox("🤖 모델 선택", list(MODELS.keys()))
model_info = MODELS[selected_model]
model_id = model_info["id"]

# 비용 비교표
with st.expander("💰 모델별 비용 비교"):
    st.markdown("""
    | 모델 | 초당 비용 | 10초 영상 | 오디오 | 특징 |
    |------|----------|----------|--------|------|
    | LTX-2 Distilled | $0.02 | $0.20 | ✅ | 가장 저렴, 빠름 |
    | Grok Imagine | $0.05 | $0.50 | ✅ | 가성비 최고 |
    | Kling 2.6 | $0.07 | $0.70 | ✅ | 안정적 품질 |
    | Sora 2 Standard | $0.10 | $1.00 | ✅ | 고품질 |
    | **Seedance 1.5 Pro** | $0.15 | $1.50 | ✅ | **립싱크+다국어** |
    | Veo 3 Fast | $0.15 | $1.50 | ✅ | 립싱크 강점 |
    | Sora 2 Pro | $0.30 | $3.00 | ✅ | 최고 품질 |
    | Veo 3 Standard | $0.40 | $4.00 | ✅ | 프리미엄 |
    """)

# 모드 선택
mode = st.radio("모드 선택", ["📝 텍스트 → 영상", "🖼️ 이미지 → 영상"], horizontal=True)

# 이미지→영상 지원 체크
if mode == "🖼️ 이미지 → 영상" and not model_info["image_support"]:
    st.warning(f"⚠️ {selected_model.split('(')[0]}은 이미지→영상을 지원하지 않습니다. 다른 모델을 선택해주세요.")

st.markdown("---")

# ZIP 다운로드 함수
def create_zip_t2v(results):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, r in enumerate(results):
            if r['status'] == 'success' and r.get('url'):
                try:
                    video_data = requests.get(r['url'], timeout=60).content
                    filename = f"{idx+1:03d}.mp4"
                    zf.writestr(filename, video_data)
                except:
                    pass
    zip_buffer.seek(0)
    return zip_buffer

def create_zip_i2v(results):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            if r['status'] == 'success' and r.get('url'):
                try:
                    video_data = requests.get(r['url'], timeout=60).content
                    original_name = r.get('name', 'video')
                    base_name = os.path.splitext(original_name)[0]
                    filename = f"{base_name}.mp4"
                    zf.writestr(filename, video_data)
                except:
                    pass
    zip_buffer.seek(0)
    return zip_buffer

# ========== 텍스트 → 영상 ==========
if mode == "📝 텍스트 → 영상":
    st.subheader("📝 텍스트 → 영상 생성")
    
    prompts_text = st.text_area(
        "프롬프트 입력 (빈 줄로 구분)",
        height=200,
        placeholder="A cat walking on the street, cinematic\n\nA dog playing in the park, sunny day"
    )
    
    # 모델별 설정
    st.markdown("#### ⚙️ 설정")
    
    if "ltx" in model_id:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            width = st.selectbox("가로", [512, 768, 1024, 1280], index=1)
        with col2:
            height = st.selectbox("세로", [512, 576, 720, 768], index=0)
        with col3:
            steps = st.slider("스텝", 4, 20, 8)
        with col4:
            frames = st.selectbox("프레임", [49, 97, 129], index=1, help="49≈2초, 97≈4초, 129≈5초")
    
    elif "grok" in model_id:
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("영상 길이", [5, 10, 15], index=1, help="초 단위")
        with col2:
            aspect_ratio = st.selectbox("화면 비율", ["16:9", "9:16", "1:1"], index=0)
    
    elif "kling" in model_id:
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("영상 길이", [5, 10], index=1, help="초 단위")
        with col2:
            aspect_ratio = st.selectbox("화면 비율", ["16:9", "9:16", "1:1"], index=0)
    
    elif "sora" in model_id:
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("영상 길이", [5, 10, 15], index=1, help="초 단위")
        with col2:
            resolution = st.selectbox("해상도", ["480p", "720p", "1080p"], index=1)
    
    elif "seedance" in model_id:
        col1, col2, col3 = st.columns(3)
        with col1:
            duration = st.selectbox("영상 길이", [5, 10], index=1, help="초 단위")
        with col2:
            resolution = st.selectbox("해상도", ["480p", "720p", "1080p"], index=2)
        with col3:
            language = st.selectbox("음성 언어", ["Korean", "English", "Japanese", "Chinese", "Spanish"], index=0)
    
    elif "veo" in model_id:
        col1, col2 = st.columns(2)
        with col1:
            duration = st.selectbox("영상 길이", [5, 8], index=1, help="초 단위")
        with col2:
            aspect_ratio = st.selectbox("화면 비율", ["16:9", "9:16"], index=0)
    
    # 프롬프트 파싱
    def parse_prompts(text):
        blocks = text.strip().split('\n\n')
        prompts = []
        for block in blocks:
            prompt = ' '.join(block.strip().split('\n'))
            if prompt:
                prompts.append(prompt)
        return prompts
    
    prompts = parse_prompts(prompts_text)
    
    if prompts:
        st.info(f"📋 {len(prompts)}개 프롬프트 감지됨")
    
    # 생성 시작
    if st.button("🚀 전체 생성 시작", type="primary", key="t2v_start"):
        if not api_key:
            st.error("API 키를 입력해주세요")
        elif not prompts:
            st.error("프롬프트를 입력해주세요")
        else:
            results = []
            progress = st.progress(0)
            status = st.empty()
            
            for idx, prompt in enumerate(prompts):
                status.text(f"생성 중... {idx+1}/{len(prompts)}: {prompt[:50]}...")
                
                # 모델별 파라미터 구성
                if "ltx" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "width": width,
                        "height": height,
                        "num_frames": frames,
                        "num_inference_steps": steps
                    }
                elif "grok" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "duration": duration,
                        "aspect_ratio": aspect_ratio
                    }
                elif "kling" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "duration": duration,
                        "aspect_ratio": aspect_ratio
                    }
                elif "sora" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "duration": duration,
                        "resolution": resolution
                    }
                elif "seedance" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "duration": duration,
                        "resolution": resolution,
                        "language": language.lower()
                    }
                elif "veo" in model_id:
                    input_params = {
                        "prompt": prompt,
                        "duration": duration,
                        "aspect_ratio": aspect_ratio
                    }
                else:
                    input_params = {"prompt": prompt}
                
                try:
                    # API 호출
                    response = requests.post(
                        f"https://api.replicate.com/v1/models/{model_id}/predictions",
                        headers={
                            "Authorization": f"Token {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={"input": input_params},
                        timeout=30
                    )
                    
                    if response.status_code != 201:
                        results.append({"prompt": prompt, "status": "error", "error": f"API 오류: {response.status_code}"})
                        continue
                    
                    pred_id = response.json().get("id")
                    if not pred_id:
                        results.append({"prompt": prompt, "status": "error", "error": "예측 ID 없음"})
                        continue
                    
                    # 폴링
                    for _ in range(180):
                        time.sleep(5)
                        poll = requests.get(
                            f"https://api.replicate.com/v1/predictions/{pred_id}",
                            headers={"Authorization": f"Token {api_key}"}
                        )
                        result = poll.json()
                        
                        if result["status"] == "succeeded":
                            output = result.get("output")
                            if isinstance(output, list):
                                url = output[0] if output else None
                            elif isinstance(output, dict):
                                url = output.get("video") or output.get("url")
                            else:
                                url = output
                            results.append({"prompt": prompt, "status": "success", "url": url})
                            break
                        elif result["status"] == "failed":
                            results.append({"prompt": prompt, "status": "error", "error": result.get("error", "실패")})
                            break
                    else:
                        results.append({"prompt": prompt, "status": "error", "error": "시간 초과"})
                
                except Exception as e:
                    results.append({"prompt": prompt, "status": "error", "error": str(e)})
                
                progress.progress((idx + 1) / len(prompts))
            
            status.text("✅ 완료!")
            st.session_state['results'] = results
            
            # 결과 표시
            success_count = sum(1 for r in results if r['status'] == 'success')
            st.success(f"✅ {success_count}/{len(results)} 성공")
            
            if success_count > 0:
                zip_data = create_zip_t2v(results)
                st.download_button(
                    "📦 전체 다운로드 (ZIP)",
                    zip_data,
                    "videos.zip",
                    "application/zip"
                )
            
            for idx, r in enumerate(results):
                with st.expander(f"{'✅' if r['status']=='success' else '❌'} {idx+1}. {r['prompt'][:50]}..."):
                    if r['status'] == 'success':
                        st.video(r['url'])
                        st.code(r['url'])
                    else:
                        st.error(r.get('error', '알 수 없는 오류'))

# ========== 이미지 → 영상 ==========
else:
    st.subheader("🖼️ 이미지 → 영상 생성")
    
    if not model_info["image_support"]:
        st.stop()
    
    # 이미지 업로드
    uploaded_files = st.file_uploader(
        "이미지 업로드 (여러 개 가능)",
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if 'i2v_items' not in st.session_state:
            st.session_state['i2v_items'] = []
        
        # 새 파일 추가
        existing_names = {item['name'] for item in st.session_state['i2v_items']}
        for f in uploaded_files:
            if f.name not in existing_names:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                ext = f.name.split('.')[-1].lower()
                mime = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
                st.session_state['i2v_items'].append({
                    'name': f.name,
                    'data_uri': f"data:{mime};base64,{b64}",
                    'prompt': '',
                    'preview': data
                })
        
        if st.button("🗑️ 목록 초기화"):
            st.session_state['i2v_items'] = []
            st.rerun()
        
        # 프롬프트 입력 방식
        bulk_mode = st.toggle("📝 프롬프트 일괄 입력", value=True)
        
        if bulk_mode:
            bulk_prompts = st.text_area(
                "프롬프트 입력 (빈 줄로 구분, 이미지 순서대로 매칭)",
                height=150,
                placeholder="첫 번째 이미지 프롬프트\n\n두 번째 이미지 프롬프트"
            )
            
            def parse_bulk_prompts(text):
                blocks = text.strip().split('\n\n')
                return [' '.join(b.strip().split('\n')) for b in blocks if b.strip()]
            
            prompt_list = parse_bulk_prompts(bulk_prompts)
            
            # 매칭 미리보기
            st.markdown("#### 📋 매칭 미리보기")
            items = st.session_state['i2v_items']
            
            if len(prompt_list) != len(items) and prompt_list:
                st.warning(f"⚠️ 이미지 {len(items)}개, 프롬프트 {len(prompt_list)}개 - 개수가 다릅니다")
            
            cols = st.columns(min(4, len(items)))
            for idx, item in enumerate(items):
                with cols[idx % 4]:
                    st.image(item['preview'], caption=item['name'], width=150)
                    matched = prompt_list[idx] if idx < len(prompt_list) else "(프롬프트 없음)"
                    st.caption(f"→ {matched[:30]}..." if len(matched) > 30 else f"→ {matched}")
        else:
            # 개별 입력
            st.markdown("#### 📋 이미지별 프롬프트")
            for idx, item in enumerate(st.session_state['i2v_items']):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(item['preview'], caption=item['name'], width=100)
                with col2:
                    item['prompt'] = st.text_input(f"프롬프트 {idx+1}", key=f"prompt_{idx}", value=item['prompt'])
        
        # 모델별 설정
        st.markdown("#### ⚙️ 설정")
        
        if "ltx" in model_id:
            col1, col2, col3 = st.columns(3)
            with col1:
                i2v_steps = st.slider("스텝", 4, 20, 8, key="i2v_steps")
            with col2:
                i2v_frames = st.selectbox("프레임", [49, 97, 129], index=1, key="i2v_frames")
            with col3:
                i2v_resolution = st.selectbox("최대 해상도", ["512x512", "768x512", "1024x576", "1280x720"], index=1, key="i2v_res")
        
        elif "grok" in model_id:
            col1, col2 = st.columns(2)
            with col1:
                i2v_duration = st.selectbox("영상 길이", [5, 10, 15], index=1, key="i2v_dur")
            with col2:
                i2v_aspect = st.selectbox("화면 비율", ["16:9", "9:16", "1:1"], index=0, key="i2v_asp")
        
        elif "kling" in model_id:
            col1, col2 = st.columns(2)
            with col1:
                i2v_duration = st.selectbox("영상 길이", [5, 10], index=1, key="i2v_dur")
            with col2:
                i2v_aspect = st.selectbox("화면 비율", ["16:9", "9:16", "1:1"], index=0, key="i2v_asp")
        
        elif "sora" in model_id:
            col1, col2 = st.columns(2)
            with col1:
                i2v_duration = st.selectbox("영상 길이", [5, 10, 15], index=1, key="i2v_dur")
            with col2:
                i2v_resolution = st.selectbox("해상도", ["480p", "720p", "1080p"], index=1, key="i2v_res")
        
        elif "seedance" in model_id:
            col1, col2, col3 = st.columns(3)
            with col1:
                i2v_duration = st.selectbox("영상 길이", [5, 10], index=1, key="i2v_dur")
            with col2:
                i2v_resolution = st.selectbox("해상도", ["480p", "720p", "1080p"], index=2, key="i2v_res")
            with col3:
                i2v_language = st.selectbox("음성 언어", ["Korean", "English", "Japanese", "Chinese", "Spanish"], index=0, key="i2v_lang")
        
        # 생성 시작
        if st.button("🚀 이미지→영상 생성 시작", type="primary", key="i2v_start"):
            items = st.session_state['i2v_items']
            
            if not api_key:
                st.error("API 키를 입력해주세요")
            elif not items:
                st.error("이미지를 업로드해주세요")
            else:
                # 프롬프트 매칭
                if bulk_mode:
                    for idx, item in enumerate(items):
                        item['prompt'] = prompt_list[idx] if idx < len(prompt_list) else ""
                
                results = []
                progress = st.progress(0)
                status = st.empty()
                
                for idx, item in enumerate(items):
                    status.text(f"생성 중... {idx+1}/{len(items)}: {item['name']}")
                    
                    # 모델별 파라미터
                    if "ltx" in model_id:
                        res_w, res_h = map(int, i2v_resolution.split('x'))
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image",
                            "width": res_w,
                            "height": res_h,
                            "num_frames": i2v_frames,
                            "num_inference_steps": i2v_steps
                        }
                    elif "grok" in model_id:
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image",
                            "duration": i2v_duration,
                            "aspect_ratio": i2v_aspect
                        }
                    elif "kling" in model_id:
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image",
                            "duration": i2v_duration,
                            "aspect_ratio": i2v_aspect
                        }
                    elif "sora" in model_id:
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image",
                            "duration": i2v_duration,
                            "resolution": i2v_resolution
                        }
                    elif "seedance" in model_id:
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image",
                            "duration": i2v_duration,
                            "resolution": i2v_resolution,
                            "language": i2v_language.lower()
                        }
                    else:
                        input_params = {
                            "image": item['data_uri'],
                            "prompt": item['prompt'] or "animate this image"
                        }
                    
                    try:
                        response = requests.post(
                            f"https://api.replicate.com/v1/models/{model_id}/predictions",
                            headers={
                                "Authorization": f"Token {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={"input": input_params},
                            timeout=30
                        )
                        
                        if response.status_code != 201:
                            results.append({"name": item['name'], "status": "error", "error": f"API 오류: {response.status_code}"})
                            continue
                        
                        pred_id = response.json().get("id")
                        if not pred_id:
                            results.append({"name": item['name'], "status": "error", "error": "예측 ID 없음"})
                            continue
                        
                        # 폴링
                        for _ in range(180):
                            time.sleep(5)
                            poll = requests.get(
                                f"https://api.replicate.com/v1/predictions/{pred_id}",
                                headers={"Authorization": f"Token {api_key}"}
                            )
                            result = poll.json()
                            
                            if result["status"] == "succeeded":
                                output = result.get("output")
                                if isinstance(output, list):
                                    url = output[0] if output else None
                                elif isinstance(output, dict):
                                    url = output.get("video") or output.get("url")
                                else:
                                    url = output
                                results.append({
                                    "name": item['name'],
                                    "status": "success",
                                    "url": url,
                                    "preview": item['preview'],
                                    "prompt": item['prompt']
                                })
                                break
                            elif result["status"] == "failed":
                                results.append({"name": item['name'], "status": "error", "error": result.get("error", "실패")})
                                break
                        else:
                            results.append({"name": item['name'], "status": "error", "error": "시간 초과"})
                    
                    except Exception as e:
                        results.append({"name": item['name'], "status": "error", "error": str(e)})
                    
                    progress.progress((idx + 1) / len(items))
                
                status.text("✅ 완료!")
                st.session_state['i2v_results'] = results
                
                # 결과 표시
                success_count = sum(1 for r in results if r['status'] == 'success')
                st.success(f"✅ {success_count}/{len(results)} 성공")
                
                if success_count > 0:
                    zip_data = create_zip_i2v(results)
                    st.download_button(
                        "📦 전체 다운로드 (ZIP)",
                        zip_data,
                        "videos.zip",
                        "application/zip"
                    )
                
                for r in results:
                    with st.expander(f"{'✅' if r['status']=='success' else '❌'} {r['name']}"):
                        if r['status'] == 'success':
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                st.image(r['preview'], caption="원본", width=150)
                            with col2:
                                st.video(r['url'])
                            st.caption(f"프롬프트: {r.get('prompt', '')}")
                            st.code(r['url'])
                        else:
                            st.error(r.get('error', '알 수 없는 오류'))
