import os
import base64
import sqlite3
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from database_manager import db_manager
import google.generativeai as genai
import fitz # PyMuPDF
import tempfile

class PDFAnalyzer:
    def __init__(self):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            st.error(f"Error initializing Gemini: {str(e)}")
            self.model = None

    def extract_text_from_pdf(self, pdf_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                tmp_file.flush()
                
                doc = fitz.open(tmp_file.name)
                text = ""
                
                for page in doc:
                    text += page.get_text()
                
                doc.close()
                return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def extract_title(self, text):
        try:
            prompt = "What is the main title or heading of this document? Please provide only the title/heading without any additional explanation."
            content = f"{text}\n\n{prompt}"
            response = self.model.generate_content(content)
            return response.text.strip()
        except Exception as e:
            st.error(f"Error extracting title: {str(e)}")
            return None

    def summarize_text(self, text):
        try:
            prompt = """Please provide a concise summary of this document in around 150 words.
            Write it as a single, flowing paragraph.
            Focus on capturing the main ideas and key points of the document.
            Do not include any headings, bullet points, or lists."""
            
            content = f"{text}\n\n{prompt}"
            response = self.model.generate_content(content)
            return response.text.strip()
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")
            return None

def display_pdf(file_content):
    """Display a PDF file in the Streamlit app."""
    base64_pdf = base64.b64encode(file_content).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def ensure_directory_exists(path):
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        st.error(f"Failed to create directory: {str(e)}")
        return False

def save_document(conn, cursor, project_path, file_content, file_name, project, title, summary, category, date, version):
    """Save document and its details to filesystem and database"""
    if not ensure_directory_exists(project_path):
        raise Exception(f"Could not create directory: {project_path}")
        
    file_path = os.path.join(project_path, file_name)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")
    
    cursor.execute('''INSERT OR REPLACE INTO file_details 
                    (project, fileID, title, summary, category, date, version) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (project, file_name, title, summary, category, str(date), version))
    conn.commit()

def process_pdf(uploaded_file, analyzer):
    """Process PDF file to extract text, title, and summary"""
    text = analyzer.extract_text_from_pdf(uploaded_file)
    if not text:
        return None, None
    
    title = analyzer.extract_title(text)
    summary = analyzer.summarize_text(text)
    return title, summary

def create_document_form(selected_project):
    """Create a form to upload and add document details with automatic title and summary extraction"""
    st.markdown("""<style> [data-testid=stSidebar] { background-color: #D2E1EB; } </style>""", unsafe_allow_html=True)
    categories = db_manager.get_categories()
        
    with st.sidebar.form("document_form"):
        st.header("Document Upload")
        uploaded_file = st.file_uploader("Choose a file", type=["pdf"])
        category = st.selectbox("Category", categories)
        date = st.date_input('Document Date')
        version = st.text_input("Version")
        submit = st.form_submit_button("Upload")
        
        if submit and uploaded_file is not None:
            conn = None
            try:
                # Read file content
                file_content = uploaded_file.read()
                uploaded_file.seek(0)
                
                # Initialize analyzer and process document
                with st.spinner("Processing document with AI..."):
                    analyzer = PDFAnalyzer()
                    title, summary = process_pdf(uploaded_file, analyzer)
                    
                    if title is None or summary is None:
                        st.error("Failed to process document")
                        return
                    
                    # Display extracted information
                    st.info(f"Extracted Title: {title}")
                    st.info(f"Generated Summary: {summary}")
                
                # Database operations
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                
                # Get project path
                cursor.execute("SELECT file_path FROM project_paths WHERE file_name = ?", 
                             (selected_project,))
                project_path_result = cursor.fetchone()
                
                if not project_path_result:
                    st.error("Project path not found.")
                    return
                
                project_path = project_path_result[0]
                
                # Save document
                try:
                    save_document(
                        conn=conn,
                        cursor=cursor,
                        project_path=project_path,
                        file_content=file_content,
                        file_name=uploaded_file.name,
                        project=selected_project,
                        title=title,
                        summary=summary,
                        category=category,
                        date=date,
                        version=version
                    )
                    
                    st.success(f"Document '{title}' uploaded and analyzed successfully!")
                    st.session_state['reload_required'] = True
                    
                except Exception as e:
                    st.error(f"Failed to save document: {str(e)}")
                    
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
            finally:
                if conn:
                    conn.close()

    if st.session_state.get('reload_required', False):
        del st.session_state['reload_required']
        st.rerun()

def table_size(data):
    """ Calculate table height based on number of rows. """
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    calculated_height = min(max(min_height, len(data) * row_height + header_height), max_height)
    return calculated_height


def delete_document(project_name, file_name):
    """Delete a document from the database and file system."""
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT file_path FROM project_paths WHERE file_name = ?", (project_name,))
        project_path_result = cursor.fetchone()

        if not project_path_result:
            st.error("Project path not found.")
            return

        project_path = project_path_result[0]
        file_path = os.path.join(project_path, file_name)

        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute("DELETE FROM file_details WHERE project = ? AND fileID = ?", (project_name, file_name))
        conn.commit()
        return True  # Indicate success
    except Exception as e:
        st.error(f"Error deleting document: {e}")
        return False  # Indicate failure

def update_data_in_database(updated_df, selected_project):
    """Updates the database with changes from the grid."""

    conn = db_manager.get_connection()
    cursor = conn.cursor()

    try:
        for index, row in updated_df.iterrows():
            try:
                # Type conversion for date and version columns
                row['date'] = str(row['date'])
                row['version'] = str(row['version'])

                update_fields = []
                update_values = []
                for col in updated_df.columns:
                    if col != 'fileID':
                        update_fields.append(f"{col} = ?")
                        update_values.append(row[col])

                update_values.append(selected_project)
                update_values.append(row['fileID'])

                sql = f"UPDATE file_details SET {', '.join(update_fields)} WHERE project=? AND fileID=?"
                #st.write(f"Executing SQL: {sql}")  # Print the SQL query for debugging
                #st.write(f"With values: {update_values}") # print the values
                cursor.execute(sql, tuple(update_values))

            except sqlite3.Error as e:
                st.error(f"Error updating row {index}: {e}")
                conn.rollback()
                break
        else:
            conn.commit()
            st.success("Database updated successfully!")
            st.rerun()
    except sqlite3.Error as e:
        st.error(f"Error during update: {e}")
    finally:
        conn.close()

def view_document(selected_doc, selected_project):
    """Displays a selected document, directly using conn.cursor()."""
    conn = db_manager.get_connection() # get the connection
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT file_path FROM project_paths WHERE file_name = ?",
            (selected_project,)
        )
        project_path_result = cursor.fetchone()

        if project_path_result:
            file_path = os.path.join(project_path_result[0], selected_doc['fileID'])
            if selected_doc['fileID'].lower().endswith('.pdf'):
                try:
                    with open(file_path, 'rb') as file:
                        display_pdf(file.read())
                except FileNotFoundError:
                    st.error(f"File not found: {file_path}")
            else:
                st.warning(f"Preview not available for this file type: {os.path.splitext(file_path)[1]}")
        else:
            st.error("Project path not found. Cannot view document.")
    except sqlite3.Error as e:
        st.error(f"Error retrieving project path: {e}")
    finally:
        conn.close() 

def Documents_page():
    """
    Main function to display the Documents page.
    Handles project selection, file uploads, and document management.
    """
    SIDEBAR_LOGO = "linde-text.png"
    MAINPAGE_LOGO = "linde_india_ltd_logo.jpeg"

    sidebar_logo = SIDEBAR_LOGO
    main_body_logo = MAINPAGE_LOGO

    st.markdown("""
<style>
[data-testid="stSidebarNav"] > div:first-child > img {
    width: 900px; /* Adjust the width as needed */
    height: auto; /* Maintain aspect ratio */
}
</style>
""", unsafe_allow_html=True)
    
    st.logo(sidebar_logo, icon_image=main_body_logo)
    st.title("Documents")
    categories = db_manager.get_categories()
    selected_project = st.session_state.get("selected_project", None)

    if not selected_project:
        st.warning("Please select a project first.")
        return

    show_upload = st.session_state.get('show_upload', False)

    if st.button('Upload Documents'):
        show_upload = not show_upload
        st.session_state['show_upload'] = show_upload

    if show_upload:
        create_document_form(selected_project)

    conn = db_manager.get_connection()

    documents_df = pd.read_sql_query(
        "SELECT fileID, title, summary, category, date, version FROM file_details WHERE project = ?",
        conn,
        params=(selected_project,)
    )

    if documents_df.empty:
        st.info("No documents found for this project.")
        return

    gb = GridOptionsBuilder.from_dataframe(documents_df)
    gb.configure_column("fileID", editable=False)
    gb.configure_default_column(editable=True)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_column("summary", width=700, hide=True)
    gb.configure_column("category", editable=True, cellEditor="agSelectCellEditor", 
                   cellEditorParams={"values": categories}) 
    gb.configure_selection(selection_mode="single", use_checkbox=True)

    gridOptions = gb.build()

    ag_response = AgGrid(
        documents_df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=table_size(documents_df),
    )

    updated_data = ag_response['data']
    updated_df = pd.DataFrame(updated_data)
    selected_document = ag_response["selected_rows"]

    st.divider()

    if selected_document is not None and not selected_document.empty:
        selected_doc = selected_document.iloc[0]

        with st.container():
            st.subheader("Document Summary")
            st.write(selected_doc["summary"])
        
        # Add some spacing
        st.write("")

        col1, col2, col3 = st.columns(3)

        view_doct = st.session_state.get('view_doct', False)
                    
        with col1:
            if st.button("View Document"):
                view_doct = not view_doct
                st.session_state['view_doct'] = view_doct
                
            if view_doct:
                view_document(selected_doc, selected_project)
                
        with col2:
            if st.button("Save Changes"):
                if not updated_df.equals(documents_df):
                    selected_file_id = selected_doc['fileID']
                    df_to_update = updated_df[updated_df['fileID'] == selected_file_id]

                if not df_to_update.empty: # check if the dataframe is empty
                        update_data_in_database(df_to_update, selected_project)
                else:
                        st.error("Selected file not found in updated data.")
            
        
        with col3:
            # Initialize delete dialog state if it doesn't exist
            if "delete_files_dialog_open" not in st.session_state:
                st.session_state.delete_files_dialog_open = False

            # Delete File Button
            if st.button("Delete File"):
                if selected_document is not None and not selected_document.empty:
                    # Open delete confirmation dialog
                    st.session_state.delete_files_dialog_open = True

            # Show delete confirmation dialog
            if st.session_state.delete_files_dialog_open:
                @st.dialog("Delete Files")
                def delete_files_dialog():
                    #st.write("### Delete Confirmation")
                    selected_file_names = [selected_doc["fileID"]]
                    st.write(f"Are you sure you want to delete the following files?\n\n{', '.join(selected_file_names)}")
                    col1, col2 = st.columns(2)
                    if col1.button("Cancel"):
                        st.session_state.delete_files_dialog_open = False
                        st.rerun()  # Refresh to close dialog

                    if col2.button("Delete"):
                        success = delete_document(selected_project, selected_doc['fileID'])
                        if success:
                            st.success(f"Selected files have been deleted successfully.")
                        else:
                            st.error(f"Failed to delete files.")
                        st.session_state.delete_files_dialog_open = False
                        st.rerun()  # Refresh to update UI
                delete_files_dialog()
    else:
        st.warning("No file is currently selected.")

if __name__ == "__main__":
    Documents_page()