import streamlit as st
import json
import os

def switch_theme(theme):
    # Path to the Streamlit config file
    config_path = ".streamlit/config.toml"
    
    # Create .streamlit directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Prepare the theme configuration
    if theme == "dark":
        theme_config = """
[theme]
base = "dark"
primaryColor = "#1E88E5"  # Adjusted for dark mode visibility
        """
    else:
        theme_config = """
[theme]
base = "light"
primaryColor = "#005591"  # Linde blue

[server]
runOnSave = true

[browser]
wideMode = true
        """
    
    # Write the configuration
    with open(config_path, "w") as f:
        f.write(theme_config)
    
    # Force a rerun to apply the theme
    st.rerun()

def main():
    # Initialize theme state
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    # Create theme toggle in sidebar
    with st.sidebar:
        st.title("Theme Settings")
        if st.toggle("Dark Mode", value=st.session_state.theme == 'dark'):
            if st.session_state.theme != 'dark':
                st.session_state.theme = 'dark'
                switch_theme('dark')
        else:
            if st.session_state.theme != 'light':
                st.session_state.theme = 'light'
                switch_theme('light')

    # Your main app content
    st.title("My Streamlit App")
    st.write("Toggle the theme using the sidebar!")
    
    # Example components
    st.button("Sample Button")
    st.slider("Sample Slider", 0, 100, 50)

if __name__ == "__main__":
    main()