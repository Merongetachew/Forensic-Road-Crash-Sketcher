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
if 'img_width' not in st.session_state:
    st.session_state.img_width = 0
if 'img_height' not in st.session_state:
    st.session_state.img_height = 0

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
        st.session_state.original_width = w
        st.session_state.original_height = h
        
        if w > max_width:
            new_w = max_width
            new_h = int(h * (max_width / w))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            st.session_state.scale_x = w / new_w
            st.session_state.scale_y = h / new_h
            st.session_state.img_width = new_w
            st.session_state.img_height = new_h
        else:
            st.session_state.scale_x = 1
            st.session_state.scale_y = 1
            st.session_state.img_width = w
            st.session_state.img_height = h
            
        st.session_state.img = img
        st.session_state.image_loaded = True
        
        # Display image - FIXED: use 'width' parameter instead of 'use_container_width'
        st.image(img, width=st.session_state.img_width)
        
        # Drawing instructions
        st.info("📝 **Drawing Instructions:** Use the coordinate inputs below to add points. Draw Reference Line first!")
        
        # Point input using session state
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            x_coord = st.number_input("X", value=0.0, step=1.0, key="x_input")
        with col_b:
            y_coord = st.number_input("Y", value=0.0, step=1.0, key="y_input")
        with col_c:
            if st.button("➕ Add Point", use_container_width=True):
                if x_coord >= 0 and y_coord >= 0:
                    st.session_state.points.append({
                        'x': x_coord,
                        'y': y_coord,
                        'color': current_color,
                        'width': stroke_width,
                        'mode': st.session_state.drawing_mode,
                        'timestamp': dt.datetime.now().strftime('%H:%M:%S')
                    })
                    st.success(f"✓ Point added at ({x_coord}, {y_coord})")
                    st.rerun()
        with col_d:
            if st.button("🗑️ Last Point", use_container_width=True):
                if st.session_state.points:
                    st.session_state.points.pop()
                    st.rerun()
        
        # Display current points count
        if st.session_state.points:
            st.write(f"**Total points:** {len(st.session_state.points)}")
            
            # Group points into lines
            lines = []
            current_line = []
            for i, point in enumerate(st.session_state.points):
                current_line.append(point)
                if i < len(st.session_state.points) - 1:
                    next_point = st.session_state.points[i + 1]
                    # Check if same mode
                    if point['mode'] != next_point['mode']:
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
                    if pixel_dist > 0:
                        meters_per_pixel = 1.0 / pixel_dist
                        st.session_state.reference_line = meters_per_pixel
                        st.success(f"✅ Reference line set! Scale: 1 pixel = {meters_per_pixel:.4f} meters")
                    else:
                        st.error("❌ Reference line points are too close!")
            
            # Show measurements in the right column
            with measure_col:
                st.subheader("📊 Measurements")
                
                if st.session_state.reference_line:
                    st.success(f"Scale: 1px = {st.session_state.reference_line:.4f}m")
                    st.info(f"Reference: {st.session_state.reference_line * 100:.2f}cm per pixel")
                    
                    st.markdown("---")
                    st.subheader("📏 Object Lengths")
                    
                    # Calculate lengths for each line
                    object_count = 0
                    for idx, line in enumerate(lines):
                        if len(line) >= 2 and line[0]['mode'] != "Reference Line (1m)":
                            total_length = 0
                            for i in range(len(line)-1):
                                dist = np.sqrt((line[i+1]['x'] - line[i]['x'])**2 + 
                                             (line[i+1]['y'] - line[i]['y'])**2)
                                total_length += dist
                            actual_length = total_length * st.session_state.reference_line
                            object_count += 1
                            
                            # Display with colored background
                            st.metric(
                                label=f"📐 Object {object_count} ({line[0]['mode']})",
                                value=f"{actual_length:.2f} meters",
                                delta=f"{actual_length * 3.28084:.2f} feet" if actual_length else None
                            )
                    
                    if object_count == 0:
                        st.info("No objects measured yet. Draw some lines!")
                else:
                    st.warning("⚠️ Draw a Reference Line first!")
                    st.info("""
                    **How to set reference:**
                    1. Select 'Reference Line (1m)'
                    2. Add 2 points that represent 1 meter
                    3. Example: Draw along a car license plate (standard ~1ft or 0.3m)
                    """)
            
            # Show points table
            with st.expander("📝 View all drawn points"):
                if st.session_state.points:
                    points_df = pd.DataFrame(st.session_state.points)
                    # Reorder columns for better display
                    columns_order = ['x', 'y', 'mode', 'color', 'width', 'timestamp']
                    points_df = points_df[[col for col in columns_order if col in points_df.columns]]
                    st.dataframe(points_df, use_container_width=True)
    
    else:
        st.info("👈 Please upload an image from the sidebar to begin")
        st.markdown("""
        ### Quick Start Guide:
        1. Upload a crash scene photo
        2. Draw a Reference Line (1 meter)
        3. Draw objects/evidence
        4. Generate forensic report
        """)

