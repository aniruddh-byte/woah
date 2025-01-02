import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import tempfile
from typing import Dict
import os

# Configure page settings
st.set_page_config(page_title="Multi-Document Analyzer", layout="wide")

def initialize_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return None

def extract_text_from_pdf(pdf_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_file.flush()
            
            doc = fitz.open(tmp_file.name)
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            os.unlink(tmp_file.name)
            return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None

def answer_question_all_docs(model, documents: Dict[str, dict], question: str):
    try:
        combined_docs = ""
        for doc_name, doc_data in documents.items():
            combined_docs += f"\n\nDocument: {doc_name}\n{doc_data['text']}"
        
        prompt = """Provide a concise answer (20-30 words) to the question based on the provided documents.
        After the answer, add a new line and list the document name(s) where the information was found in brackets.
        Format: 
        Answer text
        [Source: Document1.pdf, Document2.pdf]
        
        Documents:
        {documents}
        
        Question: {question}"""
        
        content = prompt.format(documents=combined_docs, question=question)
        response = model.generate_content(content)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return None

def initialize_session_state():
    if 'documents' not in st.session_state:
        st.session_state.documents = {}
    if 'qa_history' not in st.session_state:
        st.session_state.qa_history = []

def process_uploaded_file(uploaded_file, model):
    if uploaded_file.name not in st.session_state.documents:
        text = extract_text_from_pdf(uploaded_file)
        if text:
            st.session_state.documents[uploaded_file.name] = {
                'text': text
            }
            return True
    return False

def main():
    st.title("Multi-Document Q&A System")
    
    model = initialize_gemini()
    if not model:
        st.stop()
    
    initialize_session_state()
    
    uploaded_files = st.file_uploader("Upload your documents (PDF)", 
                                    type=['pdf'], 
                                    accept_multiple_files=True)
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            process_uploaded_file(uploaded_file, model)
        
        for doc_name in st.session_state.documents.keys():
            with st.expander(f"📄 {doc_name}", expanded=False):
                st.text_area("Content:", 
                            st.session_state.documents[doc_name]['text'],
                            height=200,
                            disabled=True)
        
        question = st.text_input("Ask a question:")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            ask_button = st.button("Ask")
        with col2:
            clear_history = st.button("Clear History")
        
        if ask_button and question:
            if not st.session_state.documents:
                st.warning("Please upload at least one document first.")
            else:
                with st.spinner("Searching..."):
                    answer = answer_question_all_docs(model, st.session_state.documents, question)
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