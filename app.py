import streamlit as st
import requests
import time
import base64
import zipfile
import io
import os

st.set_page_config(page_title="LTX-2 일괄 생성기", page_icon="🎬", layout="wide")

st.title("🎬 LTX-2 일괄 영상 생성기")

# API 키
api_key = st.text_input("🔑 Replicate API 키", type="password", placeholder="r8_...")

# 모드 선택
mode = st.radio("모드 선택", ["📝 텍스트 → 영상", "🖼️ 이미지 → 영상"], horizontal=True)

st.markdown("---")

# ==================== 텍스트 → 영상 ====================
if mode == "📝 텍스트 → 영상":
    st.markdown("### 📝 프롬프트 입력")
    st.caption("빈 줄(엔터 두 번)로 프롬프트를 구분하세요")

    prompts_text = st.text_area(
        "프롬프트 목록",
        height=200,
        placeholder="""A cat walking on the street, cinematic,
detailed fur, soft lighting

A dog playing in the park, sunny day,
golden retriever, happy expression""",
        label_visibility="collapsed"
    )

    # 설정
    col1, col2, col3 = st.columns(3)
    with col1:
        width = st.selectbox("가로", [512, 768, 1024, 1280], index=1)
    with col2:
        height = st.selectbox("세로", [512, 576, 720, 768], index=0)
    with col3:
        steps = st.slider("스텝", 4, 20, 8)
    
    frames = st.selectbox("프레임 수", [49, 97, 129], index=1, help="49≈2초, 97≈4초, 129≈5초")

    # 프롬프트 파싱
    def parse_prompts(text):
        chunks = text.strip().split('\n\n')
        prompts = []
        for chunk in chunks:
            prompt = ' '.join(line.strip() for line in chunk.strip().split('\n') if line.strip())
            if prompt:
                prompts.append(prompt)
        return prompts

    # 미리보기
    if prompts_text.strip():
        prompts_preview = parse_prompts(prompts_text)
        st.markdown(f"**📋 인식된 프롬프트: {len(prompts_preview)}개**")
        for i, p in enumerate(prompts_preview):
            st.caption(f"{i+1}. {p[:80]}{'...' if len(p)>80 else ''}")

    # 생성 버튼
    if st.button("🚀 전체 생성 시작", type="primary", use_container_width=True, key="t2v_btn"):
        if not api_key:
            st.error("API 키를 입력하세요")
        elif not prompts_text.strip():
            st.error("프롬프트를 입력하세요")
        else:
            prompts = parse_prompts(prompts_text)
            st.info(f"총 {len(prompts)}개 영상 생성 시작...")
            
            headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
            results = []
            progress = st.progress(0)
            status = st.empty()
            
            for i, prompt in enumerate(prompts):
                status.info(f"⏳ {i+1}/{len(prompts)} 생성 중: {prompt[:50]}...")
                
                resp = requests.post(
                    "https://api.replicate.com/v1/models/lightricks/ltx-2-distilled/predictions",
                    headers=headers,
                    json={"input": {"prompt": prompt, "width": width, "height": height,
                                     "num_frames": frames, "num_inference_steps": steps}}
                )
                
                if resp.status_code not in (200, 201):
                    results.append({"prompt": prompt, "status": "실패", "error": resp.text[:100], "index": i})
                    progress.progress((i+1)/len(prompts))
                    continue
                
                pred_id = resp.json().get("id")
                if not pred_id:
                    results.append({"prompt": prompt, "status": "실패", "error": "ID 없음", "index": i})
                    progress.progress((i+1)/len(prompts))
                    continue
                
                # 폴링
                video_url = None
                for _ in range(120):
                    time.sleep(5)
                    r = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers).json()
                    if r.get("status") == "succeeded":
                        output = r.get("output")
                        video_url = output[0] if isinstance(output, list) else output.get("video", str(output)) if isinstance(output, dict) else str(output)
                        break
                    elif r.get("status") in ("failed", "canceled"):
                        break
                
                if video_url:
                    results.append({"prompt": prompt, "status": "성공", "url": video_url, "index": i})
                else:
                    results.append({"prompt": prompt, "status": "실패", "error": "시간 초과", "index": i})
                
                progress.progress((i+1)/len(prompts))
            
            status.success(f"✅ 완료! 성공: {sum(1 for r in results if r['status']=='성공')}/{len(results)}")
            st.session_state['results'] = results


