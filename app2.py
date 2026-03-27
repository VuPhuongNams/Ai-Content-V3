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
st.set_page_config(page_title="AI Content V3", page_icon="🎬", layout="centered")

st.title("🎬 AI Content V3")
st.write("Dự án của Nam - Up file, chọn chế độ và để AI lo phần 'cháy' nhất!")

# ===== LẤY API KEY TỪ SECRETS CỦA STREAMLIT =====
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    # Gán cứng model để tăng tốc độ load web (không cần quét nữa)
    selected_model = "gemini-1.5-flash" 
except Exception as e:
    st.error(f"⚠️ Lỗi hệ thống: Chưa cấu hình API Key trong Secrets. Chi tiết: {e}")
    st.stop()

# ==========================================
# SIDEBAR: QUÉT MODEL & LỊCH SỬ
# ==========================================
with st.sidebar:
    st.header("📚 Lịch sử sáng tạo")
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
# TỪ ĐIỂN PROMPT CHUNG CHO CẢ ẢNH & VIDEO
# ==========================================
danh_sach_phong_cach = [
    "💘 Thả thính tinh tế", "🥀 Tâm trạng deep", "🌿 Chill nhẹ nhàng", "🖤 Lạnh lùng ít nói",
    "😎 Ngầu thật sự", "💸 Flex nhẹ", "👑 Tự tin bản thân", "🔥 Năng lượng cao",
    "😂 Hài mặn", "🤡 Tự dìm bản thân", "🧠 Cà khịa thông minh", "📈 Bắt trend mạng xã hội",
    "🧾 Review ngắn gọn", "📌 Caption kể chuyện", "🎯 Kêu gọi tương tác (CTA)", "📖 Quote ý nghĩa"
]

prompt_dictionary = {
    "💘 Thả thính tinh tế": "Đóng vai một người dùng mạng xã hội gen Z sành điệu. Viết caption thả thính ngầm, mập mờ, chơi chữ thông minh, tuyệt đối không sến súa, khiến crush đọc xong phải suy nghĩ.",
    "🥀 Tâm trạng deep": "Đóng vai người mang nhiều tâm sự. Viết vài câu mang vibe buồn man mác, suy tư về cuộc sống/tình yêu, cảm giác cô đơn giữa phố thị ồn ào.",
    "🌿 Chill nhẹ nhàng": "Viết caption mang lại cảm giác bình yên, chữa lành (healing), yêu đời, tận hưởng những điều giản dị trong cuộc sống.",
    "🖤 Lạnh lùng ít nói": "Viết caption CỰC KỲ NGẮN (tối đa 5 chữ). Chỉ dùng 1 emoji màu tối. Toát lên vẻ bí ẩn, bất cần, không quan tâm sự đời.",
    "😎 Ngầu thật sự": "Vibe tự tin, dân chơi, chất lừ. Ngôn từ mạnh mẽ, dứt khoát, mang phong cách đường phố (streetwear).",
    "💸 Flex nhẹ": "Đóng vai người thích khoe khoang một cách khiêm tốn (humble brag). Khoe vật chất/thành tích nhưng văn phong giả vờ than thở hoặc vô tình nhắc tới.",
    "👑 Tự tin bản thân": "Khẳng định giá trị độc bản của bản thân (Self-love). Độc lập, kiêu hãnh nhưng không phản cảm.",
    "🔥 Năng lượng cao": "Dùng ngôn ngữ truyền động lực, nhiệt huyết bùng cháy, cổ vũ mọi người nỗ lực làm việc và tiến lên.",
    "😂 Hài mặn": "Dùng ngôn ngữ Gen Z lầy lội, content 'vô tri' nhưng buồn cười, có thể dùng phép cường điệu.",
    "🤡 Tự dìm bản thân": "Tự lôi điểm xấu, sự xui xẻo hoặc nghèo rớt mồng tơi của mình ra làm trò đùa. Văn phong gây cười, dễ đồng cảm.",
    "🧠 Cà khịa thông minh": "Đóng vai đứa bạn thân toxic. Soi lỗi bức ảnh/video, dìm hàng người trong đó bằng những câu châm biếm sâu cay, hài hước nhưng mang tính trêu chọc bạn bè.",
    "📈 Bắt trend mạng xã hội": "Sử dụng những ngôn ngữ lóng, cú pháp đang viral nhất trên TikTok/Facebook Việt Nam hiện tại.",
    "🧾 Review ngắn gọn": "Viết theo format đánh giá nhanh: Chấm điểm (.../10), 1 dòng khen, 1 dòng chê, chốt lại có nên thử không.",
    "📌 Caption kể chuyện": "Mở đầu bằng cụm từ 'Chuyện là...'. Viết một mẩu chuyện cực kỳ ngắn (3-4 dòng), hài hước hoặc lôi cuốn liên quan đến nội dung ảnh/video.",
    "🎯 Kêu gọi tương tác (CTA)": "Viết caption dưới dạng câu hỏi mở, đưa ra một nhận định gây tranh cãi nhẹ hoặc thách đố để ép người xem phải để lại bình luận.",
    "📖 Quote ý nghĩa": "Đóng vai một nhà văn. Trích dẫn hoặc tự viết một câu nói mang tính triết lý, có vần điệu, sâu sắc về nhân sinh quan."
}

