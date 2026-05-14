import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import datetime as dt
import pandas as pd

st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# Initialize session state
if 'points' not in st.session_state:
    st.session_state.points = []
if 'reference_line' not in st.session_state:
    st.session_state.reference_line = None
if 'image_loaded' not in st.session_state:
    st.session_state.image_loaded = False
if 'img' not in st.session_state:
    st.session_state.img = None
if 'drawing_mode' not in st.session_state:
    st.session_state.drawing_mode = "Line"

# Sidebar
st.sidebar.header("📍 Scene Location")
col1, col2 = st.sidebar.columns(2)
with col1:
    lat_input = st.text_input("Latitude", "0.000000")
with col2:
    lon_input = st.text_input("Longitude", "0.000000")

st.sidebar.header("🎨 Drawing Controls")
st.session_state.drawing_mode = st.sidebar.radio(
    "Tool:", 
    ["Line", "Free Draw", "Reference Line (1m)"]
)
current_color = st.sidebar.color_picker("Color", "#FF0000")
stroke_width = st.sidebar.slider("Width", 1, 10, 3)

st.sidebar.header("📸 Upload Photo")
uploaded_file = st.sidebar.file_uploader("Choose image", type=["jpg", "jpeg", "png"])

# Clear button
if st.sidebar.button("🗑️ Clear Drawing"):
    st.session_state.points = []
    st.session_state.reference_line = None
    st.rerun()

# Main display area
st.subheader("🖌️ Drawing Area")

# Create columns for drawing and measurements
draw_col, measure_col = st.columns([2, 1])

with draw_col:
    if uploaded_file is not None:
        # Load and display image
        img = Image.open(uploaded_file).convert("RGB")
        
        # Resize for display (max width 800px)
        max_width = 800
        w, h = img.size
        if w > max_width:
            new_w = max_width
            new_h = int(h * (max_width / w))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            st.session_state.scale_x = w / new_w
            st.session_state.scale_y = h / new_h
        else:
            st.session_state.scale_x = 1
            st.session_state.scale_y = 1
            
        st.session_state.img = img
        st.session_state.image_loaded = True
        
        # Display image
        st.image(img, use_container_width=True)
        
        # Drawing instructions
        st.info("📝 **Drawing Instructions:** Click on the image to draw points. Draw Reference Line first!")
        
        # Point input using session state
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            x_coord = st.number_input("X coordinate", value=0.0, step=1.0)
        with col_b:
            y_coord = st.number_input("Y coordinate", value=0.0, step=1.0)
        with col_c:
            if st.button("➕ Add Point"):
                if x_coord > 0 or y_coord > 0:
                    st.session_state.points.append({
                        'x': x_coord,
                        'y': y_coord,
                        'color': current_color,
                        'width': stroke_width,
                        'mode': st.session_state.drawing_mode
                    })
                    st.success(f"Point added at ({x_coord}, {y_coord})")
                    st.rerun()
        
        # Display current points
        if st.session_state.points:
            st.write(f"**Points drawn:** {len(st.session_state.points)}")
            
            # Group points into lines
            lines = []
            current_line = []
            for i, point in enumerate(st.session_state.points):
                current_line.append(point)
                if i < len(st.session_state.points) - 1:
                    next_point = st.session_state.points[i + 1]
                    # Check if same mode and color
                    if point['mode'] != next_point['mode'] or point['color'] != next_point['color']:
                        lines.append(current_line)
                        current_line = []
            if current_line:
                lines.append(current_line)
            
            # Calculate measurements
            if st.session_state.reference_line is None:
                # Check if we have a reference line
                ref_lines = [line for line in lines if line and line[0]['mode'] == "Reference Line (1m)"]
                if ref_lines and len(ref_lines[0]) >= 2:
                    p1 = ref_lines[0][0]
                    p2 = ref_lines[0][1]
                    pixel_dist = np.sqrt((p2['x'] - p1['x'])**2 + (p2['y'] - p1['y'])**2)
                    meters_per_pixel = 1.0 / pixel_dist if pixel_dist > 0 else 1
                    st.session_state.reference_line = meters_per_pixel
                    st.success(f"✅ Reference line set! Scale: {meters_per_pixel:.4f} meters/pixel")
            
            # Show measurements in the right column
            with measure_col:
                st.subheader("📊 Measurements")
                
                if st.session_state.reference_line:
                    st.success(f"Scale: 1 pixel = {st.session_state.reference_line:.4f} meters")
                    
                    # Calculate lengths for each line
                    for idx, line in enumerate(lines):
                        if len(line) >= 2 and line[0]['mode'] != "Reference Line (1m)":
                            total_length = 0
                            for i in range(len(line)-1):
                                dist = np.sqrt((line[i+1]['x'] - line[i]['x'])**2 + 
                                             (line[i+1]['y'] - line[i]['y'])**2)
                                total_length += dist
                            actual_length = total_length * st.session_state.reference_line
                            st.metric(f"Object {idx+1}", f"{actual_length:.2f} meters")
                else:
                    st.warning("⚠️ Draw a Reference Line first!")
                    st.info("1. Select 'Reference Line (1m)' tool")
                    st.info("2. Add two points to create a 1-meter reference")
            
            # Show points table
            with st.expander("📝 View drawn points"):
                points_df = pd.DataFrame(st.session_state.points)
                st.dataframe(points_df)
    
    else:
        st.info("👈 Please upload an image from the sidebar")

