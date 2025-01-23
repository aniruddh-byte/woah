import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
import os

# New Files
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
        project_page.projects_page()

    if selected == "Docs":
        documents_page.Documents_page()

    if selected == "Questionnaire":
        questionnaire_page.Questionnaire_page()

    if selected == "Report":
        reports_page.Reports_page()

if __name__ == "__main__":
    main()