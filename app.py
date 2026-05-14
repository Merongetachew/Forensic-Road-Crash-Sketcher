import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import datetime as dt
import base64
import json

st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# Initialize session state
if 'drawing_points' not in st.session_state:
    st.session_state.drawing_points = []
if 'drawing_mode' not in st.session_state:
    st.session_state.drawing_mode = 'line'
if 'objects_list' not in st.session_state:
    st.session_state.objects_list = []
if 'current_color' not in st.session_state:
    st.session_state.current_color = '#FF0000'
if 'img_display' not in st.session_state:
    st.session_state.img_display = None
if 'img_original' not in st.session_state:
    st.session_state.img_original = None
if 'scale_factor' not in st.session_state:
    st.session_state.scale_factor = 1.0

# Sidebar controls
st.sidebar.header("📍 Scene Location")
col1, col2 = st.sidebar.columns(2)
with col1:
    lat_input = st.text_input("Latitude", str(dt.datetime.now().strftime("%Y%m%d")))
with col2:
    lon_input = st.text_input("Longitude", "000000")

st.sidebar.header("🎨 Drawing Controls")
drawing_tool = st.sidebar.radio("Tool:", ["✏️ Line", "✏️ Free Draw", "📏 Reference Line"])
st.session_state.current_color = st.sidebar.color_picker("Color", "#FF0000")
stroke_width = st.sidebar.slider("Width", 1, 10, 3)

# Reference length input
reference_length = st.sidebar.number_input("Reference Line Length (meters)", value=1.0, min_value=0.1, step=0.1)

st.sidebar.header("📸 Upload Photo")
uploaded_file = st.sidebar.file_uploader("Choose image", type=["jpg", "jpeg", "png"])

# Clear drawing button
if st.sidebar.button("🗑️ Clear All Drawings"):
    st.session_state.drawing_points = []
    st.session_state.objects_list = []
    st.rerun()

# Image processing function
def process_image(uploaded_file):
    if uploaded_file:
        img = Image.open(uploaded_file).convert("RGB")
        
        # Calculate display size (max 800px width for stability)
        max_width = 800
        w, h = img.size
        if w > max_width:
            new_w = max_width
            new_h = int(h * (max_width / w))
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            scale_x = w / max_width
            scale_y = h / new_h
        else:
            img_resized = img.copy()
            new_w, new_h = w, h
            scale_x, scale_y = 1.0, 1.0
        
        return img_resized, new_w, new_h, scale_x, scale_y
    return None, 0, 0, 1.0, 1.0

# Drawing canvas using pure HTML/JS (bypasses streamlit-drawable-canvas issues)
def draw_canvas_js(img_array, width, height):
    # Convert image to base64 for HTML embedding
    img_pil = Image.fromarray(img_array.astype('uint8')) if isinstance(img_array, np.ndarray) else img_array
    buffered = io.BytesIO()
    img_pil.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Get existing drawings
    drawings_json = json.dumps(st.session_state.drawing_points)
    
    # Custom HTML/JS canvas
    canvas_html = f"""
    <style>
        .canvas-container {{
            position: relative;
            display: inline-block;
            margin: 0 auto;
            cursor: crosshair;
        }}
        #imageCanvas {{
            position: absolute;
            top: 0;
            left: 0;
            z-index: 1;
        }}
        #drawingCanvas {{
            position: absolute;
            top: 0;
            left: 0;
            z-index: 2;
        }}
        .canvas-wrapper {{
            position: relative;
            display: inline-block;
        }}
        button {{
            margin: 5px;
            padding: 5px 10px;
            cursor: pointer;
        }}
    </style>
    
    <div class="canvas-wrapper">
        <canvas id="imageCanvas" width="{width}" height="{height}" style="border: 1px solid #ccc;"></canvas>
        <canvas id="drawingCanvas" width="{width}" height="{height}" style="border: 1px solid #ccc;"></canvas>
    </div>
    <div style="margin-top: 10px;">
        <button onclick="clearCanvas()">Clear Drawing</button>
        <button onclick="undoLast()">Undo</button>
        <button onclick="finishDrawing()">Finish & Measure</button>
    </div>
    
    <script>
        var imageCanvas = document.getElementById('imageCanvas');
        var drawingCanvas = document.getElementById('drawingCanvas');
        var ctxImg = imageCanvas.getContext('2d');
        var ctxDraw = drawingCanvas.getContext('2d');
        var drawing = false;
        var points = {drawings_json};
        var currentPoints = [];
        var mode = '{drawing_tool}';
        var color = '{st.session_state.current_color}';
        var lineWidth = {stroke_width};
        
        // Load image
        var img = new Image();
        img.onload = function() {{
            ctxImg.drawImage(img, 0, 0, {width}, {height});
            redrawDrawings();
        }};
        img.src = 'data:image/png;base64,{img_base64}';
        
        function redrawDrawings() {{
            ctxDraw.clearRect(0, 0, {width}, {height});
            ctxDraw.strokeStyle = color;
            ctxDraw.lineWidth = lineWidth;
            ctxDraw.lineCap = 'round';
            
            for (var i = 0; i < points.length; i++) {{
                var line = points[i];
                if (line.points.length > 1) {{
                    ctxDraw.beginPath();
                    ctxDraw.moveTo(line.points[0].x, line.points[0].y);
                    for (var j = 1; j < line.points.length; j++) {{
                        ctxDraw.lineTo(line.points[j].x, line.points[j].y);
                    }}
                    ctxDraw.stroke();
                }}
            }}
        }}
        
        function getMousePos(e) {{
            var rect = drawingCanvas.getBoundingClientRect();
            var scaleX = drawingCanvas.width / rect.width;
            var scaleY = drawingCanvas.height / rect.height;
            return {{
                x: (e.clientX - rect.left) * scaleX,
                y: (e.clientY - rect.top) * scaleY
            }};
        }}
        
        function startDrawing(e) {{
            drawing = true;
            var pos = getMousePos(e);
            currentPoints = [pos];
            ctxDraw.beginPath();
            ctxDraw.moveTo(pos.x, pos.y);
        }}
        
        function draw(e) {{
            if (!drawing) return;
            var pos = getMousePos(e);
            currentPoints.push(pos);
            ctxDraw.lineTo(pos.x, pos.y);
            ctxDraw.stroke();
        }}
        
        function stopDrawing() {{
            if (drawing && currentPoints.length > 1) {{
                points.push({{
                    points: currentPoints,
                    color: color,
                    width: lineWidth
                }});
                currentPoints = [];
            }}
            drawing = false;
        }}
        
        function clearCanvas() {{
            points = [];
            ctxDraw.clearRect(0, 0, {width}, {height});
        }}
        
        function undoLast() {{
            points.pop();
            redrawDrawings();
        }}
        
        function finishDrawing() {{
            var output = {{
                points: points,
                imageWidth: {width},
                imageHeight: {height}
            }};
            var jsonStr = JSON.stringify(output);
            var input = document.createElement('input');
            input.type = 'hidden';
            input.id = 'drawing_output';
            input.value = jsonStr;
            document.body.appendChild(input);
            
            // Trigger Streamlit update
            const event = new Event('streamlit:setComponentValue');
            input.dispatchEvent(event);
        }}
        
        drawingCanvas.addEventListener('mousedown', startDrawing);
        drawingCanvas.addEventListener('mousemove', draw);
        drawingCanvas.addEventListener('mouseup', stopDrawing);
        drawingCanvas.addEventListener('mouseleave', stopDrawing);
    </script>
    """
    
    return canvas_html

