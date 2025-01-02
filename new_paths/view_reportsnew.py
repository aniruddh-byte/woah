import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import io
import json
from database_manager import db_manager
from datetime import datetime
    
def view_reports_page(selected_project,selected_questionnaire):
    """
    Display the main page for viewing reports of a selected project.

    Args:
    selected_project (str): The name of the selected project.
    selected_questionnaire (str): The name of the selected questionnaire.
    db_manager (DatabaseManager): Instance of the database manager.
    """
    
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
    
    # Get project details from database
    project_info = db_manager.get_project_details(selected_project)
    if project_info is not None:
        st.sidebar.title("Project Information")
        st.sidebar.write(f"**Name:** {selected_project}")
        st.sidebar.write(f"**Team Lead:** {project_info['team_lead']}")
        st.sidebar.write(f"**Description:** {project_info['description']}")
        st.sidebar.divider()
    else:
        st.error(f"Could not find project details for '{selected_project}'")
        return
    
    # Find reports from database
    reports = find_reports_db(db_manager, selected_project)
    
    if reports:
        st.subheader("Select Report")
        
        # Create columns for report selection and delete button
        col1, col2 = st.columns([3,1])
        
        selected_report = st.selectbox(
                "Choose a report to view",
                options=[report['name'] for report in reports],
                format_func=lambda x: f"{x}"
            )
        
        if selected_report:
            report = next(r for r in reports if r['name'] == selected_report)
            
            # Display report details
            try:
                display_report_details_db(report, report['id'], selected_project, selected_project, selected_questionnaire, db_manager)
            except Exception as e:
                st.error(f"Error displaying report details: {str(e)}")
                st.write("Please check the report data and try again.")
    else:
        st.info("No reports found for this project.")

def find_reports_db(db_manager,project_name):
    """
    Find all reports associated with a given project from the database.

    Args:
    db_manager (DatabaseManager): Instance of the database manager.
    project_name (str): The name of the project to find reports for.

    Returns:
    list: A list of dictionaries containing report information.
    """
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, num_docs, created_at, questionnaire
            FROM reports
            WHERE project = ?
        """, (project_name,))
        
        reports = []
        for row in cursor.fetchall():
            reports.append({
                'id': row[0],
                'name': row[1],
                'num_docs': row[2],
                'created_at': row[3],
                'questionnaire': row[4]
            })
        return reports
    finally:
        conn.close()

def get_report_documents(db_manager, report_id, doc_type):
    """
    Retrieve documents associated with a report from the database.

    Args:
    db_manager (DatabaseManager): Instance of the database manager.
    report_id (int): The ID of the report.
    doc_type (str): Type of documents to retrieve ('included' or 'assigned').

    Returns:
    list: List of document information.
    """
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content
            FROM report_documents
            WHERE report_id = ? AND type = ?
        """, (report_id, doc_type))
        
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return []
    finally:
        conn.close()

