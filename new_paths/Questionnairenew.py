import streamlit as st
import pandas as pd
from datetime import date
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from new_paths.manage_questionsnew import manage_questions_page
from database_manager import db_manager

def save_questionnaire_data(data, path):
    """
    Save questionnaire data to database.

    Args:
    data (pd.DataFrame): The questionnaire data to save.
    path (str): Unused parameter kept for compatibility.
    """
    for _, row in data.iterrows():
        db_manager.insert_questionnaire(
            name=row['name'],
            category=row['category'],
            user=row['user'],
            description=row['description'],
            date_str=str(row['date'])
        )
        
def update_questionnaire_data(updated_df, questionnaire_path):
    """
    Update the questionnaire data in the database.

    Args:
    updated_df (pd.DataFrame): The updated questionnaire data.
    questionnaire_path (str): Unused parameter kept for compatibility.
    """
    for _, row in updated_df.iterrows():
        db_manager.insert_questionnaire(
            name=row['name'],
            category=row['category'],
            user=row['user'],
            description=row['description'],
            date_str=str(row['date'])
        )
    st.success("Questionnaire data updated successfully!")

def upload_questions(selected_questionnaire):
    #Add file uploader for CSV
    uploaded_file = st.file_uploader("Upload questions CSV (first column = index, second column = question)", type=['csv'])
    if uploaded_file is not None:
        try:
            questions_df = pd.read_csv(uploaded_file)
            if len(questions_df.columns) < 2:
                st.error("CSV file must have at least two columns")
            else:
                # Save questions using first two columns regardless of names
                if db_manager.save_questions_from_csv(selected_questionnaire, questions_df):
                    st.success("Questions uploaded successfully!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")

def input_questions(selected_questionnaire):
    #Add file uploader for CSV
    uploaded_file = st.file_uploader("Upload questions CSV (first column = index, second column = question)", type=['csv'])
    if uploaded_file is not None:
        try:
            questions_df = pd.read_csv(uploaded_file)
            if len(questions_df.columns) < 2:
                st.error("CSV file must have at least two columns")
            else:
                # Save questions using first two columns regardless of names
                if db_manager.save_questions_from_csv(selected_questionnaire, questions_df):
                    st.success("Questions uploaded successfully!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")

def input_questionnaire_data(categories, questionnaire_path):
    """
    Display a form for inputting new questionnaire data and handle form submission.
    """
    with st.sidebar.form("Create_Questionnaire"):
        st.title("Create new Questionnaire")
        title = st.text_input("Title")
        category = st.selectbox("Category", categories)
        user_name = st.text_input("By User")
        description = st.text_area("Description")
        input_date = st.date_input('Date', value=date.today())

        submit = st.form_submit_button("Submit")

        if submit:
            if not title:
                st.error("Please enter a title for the questionnaire.")
                return
                
            # Save questionnaire to database
            if db_manager.insert_questionnaire(title, category, user_name, description, str(input_date)):
                # Save questions if there are any
                if db_manager.save_questions(title):
                        st.success(f"Questionnaire '{title}' questions saved successfully!")
                        st.rerun()
                else:
                    st.warning("No questions were uploaded.")
            else:
                st.error("Failed to save questionnaire data.")

def get_questions(questionnaire_path, selected_questionnaire):
    """
    Retrieve questions for a specific questionnaire from database.

    Args:
    questionnaire_path (str): Unused parameter kept for compatibility.
    selected_questionnaire (str): The name of the selected questionnaire.

    Returns:
    pd.DataFrame: A DataFrame containing the questions for the selected questionnaire.
    """
    return db_manager.get_questionnaire_questions(selected_questionnaire)


def table_size(questionnaire_path):
    """Calculate appropriate table height based on number of rows."""
    questionnaire_df = db_manager.get_all_questionnaires()
    row_height = 35
    header_height = 40
    min_height = 35
    max_height = 400
    calculated_height = min(max(min_height, len(questionnaire_df) * row_height + header_height), max_height)
    return calculated_height

def new_questions(selected_questionnaire_name):
    new_question = st.session_state.get('new_question', False)

    # Create a button to toggle the visibility of the content
    if st.button('Add New Questions'):
        new_question = not new_question
        st.session_state['new_question'] = new_question

    # Display the content based on the state variable
    if new_question:
        input_questions(selected_questionnaire_name)


