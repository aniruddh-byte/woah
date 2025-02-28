import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import tempfile
import os
import base64
import uuid
import json
from pathlib import Path

# Page configuration with sidebar hidden
st.set_page_config(page_title="Document Q&A System", layout="wide", initial_sidebar_state="collapsed")

# Hide the sidebar completely with CSS
hide_sidebar_style = """
    <style>
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

def init_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Failed to initialize Gemini: {e}")
        return None

def process_document(file, model):
    content = {'text': {}, 'type': 'pdf'}
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file.getvalue())
            tmp_file.flush()
            
            doc = fitz.open(tmp_file.name)
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    content['text'][page_num + 1] = text
                    
                # Convert page to image for display
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                content[f'page_{page_num + 1}'] = base64.b64encode(pix.tobytes("png")).decode('utf-8')
            
            # Save file content for download
            content['file_content'] = base64.b64encode(file.getvalue()).decode('utf-8')
            content['file_name'] = file.name
            
            doc.close()
            os.unlink(tmp_file.name)
            return content
            
    except Exception as e:
        st.error(f"Error processing document: {e}")
        return None

def answer_question(model, documents, question):
    try:
        context = []
        for doc_name, doc_content in documents.items():
            for page_num, text in doc_content['text'].items():
                context.append({
                    'text': text,
                    'page': page_num,
                    'document': doc_name
                })
        
        prompt_context = ' '.join([f"[Doc: {c['document']}, Page {c['page']}]: {c['text']}" for c in context])
        prompt = f"""Question: {question}
        Context: {prompt_context}
        Provide a concise answer in 50 words or less. Include the document name and page number.
        Format your response exactly like this:
        Answer text
        Referenced document: "document_name",  Page No.: X"""
        
        response = model.generate_content(prompt)
        return response.text.strip() if response else "No answer found."
    
    except Exception as e:
        st.error(f"Error generating answer: {e}")
        return None

def save_document_content():
    """Save documents in session state to a persistent location for the viewer page"""
    docs_dir = Path("docs_cache")
    docs_dir.mkdir(exist_ok=True)
    
    doc_paths = {}
    
    for doc_name, doc_content in st.session_state.documents.items():
        # Save encoded page images
        for page_key, page_data in doc_content.items():
            if page_key.startswith('page_'):
                page_num = int(page_key.split('_')[1])
                
                # Save the image data
                img_path = docs_dir / f"{doc_name.replace('/', '_')}_{page_num}.png"
                if not img_path.exists():  # Only save if doesn't exist
                    with open(img_path, 'wb') as f:
                        f.write(base64.b64decode(page_data))
                
                # Keep track of paths
                if doc_name not in doc_paths:
                    doc_paths[doc_name] = {}
                doc_paths[doc_name][str(page_num)] = str(img_path)
        
        # Save the file content for download if it exists
        if 'file_content' in doc_content and 'file_name' in doc_content:
            file_path = docs_dir / f"{doc_name.replace('/', '_')}_original.pdf"
            if not file_path.exists():  # Only save if doesn't exist
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(doc_content['file_content']))
            
            # Add file path to doc_paths for download
            if doc_name not in doc_paths:
                doc_paths[doc_name] = {}
            doc_paths[doc_name]['original_file'] = str(file_path)
    
    # Save a mapping file that the viewer page can access
    with open(docs_dir / "doc_paths.json", 'w') as f:
        json.dump(doc_paths, f)

def main():
    st.title("📚 Document Q&A System")
    
    model = init_gemini()
    if not model:
        st.stop()
    
    # Initialize session state
    if 'documents' not in st.session_state:
        st.session_state.documents = {}
    if 'qa_history' not in st.session_state:
        st.session_state.qa_history = []
    
    # File upload
    files = st.file_uploader("Upload PDF documents", type=['pdf'], accept_multiple_files=True)
    
    if files:
        for file in files:
            if file.name not in st.session_state.documents:
                with st.spinner(f"Processing {file.name}..."):
                    content = process_document(file, model)
                    if content:
                        st.session_state.documents[file.name] = content
        
        # Save documents for the viewer page to access
        save_document_content()
        
        # Q&A Interface
        st.markdown("### ❓ Ask Questions")
        question = st.text_input("Enter your question:")
        
        if st.button("🔍 Ask", type="primary") and question:
            with st.spinner("Generating answer..."):
                answer = answer_question(model, st.session_state.documents, question)
                if answer:
                    # Split answer into text and reference
                    answer_parts = answer.split('\nReferenced document:', 1)
                    if len(answer_parts) == 2:
                        answer_text = answer_parts[0].strip()
                        ref_info = answer_parts[1].strip()
                        
                        # Extract page number and document name
                        try:
                            doc_name = ref_info.split('"')[1]
                            page_num = int(ref_info.split('Page No.:', 1)[1].strip())
                            
                            # Store reference information
                            doc_ref = {'name': doc_name, 'page': page_num}
                        except:
                            doc_ref = None
                            st.warning("Couldn't parse page reference information")
                        
                        # Display answer and reference info
                        st.markdown("#### Answer")
                        st.write(answer_text)
                        st.write(f"Referenced document: {ref_info}")
                    
                    st.session_state.qa_history.append({
                        'id': str(uuid.uuid4()),
                        'question': question,
                        'answer': answer,
                        'doc_ref': doc_ref if 'doc_ref' in locals() else None
                    })
        
        # Show history with document reference buttons
        if st.session_state.qa_history:
            st.markdown("### 📜 Previous Q&A")
            for qa in reversed(st.session_state.qa_history):
                col1, col2 = st.columns([8, 2])
                
                with col1:
                    with st.expander(f"Q: {qa['question']}"):
                        st.markdown(qa['answer'])
                
                with col2:
                    if qa.get('doc_ref'):
                        # Get the URL for the viewer in a new window
                        doc_name = qa['doc_ref']['name']
                        page_num = qa['doc_ref']['page']
                        
                        # Generate correctly formatted URL for GitHub Codespaces or localhost
                        codespace_name = os.getenv('CODESPACE_NAME')
                        if codespace_name:
                            base_url = f"https://{codespace_name}-8501.app.github.dev"
                        else:
                            base_url = "http://localhost:8501"
                        
                        viewer_url = f"{base_url}/document_viewer?doc_name={doc_name}&page_num={page_num}"
                        
                        st.markdown(
                            f'<a href="{viewer_url}" target="_blank">'
                            '<button style="width:100%; padding:8px; background-color:#D3D3D3; color:black; border:none; border-radius:4px; cursor:pointer;">'
                            'View Document</button></a>',
                            unsafe_allow_html=True
                        )
    else:
        st.info("👆 Upload PDF documents to get started!")

if __name__ == "__main__":
    main()