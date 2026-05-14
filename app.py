import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw
import math
import io
import base64

# 1. Helper to fix the "White Screen" issue
def get_image_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

# 2. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 3. GPS Detection
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()
coords = "N/A"
if loc and 'coords' in loc:
    coords = f"{loc['coords']['latitude']:.6f}, {loc['coords']['longitude']:.6f}"
    st.sidebar.success("✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=coords)

# 4. Controls
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Unique key ensures refresh on new upload
    canvas_key = f"canvas_{uploaded_file.name}"
    
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for PC
    display_width = 1000 
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))
    
    # CONVERT TO BASE64 (The Fix for image_94e296.png)
    bg_image_data = get_image_base64(img_resized)

    st.subheader("Sketching Interface")
    
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized, # Still provided as fallback
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key=canvas_key,
        display_toolbar=True,
        update_streamlit=True,
    )

    # 5. Report & Measurement Logic
    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        if len(objects) > 0:
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                label = "REF: 1.0m" if i == 0 else f"OBJ {i}: {length:.2f}m"
                
                lx, ly = obj.get('left', 0), obj.get('top', 0)
                draw.rectangle([lx, ly-35, lx+160, ly], fill="black")
                draw.text((lx+5, ly-30), label, fill="white")
                st.write(f"📏 **{label}**")

            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            st.sidebar.download_button("📥 Download Report", data=buf.getvalue(), file_name="forensic_report.png")
else:
    st.info("Upload a photo to begin.")
