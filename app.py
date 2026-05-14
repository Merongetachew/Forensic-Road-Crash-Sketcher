import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection (Sidebar)
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()
lat_val, lon_val = "N/A", "N/A"

if loc and 'coords' in loc:
    lat_val = f"{loc['coords']['latitude']:.6f}"
    lon_val = f"{loc['coords']['longitude']:.6f}"
    st.sidebar.success(f"✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=f"{lat_val}, {lon_val}")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # --- STEP 1: FAST LOAD & COMPRESS ---
    # We use a smaller size (700px) to ensure it loads on mobile data in the field
    img_raw = Image.open(uploaded_file).convert("RGB")
    display_width = 700 
    display_height = int(img_raw.height * (display_width / img_raw.width))
    img_resized = img_raw.resize((display_width, display_height), Image.Resampling.LANCZOS)

    # --- STEP 2: STABLE CANVAS ---
    # We use a unique key to force a fresh reload of the component
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key="forensic_v14_stable", 
        update_streamlit=True,
    )

    # --- STEP 3: REPORT GENERATION ---
    if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
        objects = canvas_result.json_data["objects"]
        
        # Calibration: First line = 1.0 meter
        cal = objects[0]
        px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
        ppm = px_dist / 1.0 if px_dist > 0 else 1

        # Create the final forensic overlay
        report_img = img_resized.copy().convert("RGBA")
        sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
        final_report = Image.alpha_composite(report_img, sketch_layer)
        draw = ImageDraw.Draw(final_report)

        for i, obj in enumerate(objects):
            dist_px = math.sqrt(obj.get('width', 0)**2 + obj.get('height', 0)**2)
            length = dist_px / ppm
            label = "REF: 1m" if i == 0 else f"V{i}: {length:.2f}m"
            
            x, y = obj.get('left', 0), obj.get('top', 0)
            draw.rectangle([x, y-25, x+80, y], fill="black")
            draw.text((x+5, y-20), label, fill="white")

        # Evidence Footer
        draw.rectangle([0, display_height-40, display_width, display_height], fill="black")
        draw.text((10, display_height-30), f"GPS: {lat_val}, {lon_val} | Oromia Road Safety", fill="yellow")

        # Download Button
        buf = io.BytesIO()
        final_report.convert("RGB").save(buf, format="PNG")
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 Download Report", buf.getvalue(), f"crash_{lat_val}.png")
