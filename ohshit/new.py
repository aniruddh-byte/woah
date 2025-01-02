import streamlit as st
import PyPDF2
import re

def extract_internal_title(pdf_file):
    """
    Extract the title from within the PDF document content.
    Specifically looks for the first line of text that appears to be a title.
    """
    try:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        if len(pdf_reader.pages) > 0:
            # Get first page text
            first_page = pdf_reader.pages[0]
            text = first_page.extract_text()
            
            # Split into lines and clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Look specifically for title patterns
            for line in lines[:5]:  # Check first 5 lines
                # Clean the line
                cleaned_line = line.strip()
                
                # If it's in ALL CAPS, it's likely a title
                if cleaned_line.isupper():
                    return cleaned_line
                
            # If no ALL CAPS title found, return first non-empty line
            return lines[0] if lines else None
            
        return None
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def main():
    st.title("📄 Document Title Extractor")
    st.write("Upload PDF files to extract titles from document content")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type="pdf",
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write("### Extracted Document Titles")
        
        for uploaded_file in uploaded_files:
            with st.expander(f"📄 {uploaded_file.name}"):
                # Create columns for layout
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.write("**File Name:**")
                    st.write("**Document Title:**")
                
                with col2:
                    st.write(uploaded_file.name)
                    # Extract and display title
                    title = extract_internal_title(uploaded_file)
                    if title:
                        st.write(title)
                    else:
                        st.write("❌ No title found in document content")
                
                # Show first page content for verification
                if st.button("Show First Page Content", key=uploaded_file.name):
                    try:
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        if len(pdf_reader.pages) > 0:
                            text = pdf_reader.pages[0].extract_text()
                            st.text_area("First Page Content:", text, height=200)
                    except Exception as e:
                        st.error(f"Error showing content: {str(e)}")
                
                # Reset file pointer
                uploaded_file.seek(0)
        
        # Add download button for results
        if len(uploaded_files) > 0:
            results = "\n".join([
                f"File: {f.name}\nTitle: {extract_internal_title(f)}\n"
                for f in uploaded_files
            ])
            st.download_button(
                label="Download Results",
                data=results,
                file_name="extracted_titles.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()