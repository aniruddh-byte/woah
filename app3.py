import streamlit as st
import json
from pathlib import Path
import base64
import io
import os
import tempfile

# Page configuration
st.set_page_config(page_title="Document Viewer", layout="wide")



def display_pdf_data(file_content):
    """Display a PDF file in the Streamlit app."""
    base64_pdf = base64.b64encode(file_content).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    st.title("📄 Document Viewer")
    
    # Get session ID from URL parameters
    session_id = st.query_params.get("session", None)
    
    if session_id:
        # Load document data from temporary file
        temp_file = Path("temp_docs") / f"{session_id}.json"
        if temp_file.exists():
            try:
                with open(temp_file) as f:
                    session_data = json.load(f)
                
                st.markdown(f"### {session_data['document']}")
                st.markdown(f"#### Page {session_data['page']}")
                
                # Re-create PDF from the page
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    # Write original PDF content
                    tmp_file.write(base64.b64decode(session_data['content']))
                    tmp_file.flush()
                    
                    # Read as PDF
                    with open(tmp_file.name, "rb") as pdf_file:
                        base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
                        display_pdf_data(base64_pdf)
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                
                # Clean up the session file
                temp_file.unlink()
            except Exception as e:
                st.error(f"Error loading document: {e}")
        else:
            st.error("Document session expired or not found")
    else:
        st.error("No document specified")

if __name__ == "__main__":
    main()