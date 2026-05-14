import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import math
import io
import base64

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# Initialize session state for the image if it doesn't exist
if 'bg_image' not in st.session_state:
    st.session_state.bg_image = None

# 2. Controls & Upload
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Load image once and store in session state
    img = Image.open(uploaded_file).convert("RGB")
    
    # Standardize dimensions for PC display
    max_width = 1000
    w, h = img.size
    display_width = max_width if w > max_width else w
    display_height = int(h * (display_width / w))
    
    st.session_state.bg_image = img.resize((display_width, display_height))
    
    # Use a unique key that changes with the file to force a fresh render
    canvas_key = f"canvas_{uploaded_file.name}"

    st.subheader("Sketching Interface")
    
    # THE CRITICAL STEP: Only call st_canvas if we have an image in state
    if st.session_state.bg_image is not None:
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=4,
            stroke_color=color,
            background_image=st.session_state.bg_image,
            height=display_height,
            width=display_width,
            drawing_mode=mode,
            key=canvas_key,
            update_streamlit=True,
            display_toolbar=True,
        )

        # 3. Measurement Logic
        if canvas_result.json_data:
            objects = canvas_result.json_data["objects"]
            if len(objects) > 0:
                cal = objects[0]
                px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
                ppm = px_dist / 1.0 if px_dist > 0 else 1

                # Generate high-visibility report overlay
                report_img = st.session_state.bg_image.copy().convert("RGBA")
                sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
                final_report = Image.alpha_composite(report_img, sketch_layer)
                draw = ImageDraw.Draw(final_report)

                for i, obj in enumerate(objects):
                    dx, dy = obj.get('width', 0), obj.get('height', 0)
                    length = math.sqrt(dx**2 + dy**2) / ppm
                    label = "REF: 1.0m" if i == 0 else f"OBJ {i}: {length:.2f}m"
                    
                    lx, ly = obj.get('left', 0), obj.get('top', 0)
                    draw.rectangle([lx, ly-35, lx+160, ly], fill="black", outline="white")
                    draw.text((lx+5, ly-30), label, fill="white")
                    st.write(f"📏 **{label}**")

                # Export logic
                buf = io.BytesIO()
                final_report.convert("RGB").save(buf, format="PNG")
                st.sidebar.download_button("📥 Download Report", data=buf.getvalue(), file_name="forensic_report.png")
else:
    st.info("Upload a photo to begin.")
