import streamlit as st
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode, GridOptionsBuilder
import pandas as pd
from database_manager import db_manager

def add_category():
    """
    This function creates a Streamlit popover with an input field for adding a new category.
    When a category is added, it updates the database and refreshes the page.
    """
    with st.popover("Add a new category"):
        new_category = st.text_input("Click enter to add categories")
        if new_category and st.button("Add Category"):
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (categories) VALUES (?)", (new_category,))
                conn.commit()
                st.success(f"Category '{new_category}' added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding category: {e}")
            finally:
                conn.close()

def table_size(categories_df):
    """
    Calculate the appropriate height for the AgGrid table based on the number of rows.

    Args:
    categories_df (pd.DataFrame): The DataFrame containing the categories.

    Returns:
    int: The calculated height for the AgGrid table in pixels.
    """
    # Calculate the height based on the number of rows
    row_height = 35  # Approximate height of each row in pixels
    header_height = 40  # Approximate height of the header in pixels
    min_height = 50  # Minimum height of the grid
    max_height = 600  # Maximum height of the grid
    calculated_height = min(max(min_height, len(categories_df) * row_height + header_height), max_height)
    return calculated_height

def display_categories(categories_df):
    """
    Display the categories in an interactive AgGrid table and handle category management operations.
    """
    gb = GridOptionsBuilder.from_dataframe(categories_df)
    gb.configure_default_column(editable=False)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_default_column(fontSize=50)

    gridOptions = gb.build()

    ag_response = AgGrid(
        categories_df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=table_size(categories_df)
    )

    updated_data = ag_response["data"]
    updated_df = pd.DataFrame(updated_data)

    selected_rows = ag_response["selected_rows"]

    col1, col2 = st.columns([3,1])
    with col1:
        add_category()

    with col2:
        if st.button("Delete Category"):
            if selected_rows is not None and len(selected_rows) > 0:
                st.session_state.delete_dialog_open = True
            else:
                st.warning("No category is currently selected.")

        if st.session_state.delete_dialog_open:
            @st.dialog("Delete Category")
            def delete_category_dialog(selected_rows):
                """Display a confirmation dialog for deleting selected categories."""
                # Debug information
                #st.write("Debug Info:")
                #st.write(f"Type of selected_rows: {type(selected_rows)}")
                #st.write("Content of selected_rows:")
                #st.write(selected_rows)

                st.write(f"Are you sure you want to delete the selected categories?")
                col1, col2 = st.columns(2)
                
                if col1.button("Cancel"):
                    st.session_state.delete_dialog_open = False
                    st.rerun()

                if col2.button("Delete"):
                    conn = db_manager.get_connection()
                    cursor = conn.cursor()
                    try:
                        # Convert selected_rows to DataFrame if it isn't already
                        if isinstance(selected_rows, pd.DataFrame):
                            rows_to_process = selected_rows
                        else:
                            rows_to_process = pd.DataFrame(selected_rows)

                        # Get the category column (might be 'Categories' or 'categories')
                        category_column = 'Categories' if 'Categories' in rows_to_process.columns else 'categories'
                        
                        if category_column in rows_to_process.columns:
                            deleted_categories = []
                            for category in rows_to_process[category_column]:
                                cursor.execute("DELETE FROM categories WHERE categories = ?", (category,))
                                deleted_categories.append(category)
                            
                            if deleted_categories:
                                conn.commit()
                                st.success(f"Successfully deleted categories: {', '.join(deleted_categories)}")
                            else:
                                st.warning("No categories were deleted.")
                        else:
                            st.error(f"Could not find category column. Available columns: {rows_to_process.columns.tolist()}")
                            
                    except Exception as e:
                        st.error(f"Error deleting categories: {str(e)}")
                        st.write("Error details:", type(e).__name__)
                    finally:
                        conn.close()

                    st.session_state.delete_dialog_open = False
                    st.rerun()
                
            delete_category_dialog(selected_rows)

    return updated_df

def Categories_page():
    """
    This function sets up the page layout, loads the categories from the database,
    and calls the display function to show and manage the categories.
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
        
    st.title("Categories")
    
    # Fetch categories from database
    conn = db_manager.get_connection()
    try:
        categories_df = pd.read_sql_query("SELECT categories as Categories FROM categories", conn)
    except Exception as e:
        st.error(f"Error fetching categories: {e}")
        categories_df = pd.DataFrame(columns=["Categories"])
    finally:
        conn.close()

    display_categories(categories_df)