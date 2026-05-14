import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont
import math
import io
import numpy as np

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Forensic Road Sketcher Pro")

# 2. GPS Detection (removed streamlit_js_eval due to compatibility issues)
st.sidebar.subheader("📍 Scene Location")
st.sidebar.warning("⚠️ GPS requires HTTPS/SSL. Enter coordinates manually for web deployment:")

# Manual GPS input for web deployment
col1, col2 = st.sidebar.columns(2)
with col1:
    lat_input = st.text_input("Latitude", "0.000000")
with col2:
    lon_input = st.text_input("Longitude", "0.000000")

lat_val, lon_val = lat_input, lon_input
coords = f"{lat_val}, {lon_val}"
st.sidebar.text_area("Coordinates:", value=coords, height=70)

st.sidebar.header("🎨 Drawing Controls")
mode = st.sidebar.selectbox("Drawing Tool:", ("line", "freedraw", "rect", "circle"))
color = st.sidebar.color_picker("Line Color", "#FF0000")
stroke_width = st.sidebar.slider("Stroke Width", 1, 10, 4)

# Drawing mode options
drawing_mode = "line" if mode == "line" else "freedraw"

st.sidebar.header("📸 Scene Photo")
uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png", "bmp"])

# Initialize session state for canvas
if 'canvas_key' not in st.session_state:
    st.session_state.canvas_key = "forensic_canvas_initial"

# Reset canvas button
if st.sidebar.button("🔄 Reset Drawing"):
    st.session_state.canvas_key = f"forensic_canvas_{np.random.randint(0, 1000000)}"
    st.rerun()

if uploaded_file:
    try:
        # Open and convert image
        img = Image.open(uploaded_file).convert("RGB")
        w, h = img.size
        
        # Calculate display dimensions (maintain aspect ratio)
        max_display_width = 900  # Fixed max width for stability
        display_width = min(max_display_width, w)
        display_height = int(h * (display_width / w))
        
        # Resize image for display
        img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        # Create canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0.3)",
            stroke_width=stroke_width,
            stroke_color=color,
            background_image=img_resized,
            height=display_height,
            width=display_width,
            drawing_mode=drawing_mode,
            key=st.session_state.canvas_key,
            update_streamlit=True,
            display_toolbar=True,
        )
        
        # Process drawing if exists
        if canvas_result.image_data is not None:
            try:
                # Create report image
                report_img = img_resized.copy().convert("RGBA")
                
                # Convert canvas image data to PIL Image
                canvas_image_data = canvas_result.image_data.astype('uint8')
                sketch_layer = Image.fromarray(canvas_image_data).convert("RGBA")
                
                # Composite images
                final_report = Image.alpha_composite(report_img, sketch_layer)
                draw = ImageDraw.Draw(final_report)
                
                # Try to use a default font
                try:
                    # Try to load a system font
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                
                # Process drawn objects for measurements
                if canvas_result.json_data and 'objects' in canvas_result.json_data:
                    objects = canvas_result.json_data["objects"]
                    
                    if len(objects) > 0:
                        # Calculate pixels per meter (assuming first object is 1 meter reference)
                        first_obj = objects[0]
                        px_dist = math.sqrt(first_obj.get('width', 0)**2 + first_obj.get('height', 0)**2)
                        ppm = px_dist / 1.0 if px_dist > 0 else 100
                        
                        # Add measurements for each object
                        for idx, obj in enumerate(objects):
                            dx = obj.get('width', 0)
                            dy = obj.get('height', 0)
                            length = math.sqrt(dx**2 + dy**2) / ppm
                            
                            if idx == 0:
                                label = f"📏 REFERENCE: 1.0 m"
                            else:
                                label = f"🚗 OBJECT {idx}: {length:.2f} m"
                            
                            # Get object position
                            left = obj.get('left', 0)
                            top = obj.get('top', 0)
                            
                            # Calculate text size
                            bbox = draw.textbbox((0, 0), label, font=font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                            
                            # Smart label positioning (avoid edges)
                            padding = 10
                            if top < text_height + 50:
                                label_y = top + 30
                            else:
                                label_y = top - text_height - 10
                            
                            # Ensure label stays within bounds
                            label_x = max(padding, min(left, display_width - text_width - padding))
                            label_y = max(padding, min(label_y, display_height - text_height - padding))
                            
                            # Draw label background
                            draw.rectangle(
                                [label_x - 5, label_y - 5, label_x + text_width + 5, label_y + text_height + 5],
                                fill="black",
                                outline="white",
                                width=1
                            )
                            draw.text((label_x, label_y), label, fill="white", font=font)
                
                # Add GPS information to report
                gps_text = f"📍 GPS Coordinates: {lat_val}, {lon_val}"
                timestamp = f"🕐 Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}" if 'pd' in dir() else f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Footer background
                footer_height = 80
                draw.rectangle([0, display_height - footer_height, display_width, display_height], fill="black", outline="white", width=2)
                
                # Add footer text
                try:
                    small_font = ImageFont.truetype("arial.ttf", 14)
                except:
                    small_font = ImageFont.load_default()
                
                draw.text((10, display_height - 65), gps_text, fill="yellow", font=small_font)
                draw.text((10, display_height - 45), timestamp, fill="lightgray", font=small_font)
                draw.text((10, display_height - 25), "🔍 Forensic Road Sketcher Pro", fill="white", font=small_font)
                
                # Prepare download
                buf = io.BytesIO()
                final_report.convert("RGB").save(buf, format="PNG", optimize=True)
                buf.seek(0)
                
                # Download button
                st.sidebar.markdown("---")
                st.sidebar.download_button(
                    label="📥 Download Forensic Report",
                    data=buf,
                    file_name=f"forensic_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # Display success message
                st.sidebar.success("✅ Report ready for download!")
                
            except Exception as e:
                st.sidebar.error(f"Error processing drawing: {str(e)}")
        
        # Instructions for user
        with st.expander("📖 How to use:"):
            st.markdown("""
            **Drawing Instructions:**
            1. **Reference Line**: Draw a 1-meter line first (this will be your measurement reference)
            2. **Draw Objects**: Use line/freedraw mode to outline vehicles or evidence
            3. **Measurements**: Objects will be automatically measured based on your reference line
            4. **Download**: Click download button to save the forensic report
            
            **Tips:**
            - Draw a clear 1-meter reference line (e.g., known object length)
            - Use different colors for different evidence types
            - You can reset drawing using the reset button
            """)
            
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
        st.info("Please try uploading a different image file (JPG, PNG, or JPEG format)")

else:
    # Display instructions when no image is uploaded
    st.info("👈 Please upload a scene photo from the sidebar to start sketching")
    
    # Show example
    with st.expander("ℹ️ About Forensic Road Sketcher Pro"):
        st.markdown("""
        **Features:**
        - Draw directly on accident scene photos
        - Automatic measurement calculation using reference lines
        - GPS coordinate documentation
        - High-resolution forensic report generation
        - Multiple drawing tools (line, freehand, rectangle, circle)
        
        **Best for:**
        - Accident scene documentation
        - Forensic evidence mapping
        - Insurance claim documentation
        - Police reports
        """)

# Add required imports at the top (dynamically handle datetime)
import datetime as dt
import pandas as pd
