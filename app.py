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
    coords = f"{lat_val}, {lon_val}"
    st.sidebar.success(f"✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=coords)
else:
    st.sidebar.info("📡 Detecting GPS... Please allow location access.")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # --- OPTIMIZATION: Fast loading and resizing ---
    img_raw = Image.open(uploaded_file).convert("RGB")
    orig_w, orig_h = img_raw.size
    
    # Scale down for speed (Max width 1000px)
    display_width = 1000 if orig_w > 1000 else orig_w
    display_height = int(orig_h * (display_width / orig_w))
    img_resized = img_raw.resize((display_width, display_height), Image.Resampling.LANCZOS)

    # 3. Drawing Canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key="forensic_canvas_v9", # Updated key to clear old cache
        update_streamlit=True,
    )

    # 4. Report Generation Logic
    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        
        if len(objects) > 0:
            # Scale reference (Assume first line is 1.0 meter)
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            # Prepare layers
            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            # Draw Labels
            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                
                label = f"REF: 1.0m" if i == 0 else f"V{i}: {length:.2f}m"
                
                left, top = obj.get('left', 0), obj.get('top', 0)
                bbox = draw.textbbox((0, 0), label)
                t_w, t_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

                # Keep text within image boundaries
                final_x = max(10, min(left, display_width - t_w - 20))
                final_y = top - 45 if top > 60 else top + 30

                # High-visibility background for text
                draw.rectangle(
                    [final_x - 5, final_y - 5, final_x + t_w + 5, final_y + t_h + 5], 
                    fill="black", outline="white"
                )
                draw.text((final_x, final_y), label, fill="white")

            # GPS Footer
            footer_h = 50
            gps_text = f"GPS: {lat_val}, {lon_val} | Forensic Road Surveillance"
            draw.rectangle([0, display_height - footer_h, display_width, display_height], fill="black")
            draw.text((20, display_height - 35), gps_text, fill="yellow")

            # Download Section
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG", optimize=True) # Optimized PNG
            st.sidebar.markdown("---")
            st.sidebar.download_button(
                label="📥 Download Forensic Report",
                data=buf.getvalue(),
                file_name=f"crash_report_{lat_val}.png",
                mime="image/png"
            )
