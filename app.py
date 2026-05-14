import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation
from PIL import Image, ImageDraw
import math
import io

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection (Restored as seen in image_95b891.png)
st.sidebar.subheader("📍 Scene Location")
loc = get_geolocation()
coords = "N/A"
if loc and 'coords' in loc:
    coords = f"{loc['coords']['latitude']:.6f}, {loc['coords']['longitude']:.6f}"
    st.sidebar.success("✅ GPS Locked")
    st.sidebar.text_input("Coordinates:", value=coords)

# 3. Drawing Controls
st.sidebar.header("Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw"))
color = st.sidebar.color_picker("Line Color", "#FF0000")

uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # Use a unique key based on the filename to reset the canvas for each new photo
    canvas_key = f"canvas_{uploaded_file.name}"
    
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # PC-Specific Scaling: We want it large, but the canvas needs explicit pixels
    # We'll set a standard width of 1000 and calculate the height
    display_width = 1000 
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))

    st.subheader("Sketching Interface")
    
    # IMPORTANT: The background_image MUST be the resized PIL image
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=4,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key=canvas_key,
        display_toolbar=True, # Shows the undo/redo/trash icons seen in your screenshot
        update_streamlit=True,
    )

    # 4. Measurement Logic (Matches your Surveillance Coordinator needs)
    if canvas_result.json_data:
        objects = canvas_result.json_data["objects"]
        if len(objects) > 0:
            # Line 0 = 1.0m Reference Calibration
            cal = objects[0]
            px_dist = math.sqrt(cal.get('width', 0)**2 + cal.get('height', 0)**2)
            ppm = px_dist / 1.0 if px_dist > 0 else 1

            # High-Visibility Report Creation
            report_img = img_resized.copy().convert("RGBA")
            sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
            final_report = Image.alpha_composite(report_img, sketch_layer)
            draw = ImageDraw.Draw(final_report)

            for i, obj in enumerate(objects):
                dx, dy = obj.get('width', 0), obj.get('height', 0)
                length = math.sqrt(dx**2 + dy**2) / ppm
                label = "REF: 1.0m" if i == 0 else f"OBJ {i}: {length:.2f}m"
                
                # Dynamic Label Placement
                lx, ly = obj.get('left', 0), obj.get('top', 0)
                draw.rectangle([lx, ly-30, lx+150, ly], fill="black")
                draw.text((lx+5, ly-25), label, fill="white")
                st.write(f"📏 **{label}**")

            # Final Output
            buf = io.BytesIO()
            final_report.convert("RGB").save(buf, format="PNG")
            st.sidebar.download_button("📥 Download Final Report", data=buf.getvalue(), file_name="forensic_report.png")
else:
    st.info("Please upload a photo to start the forensic sketch.")
