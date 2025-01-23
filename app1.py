import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF
import io
import tempfile
import os

# Page configuration
st.set_page_config(
    page_title="Document Q&A System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Gemini
def init_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return (
            genai.GenerativeModel('gemini-1.5-pro'),  # For text
            genai.GenerativeModel('gemini-1.5-flash')  # For vision
        )
    except Exception as e:
        st.error(f"Failed to initialize Gemini: {e}")
        return None, None

# Process PDF
def process_pdf(file, vision_model):
    content = {
        'text': {},
        'images': [],
        'type': 'pdf'
    }
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file.getvalue())
            tmp_file.flush()
            
            # Open PDF
            doc = fitz.open(tmp_file.name)
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                if text.strip():
                    content['text'][page_num + 1] = text
                
                # Extract images
                for img_index, img in enumerate(page.get_images()):
                    try:
                        # Get image data
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        # Get image description
                        response = vision_model.generate_content(
                            ["Describe this image concisely, focusing on key visual elements:", image]
                        )
                        
                        content['images'].append({
                            'page': page_num + 1,
                            'image': image,
                            'description': response.text if response else "No description available"
                        })
                    except Exception as e:
                        st.warning(f"Couldn't process image {img_index + 1} on page {page_num + 1}: {e}")
            
            doc.close()
            os.unlink(tmp_file.name)
            return content
            
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# Process single image
def process_image(file, vision_model):
    try:
        image = Image.open(file)
        response = vision_model.generate_content(
            ["Describe this image concisely, focusing on key visual elements:", image]
        )
        
        return {
            'image': image,
            'description': response.text if response else "No description available",
            'type': 'image'
        }
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None

# Answer questions
def answer_question(text_model, vision_model, documents, question):
    try:
        context_parts = []
        sources = []
        
        # Process each document
        for doc_name, doc_content in documents.items():
            if doc_content['type'] == 'pdf':
                # Add text content
                for page_num, text in doc_content['text'].items():
                    context_parts.append(f"Content from {doc_name} page {page_num}:\n{text}")
                    sources.append(f"{doc_name} page {page_num}")
                
                # Process images
                for img_data in doc_content['images']:
                    try:
                        response = vision_model.generate_content([
                            f"Based on this image, answer: {question}",
                            img_data['image']
                        ])
                        if response and response.text:
                            context_parts.append(response.text)
                            sources.append(f"Image on page {img_data['page']} of {doc_name}")
                    except Exception as e:
                        st.warning(f"Couldn't analyze image in {doc_name}: {e}")
            
            elif doc_content['type'] == 'image':
                try:
                    response = vision_model.generate_content([
                        f"Based on this image, answer: {question}",
                        doc_content['image']
                    ])
                    if response and response.text:
                        context_parts.append(response.text)
                        sources.append(f"Image: {doc_name}")
                except Exception as e:
                    st.warning(f"Couldn't analyze {doc_name}: {e}")
        
        if context_parts:
            # Generate comprehensive answer
            prompt = f"""Question: {question}

            Context from documents:
            {' '.join(context_parts)}

            Please provide a detailed answer that:
            1. Directly addresses the question
            2. Uses specific information from the sources
            3. Maintains a clear and organized structure
            4. References specific sources when citing information"""
            
            response = text_model.generate_content(prompt)
            if response and response.text:
                answer = response.text.strip()
                return f"{answer}\n\nSources:\n" + "\n".join(f"- {source}" for source in sources)
        
        return "No relevant information found in the provided documents."
    
    except Exception as e:
        st.error(f"Error generating answer: {e}")
        return None

# Main UI
def main():
    st.title("📚 Document Q&A System")
    
    # Initialize Gemini
    text_model, vision_model = init_gemini()
    if not text_model or not vision_model:
        st.stop()
    
    # Initialize session state
    if 'documents' not in st.session_state:
        st.session_state.documents = {}
    if 'qa_history' not in st.session_state:
        st.session_state.qa_history = []
    
    # File upload
    st.markdown("### 📤 Upload Documents")
    files = st.file_uploader(
        "Upload PDF documents",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Upload PDFs or images to analyze"
    )
    
    # Process files
    if files:
        progress = st.progress(0)
        for i, file in enumerate(files):
            if file.name not in st.session_state.documents:
                with st.spinner(f"Processing {file.name}..."):
                    if file.type == 'application/pdf':
                        content = process_pdf(file, vision_model)
                    else:
                        content = process_image(file, vision_model)
                    
                    if content:
                        st.session_state.documents[file.name] = content
            
            progress.progress((i + 1) / len(files))
        progress.empty()
        
        # Display documents
        st.markdown("### 📄 Uploaded Documents")
        for doc_name, content in st.session_state.documents.items():
            with st.expander(f"📎 {doc_name}"):
                if content['type'] == 'pdf':
                    # Show text content
                    st.markdown("#### Text Content")
                    tabs = st.tabs([f"Page {page}" for page in content['text'].keys()])
                    for i, (page, text) in enumerate(content['text'].items()):
                        with tabs[i]:
                            st.text_area("Content:", text, height=200, disabled=True)
                    
                    # Show images
                    if content['images']:
                        st.markdown("#### Images")
                        for img_data in content['images']:
                            st.image(img_data['image'], 
                                   caption=f"Page {img_data['page']}", 
                                   use_column_width=True)
                            st.markdown(f"**Description:** {img_data['description']}")
                else:
                    st.image(content['image'], use_column_width=True)
                    st.markdown(f"**Description:** {content['description']}")
        
        # Q&A Interface
        st.markdown("### ❓ Ask Questions")
        question = st.text_input(
            "Enter your question:",
            key="question_input",
            help="Ask about any content in the uploaded documents"
        )
        
        col1, col2 = st.columns([1, 5])
        with col1:
            ask = st.button("🔍 Ask", type="primary")
        with col2:
            clear = st.button("🗑️ Clear History", type="secondary")
        
        if ask and question:
            with st.spinner("Generating answer..."):
                answer = answer_question(text_model, vision_model, 
                                      st.session_state.documents, question)
                if answer:
                    st.markdown("#### Answer")
                    st.markdown(answer)
                    st.session_state.qa_history.append({
                        'question': question,
                        'answer': answer
                    })
        
        if clear:
            st.session_state.qa_history = []
            st.rerun()
        
        # Show history
        if st.session_state.qa_history:
            st.markdown("### 📜 Previous Q&A")
            for qa in reversed(st.session_state.qa_history):
                with st.expander(f"Q: {qa['question']}"):
                    st.markdown(qa['answer'])
    else:
        st.info("👆 Upload documents to get started!")

if __name__ == "__main__":
    main()