# Report generation
with measure_col:
    st.markdown("---")
    st.subheader("📄 Generate Report")
    
    if st.session_state.image_loaded and st.session_state.points:
        # Check if reference line exists
        has_reference = st.session_state.reference_line is not None
        
        if has_reference:
            if st.button("📥 Create Forensic Report", type="primary", use_container_width=True):
                try:
                    # Create a copy of the image for the report
                    report_img = st.session_state.img.copy()
                    draw = ImageDraw.Draw(report_img)
                    
                    # Try to load fonts
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                    except:
                        try:
                            font = ImageFont.truetype("arial.ttf", 20)
                            small_font = ImageFont.truetype("arial.ttf", 14)
                        except:
                            font = ImageFont.load_default()
                            small_font = ImageFont.load_default()
                    
                    # Draw all points and lines
                    points_list = st.session_state.points
                    
                    # First, draw lines
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
                    
                    # Then draw points
                    for i, point in enumerate(points_list):
                        x, y = point['x'], point['y']
                        # Draw point circle
                        draw.ellipse([x-5, y-5, x+5, y+5], fill=point['color'], outline='white', width=2)
                        
                        # Draw point number
                        label = str(i + 1)
                        draw.text((x+8, y-8), label, fill=point['color'], font=small_font)
                    
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
                    
                    # Add measurement summary on the right side
                    if st.session_state.reference_line:
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
                        
                        y_pos = 20
                        draw.text((img_width - 280, y_pos), "📏 MEASUREMENTS:", fill="yellow", font=font)
                        y_pos += 30
                        
                        object_num = 0
                        for line in lines_display:
                            if line and line[0]['mode'] != "Reference Line (1m)":
                                if len(line) >= 2:
                                    total_length = 0
                                    for i in range(len(line)-1):
                                        dist = np.sqrt((line[i+1]['x'] - line[i]['x'])**2 + 
                                                     (line[i+1]['y'] - line[i]['y'])**2)
                                        total_length += dist
                                    actual_length = total_length * st.session_state.reference_line
                                    object_num += 1
                                    draw.text((img_width - 280, y_pos), f"Object {object_num}: {actual_length:.2f}m", fill="white", font=small_font)
                                    y_pos += 22
                    
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
                    
                    st.success("✅ Report generated successfully!")
                    
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
        else:
            st.warning("⚠️ Please draw a Reference Line first before generating report")
    else:
        st.info("Upload an image and draw points first")

# Instructions
with st.expander("📖 How to Use - Step by Step"):
    st.markdown("""
    ### 🎯 Quick Start Guide
    
    **Step 1: Upload Image**
    - Click "Choose image" in the sidebar
    - Select a clear photo of the accident scene
    
    **Step 2: Set Reference Line (CRITICAL!)**
    - Select "Reference Line (1m)" tool
    - Add 2 points that represent 1 meter in real life
    - Examples: Car license plate (~0.5m), Tire diameter (~0.6m), Road line width
    
    **Step 3: Draw Objects**
    - Switch to "Line" or "Free Draw" mode
    - Add points along vehicles, skid marks, or evidence
    - Points will automatically connect into lines
    
    **Step 4: View Measurements**
    - Check the right panel for automatic length calculations
    - Measurements update as you add points
    
    **Step 5: Generate Report**
    - Click "Create Forensic Report"
    - Download the annotated image with all measurements
    
    ### 💡 Pro Tips
    - Add points in sequence (1,2,3...) for continuous lines
    - Use different colors for different evidence types
    - Reference line must be the FIRST thing you draw
    - X,Y coordinates are in pixels (0 = top-left corner)
    """)
