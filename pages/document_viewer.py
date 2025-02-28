# Save this as 'pages/document_viewer.py'
import streamlit as st
import json
import base64
import os
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter

# Page configuration with sidebar hidden
st.set_page_config(page_title="Document Viewer", layout="wide", initial_sidebar_state="collapsed")

# Hide the sidebar completely with CSS
hide_sidebar_style = """
    <style>
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

def download_button(file_path, file_name):
    """Generate a download button for the specified file"""
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    b64 = base64.b64encode(file_data).decode()
    download_href = f'<a href="data:application/pdf;base64,{b64}" download="{file_name}" target="_blank">'
    download_button_str = f'{download_href}<button style="width:100%; padding:8px; background-color:#3366ff; color:white; border:none; border-radius:4px; cursor:pointer;">📥 Download PDF</button></a>'
    return download_button_str

def display_pdf(file_path, start_page):
    """Display a PDF file in the Streamlit app with a specific starting page."""
    # Create a base64 encoded string for the PDF file
    with open(file_path, 'rb') as f:
        file_content = f.read()
    base64_pdf = base64.b64encode(file_content).decode('utf-8')
    
    # Use a URL fragment to specify the starting page
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#page={start_page}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    st.title("Document Viewer")
    
    # Get the document name and page number from the query parameters
    doc_name = st.query_params.get("doc_name")
    page_num_str = st.query_params.get("page_num")

    if doc_name and page_num_str:
        try:
            page_num = int(page_num_str)  # Use 1-based index for display

            # Load the document paths mapping
            docs_dir = Path("docs_cache")
            with open(docs_dir / "doc_paths.json", 'r') as f:
                doc_paths = json.load(f)
            
            if doc_name in doc_paths:
                # Download button for the entire PDF
                if 'original_file' in doc_paths[doc_name]:
                    file_path = Path(doc_paths[doc_name]['original_file'])
                    if file_path.exists():
                        st.markdown(
                            download_button(file_path, doc_name),
                            unsafe_allow_html=True
                        )
                        st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing

                        # Display the entire PDF starting from the specific page
                        display_pdf(file_path, page_num)
                    else:
                        st.error(f"Original file not found: {file_path}")
                else:
                    st.error(f"Document not found in cache: {doc_name}")
            else:
                st.error(f"Document not found in cache: {doc_name}")
        except Exception as e:
            st.error(f"Error loading document: {e}")
    else:
        st.error("Document name or page number not provided.")

if __name__ == "__main__":
    main()