import streamlit as st
from google import genai
import tempfile
import time
import os
from PIL import Image
import edge_tts
import asyncio

# ===== KHỞI TẠO SESSION STATE (LƯU LỊCH SỬ) =====
if 'history' not in st.session_state:
    st.session_state['history'] = []

# ===== CONFIG GIAO DIỆN =====
st.set_page_config(page_title="AI Content V3", page_icon="🎬", layout="wide")

st.title("🎬 AI Content V3")
st.write("Dự án của Nam - Up file, chọn chế độ và để AI lo phần 'cháy' nhất!")

# ===== NHÚNG CỨNG API KEY =====
api_key = "AIzaSyAjKwP1gIKRWDAHj-X1UfJFd1ExQPzPEw8"

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Lỗi khởi tạo Client: {e}")
    st.stop()

# ==========================================
# SIDEBAR: QUÉT MODEL & LỊCH SỬ
# ==========================================
with st.sidebar:
    st.write("---")
    st.write("🛠️ **Cấu hình AI**")
    try:
        danh_sach_model = []
        for m in client.models.list():
            if "gemini" in m.name and "flash" in m.name and "8b" not in m.name:
                ten_sach = m.name.replace("models/", "")
                danh_sach_model.append(ten_sach)
        
        if not danh_sach_model:
            st.error("API Key này không có model Flash nào khả dụng!")
            st.stop()
            
        mac_dinh = 0
        for i, ten in enumerate(danh_sach_model):
            if "gemini-1.5-flash" == ten:
                mac_dinh = i
                break
                
        selected_model = st.selectbox("🤖 Chọn con AI để chạy:", danh_sach_model, index=mac_dinh)
        st.success(f"Đã kết nối với {selected_model}")
        
    except Exception as e:
        st.error(f"Lỗi lấy danh sách model: {e}")
        st.stop()
    
    st.write("---")
    st.subheader("📚 Lịch sử sáng tạo")
    if st.session_state['history']:
        history_export_text = ""
        for idx, item in enumerate(st.session_state['history']):
            with st.expander(f"[{item['time']}] {item['type']} - {item['platform']}"):
                st.markdown(item['result'])
            history_export_text += f"[{item['time']}] {item['type']} - Nền tảng: {item['platform']}\n{item['result']}\n\n{'='*40}\n\n"
            
        st.download_button(
            label="⬇️ Tải toàn bộ Lịch sử (TXT)",
            data=history_export_text,
            file_name="Lich_Su_Content_AI.txt",
            mime="text/plain",
            use_container_width=True
        )
        if st.button("🗑️ Xóa lịch sử", use_container_width=True):
            st.session_state['history'] = []
            st.rerun()
    else:
        st.info("Chưa có nội dung nào được tạo.")

# ==========================================
# ===== CHỌN TÍNH NĂNG CHÍNH =====
media_type = st.radio("⚡ Bạn muốn làm gì?", ["Video", "Hình Ảnh", "🎙️ Tạo File Lồng Tiếng"], horizontal=True)

