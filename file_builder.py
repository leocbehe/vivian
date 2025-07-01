import streamlit as st
from typing import List
from database import get_file_list, get_messages_by_file_id
from models import File, Message
import uuid

def display_file_builder():
    """
    Displays the file builder interface.
    """
    col1, col2, col3, col4 = st.columns([1, 3, 3, 3], gap="small")
    
    with col1:
        st.subheader("Files")
        # Get all files from database
        files = get_file_list()
        
        # Create buttons for each file
        file_builder_id = None
        for file in files:
            if st.button(f"{file.file_name}", key=f"file_{file.file_id}"):
                file_builder_id = file.file_id
                st.session_state.file_builder_id = file_builder_id
        
        # Use session state to maintain selection
        if 'file_builder_id' in st.session_state:
            file_builder_id = st.session_state.file_builder_id
    
    with col2:
        st.subheader("Messages")
        messages = []
        if file_builder_id:
            # Get messages that share the selected file's ID
            messages = get_messages_by_file_id(file_builder_id)
            
            for i, message in enumerate(messages):
                c1, c2 = st.columns([3, 1], vertical_alignment='center')
                with c1:
                    st.html(
                        f"<p style='font-size: 14px;border: 1px solid grey;border-radius: 4px;padding: 8px;margin-top: 0px;margin-bottom: 0px;overflow-wrap: break-word;'>{message.message_text[:100]}...</p>",
                    )
                with c2:
                    if st.button(f"Message {i+1}", key=f"select_message_{message.id}"):
                        st.session_state.selected_message_num = message.id
                        st.session_state.selected_message_text = message.message_text
                        st.rerun()
        else:
            st.info("Select a file to view messages")
    
    with col3:
        t1, t2 = st.tabs(["Single Message View", "Combined Message View"])
        with t1:
            if messages:
                st.session_state.selected_message_text = st.text_area(
                    "Selected Message" if not st.session_state.selected_message_num else f"Message ID: {st.session_state.selected_message_num}",
                    value=st.session_state.selected_message_text,
                    height=600,
                    key="single_message_text",
                )
        with t2:
            if messages:
                concatenated_message_text = "\n\n".join([msg.message_text for msg in messages])
                st.session_state.concatenated_message_text = st.text_area(
                    "Combined Text",
                    value=concatenated_message_text,
                    height=600,
                    key="concatenated_messages"
                )
            else:
                st.info("No messages to display")
    
    with col4:
        operation_prompt = st.text_area(
            "Operation Prompt",
            height=160,
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Single Message Operation"):
                print(f"single message textarea:", st.session_state.selected_message_text)
                # Generate response using the operation prompt
                # st.session_state.current_client.generate_response(operation_prompt)
        with c2:
            if st.button("Combined Message Operation"):
                print(f"concatenated message textarea:", st.session_state.concatenated_message_text)
                # Generate response using the operation prompt
                # st.session_state.current_client.generate_response(operation_prompt)
        st.empty()