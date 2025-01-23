import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import tempfile
from typing import Dict
import os
from PIL import Image
import io

# Configure page settings
st.set_page_config(page_title="Document & Image Analyzer", layout="wide")

def initialize_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        text_model = genai.GenerativeModel('gemini-1.5-pro')
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        return text_model, vision_model
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return None, None

def get_image_description(vision_model, image):
    try:
        prompt = """Describe what you see in this image in a natural, flowing paragraph. 
        Include important details about visual elements, text, and context, but maintain 
        a conversational tone as if explaining it to someone."""
        response = vision_model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        st.error(f"Error getting image description: {str(e)}")
        return "Unable to generate image description"

def analyze_image(vision_model, image, question):
    try:
        prompt = f"""Looking at this image, please provide a natural, flowing response to 
        the following question: {question}
        
        Describe your analysis in a conversational paragraph style, integrating relevant 
        details from the image in a way that reads smoothly and naturally."""
        
        response = vision_model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        st.error(f"Error analyzing image: {str(e)}")
        return None

def process_image_file(image_file, vision_model):
    try:
        # Read the image file
        image = Image.open(image_file)
        
        # Get image description
        description = get_image_description(vision_model, image)
        
        return {
            'image': image,
            'description': description,
            'text': '',  # No text content for direct images
            'type': 'image'
        }
    except Exception as e:
        st.error(f"Error processing image file: {str(e)}")
        return None

def extract_content_from_pdf(pdf_file, vision_model):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_file.flush()
            
            doc = fitz.open(tmp_file.name)
            text = ""
            images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Extract text
                text += page.get_text()
                
                # Extract images
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Get image description
                    description = get_image_description(vision_model, image)
                    
                    images.append({
                        'page': page_num + 1,
                        'index': img_index,
                        'image': image,
                        'description': description
                    })
            
            doc.close()
            os.unlink(tmp_file.name)
            return {
                'text': text,
                'images': images,
                'type': 'pdf'
            }
    except Exception as e:
        st.error(f"Error extracting content from PDF: {str(e)}")
        return None


def answer_question_all_docs(text_model, vision_model, documents: Dict[str, dict], question: str):
    try:
        all_insights = []
        
        # Process each document/image
        for doc_name, doc_data in documents.items():
            if doc_data['type'] == 'pdf':
                # Handle PDF text content
                if doc_data['text']:
                    text_prompt = f"""Based on the following document, please provide a natural response to this question: {question}
                    Document: {doc_name}
                    Content: {doc_data['text']}
                    
                    Please respond in a flowing, paragraph style that integrates the information naturally."""
                    
                    text_response = text_model.generate_content(text_prompt).text.strip()
                    all_insights.append(text_response)
                
                # Handle PDF images
                for img_data in doc_data['images']:
                    image_response = analyze_image(vision_model, img_data['image'], question)
                    if image_response:
                        all_insights.append(f"From an image on page {img_data['page']} of {doc_name}, {image_response}")
            
            elif doc_data['type'] == 'image':
                # Handle direct image files
                image_response = analyze_image(vision_model, doc_data['image'], question)
                if image_response:
                    all_insights.append(f"Regarding the image '{doc_name}', {image_response}")
        
        if all_insights:
            # Combine all insights into a coherent response
            final_prompt = f"""Combine the following insights into a coherent, flowing response that answers this question: {question}

            Insights:
            {' '.join(all_insights)}

            Please provide a natural, paragraph-style response that integrates all relevant information smoothly."""
            
            final_response = text_model.generate_content(final_prompt).text.strip()
            return final_response
        
        return "I've examined the provided documents and images but couldn't find relevant information to answer your question."
    
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return None

def initialize_session_state():
    if 'documents' not in st.session_state:
        st.session_state.documents = {}
    if 'qa_history' not in st.session_state:
        st.session_state.qa_history = []

def process_uploaded_file(uploaded_file, text_model, vision_model):
    if uploaded_file.name not in st.session_state.documents:
        if uploaded_file.type.startswith('image/'):
            content = process_image_file(uploaded_file, vision_model)
        elif uploaded_file.type == 'application/pdf':
            content = extract_content_from_pdf(uploaded_file, vision_model)
        
        if content:
            st.session_state.documents[uploaded_file.name] = content
            return True
    return False

def main():
    st.title("Document & Image Q&A System")
    
    text_model, vision_model = initialize_gemini()
    if not text_model or not vision_model:
        st.stop()
    
    initialize_session_state()
    
    # Support both PDF and image files
    uploaded_files = st.file_uploader(
        "Upload your documents (PDF) or images (JPG, PNG)", 
        type=['pdf', 'jpg', 'jpeg', 'png'], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        with st.spinner("Processing documents and analyzing images..."):
            for uploaded_file in uploaded_files:
                process_uploaded_file(uploaded_file, text_model, vision_model)
        
        for doc_name, doc_data in st.session_state.documents.items():
            with st.expander(f"📄 {doc_name}", expanded=False):
                if doc_data['type'] == 'pdf':
                    if doc_data['text']:
                        st.text_area("Text Content:", doc_data['text'], height=200, disabled=True)
                    if doc_data['images']:
                        st.write(f"Number of images found: {len(doc_data['images'])}")
                        for img_data in doc_data['images']:
                            st.image(img_data['image'], 
                                    caption=f"Page {img_data['page']}, Image {img_data['index'] + 1}",
                                    use_column_width=True)
                            st.markdown(f"**Image Description:**\n{img_data['description']}")
                            st.divider()
                else:  # Image file
                    st.image(doc_data['image'], caption=doc_name, use_column_width=True)
                    st.markdown(f"**Image Description:**\n{doc_data['description']}")
        
        question = st.text_input("Ask a question about the documents or images:")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            ask_button = st.button("Ask")
        with col2:
            clear_history = st.button("Clear History")
        
        if ask_button and question:
            if not st.session_state.documents:
                st.warning("Please upload at least one document or image first.")
            else:
                with st.spinner("Analyzing content..."):
                    answer = answer_question_all_docs(
                        text_model,
                        vision_model,
                        st.session_state.documents,
                        question
                    )
                    if answer:
                        st.markdown("### Answer")
                        st.markdown(answer)
                        
                        st.session_state.qa_history.append({
                            'question': question,
                            'answer': answer
                        })
        
        if clear_history:
            st.session_state.qa_history = []
            st.rerun()
        
        if st.session_state.qa_history:
            st.markdown("### Previous Q&A")
            for i, qa in enumerate(reversed(st.session_state.qa_history), 1):
                with st.expander(f"Q: {qa['question']}", expanded=False):
                    st.markdown(qa['answer'])

if __name__ == "__main__":
    main()