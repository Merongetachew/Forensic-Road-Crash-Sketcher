import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw, ImageFont
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection & Copy Functionality (Restored)
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()

lat_val, lon_val = "N/A", "N/A"
coords = "N/A"

if loc and 'coords' in loc:
    lat_val = f"{loc['coords']['latitude']:.6f}"
    lon_val = f"{loc['coords']['longitude']:.6f}"
    coords = f"{lat_val}, {lon_val}"
    st.sidebar.success(f"✅ GPS Locked")
    # Interactive Copy Field
    st.sidebar.text_input("Coordinates:", value=coords, key="coord_box")
    if st.sidebar.button("📋 Click to Copy (Mobile Safe)"):
        st.sidebar.info(f"Copy this: `{coords}`")
else:
    st.sidebar.info("📡 Detecting GPS... Please allow location access.")

# 3. Restored Controls
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for stability
    display_width = 1000 if w > 1000 else w
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))

    # The Sketching Canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key="forensic_canvas_v9",
        update_streamlit=True,
    )

    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        
        if len(objects) > 0:
            # Calibration (Line 0 = 1 meter)
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            # Prepare the Forensic Report Overlay
            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            # Load Large Font for Visibility
            try:
                # Attempt to use a system font for large labels
                label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 25)
            except:
                label_font = ImageFont.load_default()

            st.subheader("Measurements & Forensic Analysis")
            
            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                
                label = f"REF: 1.0m" if i == 0 else f"VEHICLE {i}: {length:.2f}m"
                st.write(f"📏 **{label}**")
                
                # --- DYNAMIC HIGH-VISIBILITY LABELS ---
                left, top = obj.get('left', 0), obj.get('top', 0)
                
                # Get text size
                bbox = draw.textbbox((0, 0), label, font=label_font)
                t_w = bbox[2] - bbox[0]
                t_h = bbox[3] - bbox[1]

                # Clamping logic to keep label inside the image frame
                final_x = max(10, min(left, display_width - t_w - 20))
                final_y = top - 50 if top > 60 else top + 30

                # Draw Thick Black Box with White Border
                draw.rectangle(
                    [final_x - 8, final_y - 5, final_x + t_w + 8, final_y + t_h + 8], 
                    fill="black", outline="white", width=2
                )
                # Draw White Text
                draw.text((final_x, final_y), label, fill="white", font=label_font)

            # --- GPS FOOTER (Restored) ---
            gps_text = f"CRASH LOCATION GPS: {coords}"
            draw.rectangle([0, display_height - 50, display_width, display_height], fill="black")
            draw.text((20, display_height - 35), gps_text, fill="yellow")

            # Final Download Button Logic
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            
            st.sidebar.markdown("---")
            st.sidebar.download_button(
                label="📥 Download Forensic Report", 
                data=buf.getvalue(), 
                file_name=f"crash_report_{lat_val}.png",
                mime="image/png"
            )
else:
    st.info("Please upload a photo from the crash scene to begin drawing measurements.")
