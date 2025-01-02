import os
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
# Import the database manager
from database_manager import db_manager

def ensure_project_paths_file_exists():
    """
    CHANGE: This function is no longer needed as database handles this
    Database will automatically create tables if they don't exist
    """
    pass

def create_form():
    """
    MAJOR CHANGES:
    - Replace CSV file operations with database insertions
    - Use database manager to store project information
    """
    st.markdown("""
    <style>
        [data-testid=stSidebar] {
            background-color: #D2E1EB;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar.form("project_form"):
        st.header("Project Creation")
        project = st.text_input("Project Name")
        description = st.text_area('Description')
        created_by = st.text_input('Created By')
        team_lead = st.text_input('Team Lead')
        date = st.date_input('Date')
        submit = st.form_submit_button("Submit")

        if submit:
            if not project:
                st.error("Project name cannot be empty.")
                return

            # CHANGE: Use database manager to insert project
            db_manager.insert_project(
                project, 
                description, 
                created_by, 
                team_lead, 
                str(date)
            )

            # Create project directory (keep existing logic)
            project_dir = os.path.join(os.getcwd(), "projects", project)
            os.makedirs(project_dir, exist_ok=True)

            # CHANGE: Use database manager to store project path
            db_manager.insert_project_path(project, project_dir)

            # Create project-specific CSV file
            file_details_file = f"{project}.csv"
            file_details_path = os.path.join(project_dir, file_details_file)
            if not os.path.exists(file_details_path):
                columns = ['fileID', 'Title', 'Summary', 'Category', 'Date', 'Version']
                pd.DataFrame(columns=columns).to_csv(file_details_path, index=False)
                st.success(f"Container created successfully.")

            st.success(f"Project '{project}' created successfully.")

def enter_values():
    """
    No changes to this function
    """
    show_content = st.session_state.get('show_content', False)

    if st.button('Create Project'):
        show_content = not show_content
        st.session_state['show_content'] = show_content

    if show_content:
        create_form()

def table_size(data):
    """
    No changes to this function
    Calculates table height based on data rows
    """
    row_height = 35
    header_height = 40
    min_height = 50
    max_height = 600
    calculated_height = min(max(min_height, len(data) * row_height + header_height), max_height)
    return calculated_height

def delete_project(project_name):
    """
    CHANGE: Use database manager to delete project
    Mostly same logic, but using database operations
    """
    # Use database manager to delete project
    if db_manager.delete_project(project_name):
        # Get project path from database
        conn = db_manager.get_connection()
        project_file_path_df = pd.read_sql_query(
            "SELECT file_path FROM project_paths WHERE file_name = ?", 
            conn, 
            params=(project_name,)
        )

        if not project_file_path_df.empty:
            project_dir = project_file_path_df.iloc[0]['file_path']
            
            # Delete project directory
            if os.path.exists(project_dir):
                for filename in os.listdir(project_dir):
                    file_path = os.path.join(project_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        st.error(f"Failed to delete {file_path}. Reason: {e}")
                try:
                    os.rmdir(project_dir)
                except Exception as e:
                    st.error(f"Failed to delete project directory. Reason: {e}")

        st.success(f"Project '{project_name}' deleted successfully!")
    else:
        st.error(f"Failed to delete project '{project_name}'.")

def Table_data():
    """
    MAJOR CHANGES:
    - Fetch data from SQLite database instead of CSV
    - Modify save changes to update database
    """
    # CHANGE: Retrieve projects from database
    data = db_manager.get_all_projects()
    
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(editable=False)
    gb.configure_column("description", editable=True)
    gb.configure_columns(["project", "created_by", "team_lead", "date"], editable=False)
    
    gb.configure_selection(selection_mode="single", use_checkbox=True)

    gridOptions = gb.build()

    ag_response = AgGrid(
        data,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=table_size(data),
    )
    updated_data = ag_response["data"]
    
    # CHANGE: Convert updated data to DataFrame
    updated_df = pd.DataFrame(updated_data)

    selected_project = ag_response["selected_rows"]
    if selected_project is not None:
        if not selected_project.empty:
            selected_project_name = selected_project.iloc[0]["project"]
            st.session_state["selected_project"] = selected_project_name
        else:
            # If no project is selected, keep the previously selected project
            st.session_state["selected_project"] = st.session_state.get("selected_project", None)
    else:
        # If selected_project is None, keep the previously selected project
        st.session_state["selected_project"] = st.session_state.get("selected_project", None)

    selected_project_name = st.session_state.get("selected_project", None)
    if selected_project_name:
        st.success(f"Currently project '{selected_project_name}' has been selected.")
    else:
        st.warning("No project is currently selected.")

    col1, col2, col3 = st.columns(3)
    with col1:
        # CHANGE: Modify save changes to update database
        if st.button("Save Changes"):
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            for _, row in updated_df.iterrows():
                cursor.execute('''
                    UPDATE projects 
                    SET description = ? 
                    WHERE project = ?
                ''', (row['description'], row['project']))
            
            conn.commit()
            st.success("Data saved successfully!")

    with col3:
        if "delete_dialog_open" not in st.session_state:
            st.session_state.delete_dialog_open = False

        if st.button("Delete Project"):
            if selected_project_name:
                st.session_state.delete_dialog_open = True
            else:
                st.warning("Please select a project to delete.")

        if st.session_state.delete_dialog_open:
            @st.dialog("Delete Project")
            def delete_project_dialog():
                st.write(f"Are you sure you want to delete the project '{selected_project_name}'?")
                col1, col2 = st.columns(2)
                if col1.button("Cancel"):
                    st.session_state.delete_dialog_open = False
                    st.rerun()
                if col2.button("Delete"):
                    delete_project(selected_project_name)
                    st.success(f"Project '{selected_project_name}' has been deleted.")
                    st.session_state.selected_project = None
                    st.session_state.delete_dialog_open = False
                    st.rerun()

            delete_project_dialog()

def projects_page():
    """
    No changes to this function
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
    st.title("Projects")
    cr, dele = st.columns(2)
    enter_values()
    Table_data()

# Optional: Migrate existing data if needed
def migrate_existing_data():
    """
    One-time migration from CSV to SQLite
    """
    db_manager.migrate_from_csv()

if __name__ == "__main__":
    projects_page()
# Run migration (comment out after first run)
# migrate_existing_data()