# ==========================================
# 1. GIAO DIỆN XỬ LÝ VIDEO
# ==========================================
if media_type == "Video":
    st.subheader("🎥 Phòng Lab Video")
    col1, col2 = st.columns([1, 1])

    with col1:
        platform = st.selectbox("📱 Chọn nền tảng đăng:", ["TikTok", "YouTube Shorts", "Facebook Reels"])
        user_video_context = st.text_area(
            "📝 Mô tả thêm video (VD: đi du lịch Mũi Né, review son...):",
            placeholder="Giúp AI lồng tiếng chuẩn hơn...",
            height=100
        )
        uploaded_video = st.file_uploader("📤 Upload Video (MP4, MOV...)", type=['mp4', 'mov', 'avi'])

    with col2:
        if uploaded_video is not None:
            st.video(uploaded_video)
            c1, c2, c3 = st.columns(3)
            with c1:
                gen_caption_btn = st.button(f"🚀 Gen Caption & Hashtag", use_container_width=True)
            with c2:
                viral_btn = st.button(f"💯 Quét Độ Viral", use_container_width=True)
            with c3:
                vo_btn = st.button(f"📝 Viết VO Script", use_container_width=True)

    if uploaded_video is not None and (gen_caption_btn or viral_btn or vo_btn):
        with st.spinner("🤖 AI đang 'xem' video... (Vui lòng đợi vài chục giây)"):
            video_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    temp_video.write(uploaded_video.read())
                    video_path = temp_video.name

                st.info("Đang tải video lên server Google...")
                video_file = client.files.upload(file=video_path)
                
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = client.files.get(name=video_file.name)
                
                if video_file.state.name == "FAILED":
                    st.error("❌ Lỗi khi AI xử lý video.")
                    st.stop()

                analysis_type = ""
                if gen_caption_btn:
                    analysis_type = "Gen Caption Video"
                    prompt = f"""
                    Bạn là Content Creator hệ GenZ, viral top đầu TikTok/Reels.
                    Xem video này và viết caption cực cuốn cho {platform}. Ngữ cảnh: "{user_video_context}"
                    TUYỆT ĐỐI TUÂN THỦ: 1. KHÔNG chào hỏi, KHÔNG giải thích. 2. Chỉ 1-2 câu ngắn, cuốn, có emoji.
                    TRẢ VỀ ĐÚNG FORMAT: 🎯 CHỦ ĐỀ \n ✍️ CAPTION GỢI Ý \n 🏷️ HASHTAG TRENDING
                    """
                elif viral_btn:
                    analysis_type = "Quét Độ Viral Video"
                    prompt = f"""
                    Hôm nay, bạn là một 'Chuyên gia soi' độ viral của video trên TikTok/Reels.
                    Xem kỹ video này và viết báo cáo. Ngữ cảnh: "{user_video_context}"
                    TRẢ VỀ ĐÚNG FORMAT: 💯 ĐIỂM SỐ VIRAL: (0-100) \n ✨ ĐIỂM Visual \n 🚀 Điểm Nhịp Độ \n 💡 TIP ĐỂ LÊN XU HƯỚNG
                    """
                elif vo_btn:
                    analysis_type = "Viết Kịch Bản Lồng Tiếng"
                    prompt = f"""
                    Bạn là nhà biên kịch script viral cho TikTok/Reels.
                    Viết một kịch bản lồng tiếng (Voiceover Script) phù hợp nhất theo vibe của video. Ngữ cảnh: "{user_video_context}".
                    TRẢ VỀ ĐÚNG FORMAT: 🎙️ KỊCH BẢN LỒNG TIẾNG (Chỉ ghi ra lời thoại, không ghi giây, để người dùng dễ copy làm Audio) \n 🏷️ SUGGESTION ÂM THANH
                    """

                st.info(f"AI đang tiến hành: {analysis_type}...")
                response = client.models.generate_content(model=selected_model, contents=[video_file, prompt])

                st.divider()
                st.subheader(f"💡 Kết quả: {analysis_type}")
                st.markdown(response.text)

                st.session_state['history'].insert(0, {
                    "time": time.strftime("%H:%M"), "type": analysis_type, "platform": platform, "result": response.text
                })
                st.rerun()

                client.files.delete(name=video_file.name)

            except Exception as e:
                if "429" in str(e) or "503" in str(e):
                    st.error(f"⏳ Hệ thống AI báo bận. Chọn MODEL KHÁC ở menu bên trái nhé!")
                else:
                    st.error(f"❌ Có lỗi: {e}")
            finally:
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)

