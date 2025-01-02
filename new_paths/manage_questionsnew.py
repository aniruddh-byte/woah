import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode
from database_manager import db_manager
import google.generativeai as genai
import tempfile
import os

def initialize_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return None

def answer_question(model, document_text, question: str):
    try:
        prompt = """Provide a concise answer (20-30 words) to the question based on the document content.
        Include the relevant section/function name in brackets after the answer.
        
        Document:
        {document}
        
        Question: {question}"""
        
        content = prompt.format(document=document_text, question=question)
        response = model.generate_content(content)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return None


def manage_questions_page(questionnaire_path, selected_questionnaire):
    """
    Manage the questions page for a selected questionnaire.
    
    Args:
    questionnaire_path (str): Path to CSV file if uploading questions.
    selected_questionnaire (str): The name of the selected questionnaire.
    """
    st.title(f"Manage Questions for '{selected_questionnaire}'")

    # Add file uploader for CSV
    #uploaded_file = st.file_uploader("Upload questions CSV (first column = index, second column = question)", type=['csv'])
    #if uploaded_file is not None:
    #    try:
    #        questions_df = pd.read_csv(uploaded_file)
    #        if len(questions_df.columns) < 2:
    #            st.error("CSV file must have at least two columns")
    #        else:
    #            # Save questions using first two columns regardless of names
    #            if db_manager.save_questions_from_csv(selected_questionnaire, questions_df):
    #                st.success("Questions uploaded successfully!")
    #                st.rerun()
    #    except Exception as e:
    #        st.error(f"Error reading CSV file: {e}")

    # Initialize delete dialog state if not exists
    if 'delete_dialog_open' not in st.session_state:
        st.session_state.delete_dialog_open = False

    # Load existing questions from database (now sorted)
    questions_df = db_manager.get_questionnaire_questions(selected_questionnaire)

    if questions_df.empty:
        st.write("No existing questions found. Please add new questions.")
    else:
        gb = GridOptionsBuilder.from_dataframe(questions_df)
        gb.configure_column("identifier", headerName="Index", width=100)
        gb.configure_column("question", editable=False, width=300)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        gb.configure_default_column(editable=False)
        gridOptions = gb.build()

        ag_response = AgGrid(
            questions_df,
            gridOptions=gridOptions,
            fit_columns_on_grid_load=True,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            enable_enterprise_modules=False,
            height=table_size(questions_df),
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )

        selected_rows = ag_response["selected_rows"]

        col1, col2, col3 = st.columns([2,1,1])
        
        with col1:
            add_new_questions(questions_df, selected_questionnaire, col1)

        with col2:
                # Convert DataFrame to CSV
                csv = questions_df.to_csv(index=False)

                # Create download button
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{selected_questionnaire}_questions.csv",
                    mime="text/csv",
                )
        
        with col3:
            if st.button("Delete Questions"):
                if selected_rows is not None and len(selected_rows) > 0:
                    st.session_state.delete_dialog_open = True
                else:
                    st.warning("No questions are currently selected.")

            if st.session_state.delete_dialog_open:
                @st.dialog("Delete Questions")
                def delete_questions_dialog(selected_rows):
                    st.write(f"Are you sure you want to delete {len(selected_rows)} questions?")
                    col1, col2 = st.columns(2)
                    
                    if col1.button("Cancel"):
                        st.session_state.delete_dialog_open = False
                        st.rerun()

                    if col2.button("Delete"):
                        db_manager.delete_questions_from_db(selected_questionnaire, selected_rows)
                        st.session_state.delete_dialog_open = False
                        st.rerun()
                
                delete_questions_dialog(selected_rows)

        

def add_new_questions(questions_df, selected_questionnaire, ad):
    """
    Add new questions to the questionnaire in database.

    Args:
    questions_df (pd.DataFrame): The DataFrame containing existing questions.
    selected_questionnaire (str): The name of the selected questionnaire.
    ad: The Streamlit column object for adding questions.
    """
    with ad.popover("Add New Questions"):
        # Add file uploader for CSV
        
        new_identifier = st.text_input("Enter question index/number seperated by '.':")
        new_question = st.text_area("Enter the new question:")

        if st.button("Add Question"):
            if new_identifier and new_question:
                # Check if identifier already exists
                existing_identifiers = questions_df['identifier'].astype(str).tolist()
                if new_identifier in existing_identifiers:
                    st.error(f"Index {new_identifier} already exists. Please use a different index.")
                else:
                    if db_manager.insert_question(selected_questionnaire, new_identifier, new_question):
                        st.success("New question added!")
                        st.rerun()
            else:
                st.warning("Please enter both index and question.")

#def delete_selected_questions(selected_questions, questions_df, selected_questionnaire, dl):


def table_size(questions_df):
    """Calculate the appropriate height for the AgGrid table."""
    row_height = 35
    header_height = 40
    min_height = 25
    max_height = 400
    calculated_height = min(max(min_height, len(questions_df) * row_height + header_height), max_height)
    return calculated_height
