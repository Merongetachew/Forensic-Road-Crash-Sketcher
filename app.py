import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(layout="wide", page_title="Forensic Sketcher")

uploaded_file = st.sidebar.file_uploader("Upload Photo", type=["jpg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    # Resize significantly to 600px to force it to load in low memory
    img.thumbnail((600, 600)) 
    
    st.image(img, caption="Uploaded Scene (Reference)") # FALLBACK: Shows the image above the canvas

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3,
        stroke_color="#FF0000",
        background_image=img, # Try to load as background
        height=img.height,
        width=img.width,
        drawing_mode="line",
        key="emergency_fix_v1",
        update_streamlit=True,
    )