# ==================== 이미지 → 영상 ====================
else:
    st.markdown("### 🖼️ 이미지 → 영상")
    
    # 이미지 업로드
    uploaded_files = st.file_uploader(
        "이미지 업로드 (여러 개 가능)",
        type=['png', 'jpg', 'jpeg', 'webp'],
        accept_multiple_files=True
    )
    
    # 업로드된 이미지 관리
    if 'i2v_items' not in st.session_state:
        st.session_state['i2v_items'] = []
    
    # 새 파일 업로드 시 목록에 추가
    if uploaded_files:
        for file in uploaded_files:
            existing_names = [item['name'] for item in st.session_state['i2v_items']]
            if file.name not in existing_names:
                file_bytes = file.read()
                b64 = base64.b64encode(file_bytes).decode()
                mime = file.type or "image/png"
                data_uri = f"data:{mime};base64,{b64}"
                
                st.session_state['i2v_items'].append({
                    'name': file.name,
                    'data_uri': data_uri,
                    'prompt': '',
                    'preview': file_bytes
                })
                file.seek(0)
    
    # 목록 초기화 버튼
    if st.session_state['i2v_items']:
        if st.button("🗑️ 목록 초기화", key="clear_i2v"):
            st.session_state['i2v_items'] = []
            st.rerun()
    
    # 프롬프트 입력 방식 토글
    if st.session_state['i2v_items']:
        st.markdown(f"**📋 업로드된 이미지: {len(st.session_state['i2v_items'])}개**")
        
        # 토글: 일괄 입력 vs 개별 입력
        prompt_mode = st.toggle("📝 프롬프트 일괄 입력", value=True, key="prompt_mode")
        
        if prompt_mode:
            # ===== 일괄 입력 모드 =====
            st.caption("빈 줄(엔터 두 번)로 구분하면 순서대로 이미지에 매칭됩니다")
            
            # 기존 프롬프트들을 텍스트로 변환
            existing_prompts = "\n\n".join([item['prompt'] for item in st.session_state['i2v_items'] if item['prompt']])
            
            bulk_prompts = st.text_area(
                "프롬프트 일괄 입력",
                height=200,
                value=existing_prompts,
                placeholder="""camera slowly zooms in, cinematic

character walks forward, smooth motion

gentle pan to the right, soft lighting""",
                label_visibility="collapsed",
                key="bulk_prompts"
            )
            
            # 프롬프트 파싱
            def parse_bulk_prompts(text):
                if not text.strip():
                    return []
                chunks = text.strip().split('\n\n')
                prompts = []
                for chunk in chunks:
                    prompt = ' '.join(line.strip() for line in chunk.strip().split('\n') if line.strip())
                    if prompt:
                        prompts.append(prompt)
                return prompts
            
            parsed = parse_bulk_prompts(bulk_prompts)
            
            # 매칭 미리보기
            st.markdown("#### 🔗 매칭 미리보기")
            
            cols = st.columns(4)
            for i, item in enumerate(st.session_state['i2v_items']):
                with cols[i % 4]:
                    st.image(item['preview'], width=100)
                    matched_prompt = parsed[i] if i < len(parsed) else "(프롬프트 없음)"
                    st.caption(f"**{i+1}.** {matched_prompt[:30]}{'...' if len(matched_prompt)>30 else ''}")
                    # 세션에 저장
                    st.session_state['i2v_items'][i]['prompt'] = parsed[i] if i < len(parsed) else ""
            
            # 개수 안내
            if len(parsed) < len(st.session_state['i2v_items']):
                st.warning(f"⚠️ 프롬프트 {len(parsed)}개 < 이미지 {len(st.session_state['i2v_items'])}개 — 부족한 이미지는 기본 프롬프트 사용")
            elif len(parsed) > len(st.session_state['i2v_items']):
                st.info(f"ℹ️ 프롬프트 {len(parsed)}개 > 이미지 {len(st.session_state['i2v_items'])}개 — 초과 프롬프트는 무시됨")
            else:
                st.success(f"✅ 프롬프트 {len(parsed)}개 = 이미지 {len(st.session_state['i2v_items'])}개 — 완벽 매칭!")
        
        else:
            # ===== 개별 입력 모드 =====
            st.caption("각 이미지에 개별적으로 프롬프트를 입력하세요")
            
            for i, item in enumerate(st.session_state['i2v_items']):
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(item['preview'], width=120, caption=f"{i+1}. {item['name']}")
                    with col2:
                        prompt = st.text_input(
                            f"프롬프트 {i+1}",
                            value=item['prompt'],
                            key=f"prompt_{i}",
                            placeholder="예: camera slowly zooms in, gentle movement"
                        )
                        st.session_state['i2v_items'][i]['prompt'] = prompt
                    st.markdown("---")
    
    # 설정
    st.markdown("#### ⚙️ 설정")
    col1, col2, col3 = st.columns(3)
    with col1:
        i2v_steps = st.slider("스텝", 4, 20, 8, key="i2v_steps")
    with col2:
        i2v_frames = st.selectbox("프레임 수", [49, 97, 129], index=1, 
                                   help="49≈2초, 97≈4초, 129≈5초")
    with col3:
        i2v_resolution = st.selectbox("최대 해상도", 
                                       ["512x512", "768x512", "1024x576", "1280x720"], 
                                       index=1, key="i2v_res",
                                       help="높을수록 비용 증가")

    # 생성 버튼
    if st.button("🚀 이미지→영상 생성 시작", type="primary", use_container_width=True, key="i2v_btn"):
        if not api_key:
            st.error("API 키를 입력하세요")
        elif not st.session_state['i2v_items']:
            st.error("이미지를 업로드하세요")
        else:
            items = st.session_state['i2v_items']
            st.info(f"총 {len(items)}개 영상 생성 시작...")
            
            # 해상도 파싱
            res_w, res_h = map(int, i2v_resolution.split('x'))
            
            headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
            results = []
            progress = st.progress(0)
            status = st.empty()
            
            for i, item in enumerate(items):
                status.info(f"⏳ {i+1}/{len(items)} 생성 중: {item['name']}...")
                
                resp = requests.post(
                    "https://api.replicate.com/v1/models/lightricks/ltx-2-distilled/predictions",
                    headers=headers,
                    json={"input": {
                        "image": item["data_uri"],
                        "prompt": item["prompt"] or "slow gentle camera movement",
                        "num_frames": i2v_frames,
                        "num_inference_steps": i2v_steps,
                        "width": res_w,
                        "height": res_h
                    }}
                )
                
                if resp.status_code not in (200, 201):
                    error_msg = resp.text[:200]
                    results.append({"item": item, "status": "실패", "error": error_msg})
                    progress.progress((i+1)/len(items))
                    continue
                
                pred_id = resp.json().get("id")
                if not pred_id:
                    results.append({"item": item, "status": "실패", "error": "ID 없음"})
                    progress.progress((i+1)/len(items))
                    continue
                
                # 폴링
                video_url = None
                for _ in range(120):
                    time.sleep(5)
                    r = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers).json()
                    
                    if r.get("status") == "succeeded":
                        output = r.get("output")
                        if isinstance(output, list):
                            video_url = output[0]
                        elif isinstance(output, dict):
                            video_url = output.get("video", output.get("url", str(output)))
                        else:
                            video_url = str(output)
                        break
                    elif r.get("status") in ("failed", "canceled"):
                        error = r.get("error", "생성 실패")
                        results.append({"item": item, "status": "실패", "error": str(error)[:100]})
                        break
                
                if video_url:
                    results.append({"item": item, "status": "성공", "url": video_url})
                elif not any(r.get('item', {}).get('name') == item['name'] for r in results if 'item' in r):
                    results.append({"item": item, "status": "실패", "error": "시간 초과"})
                
                progress.progress((i+1)/len(items))
            
            success_count = sum(1 for r in results if r['status'] == '성공')
            status.success(f"✅ 완료! 성공: {success_count}/{len(results)}")
            st.session_state['i2v_results'] = results