# ==========================================
# 2. GIAO DIỆN XỬ LÝ HÌNH ẢNH
# ==========================================
elif media_type == "Hình Ảnh":
    st.subheader("🖼️ Phòng Lab Hình Ảnh")
    col1, col2 = st.columns([1, 1])

    with col1:
        platform_img = st.selectbox("📱 Chọn nền tảng đăng ảnh:", ["Instagram Post", "Facebook Post", "TikTok (dạng ảnh)", "Zalo"])
        caption_style = st.selectbox("✍️ Chọn phong cách caption:", ["Thả thính", "Ngầu nhẹ", "Hài nhây", "Tâm trạng", "Động lực cuộc sống", "Review", "🔥 Roast Cà Khịa (Toxic Friends)"])
        mo_ta_anh_tay = st.text_area("📝 Mô tả thêm ảnh:", placeholder="Giúp AI viết caption sát với ngữ cảnh thật nhất...", height=100)
        uploaded_img = st.file_uploader("📤 Upload Hình Ảnh (JPG, PNG...)", type=['jpg', 'jpeg', 'png'])

    with col2:
        if uploaded_img is not None:
            image = Image.open(uploaded_img)
            st.image(image, caption="Ảnh đã tải lên", use_container_width=True)
            cImg1, cImg2, cImg3 = st.columns(3)
            with cImg1:
                gen_img_btn = st.button(f"🚀 Gen Caption", use_container_width=True)
            with cImg2:
                viral_img_btn = st.button(f"💯 Quét Độ Viral", use_container_width=True)
            with cImg3:
                script_img_btn = st.button(f"🪄 Kịch Bản TikTok", use_container_width=True)

    if uploaded_img is not None and (gen_img_btn or viral_img_btn or script_img_btn):
        with st.spinner("🤖 AI đang 'nhìn' ảnh..."):
            try:
                analysis_img_type = ""
                if gen_img_btn:
                    analysis_img_type = "Gen Caption Hình Ảnh"
                    if caption_style == "🔥 Roast Cà Khịa (Toxic Friends)":
                        prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Đóng vai bạn thân toxic, soi lỗi bức ảnh này và viết caption dìm hàng cực mạnh, hài hước. Không khen."
                    else:
                        prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Viết caption style {caption_style} cho nền tảng {platform_img}. Cực ngắn gọn, 1-2 câu, không hashtag."
                elif viral_img_btn:
                    analysis_img_type = "Quét Độ Viral Hình Ảnh"
                    prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Đánh giá độ viral của ảnh này. Nhận xét visual, ánh sáng và tip chỉnh sửa."
                elif script_img_btn:
                    analysis_img_type = "Biến ảnh thành Kịch Bản Video"
                    prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Chế bức ảnh tĩnh này thành 1 kịch bản video ngắn TikTok viral. Mô tả góc quay tưởng tượng, thoại và nhạc nền."

                st.info(f"AI đang tiến hành: {analysis_img_type}...")
                response_img = client.models.generate_content(model=selected_model, contents=[image, prompt_img])

                st.divider()
                st.subheader(f"💡 Kết quả: {analysis_img_type}")
                st.markdown(response_img.text)

                st.session_state['history'].insert(0, {
                    "time": time.strftime("%H:%M"), "type": analysis_img_type, "platform": platform_img, "result": response_img.text
                })
                st.rerun()

            except Exception as e:
                if "429" in str(e) or "503" in str(e):
                    st.error(f"⏳ AI đang bận. Chọn model khác ở menu trái nhé!")
                else:
                    st.error(f"❌ Có lỗi: {e}")

# ==========================================
# 3. GIAO DIỆN TẠO AUDIO (EDGE TTS NHƯ NGƯỜI THẬT)
# ==========================================
else:
    st.subheader("🎙️ Studio Lồng Tiếng (AI Voice Người Thật)")
    st.write("Sử dụng công nghệ Neural TTS siêu thực. Chuyên dùng cho lồng tiếng TikTok/Reels!")
    
    # Từ điển giọng đọc chuẩn
    voice_options = {
        "👩 Nữ miền Nam (Hoài My - Ấm áp, tự nhiên)": "vi-VN-HoaiMyNeural",
        "👨 Nam miền Bắc (Nam Minh - Trầm ấm, chuyên nghiệp)": "vi-VN-NamMinhNeural"
    }
    
    selected_voice_name = st.selectbox("🎭 Chọn Giọng đọc:", list(voice_options.keys()))
    
    vo_text = st.text_area(
        "📝 Nhập nội dung cần lồng tiếng:", 
        height=200, 
        placeholder="Ví dụ: Xin chào mọi người, hôm nay mình sẽ dẫn các bạn đi ăn thử quán ruột của mình..."
    )
    
    # Hàm chạy bất đồng bộ cho edge-tts
    async def generate_audio(text, voice, filename):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)

    if st.button("🎧 Tạo File Lồng Tiếng (MP3)"):
        if not vo_text.strip():
            st.warning("Vui lòng nhập nội dung cần đọc!")
        else:
            with st.spinner("🎤 Đang thu âm tại Studio AI..."):
                try:
                    audio_file_path = "voiceover_ai_pro.mp3"
                    selected_voice_code = voice_options[selected_voice_name]
                    
                    # Gọi hàm tạo audio
                    asyncio.run(generate_audio(vo_text, selected_voice_code, audio_file_path))
                    
                    st.success("Tạo file âm thanh thành công! Giọng siêu tự nhiên nhé.")
                    
                    # Phát nhạc trên web
                    st.audio(audio_file_path, format="audio/mp3")
                    
                    # Nút tải file
                    with open(audio_file_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Tải Audio này về máy (MP3)",
                            data=file,
                            file_name="AI_Voiceover_Pro.mp3",
                            mime="audio/mp3"
                        )
                except Exception as e:
                    st.error(f"Lỗi khi tạo Audio: {e}")