import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import json
import sqlite3
import streamlit as st
import google.generativeai as genai
from typing import Dict, List
from datetime import datetime
from database_manager import db_manager
from new_paths.view_reportsnew import view_reports_page

def initialize_gemini():
    """Initialize the Gemini AI model."""
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return None

def answer_question(model, question: str, documents: List[Dict], max_tokens: int = 1000) -> tuple:
    """
    Use AI to answer a question based on the provided documents.
    
    Args:
        model: The initialized Gemini model
        question: The question to answer
        documents: List of document dictionaries containing text content
        max_tokens: Maximum response length
    
    Returns:
        tuple: (answer, reference_doc)
    """
    try:
        # Combine all document contents
        combined_docs = ""
        for doc in documents:
            # Add document title and content
            combined_docs += f"\nDocument: {doc.get('title', 'Untitled')}\n{doc.get('summary', '')}\n"
        
        prompt = """Based on the provided documents, answer the following question. 
        Provide a clear, concise answer and specify which document(s) contained the information.
        Format your response as:
        Answer: [Your answer here]
        Source: [Document title]
        
        Documents:
        {documents}
        
        Question: {question}"""
        
        response = model.generate_content(
            prompt.format(documents=combined_docs, question=question),
            generation_config={"max_output_tokens": max_tokens}
        )
        
        # Parse response to extract answer and source
        response_text = response.text.strip()
        answer_parts = response_text.split("Source:", 1)
        
        if len(answer_parts) == 2:
            answer = answer_parts[0].replace("Answer:", "").strip()
            source = answer_parts[1].strip()
        else:
            answer = response_text
            source = "Multiple documents"
            
        return answer, source
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return "", "Error occurred"

def process_questions_with_ai(db_manager, report_id: int, documents: List[Dict]):
    """
    Process all questions for a report using AI and store the answers.
    
    Args:
        db_manager: DatabaseManager instance
        report_id: ID of the report
        documents: List of document dictionaries
    """
    model = initialize_gemini()
    if not model:
        st.error("Failed to initialize AI model")
        return False
        
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Get all questions for the report
        cursor.execute("""
            SELECT id, question_text
            FROM questionnaire_responses
            WHERE report_id = ?
        """, (report_id,))
        
        questions = cursor.fetchall()
        total_questions = len(questions)
        
        # Create a placeholder for progress
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for i, (question_id, question_text) in enumerate(questions, 1):
            # Update progress message
            progress_text.text(f"Processing question {i} of {total_questions}")
            
            # Get AI-generated answer
            answer, reference = answer_question(model, question_text, documents)
            
            # Update the database with the answer
            cursor.execute("""
                UPDATE questionnaire_responses
                SET answer = ?, reference = ?
                WHERE id = ?
            """, (answer, reference, question_id))
            
            # Update progress bar
            progress_bar.progress(i / total_questions)
        
        # Clear progress indicators
        progress_text.empty()
        progress_bar.empty()
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error processing questions: {str(e)}")
        return False
    finally:
        conn.close()

def questionnaire_table_size(questionnaire_data):
    """Calculate the appropriate height for the questionnaire AgGrid table."""
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    calculated_height = min(max(min_height, len(questionnaire_data) * row_height + header_height), max_height)
    return calculated_height

def enter_name():
    """Display an input field for the user to enter a report name."""
    st.subheader("1. Enter Report Name:")
    report_name = st.text_input("Enter Report Name:")
    if report_name:
        return report_name
    return None