# ==================== 일괄 다운로드 함수 ====================
def create_zip_t2v(results):
    """텍스트→영상: 001, 002 순번으로 파일명"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        success_idx = 0
        for r in results:
            if r['status'] == '성공':
                success_idx += 1
                video_url = r['url']
                
                try:
                    video_resp = requests.get(video_url, timeout=60)
                    if video_resp.status_code == 200:
                        filename = f"{success_idx:03d}.mp4"
                        zf.writestr(filename, video_resp.content)
                except Exception as e:
                    st.warning(f"다운로드 실패: {e}")
    
    zip_buffer.seek(0)
    return zip_buffer


def create_zip_i2v(results):
    """이미지→영상: 원본 이미지 파일명과 동일하게"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            if r['status'] == '성공':
                video_url = r['url']
                # 원본 이미지 파일명에서 확장자만 .mp4로 변경
                original_name = r['item']['name']
                name_without_ext = os.path.splitext(original_name)[0]
                filename = f"{name_without_ext}.mp4"
                
                try:
                    video_resp = requests.get(video_url, timeout=60)
                    if video_resp.status_code == 200:
                        zf.writestr(filename, video_resp.content)
                except Exception as e:
                    st.warning(f"다운로드 실패 ({filename}): {e}")
    
    zip_buffer.seek(0)
    return zip_buffer