# ==========================================
# ===== CHỌN TÍNH NĂNG CHÍNH =====
# ==========================================
st.write("---")
media_type = st.radio("⚡ Bạn muốn làm gì?", ["Video", "Hình Ảnh", "🎙️ Tạo File Lồng Tiếng"], horizontal=True)

# ==========================================
# 1. GIAO DIỆN XỬ LÝ VIDEO
# ==========================================
if media_type == "Video":
    st.subheader("🎥 Phòng Lab Video")
    
    colA, colB = st.columns(2)
    with colA:
        platform = st.selectbox("📱 Chọn nền tảng đăng:", ["TikTok", "YouTube Shorts", "Facebook Reels"])
    with colB:
        caption_style_vid = st.selectbox("✍️ Phong cách Caption:", danh_sach_phong_cach)

    user_video_context = st.text_area(
        "📝 Mô tả thêm video (VD: đi du lịch Mũi Né, review son...):",
        placeholder="Giúp AI lồng tiếng chuẩn hơn...",
        height=70
    )
    
    uploaded_video = st.file_uploader("📤 Upload Video (MP4, MOV...)", type=['mp4', 'mov', 'avi'])

    if uploaded_video is not None:
        st.video(uploaded_video)
        st.success("✅ Đã tải video lên thành công! Hãy chọn thao tác bên dưới:")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            gen_caption_btn = st.button(f"🚀 Gen Caption & Hashtag", use_container_width=True)
        with c2:
            viral_btn = st.button(f"💯 Quét Độ Viral", use_container_width=True)
        with c3:
            vo_btn = st.button(f"📝 Viết VO Script", use_container_width=True)

        if gen_caption_btn or viral_btn or vo_btn:
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
                        analysis_type = caption_style_vid
                        vai_dien = prompt_dictionary.get(caption_style_vid, "Viết caption bình thường.")
                        prompt = f"""
                        Nhiệm vụ: Phân tích video này và viết 3 mẫu caption khác nhau để đăng lên {platform}.
                        THÔNG TIN BỔ SUNG: Ngữ cảnh: "{user_video_context}"
                        CHỈ THỊ NHẬP VAI BẮT BUỘC: {vai_dien}
                        QUY TẮC ĐẦU RA (NGHIÊM CẤM LÀM SAI):
                        1. Không dông dài giải thích. 2. Ngôn ngữ phải tự nhiên 100% như người thật.
                        3. In ra trực tiếp 3 kết quả đánh số 1️⃣ 2️⃣ 3️⃣. Cuối cùng kèm 1 dòng Hashtag.
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

                    st.info(f"AI đang phân tích: {analysis_type}...")
                    response = client.models.generate_content(model=selected_model, contents=[video_file, prompt])

                    st.divider()
                    st.subheader(f"💡 Kết quả: {analysis_type}")
                    st.markdown(response.text)
                    st.balloons()

                    # LƯU LỊCH SỬ & LÀM MỚI TRANG
                    st.session_state['history'].insert(0, {
                        "time": time.strftime("%H:%M"), "type": f"Video: {analysis_type}", "platform": platform, "result": response.text
                    })
                    
                    client.files.delete(name=video_file.name)
                    st.rerun() # <-- Đã fix lỗi thiếu làm mới trang

                except Exception as e:
                    if "429" in str(e) or "503" in str(e):
                        st.error(f"⏳ Hệ thống AI báo bận. Vui lòng thử lại sau vài giây!")
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
    
    colA, colB = st.columns(2)
    with colA:
        platform_img = st.selectbox("📱 Nền tảng:", ["Instagram", "Facebook", "TikTok", "Threads", "Zalo"])
    with colB:
        caption_style = st.selectbox("✍️ Phong cách:", danh_sach_phong_cach)
    
    mo_ta_anh_tay = st.text_area("📝 Mô tả thêm ảnh:", placeholder="VD: đi cafe cuối tuần, mới thất tình, đi ăn sinh nhật...", height=70)
    
    uploaded_img = st.file_uploader("📤 Upload Hình Ảnh (JPG, PNG...)", type=['jpg', 'jpeg', 'png'])

    if uploaded_img is not None:
        image = Image.open(uploaded_img)
        st.image(image, caption="Ảnh đã tải lên", use_container_width=True)
        st.success("✅ Đã tải ảnh lên! Chọn tính năng để AI phân tích:")
        
        cImg1, cImg2, cImg3 = st.columns(3)
        with cImg1:
            gen_img_btn = st.button(f"🚀 Gen Caption", use_container_width=True)
        with cImg2:
            viral_img_btn = st.button(f"💯 Quét Viral", use_container_width=True)
        with cImg3:
            script_img_btn = st.button(f"🪄 Viết Kịch Bản", use_container_width=True)

        if gen_img_btn or viral_img_btn or script_img_btn:
            with st.spinner("🤖 AI đang 'nhập vai' và phân tích ảnh..."):
                try:
                    analysis_img_type = ""
                    
                    if gen_img_btn:
                        analysis_img_type = caption_style
                        vai_dien = prompt_dictionary.get(caption_style, "Viết caption bình thường.")
                        
                        prompt_img = f"""
                        Nhiệm vụ: Phân tích bức ảnh này và viết 3 mẫu caption khác nhau để đăng lên nền tảng {platform_img}.
                        THÔNG TIN BỔ SUNG: Ngữ cảnh: "{mo_ta_anh_tay}"
                        CHỈ THỊ NHẬP VAI BẮT BUỘC: {vai_dien}
                        QUY TẮC ĐẦU RA (NGHIÊM CẤM LÀM SAI):
                        1. Không dông dài giải thích. 2. Ngôn ngữ tự nhiên 100%. 3. In ra trực tiếp 3 kết quả (1️⃣ 2️⃣ 3️⃣).
                        """
                    elif viral_img_btn:
                        analysis_img_type = "Quét Độ Viral Hình Ảnh"
                        prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Đánh giá góc độ thẩm mỹ và khả năng viral của ảnh này trên mạng xã hội. Trả về format: 💯 Điểm Viral (0-100) | ✨ Ưu điểm visual | 💡 Điểm trừ & Mẹo chỉnh sửa."
                    elif script_img_btn:
                        analysis_img_type = "Biến ảnh thành Kịch Bản Video"
                        prompt_img = f"Ngữ cảnh: {mo_ta_anh_tay}. Hãy chế bức ảnh tĩnh này thành 1 kịch bản video ngắn TikTok siêu cuốn. Chia rõ luồng: [Giây 0-3]: ... | [Giây 3-7]: ... Kèm theo gợi ý nhạc trending."

                    st.info(f"AI đang thực thi: {analysis_img_type}...")
                    response_img = client.models.generate_content(model=selected_model, contents=[image, prompt_img])

                    st.divider()
                    st.subheader(f"💡 Kết quả: {analysis_img_type}")
                    st.markdown(response_img.text)
                    st.balloons()

                    # LƯU LỊCH SỬ & LÀM MỚI TRANG
                    st.session_state['history'].insert(0, {
                        "time": time.strftime("%H:%M"), "type": f"Ảnh: {analysis_img_type}", "platform": platform_img, "result": response_img.text
                    })
                    st.rerun() # <-- Đã fix lỗi thiếu làm mới trang

                except Exception as e:
                    if "429" in str(e) or "503" in str(e):
                        st.error(f"⏳ AI đang bận. Vui lòng thử lại sau vài giây!")
                    else:
                        st.error(f"❌ Có lỗi: {e}")

# ==========================================
# 3. GIAO DIỆN TẠO AUDIO 
# ==========================================
else:
    st.subheader("🎙️ Studio Lồng Tiếng (AI Voice Người Thật)")
    st.write("Sử dụng công nghệ Neural TTS siêu thực. Chuyên dùng cho lồng tiếng TikTok/Reels!")
    
    voice_options = {
        "👩 Nữ miền Nam (Hoài My - Ấm áp)": "vi-VN-HoaiMyNeural",
        "👨 Nam miền Bắc (Nam Minh - Trầm ấm)": "vi-VN-NamMinhNeural"
    }
    
    selected_voice_name = st.selectbox("🎭 Chọn Giọng đọc:", list(voice_options.keys()))
    
    vo_text = st.text_area(
        "📝 Nhập nội dung cần lồng tiếng:", 
        height=200, 
        placeholder="Ví dụ: Xin chào mọi người, hôm nay mình sẽ dẫn các bạn đi..."
    )
    
    async def generate_audio(text, voice, filename):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)

    if st.button("🎧 Tạo File MP3", use_container_width=True):
        if not vo_text.strip():
            st.warning("Vui lòng nhập nội dung cần đọc!")
        else:
            with st.spinner("🎤 Đang thu âm..."):
                try:
                    audio_file_path = "voiceover_ai_pro.mp3"
                    selected_voice_code = voice_options[selected_voice_name]
                    
                    asyncio.run(generate_audio(vo_text, selected_voice_code, audio_file_path))
                    
                    st.success("🎉 Tạo file âm thanh thành công!")
                    st.audio(audio_file_path, format="audio/mp3")
                    st.balloons()
                    
                    with open(audio_file_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Tải Audio (MP3)",
                            data=file,
                            file_name="AI_Voiceover_Pro.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Lỗi khi tạo Audio: {e}")