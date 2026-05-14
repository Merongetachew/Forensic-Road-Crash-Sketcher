import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

st.set_page_config(layout="wide")

# 1. Function to convert PIL image to a CSS-friendly string
def get_base64_image(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

st.title("Forensic Sketch Tool")
uploaded_file = st.sidebar.file_uploader("Upload Scene Photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    
    # Scale for PC screen
    max_width = 1000
    w, h = img.size
    display_width = max_width if w > max_width else w
    display_height = int(h * (display_width / w))
    img_resized = img.resize((display_width, display_height))
    
    # Create the Base64 string
    img_base64 = get_base64_image(img_resized)

    # 2. THE FIX: Custom CSS to force the image to show behind the canvas
    # This places the image at the exact same coordinates as the canvas
    st.markdown(
        f"""
        <style>
        .stCanvas {{
            background-image: url("data:image/png;base64,{img_base64}");
            background-size: contain;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_name=True,
    )

    # 3. Transparent Canvas
    # We set background_image=None because the CSS above is doing the work now
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3,
        stroke_color="#FF0000",
        background_color="rgba(0,0,0,0)", # Fully transparent
        background_image=None, 
        height=display_height,
        width=display_width,
        drawing_mode="line",
        key="canvas_css_fix",
        display_toolbar=True,
    )
    
    st.info("The image is now forced into the background via CSS.")

else:
    st.warning("Please upload a photo in the sidebar.")
