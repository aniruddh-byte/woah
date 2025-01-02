import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

#new Files
import new_paths.Categoriesnew as categories_page
import new_paths.Projectsnew as project_page
import new_paths.Documentsnew as documents_page
import new_paths.Questionnairenew as questionnaire_page
import new_paths.reportsnew as reports_page


st.set_page_config(layout="wide")

def main():
    """
    Main function to control the flow of the application.
    
    This function manages the navigation and page routing.
    """
    # Initialize session state for project selection if not exists
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None

    # The top menu bar
    selected = option_menu(
        menu_title=None,
        options=["Category", "Projects", "Docs", "Questionnaire", "Report"],
        icons=['list', 'files', 'upload', 'question', 'folder'], 
        menu_icon="cast", 
        default_index=1,
        orientation="horizontal"
    )

    # Page routing
    if selected == "Category":
        categories_page.Categories_page()

    if selected == "Projects":
        # Ensure the Projects page can set the selected project in session state
        project_page.projects_page()

    if selected == "Docs":
        # Pass the selected project to the Documents page
        documents_page.Documents_page()

    if selected == "Questionnaire":
        questionnaire_page.Questionnaire_page()

    if selected == "Report":
        reports_page.Reports_page()

if __name__ == "__main__":
    main()