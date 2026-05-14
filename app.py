import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw, ImageFont
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection & Copy Button
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()

lat_val, lon_val = "N/A", "N/A"
if loc and 'coords' in loc:
    lat_val = f"{loc['coords']['latitude']:.6f}"
    lon_val = f"{loc['coords']['longitude']:.6f}"
    coords = f"{lat_val}, {lon_val}"
    st.sidebar.success(f"✅ GPS Locked")
    # Copy functionality
    st.sidebar.text_input("Coordinates (Copy below):", value=coords)
    if st.sidebar.button("📋 Click to Copy (Mobile Safe)"):
        st.write(f"Copy this: `{coords}`")
else:
    st.sidebar.info("📡 Detecting GPS... Please allow location access.")

st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for mobile stability
    display_width = 1000 if w > 1000 else w
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key="forensic_canvas_v8",
        update_streamlit=True,
    )

    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        
        if len(objects) > 0:
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            # Build high-resolution report
            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            # --- DYNAMIC EDGE-SAFE LABELS ---
            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                
                label = f"REF: 1.0m" if i == 0 else f"VEHICLE {i}: {length:.2f}m"
                
                # Calculate initial placement
                left, top = obj.get('left', 0), obj.get('top', 0)
                
                # Get text bounding box to calculate width/height of the label
                bbox = draw.textbbox((0, 0), label)
                t_w = bbox[2] - bbox[0]
                t_h = bbox[3] - bbox[1]

                # CLAMPING LOGIC: Keep label inside the frame
                # If too high, move below. If too far right, shift left.
                final_x = max(10, min(left, display_width - t_w - 20))
                final_y = top - 45 if top > 60 else top + 30

                # Draw High-Visibility Box
                draw.rectangle(
                    [final_x - 10, final_y - 5, final_x + t_w + 10, final_y + t_h + 10], 
                    fill="black", outline="white", width=2
                )
                draw.text((final_x, final_y), label, fill="white")

            # GPS & Angle Logic
            gps_text = f"GPS: {lat_val}, {lon_val}"
            draw.rectangle([0, display_height - 50, display_width, display_height], fill="black")
            draw.text((20, display_height - 35), gps_text, fill="yellow")

            # Final download
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            st.sidebar.markdown("---")
            st.sidebar.download_button("📥 Download Report", data=buf.getvalue(), file_name="forensic_report.png")