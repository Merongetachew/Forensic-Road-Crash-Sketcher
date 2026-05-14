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
coords = "N/A"
if loc and 'coords' in loc:
    coords = f"{loc['coords']['latitude']:.6f}, {loc['coords']['longitude']:.6f}"
    st.sidebar.success("✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=coords)

# 3. Controls
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Force a unique key for every upload to refresh the background
    canvas_key = f"canvas_{uploaded_file.name}"
    
    # Open and prepare the image
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for PC visibility
    display_width = 1000 
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))

    st.subheader("Sketching Interface")
    
    # CRITICAL FIX: We pass the PIL Image object directly. 
    # If this still shows white, the issue is often a browser cache.
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized, # Passing the PIL object directly
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key=canvas_key,
        display_toolbar=True,
        update_streamlit=True,
    )

    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        if len(objects) > 0:
            # Calibration: Line 0 = 1.0m
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            # High-Visibility Labels (Black Box, White Text)
            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                label = "REF: 1.0m" if i == 0 else f"VEH {i}: {length:.2f}m"
                
                lx, ly = obj.get('left', 0), obj.get('top', 0)
                # Drawing high-contrast label
                draw.rectangle([lx, ly-35, lx+160, ly], fill="black", outline="white")
                draw.text((lx+5, ly-30), label, fill="white")
                st.write(f"📏 **{label}**")

            # GPS Footer
            draw.rectangle([0, display_height-40, display_width, display_height], fill="black")
            draw.text((10, display_height-30), f"LOCATION: {coords}", fill="yellow")

            # Download Option
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            st.sidebar.download_button("📥 Download Forensic Report", data=buf.getvalue(), file_name="forensic_report.png")
else:
    st.info("Upload a photo to begin.")
