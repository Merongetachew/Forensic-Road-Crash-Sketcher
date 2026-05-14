import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

# Manual Coordinate Entry
st.sidebar.subheader("📍 Scene Location")
lat_input = st.sidebar.text_input("Latitude:", "")
lon_input = st.sidebar.text_input("Longitude:", "")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # --- IMAGE PRE-PROCESSING ---
    img_raw = Image.open(uploaded_file).convert("RGB")
    
    # Standardize size for mobile/web consistency
    display_width = 800 
    display_height = int(img_raw.height * (display_width / img_raw.width))
    img_resized = img_raw.resize((display_width, display_height), Image.Resampling.LANCZOS)

    # --- THE CANVAS ---
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized, # Passing the PIL object directly
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key="forensic_v17_final", 
        update_streamlit=True,
    )

    # --- REPORT GENERATION ---
    if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
        objects = canvas_result.json_data["objects"]
        
        # Scale: First line = 1.0m
        cal = objects[0]
        px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
        ppm = px_dist / 1.0 if px_dist > 0 else 1

        # Create overlay
        report_img = img_resized.copy().convert("RGBA")
        sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
        final_report = Image.alpha_composite(report_img, sketch_layer)
        draw = ImageDraw.Draw(final_report)

        for i, obj in enumerate(objects):
            length = math.sqrt(obj.get('width', 0)**2 + obj.get('height', 0)**2) / ppm
            label = "REF: 1m" if i == 0 else f"V{i}: {length:.2f}m"
            x, y = obj.get('left', 0), obj.get('top', 0)
            draw.rectangle([x, y-25, x+80, y], fill="black")
            draw.text((x+5, y-20), label, fill="white")

        # Footer
        draw.rectangle([0, display_height-40, display_width, display_height], fill="black")
        footer_text = f"GPS: {lat_input}, {lon_input} | Road Safety Surveillance"
        draw.text((10, display_height-30), footer_text, fill="yellow")

        # Download
        buf = io.BytesIO()
        final_report.convert("RGB").save(buf, format="PNG")
        st.sidebar.download_button("📥 Download Report", buf.getvalue(), "crash_scene.png")