# ==================== 결과 표시 ====================
st.markdown("---")
st.markdown("### 🎥 생성 결과")

# 텍스트→영상 결과
if 'results' in st.session_state and st.session_state['results']:
    st.markdown("#### 텍스트 → 영상")
    
    success_list = [r for r in st.session_state['results'] if r['status'] == '성공']
    
    if success_list:
        st.markdown(f"**✅ 성공: {len(success_list)}개**")
        
        if st.button("📦 전체 다운로드 (ZIP)", key="download_t2v", type="primary"):
            with st.spinner("ZIP 파일 생성 중..."):
                zip_file = create_zip_t2v(st.session_state['results'])
                st.download_button(
                    label="💾 ZIP 다운로드",
                    data=zip_file,
                    file_name="ltx2_videos.zip",
                    mime="application/zip",
                    key="zip_t2v"
                )
    
    for i, r in enumerate(st.session_state['results']):
        if r['status'] == '성공':
            success_num = sum(1 for x in st.session_state['results'][:i+1] if x['status'] == '성공')
            label = f"✅ {success_num:03d}.mp4 — {r['prompt'][:40]}..."
        else:
            label = f"❌ {r['prompt'][:50]}..."
        
        with st.expander(label, expanded=r['status']=='성공'):
            if r['status'] == '성공':
                st.video(r['url'])
                st.code(r['url'], language=None)
            else:
                st.error(r.get('error', '실패'))

# 이미지→영상 결과
if 'i2v_results' in st.session_state and st.session_state['i2v_results']:
    st.markdown("#### 이미지 → 영상")
    
    success_list = [r for r in st.session_state['i2v_results'] if r['status'] == '성공']
    
    if success_list:
        st.markdown(f"**✅ 성공: {len(success_list)}개**")
        
        if st.button("📦 전체 다운로드 (ZIP)", key="download_i2v", type="primary"):
            with st.spinner("ZIP 파일 생성 중..."):
                zip_file = create_zip_i2v(st.session_state['i2v_results'])
                st.download_button(
                    label="💾 ZIP 다운로드",
                    data=zip_file,
                    file_name="ltx2_i2v_videos.zip",
                    mime="application/zip",
                    key="zip_i2v"
                )
    
    for i, r in enumerate(st.session_state['i2v_results']):
        # 원본 이미지 파일명으로 표시
        original_name = r['item']['name']
        video_name = os.path.splitext(original_name)[0] + ".mp4"
        
        if r['status'] == '성공':
            label = f"✅ {video_name}"
        else:
            label = f"❌ {video_name}"
        
        with st.expander(label, expanded=r['status']=='성공'):
            col1, col2 = st.columns(2)
            with col1:
                st.image(r['item']['preview'], caption=f"원본: {original_name}", width=200)
                st.caption(f"프롬프트: {r['item']['prompt'] or '(없음)'}")
            with col2:
                if r['status'] == '성공':
                    st.caption(f"📁 {video_name}")
                    st.video(r['url'])
                    st.code(r['url'], language=None)
                else:
                    st.error(r.get('error', '실패'))