def show_questionnaires():
    """Display questionnaires in an AgGrid table and handle selection."""
    questionnaire_data = db_manager.get_all_questionnaires()
    
    if questionnaire_data.empty:
        st.error("No questionnaires found in the database.")
        return None
    
    gb = GridOptionsBuilder.from_dataframe(questionnaire_data)
    gb.configure_default_column(editable=False)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_grid_options(
        # Theme customization
        rowStyle={'background-color': '#FFFFFF'},  # Default row color
        # Custom CSS properties for selection
        cssStyle={
            '--ag-selected-row-background-color': '#b7e4ff',
            '--ag-row-hover-color': '#F0FFFF',
            '--ag-selected-row-background-color-hover': '#a1d9ff',
            '--ag-range-selection-border-color': '#2196f3',
            '--ag-range-selection-background-color': '#e5f5ff',
            '--ag-cell-focus-color': '#89CFF0',
        }
    )

    gridOptions = gb.build()

    # Define custom CSS
    custom_css = {
        # Regular row hover
        ".ag-row:hover": {
            "background-color": "#F0FFFF !important"
        },
        ".ag-row-selected": {
            "background-color": "#b7e4ff !important"
        },
        ".ag-row-selected:hover": {
            "background-color": "#a1d9ff !important"
        },
        ".ag-checkbox-input-wrapper.ag-checked::after": {
            "color": "#2196f3"  # Checkbox color when selected
        },
        ".ag-cell-focus": {
            "border-color": "#2196f3 !important",
            #"background-color": "#e5f5ff !important"
        },
        ".ag-cell-focus:not(.ag-cell-range-selected)": {
            "border-color": "#2196f3 !important"
        }
    }
    
    st.subheader("2. Select a Questionnaire:")
    grid_response = AgGrid(
        questionnaire_data,
        gridOptions=gridOptions,
        fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        enable_enterprise_modules=False,
        key='questionnaire_grid',
        height=questionnaire_table_size(questionnaire_data),
        custom_css = custom_css
    )
    
    selected_rows = grid_response["selected_rows"]
    
    if selected_rows is not None and len(selected_rows) > 0:
        selected_questionnaire = selected_rows.iloc[0]
        display_questionnaire_details(selected_questionnaire)
        st.session_state.selected_category = selected_questionnaire['category']
        return selected_questionnaire
    
    st.warning("No questionnaire selected.")
    st.session_state.selected_category = None
    return None

def display_questionnaire_details(questionnaire):
    
    """Display questionnaire details in the sidebar."""
    st.sidebar.title("Questionnaire Details")
    st.sidebar.write(f"**Name:** {questionnaire['name']}")
    st.sidebar.write(f"**Category:** {questionnaire['category']}")
    st.sidebar.write(f"**User:** {questionnaire['user']}")
    st.sidebar.write(f"**Description:** {questionnaire['description']}")
    st.sidebar.write(f"**Date:** {questionnaire['date']}")
    st.sidebar.divider()

def show_filtered_documents(project_name):
    """Display filtered documents based on the selected questionnaire category."""
    if 'selected_category' not in st.session_state or st.session_state.selected_category is None:
        st.warning("Please select a questionnaire first to view relevant documents.")
        return None

    # Query file_details table for documents matching the category
    conn = db_manager.get_connection()
    query = """
        SELECT * FROM file_details 
        WHERE project = ? AND category LIKE ?
    """
    filtered_data = pd.read_sql_query(
        query, 
        conn, 
        params=(project_name, f"%{st.session_state.selected_category}%")
    )
    conn.close()

    if filtered_data.empty:
        st.info(f"No documents found for the category: {st.session_state.selected_category}")
        return None

    gb = GridOptionsBuilder.from_dataframe(filtered_data)
    gb.configure_default_column(editable=False)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_grid_options(
        # Theme customization
        rowStyle={'background-color': '#FFFFFF'},  # Default row color
        # Custom CSS properties for selection
        cssStyle={
            '--ag-selected-row-background-color': '#b7e4ff',
            '--ag-row-hover-color': '#F0FFFF',
            '--ag-selected-row-background-color-hover': '#a1d9ff',
            '--ag-range-selection-border-color': '#2196f3',
            '--ag-range-selection-background-color': '#e5f5ff',
            '--ag-cell-focus-color': '#89CFF0',
        }
    )

    gridOptions = gb.build()

    # Define custom CSS
    custom_css = {
        # Regular row hover
        ".ag-row:hover": {
            "background-color": "#F0FFFF !important"
        },
        ".ag-row-selected": {
            "background-color": "#b7e4ff !important"
        },
        ".ag-row-selected:hover": {
            "background-color": "#a1d9ff !important"
        },
        ".ag-checkbox-input-wrapper.ag-checked::after": {
            "color": "#2196f3"  # Checkbox color when selected
        },
        ".ag-cell-focus": {
            "border-color": "#2196f3 !important",
            #"background-color": "#e5f5ff !important"
        },
        ".ag-cell-focus:not(.ag-cell-range-selected)": {
            "border-color": "#2196f3 !important"
        }
    }

    st.subheader("3. Documents to be assigned to the questionnaire:")
    ag_response = AgGrid(
        filtered_data,
        gridOptions=gridOptions,
        fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        enable_enterprise_modules=False,
        key='documents_grid',
        height=documents_table_size(filtered_data),
        custom_css  = custom_css
    )

    selected_docs = ag_response["selected_rows"]
    if selected_docs is not None and len(selected_docs) > 0:
        st.write("Client documents to assign to the questionnaire:")
        st.table(pd.DataFrame(selected_docs))
        return selected_docs
    
    return None