# Report generation
with measure_col:
    st.markdown("---")
    st.subheader("📄 Generate Report")
    
    if st.session_state.image_loaded and st.session_state.points:
        if st.button("📥 Create Forensic Report", type="primary"):
            try:
                # Create a copy of the image for the report
                report_img = st.session_state.img.copy()
                draw = ImageDraw.Draw(report_img)
                
                # Try to load a font
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                    small_font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
                
                # Draw all points on the image
                for i, point in enumerate(st.session_state.points):
                    x, y = point['x'], point['y']
                    # Draw point
                    draw.ellipse([x-5, y-5, x+5, y+5], fill=point['color'], outline='white', width=2)
                    
                    # Draw label
                    label = f"P{i+1}"
                    draw.text((x+10, y-10), label, fill=point['color'], font=small_font)
                
                # Draw lines between consecutive points with same mode
                points_list = st.session_state.points
                i = 0
                while i < len(points_list) - 1:
                    current = points_list[i]
                    next_point = points_list[i + 1]
                    
                    # Draw line if same mode
                    if current['mode'] == next_point['mode']:
                        draw.line([(current['x'], current['y']), 
                                  (next_point['x'], next_point['y'])], 
                                 fill=current['color'], 
                                 width=current['width'])
                    i += 1
                
                # Add GPS information
                gps_text = f"📍 GPS: {lat_input}, {lon_input}"
                timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                case_id = f"CASE-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                # Footer
                footer_height = 100
                img_width, img_height = report_img.size
                draw.rectangle([0, img_height - footer_height, img_width, img_height], fill="black")
                
                draw.text((10, img_height - 80), gps_text, fill="yellow", font=small_font)
                draw.text((10, img_height - 60), f"🕐 {timestamp}", fill="white", font=small_font)
                draw.text((10, img_height - 40), f"📋 {case_id}", fill="white", font=small_font)
                draw.text((10, img_height - 20), "🔍 Forensic Road Sketcher Pro", fill="lightgray", font=small_font)
                
                # Add measurement summary
                if st.session_state.reference_line:
                    y_pos = 20
                    draw.text((img_width - 300, y_pos), "MEASUREMENTS:", fill="yellow", font=font)
                    y_pos += 25
                    
                    # Group points into lines for measurement display
                    lines_display = []
                    current_line = []
                    for idx, point in enumerate(points_list):
                        current_line.append(point)
                        if idx < len(points_list) - 1:
                            next_p = points_list[idx + 1]
                            if point['mode'] != next_p['mode']:
                                if len(current_line) >= 2:
                                    lines_display.append(current_line)
                                current_line = []
                    if len(current_line) >= 2:
                        lines_display.append(current_line)
                    
                    for idx, line in enumerate(lines_display):
                        if line[0]['mode'] != "Reference Line (1m)":
                            total_length = 0
                            for i in range(len(line)-1):
                                dist = np.sqrt((line[i+1]['x'] - line[i]['x'])**2 + 
                                             (line[i+1]['y'] - line[i]['y'])**2)
                                total_length += dist
                            actual_length = total_length * st.session_state.reference_line
                            draw.text((img_width - 300, y_pos), f"Object {idx+1}: {actual_length:.2f}m", fill="white", font=small_font)
                            y_pos += 20
                
                # Save report
                buf = io.BytesIO()
                report_img.save(buf, format="PNG", optimize=True)
                buf.seek(0)
                
                st.download_button(
                    label="💾 Download Report (PNG)",
                    data=buf,
                    file_name=f"forensic_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                st.success("✅ Report ready!")
                
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
    else:
        st.info("Upload an image and draw points first")

# Instructions
with st.expander("📖 How to Use"):
    st.markdown("""
    ### Step-by-Step Guide:
    
    1. **Upload a photo** using the sidebar
    2. **Draw Reference Line** (very important!)
       - Select "Reference Line (1m)"
       - Add 2 points on the image representing 1 meter in real life
       - The system will calculate the scale automatically
    3. **Draw objects** you want to measure
       - Switch to "Line" or "Free Draw" mode
       - Add points along the object/evidence
    4. **View measurements** in the right panel
    5. **Generate report** to download the final forensic document
    
    ### Tips:
    - For reference line: Draw along a known 1-meter object (e.g., license plate width, tire diameter)
    - Add points in sequence to create continuous lines
    - Use different colors for different evidence types
    """)
