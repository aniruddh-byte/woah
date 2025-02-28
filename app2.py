import streamlit as st
import pdfplumber
from PIL import Image
import base64

# Function to extract a specific page as an image
def extract_page_as_image(pdf_file, page_number):
    with pdfplumber.open(pdf_file) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            st.error("Invalid page number")
            return None
        page = pdf.pages[page_number - 1]
        return page.to_image(resolution=150).original  # Convert page to image

# Function to create a download link
def get_pdf_download_link(pdf_file):
    # Read file as bytes
    pdf_bytes = pdf_file.getvalue()
    # Encode to base64
    b64 = base64.b64encode(pdf_bytes).decode()
    # Generate HTML link
    href = f'<a href="data:application/pdf;base64,{b64}" download="{pdf_file.name}" target="_blank">Open PDF in new tab</a>'
    return href

# Streamlit app
st.title("PDF Page Viewer")

# Upload PDF file
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file is not None:
    # Display the download link
    st.markdown(get_pdf_download_link(uploaded_file), unsafe_allow_html=True)
    
    # Create two columns for input and button
    col1, col2 = st.columns([2, 1])
    
    # Input for page number
    page_number = st.number_input("Enter the page number", min_value=1, value=1)
    
    show_page = st.session_state.get('show_page', False)
    
    if st.button('Show Page'):
        show_page = not show_page
        st.session_state['show_page'] = show_page
        
    if show_page:
        page_image = extract_page_as_image(uploaded_file, page_number)
        if page_image:
            st.image(page_image, caption=f"Page {page_number}", use_column_width=True)