def documents_table_size(filtered_data):
    """Calculate the appropriate height for the documents AgGrid table."""
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    calculated_height = min(max(min_height, len(filtered_data) * row_height + header_height), max_height)
    return calculated_height

def create_report(db_manager, project, questionnaire_name, report_name, selected_docs):
    """Create a new report in the database and process questions with AI."""
    try:
        # Create the report entry
        report_id = db_manager.create_report(
            project=project,
            questionnaire=questionnaire_name,
            name=report_name,
            num_docs=len(selected_docs)
        )

        if not report_id:
            st.error("Failed to create report entry.")
            return None

        # Handle different formats of selected_docs
        if isinstance(selected_docs, pd.DataFrame):
            docs_to_save = selected_docs.to_dict('records')
        elif isinstance(selected_docs, list):
            if selected_docs and isinstance(selected_docs[0], dict):
                docs_to_save = selected_docs
            else:
                docs_to_save = [{'title': title} for title in selected_docs]
        else:
            raise ValueError(f"Unexpected type for selected_docs: {type(selected_docs)}")

        # Save documents
        db_manager.save_included_documents(report_id, docs_to_save)
        
        # Set up questionnaire
        questions_df = db_manager.get_questionnaire_questions(questionnaire_name)
        if questions_df.empty:
            st.warning("No questions found for the questionnaire.")
        else:
            # Initialize questionnaire responses
            db_manager.update_questionnaire_completion(questions_df, report_id)
            
            # Process questions with AI
            with st.spinner("Processing questions with AI..."):
                success = process_questions_with_ai(db_manager, report_id, docs_to_save)
                if success:
                    st.success("Successfully processed all questions with AI!")
                else:
                    st.warning("Some questions could not be processed with AI.")

        st.success("Report created successfully!")
        return report_id

    except Exception as e:
        st.error(f"Error creating report: {str(e)}")
        return None

def Reports_page():
    """Main function to render the Reports page."""
    st.title("Reports")
    
    selected_project = st.session_state.get("selected_project", None)

    if not selected_project:
        st.warning("Please select a project first.")
        return

    project_details = db_manager.get_project_details(selected_project)
    if project_details is None:
        st.error("Project details not found.")
        return

    # Add view/create reports toggle
    if st.session_state.get('view_reports', False):
        if st.sidebar.button("Create Reports"):
            st.session_state.view_reports = False
            st.rerun()
    else:
        if st.sidebar.button("View Reports"):
            st.session_state.view_reports = True
            st.rerun()

    
    if st.session_state.get('view_reports', False):
        selected_questionnaire = st.session_state.get('selected_questionnaire', None)
        view_reports_page(selected_project,selected_questionnaire)
    else:
        display_reports_page(db_manager, selected_project, project_details)
        

def display_reports_page(db_manager, selected_project, project_details):
    
    SIDEBAR_LOGO = "linde-text.png"
    MAINPAGE_LOGO = "linde_india_ltd_logo.jpeg"

    sidebar_logo = SIDEBAR_LOGO
    main_body_logo = MAINPAGE_LOGO

    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] > div:first-child > img {
        width: 900px;
        height: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.logo(sidebar_logo, icon_image=main_body_logo)
    
    st.markdown("""
    <style>
        [data-testid=stSidebar] {
            background-color: #D2E1EB;
        }
    </style>
    """, unsafe_allow_html=True)

    """Display the main reports creation page."""
    # Display project information
    st.sidebar.title("Project Information")
    st.sidebar.write(f"**Name:** '{selected_project}'")
    st.sidebar.write(f"**Team Lead**: {project_details['team_lead']}")
    st.sidebar.write(f"**Description**: {project_details['description']}")
    st.sidebar.divider()

    # Get report name
    report_name = enter_name()
    st.session_state['report_name'] = report_name

    if not report_name:
        st.warning("Enter report name to Proceed!")
        return

    # Show questionnaires and handle selection
    selected_questionnaire = show_questionnaires()

    if selected_questionnaire is not None:
        st.session_state.selected_questionnaire = selected_questionnaire
        selected_docs = show_filtered_documents(selected_project)

        if selected_docs is not None and len(selected_docs) > 0:
            if st.button("Create Report"):
                create_report(
                    db_manager,
                    selected_project,
                    selected_questionnaire['name'],
                    report_name,
                    selected_docs
                )
    return selected_questionnaire