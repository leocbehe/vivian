import streamlit as st
from database import get_file_list, get_context_list, create_file, create_context, get_context_by_id
from web_client import WebClient
import pprint as pp
import os
import sidebar_functions

def display_sidebar():
    """
    Defines and renders the content of the Streamlit sidebar.
    """
        
    with st.sidebar:
        if st.session_state.current_tab == "file_builder":
            # Display the file list
            st.header("Select File")
            file_list = get_file_list()
            if file_list:
                for file in file_list:
                    st.button(f"{file.file_name[:16]}...{file.file_name[-16:]}" if len(file.file_name) > 32 else file.file_name, use_container_width=True)
            else:
                st.write("No files found.")
        if st.session_state.current_tab == "chat_analysis":
            # Display current model and context without extra header
            current_model = st.session_state.current_model
            current_context_id = st.session_state.current_context_id if 'current_context_id' in st.session_state and st.session_state.current_context_id else None
            # st.markdown(f"Current Model: `{current_model}`")
            st.html("<div style='text-align:center;'>Current Context: N/A</div>" if current_context_id is None \
                    else f"<div style='text-align:center;font-family:Trebuchet MS;font-size:14px;'>Context: {str(current_context_id)}</div>")
            
            st.html("<div style='text-align:center;font-size:20px;font-family:Trebuchet MS;'>Views</div>")
            if st.button("List Files", use_container_width=True):
                sidebar_functions.list_files_button()

            if st.button("List Models", use_container_width=True):
                sidebar_functions.list_models_button()

            if st.button("List Contexts", use_container_width=True):
                sidebar_functions.list_contexts_button()
            
            if st.button("List Cached Files", use_container_width=True):
                sidebar_functions.list_cached_files_button()

            if st.button("View Context", use_container_width=True):
                sidebar_functions.view_context_button()

            if st.button("Saved Prompts", use_container_width=True):
                sidebar_functions.view_saved_prompts_button()

            # st.html("<hr>")

            st.html("<div style='text-align:center;font-size:20px;font-family:Trebuchet MS;'>Actions</div>")
            if st.button("Listen to Audio", use_container_width=True):
                sidebar_functions.listen_to_audio_button()

            if st.button("New Context", use_container_width=True, key="new_chat_button"):
                sidebar_functions.new_context_button()

            if st.button("Import File", use_container_width=True):
                st.session_state.show_file_uploader = True
                st.session_state.uploaded_file = None
            if st.session_state.show_file_uploader:
                sidebar_functions.import_file_button()

            if st.button("Get Webpage", use_container_width=True):
                st.session_state.show_webpage_downloader = True
            if st.session_state.show_webpage_downloader:
                sidebar_functions.get_webpage_button()

            if st.button("File To Audio", use_container_width=True):
                sidebar_functions.list_files_for_audio_generation()

            if st.button("Save New Prompt", use_container_width=True):
                sidebar_functions.save_new_prompt_button()