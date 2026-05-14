import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()
lat_val, lon_val = "N/A", "N/A"
coords = "N/A"

if loc and 'coords' in loc:
    lat_val = f"{loc['coords']['latitude']:.6f}"
    lon_val = f"{loc['coords']['longitude']:.6f}"
    coords = f"{lat_val}, {lon_val}"
    st.sidebar.success(f"✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=coords)
else:
    st.sidebar.info("📡 Detecting GPS... Please allow location access.")

# 3. Controls
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Use the filename as part of the key to force refresh on new upload
    canvas_key = f"canvas_{uploaded_file.name}"
    
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for PC display (Maintains 1000px width for clarity)
    display_width = 1000 if w > 1000 else w
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))

    st.subheader("Sketching Interface")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key=canvas_key,  # Dynamic Key Fix
        update_streamlit=True,
    )

    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        
        if len(objects) > 0:
            # Line 0 is 1.0m Reference
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            st.write("### Scene Measurements")
            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                label = f"REF: 1.0m" if i == 0 else f"OBJ {i}: {length:.2f}m"
                
                # Labeling Logic
                left, top = obj.get('left', 0), obj.get('top', 0)
                bbox = draw.textbbox((0, 0), label)
                t_w, t_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                
                final_x = max(10, min(left, display_width - t_w - 20))
                final_y = top - 45 if top > 60 else top + 30

                draw.rectangle([final_x-5, final_y-5, final_x+t_w+5, final_y+t_h+5], fill="black", outline="white")
                draw.text((final_x, final_y), label, fill="white")
                st.info(f"📏 {label}")

            # GPS Footer
            draw.rectangle([0, display_height-40, display_width, display_height], fill="black")
            draw.text((10, display_height-30), f"GPS: {coords}", fill="yellow")

            # Download
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            st.sidebar.markdown("---")
            st.sidebar.download_button("📥 Download Report", data=buf.getvalue(), file_name="forensic_report.png")
else:
    st.info("Please upload a photo to begin.")