def display_report_details_db(report, report_id, project_name, selected_project, selected_questionnaire, db_manager):
    """
    Display the details of a selected report from the database with viewable document references.
    """
    # Display report details in the sidebar
    st.sidebar.title("Report Details")
    st.sidebar.write(f"**Report Name:** {report['name']}")
    st.sidebar.write(f"**Created At:** {report['created_at']}")
    st.sidebar.write(f"**Number of Documents:** {report['num_docs']}")
    st.sidebar.write(f"**Questionnaire:** {report['questionnaire']}")
    st.sidebar.divider()
    
    # Get and display included documents
    st.subheader("Included Documents")
    included_docs = get_report_documents(db_manager, report['id'], 'included')
    documents_df = None
    if included_docs:
        documents_df = pd.DataFrame(included_docs)
        
        gb = GridOptionsBuilder.from_dataframe(documents_df)
        gb.configure_default_column(editable=False, width=150)
        gb.configure_column("project", hide=True)
        gridOptions = gb.build()
        
        AgGrid(documents_df,
               gridOptions=gridOptions,
               width='100%',
               fit_columns_on_grid_load=True,
               enable_enterprise_modules=False,
               height=table_size_drd(documents_df))
    
    # Get and display questionnaire completion data
    st.subheader("Questionnaire Completion")
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question_id, question_text, answer, reference
            FROM questionnaire_responses
            WHERE report_id = ?
        """, (report_id,))
        completion_data = cursor.fetchall()
        completion_df = pd.DataFrame(completion_data, columns=['question_id', 'question_text', 'answer', 'reference'])
        
        if not completion_df.empty:
            # Create a column for document viewing
            completion_df['view_document'] = ''
            
            gb_completion = GridOptionsBuilder.from_dataframe(completion_df)
            gb_completion.configure_default_column(editable=False, width=150)
            gb_completion.configure_column("question_id", headerName="Index", width=58)
            gb_completion.configure_column("question_text", headerName="Questions", width=230)
            gb_completion.configure_column("answer", width=300)
            gb_completion.configure_column("reference", headerName="Referenced Documents", width=200)
            gb_completion.configure_column("view_document", hide=True)
            
            gridOptions_completion = gb_completion.build()
            
            response = AgGrid(completion_df,
                   gridOptions=gridOptions_completion,
                   height=table_size_drd2(completion_df),
                   width='100%',
                   fit_columns_on_grid_load=True,
                   enable_enterprise_modules=False)
            
            # Handle document viewing
            selected_rows = response['selected_rows']
            if selected_rows:
                selected_row = selected_rows[0]
                if selected_row['reference']:
                    st.divider()
                    st.subheader("Referenced Document Contents")
                    
                    # Split references if multiple documents are referenced
                    referenced_docs = [doc.strip() for doc in selected_row['reference'].split(',')]
                    
                    for doc_name in referenced_docs:
                        if documents_df is not None:
                            doc_row = documents_df[documents_df['filename'] == doc_name]
                            if not doc_row.empty:
                                with st.expander(f"Document: {doc_name}"):
                                    st.write("**Content:**")
                                    st.text_area("", value=doc_row['content'].iloc[0], height=200, disabled=True)
                            else:
                                st.warning(f"Document '{doc_name}' not found in included documents.")
            
    finally:
        conn.close()
    
    # Generate Excel report
    project_info = db_manager.get_project_details(project_name)
    excel_data = generate_excel_report(project_name, report, project_info, 
                                     pd.DataFrame(included_docs), completion_df)

    st.download_button(
        label="Download Excel Report",
        data=excel_data,
        file_name=f"{project_name}_{report['name']}_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    col1, col2 = st.columns([1,3])    
    
    if "delete_report_open" not in st.session_state:
        st.session_state.delete_report_open = False
        
    with col1:
        if st.button("Delete Report", key="delete1"):
            st.session_state.delete_report_open = True
            
    if st.session_state.delete_report_open:
        delete_report_dialog_db(report, selected_project, db_manager)


def delete_report_dialog_db(report, project_name, db_manager):
    """
    Display a confirmation dialog for deleting a report from the database.

    Args:
    report (dict): The report information.
    project_name (str): The name of the project.
    db_manager (DatabaseManager): Instance of the database manager.
    """
    @st.dialog("Delete Report")
    def delete_report_dialog_content():
        st.write(f"Are you sure you want to delete the report '{report['name']}' for project '{project_name}'?")
        col1, col2 = st.columns(2)
        if col1.button("Cancel"):
            st.session_state.delete_report_open = False
            st.rerun()
        if col2.button("Delete"):
            delete_report_db(report['id'], db_manager)
            st.success(f"Report '{report['name']}' has been deleted.")
            st.session_state.delete_report_open = False
            st.rerun()

    delete_report_dialog_content()

def delete_report_db(report_id, db_manager):
    """
    Delete a report and its associated data from the database.

    Args:
    report_id (int): The ID of the report to delete.
    db_manager (DatabaseManager): Instance of the database manager.
    """
    conn = db_manager.get_connection()
    try:
        cursor = conn.cursor()
        # Delete report documents
        cursor.execute("DELETE FROM report_documents WHERE report_id = ?", (report_id,))
        # Delete questionnaire responses
        cursor.execute("DELETE FROM questionnaire_responses WHERE report_id = ?", (report_id,))
        # Delete report
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
    finally:
        conn.close()

# Helper functions remain the same
def table_size_drd(df):
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    return min(max(min_height, len(df) * row_height + header_height), max_height)

def table_size_drd2(completion_df):
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    return min(max(min_height, len(completion_df) * row_height + header_height), max_height)

def generate_excel_report(project_name, report, project_info, included_docs_df, completion_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Report')

        # Project details
        worksheet.write(0, 0, 'Project Name:')
        worksheet.write(0, 1, project_name)
        worksheet.write(1, 0, 'Team Lead:')
        worksheet.write(1, 1, project_info['team_lead'])
        worksheet.write(2, 0, 'Description:')
        worksheet.write(2, 1, project_info['description'])

        # Included documents table
        start_row = 4
        worksheet.write(start_row, 0, 'Included Documents:')
        included_docs_df.to_excel(writer, sheet_name='Report', startrow=start_row + 1, index=False)
        
        # Document count
        doc_count = len(included_docs_df)
        worksheet.write(start_row + doc_count + 2, 0, f'Total documents: {doc_count}')

        # Questionnaire completion table
        start_row = start_row + doc_count + 8
        worksheet.write(start_row, 0, 'Questionnaire Completion:')
        completion_df.to_excel(writer, sheet_name='Report', startrow=start_row + 1, index=False)

        # Auto-fit columnsstreamlit run 
        for i, col in enumerate(included_docs_df.columns):
            column_len = max(included_docs_df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, column_len + 2)

        for i, col in enumerate(completion_df.columns):
            column_len = max(completion_df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, column_len + 2)

    return output.getvalue()