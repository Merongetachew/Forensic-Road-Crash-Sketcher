import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont
import math
import io
import numpy as np
import datetime as dt

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Input (Manual - more reliable for web)
st.sidebar.subheader("📍 Scene Location")
col1, col2 = st.sidebar.columns(2)
with col1:
    lat_val = st.text_input("Latitude", "0.000000")
with col2:
    lon_val = st.text_input("Longitude", "0.000000")

st.sidebar.header("🎨 Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw", "rect", "circle"))
color = st.sidebar.color_picker("Line Color", "#FF0000")
stroke_width = st.sidebar.slider("Stroke Width", 1, 10, 4)

st.sidebar.header("📸 Scene Photo")
uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

# Initialize canvas key for reset
if 'canvas_key' not in st.session_state:
    st.session_state.canvas_key = "canvas"

# Reset button
if st.sidebar.button("🔄 Reset Drawing"):
    st.session_state.canvas_key = f"canvas_{np.random.randint(0, 1000000)}"
    st.rerun()

if uploaded_file:
    # Open and process image
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    
    # Scale for display - FIXED: Better scaling logic
    max_display_width = 900
    if w > max_display_width:
        display_width = max_display_width
        display_height = int(h * (display_width / w))
        img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
    else:
        display_width = w
        display_height = h
        img_resized = img.copy()
    
    # Store original dimensions for scaling
    scale_x = w / display_width
    scale_y = h / display_height
    
    # Create canvas - THIS IS THE KEY COMPONENT
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=stroke_width,
        stroke_color=color,
        background_image=img_resized,
        height=display_height,
        width=display_width,
        drawing_mode=mode,
        key=st.session_state.canvas_key,
        update_streamlit=True,
        display_toolbar=True,
    )
    
    # Process drawings
    if canvas_result.json_data and len(canvas_result.json_data["objects"]) > 0:
        objects = canvas_result.json_data["objects"]
        
        # Calculate scale from first object (assumed to be 1 meter reference)
        first_obj = objects[0]
        px_dist = math.sqrt(first_obj.get('width', 0)**2 + first_obj.get('height', 0)**2)
        
        # Reference length (user can adjust)
        reference_length = st.sidebar.number_input("Reference Line Length (meters)", value=1.0, min_value=0.1, step=0.1)
        
        if px_dist > 0:
            ppm = px_dist / reference_length  # pixels per meter
            
            # Create report image
            report_img = img_resized.copy().convert("RGBA")
            
            # Convert canvas to image
            if canvas_result.image_data is not None:
                sketch_layer = Image.fromarray(canvas_result.image_data.astype('uint8')).convert("RGBA")
                final_report = Image.alpha_composite(report_img, sketch_layer)
                draw = ImageDraw.Draw(final_report)
                
                # Try to load font
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                    small_font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
                
                # Draw measurements for each object
                for i, obj in enumerate(objects):
                    # Calculate length
                    dx = obj.get('width', 0)
                    dy = obj.get('height', 0)
                    length_m = math.sqrt(dx**2 + dy**2) / ppm
                    
                    # Create label
                    if i == 0:
                        label = f"📏 REFERENCE: {reference_length:.1f}m"
                    else:
                        label = f"📐 OBJECT {i}: {length_m:.2f}m"
                    
                    # Get position
                    left = obj.get('left', 0)
                    top = obj.get('top', 0)
                    
                    # Calculate text size for positioning
                    bbox = draw.textbbox((0, 0), label, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # Smart label positioning
                    padding = 10
                    if top < text_height + 50:
                        label_y = top + 30
                    else:
                        label_y = top - text_height - 10
                    
                    label_x = max(padding, min(left, display_width - text_width - padding))
                    label_y = max(padding, min(label_y, display_height - text_height - padding))
                    
                    # Draw label background
                    draw.rectangle(
                        [label_x - 5, label_y - 5, label_x + text_width + 5, label_y + text_height + 5],
                        fill="black",
                        outline="white",
                        width=2
                    )
                    draw.text((label_x, label_y), label, fill="white", font=font)
                
                # Add GPS info to footer
                gps_text = f"📍 GPS: {lat_val}, {lon_val}"
                timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                footer_height = 80
                draw.rectangle([0, display_height - footer_height, display_width, display_height], fill="black")
                draw.text((10, display_height - 65), gps_text, fill="yellow", font=small_font)
                draw.text((10, display_height - 45), f"🕐 {timestamp}", fill="lightgray", font=small_font)
                draw.text((10, display_height - 25), "🔍 Forensic Road Sketcher Pro", fill="white", font=small_font)
                
                # Add scale info
                scale_text = f"Scale: {ppm:.2f} pixels/meter"
                draw.text((display_width - 200, display_height - 25), scale_text, fill="white", font=small_font)
                
                # Prepare download
                buf = io.BytesIO()
                final_report.convert("RGB").save(buf, format="PNG", optimize=True)
                buf.seek(0)
                
                # Download button
                st.sidebar.markdown("---")
                st.sidebar.download_button(
                    label="📥 Download Forensic Report",
                    data=buf,
                    file_name=f"forensic_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # Show measurement info in sidebar
                st.sidebar.success(f"✅ Scale: 1m = {ppm:.1f} pixels")
                
                # Display measurements in sidebar
                st.sidebar.subheader("📊 Measurements")
                for i, obj in enumerate(objects):
                    dx = obj.get('width', 0)
                    dy = obj.get('height', 0)
                    length_m = math.sqrt(dx**2 + dy**2) / ppm
                    if i == 0:
                        st.sidebar.info(f"📏 Reference: {length_m:.2f}m (set to {reference_length}m)")
                    else:
                        st.sidebar.write(f"📐 Object {i}: {length_m:.2f} meters")
                
        else:
            st.sidebar.warning("⚠️ Draw a reference line first (at least 1 pixel long)")
            st.sidebar.info("1. Select 'line' tool")
            st.sidebar.info("2. Draw a line representing known length")
            st.sidebar.info("3. Enter actual length above")
    
    else:
        st.sidebar.info("✏️ Draw on the canvas to start measuring")
        st.sidebar.markdown("""
        **How to use:**
        1. Select 'line' tool
        2. Draw a REFERENCE LINE of known length
        3. Set actual length in meters
        4. Draw other objects to measure
        5. Download report
        """)

else:
    st.info("👈 Please upload a scene photo from the sidebar")
    
    # Show instructions
    with st.expander("📖 How to Use - Forensic Road Sketcher Pro"):
        st.markdown("""
        ### 🎯 Quick Start Guide
        
        **Step 1: Upload Image**
        - Upload a clear accident scene photo
        
        **Step 2: Set Reference Scale**
        - Use the **line** tool
        - Draw a line representing a known length (e.g., car length, road width)
        - Enter the actual length in meters in the sidebar
        
        **Step 3: Draw Evidence**
        - Draw lines along vehicles, skid marks, or evidence
        - The app automatically calculates actual lengths
        
        **Step 4: Download Report**
        - Click download button to save annotated image
        - Report includes all measurements and GPS data
        
        ### 💡 Tips
        - Reference line is critical for accurate measurements
        - Draw reference line FIRST
        - Use different colors for different evidence
        - You can draw rectangles and circles too
        """)

# Display canvas key info for debugging (optional)
with st.expander("ℹ️ App Info"):
    st.write(f"Canvas Key: {st.session_state.canvas_key}")
    if uploaded_file:
        st.write(f"Image size: {display_width}x{display_height}")
