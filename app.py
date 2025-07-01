import streamlit as st
import pandas as pd
import file_builder
import uuid
from pprint import pprint
from utility_functions import human_readable_size
from llm_client import LLMClient, get_model_info
from database import (create_context, initialize_database, update_context, get_context_by_id, 
                     get_messages_by_context_id, create_message)
from sidebar import display_sidebar
from sidebar_functions import list_contexts_button
from content_viewer import display_content_viewer 
from models import Message
from chat_interface import display_chat_interface

# --- Page Configuration (MUST BE THE VERY FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="LLM Context Manager",
    page_icon="🧠",
    layout="wide" # Use 'wide' layout for more space
)


def init_session_state():
    """
    Initializes or sets default values for Streamlit's session state variables.
    This ensures that all necessary state variables are present from the start
    and provides a clear overview of what the app tracks.
    """
    if "chat_messages_display" not in st.session_state:
        st.session_state.chat_messages_display = []
    
    if "selected_file_id" not in st.session_state:
        st.session_state.selected_file_id = None
        
    if "selected_group_id" not in st.session_state:
        st.session_state.selected_group_id = None

    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "general"

    if "webpage_url" not in st.session_state:
        st.session_state.webpage_url = ""

    if "viewer_content" not in st.session_state:
        st.session_state.viewer_content = {
            "type": "welcome_message",
            "data": "Please select an item from the sidebar."
        }

    if "current_model" not in st.session_state:
        st.session_state.current_model = {}
    
    # New: Initialize the OllamaLLM client
    if "current_client" not in st.session_state:
        st.session_state.current_client = LLMClient(max_response_length=5000)

    # Changed: Store only the context UUID instead of the full object
    if "current_context_id" not in st.session_state:
        st.session_state.current_context_id = None

    if "content_viewer_title" not in st.session_state:
        st.session_state.content_viewer_title = "Content Viewer"

    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None

    if 'show_webpage_downloader' not in st.session_state:
        st.session_state.show_webpage_downloader = False

    if 'show_file_uploader' not in st.session_state:
        st.session_state.show_file_uploader = False

    if 'response_streaming' not in st.session_state:
        st.session_state.response_streaming = False

    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "chat_analysis"

    if 'file_builder_id' not in st.session_state:
        st.session_state.file_builder_id = None

    if 'selected_message_text' not in st.session_state:
        st.session_state.selected_message_text = ""

    if 'concatenated_message_text' not in st.session_state:
        st.session_state.concatenated_message_text = ""

    if 'selected_message_num' not in st.session_state:
        st.session_state.selected_message_num = None

init_session_state()

if __name__ == "__main__":
    # Initialize database tables if they don't already exist
    initialize_database()

    tab1, tab2 = st.tabs(["ChatAnalysis", "FileBuilder"])

    with tab1:
        chat_col, viewer_col = st.columns([1,1], vertical_alignment="top", gap="small")
        with chat_col:
            display_chat_interface()
        with viewer_col:
            display_content_viewer()

    with tab2:
        with st.container():
            file_builder.display_file_builder()

    display_sidebar()