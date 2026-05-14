import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont
import math
import io
import numpy as np
import datetime as dt
import pandas as pd

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Input (Manual - avoids browser permission issues on cloud)
st.sidebar.subheader("📍 Scene Location")

col1, col2 = st.sidebar.columns(2)
with col1:
    lat_input = st.text_input("Latitude", "0.000000")
with col2:
    lon_input = st.text_input("Longitude", "0.000000")

lat_val, lon_val = lat_input, lon_input

st.sidebar.header("🎨 Drawing Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw", "rect", "circle"))
color = st.sidebar.color_picker("Line Color", "#FF0000")
stroke_width = st.sidebar.slider("Stroke Width", 1, 10, 4)

st.sidebar.header("📸 Scene Photo")
uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png", "bmp"])

# Initialize session state for canvas
if 'canvas_key' not in st.session_state:
    st.session_state.canvas_key = "forensic_canvas_initial"

if st.sidebar.button("🔄 Reset Drawing"):
    st.session_state.canvas_key = f"forensic_canvas_{np.random.randint(0, 1000000)}"
    st.rerun()

if uploaded_file:
    try:
        img = Image.open(uploaded_file).convert("RGB")
        w, h = img.size
        
        max_display_width = 900
        display_width = min(max_display_width, w)
        display_height = int(h * (display_width / w))
        img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0.3)",
            stroke_width=stroke_width,
            stroke_color=color,
            background_image=img_resized,
            height=display_height,
            width=display_width,
            drawing_mode="line" if mode == "line" else "freedraw",
            key=st.session_state.canvas_key,
            update_streamlit=True,
            display_toolbar=True,
        )
        
        if canvas_result.image_data is not None:
            try:
                report_img = img_resized.copy().convert("RGBA")
                canvas_image_data = canvas_result.image_data.astype('uint8')
                sketch_layer = Image.fromarray(canvas_image_data).convert("RGBA")
                final_report = Image.alpha_composite(report_img, sketch_layer)
                draw = ImageDraw.Draw(final_report)
                
                # Font fallback
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                
                if canvas_result.json_data and 'objects' in canvas_result.json_data:
                    objects = canvas_result.json_data["objects"]
                    if len(objects) > 0:
                        first_obj = objects[0]
                        px_dist = math.sqrt(first_obj.get('width', 0)**2 + first_obj.get('height', 0)**2)
                        ppm = px_dist / 1.0 if px_dist > 0 else 100
                        
                        for idx, obj in enumerate(objects):
                            dx = obj.get('width', 0)
                            dy = obj.get('height', 0)
                            length = math.sqrt(dx**2 + dy**2) / ppm
                            
                            label = f"📏 REFERENCE: 1.0 m" if idx == 0 else f"🚗 OBJECT {idx}: {length:.2f} m"
                            
                            left, top = obj.get('left', 0), obj.get('top', 0)
                            bbox = draw.textbbox((0, 0), label, font=font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                            
                            padding = 10
                            label_y = top + 30 if top < text_height + 50 else top - text_height - 10
                            label_x = max(padding, min(left, display_width - text_width - padding))
                            label_y = max(padding, min(label_y, display_height - text_height - padding))
                            
                            draw.rectangle([label_x - 5, label_y - 5, label_x + text_width + 5, label_y + text_height + 5], fill="black", outline="white", width=1)
                            draw.text((label_x, label_y), label, fill="white", font=font)
                
                gps_text = f"📍 GPS: {lat_val}, {lon_val}"
                timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                footer_height = 80
                draw.rectangle([0, display_height - footer_height, display_width, display_height], fill="black", outline="white", width=2)
                
                try:
                    small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 14)
                except:
                    small_font = ImageFont.load_default()
                
                draw.text((10, display_height - 65), gps_text, fill="yellow", font=small_font)
                draw.text((10, display_height - 45), timestamp, fill="lightgray", font=small_font)
                draw.text((10, display_height - 25), "🔍 Forensic Road Sketcher Pro", fill="white", font=small_font)
                
                buf = io.BytesIO()
                final_report.convert("RGB").save(buf, format="PNG", optimize=True)
                buf.seek(0)
                
                st.sidebar.markdown("---")
                st.sidebar.download_button(
                    label="📥 Download Report",
                    data=buf,
                    file_name=f"forensic_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
                st.sidebar.success("✅ Ready!")
                
            except Exception as e:
                st.sidebar.error(f"Error: {str(e)}")
                
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
else:
    st.info("👈 Upload a scene photo from the sidebar to start sketching")