def enter_values(categories, questionnaire_path):
    """
    Handle the 'New Questionnaire' button and form display logic.

    Args:
    categories (list): List of available categories.
    questionnaire_path (str): Unused parameter kept for compatibility.
    """
    show_content = st.session_state.get('show_content', False)

    # Create a button to toggle the visibility of the content
    if st.button('New Questionnaire'):
        show_content = not show_content
        st.session_state['show_content'] = show_content

    # Display the content based on the state variable
    if show_content:
        input_questionnaire_data(categories, questionnaire_path)

def show_questionnaires(questionnaire_path, categories):
    """
    Display existing questionnaires in an editable AgGrid table and handle user interactions.

    Args:
    questionnaire_path (str): Unused parameter kept for compatibility.
    categories (list): List of available categories.
    """
    questionnaire_data = db_manager.get_all_questionnaires()

    gb = GridOptionsBuilder.from_dataframe(questionnaire_data)
    gb.configure_default_column(editable=True)
    gb.configure_column("category", editable=True, cellEditor="agSelectCellEditor", 
                       cellEditorParams={"values": categories})
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gridOptions = gb.build()

    ag_response = AgGrid(
        questionnaire_data,
        gridOptions=gridOptions,
        editable=True,
        fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        enable_enterprise_modules=False,
        height=table_size(questionnaire_path)
    )

    updated_data = ag_response['data']
    selected_rows = ag_response["selected_rows"]
    
    if selected_rows is not None:
        selected_questionnaire_name = selected_rows['name']
    
    
    if selected_rows is not None:
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
            selected_questionnaire_name = selected_row['name']

            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                if st.button("Save Changes"):
                    update_questionnaire_data(updated_data, questionnaire_path)
                    st.rerun()

            with col2:
                if "delete_questionnaire_open" not in st.session_state:
                    st.session_state.delete_questionnaire_open = False
                    
                if st.button("Delete Questionnaire"):
                    if selected_rows is not None and not selected_rows.empty:
                        selected_questionnaire_name = selected_rows.iloc[0]["name"]
                        st.session_state.delete_questionnaire_open = True
                    else:
                        st.warning("No questionnaire is currently selected.")

                if st.session_state.delete_questionnaire_open:
                    @st.dialog("Delete Questionnaire")
                    def delete_questionnaire_dialog(updated_data):
                        st.write(f"Are you sure you want to delete the questionnaire '{selected_questionnaire_name}'?")
                        col1, col2 = st.columns(2)
                        if col1.button("Cancel"):
                            st.session_state.delete_questionnaire_open = False
                            st.rerun()
                        if col2.button("Delete"):
                            #current_data = pd.read_csv(questionnaire_path)
                            updated_data = updated_data[updated_data['name'] != selected_questionnaire_name]
                            update_questionnaire_data(updated_data, questionnaire_path)
                            if db_manager.delete_questionnaire(selected_questionnaire_name):
                                st.success(f"Questionnaire '{selected_questionnaire_name}' has been deleted.")
                                st.session_state.delete_questionnaire_open = False
                                st.rerun()

                    delete_questionnaire_dialog(updated_data)
                    
            manage_questions_page(questionnaire_path, selected_questionnaire_name)
            
            with col3:
                new_questions(selected_questionnaire_name)
    else:
        st.warning("No questionnaire is currently selected.")

def Questionnaire_page():
    """Render the main Questionnaire Management page."""
    SIDEBAR_LOGO = "linde-text.png"
    MAINPAGE_LOGO = "linde_india_ltd_logo.jpeg"

    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] > div:first-child > img {
        width: 900px;
        height: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    sidebar_logo = SIDEBAR_LOGO
    main_body_logo = MAINPAGE_LOGO
    
    st.logo(sidebar_logo, icon_image=main_body_logo)
    st.title("Questionnaire Management")

    # Get categories from database
    categories = db_manager.get_categories()
    
    # Initialize selected_row_data in session state
    if "selected_row_data" not in st.session_state:
        st.session_state.selected_row_data = None

    st.header("Existing Questionnaires")
    
    # Create a new questionnaire
    enter_values(categories, "unused_path")
    
    # Display the questionnaires
    show_questionnaires("unused_path", categories)