# Main display area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🖌️ Drawing Area")
    
    if uploaded_file:
        # Process image
        img_display, width, height, scale_x, scale_y = process_image(uploaded_file)
        
        if img_display:
            # Convert PIL to numpy for canvas
            img_array = np.array(img_display)
            
            # Display custom canvas
            st.markdown(draw_canvas_js(img_array, width, height), unsafe_allow_html=True)
            
            # Hidden input to capture drawing data
            drawing_data = st.text_area("Drawing Data (hidden)", key="drawing_data", label_visibility="collapsed")
            
            # Process drawing when data is received
            if drawing_data and drawing_data != "{}":
                try:
                    data = json.loads(drawing_data)
                    st.session_state.drawing_points = data.get('points', [])
                    
                    # Calculate measurements if reference line exists
                    if len(st.session_state.drawing_points) > 0:
                        ref_line = st.session_state.drawing_points[0]
                        if len(ref_line.get('points', [])) >= 2:
                            p1 = ref_line['points'][0]
                            p2 = ref_line['points'][1]
                            pixel_distance = np.sqrt((p2['x'] - p1['x'])**2 + (p2['y'] - p1['y'])**2)
                            meters_per_pixel = reference_length / pixel_distance if pixel_distance > 0 else 1
                            
                            st.success(f"📏 Scale: {meters_per_pixel:.4f} meters/pixel")
                            
                            # Display measurements for all drawings
                            for idx, drawing in enumerate(st.session_state.drawing_points):
                                if idx > 0 and len(drawing.get('points', [])) >= 2:
                                    points = drawing['points']
                                    # Calculate total length
                                    total_length = 0
                                    for i in range(len(points)-1):
                                        dist = np.sqrt((points[i+1]['x'] - points[i]['x'])**2 + 
                                                      (points[i+1]['y'] - points[i]['y'])**2)
                                        total_length += dist
                                    
                                    actual_length = total_length * meters_per_pixel
                                    st.info(f"📐 Object {idx}: {actual_length:.2f} meters")
                    
                except json.JSONDecodeError:
                    pass
            
    else:
        st.info("👈 Please upload an image from the sidebar")

with col2:
    st.subheader("📋 Measurements")
    
    if st.session_state.objects_list:
        for obj in st.session_state.objects_list:
            st.write(f"- {obj}")
    else:
        st.write("No measurements yet. Draw a reference line first!")
    
    st.markdown("---")
    st.subheader("📄 Report")
    
    if uploaded_file and st.session_state.drawing_points:
        # Generate report button
        if st.button("Generate Forensic Report"):
            try:
                # Create composite image
                img_display, width, height, _, _ = process_image(uploaded_file)
                
                if img_display:
                    draw = ImageDraw.Draw(img_display)
                    
                    # Add GPS info
                    gps_text = f"GPS: {lat_input}, {lon_input}"
                    timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    draw.text((10, 10), gps_text, fill="yellow")
                    draw.text((10, 30), timestamp, fill="white")
                    
                    # Save report
                    buf = io.BytesIO()
                    img_display.save(buf, format="PNG")
                    buf.seek(0)
                    
                    st.download_button(
                        label="📥 Download Report",
                        data=buf,
                        file_name=f"forensic_report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png"
                    )
                    
                    st.success("Report generated!")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
