import streamlit as st
import ollama
import uuid
from database import (get_context_by_id, get_messages_by_context_id, create_message, create_file, delete_message)

def generate_new_message(message_container):

    current_messages = get_messages_by_context_id(st.session_state.current_context_id)
    # Format messages for LLM client
    message_list = list(map(
        lambda m: {
            "role": m.message_type if m.message_type != "file" else "user", 
            "content": m.message_text
        }, 
        current_messages
    ))

    with message_container.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Use streaming chat
            stream = st.session_state.current_client.generate_response(message_list, stream_response=True)
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    full_response += chunk['message']['content']
                    message_placeholder.markdown(full_response + "▌")
            
            # Remove cursor and display final response
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            full_response = f"Error in generate_new_message: {e}"
            print(full_response)

    # Create and store assistant message in database
    create_message(
        id=uuid.uuid4(),
        message_type="assistant", 
        message_text=full_response, 
        message_length=len(full_response),
        context_id=st.session_state.current_context_id,
    )

def generate_for_each_message(message_container):
    current_messages = get_messages_by_context_id(st.session_state.current_context_id)
    
    # Filter to only user messages (excluding assistant and file messages)
    user_messages = [m for m in current_messages if str(m.message_type) == "user" or str(m.message_type) == "file"]
    
    for message in user_messages:
        # Create a message_list with only one message
        message_list = [{
            "role": "user",
            "content": message.message_text
        }]

        with message_container.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Use streaming chat for each individual message
                stream = st.session_state.current_client.generate_response(message_list, stream_response=True)
                
                for chunk in stream:
                    if 'message' in chunk and 'content' in chunk['message']:
                        full_response += chunk['message']['content']
                        message_placeholder.markdown(full_response + "▌")
                
                # Remove cursor and display final response
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                full_response = f"Error in generate_for_each_message: {e}"
                print(full_response)

        # Create and store assistant message in database
        create_message(
            id=uuid.uuid4(),
            message_type="assistant", 
            message_text=full_response, 
            message_length=len(full_response),
            context_id=st.session_state.current_context_id,
        )

def display_chat_interface():
    """
    Defines and renders the main chat window and interaction logic.
    """
    st.write("<h5 style='text-align:center;'>LLM Interface</h5>", unsafe_allow_html=True)

    # Display current context info if available
    if st.session_state.current_context_id:
        # Fetch the current context from database using UUID
        current_context = get_context_by_id(st.session_state.current_context_id)
        
        if current_context:
            # Get messages for this context using database function
            messages_container = st.container(height=600)
            
            with messages_container:
                # Get messages for this context using database function
                st.session_state.chat_messages_display = get_messages_by_context_id(st.session_state.current_context_id)
                st.session_state.chat_messages_display.sort(key=lambda x: x.message_created_at)
                
                # Display chat messages from current context history on app rerun
                for message in st.session_state.chat_messages_display:
                    col1, col2 = st.columns([10, 1])
                    with col1:
                        if message.message_type == "file":
                            with st.chat_message("user", avatar="📁"):
                                st.code(message.message_text[:100] + "...")
                        else:
                            with st.chat_message(message.message_type):
                                st.markdown(message.message_text)
                    with col2:
                        if st.button("🗑️", key=f"button_del_{message.id}", use_container_width=True):
                            delete_message(message.id)
                            st.rerun()
                    
            
            # Create columns for checkbox and button
            col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
            
            with col1:
                # Add checkbox for "No Response" option
                no_response = st.checkbox("No Response", help="Check this to add your message without triggering a chatbot response")
            
            with col2:
                # Add "Run Now" button
                if st.button("Run Now", help="Generate a response with current messages", use_container_width=True):
                    # Generate LLM response without adding new user message
                    with st.spinner("Thinking..."):
                        # generate_new_message(messages_container)
                        generate_new_message(messages_container)

                    st.session_state.response_streaming = True
                    # Rerun to show the new message
                    st.rerun()

            with col3:
                # Add "Run Each" button
                # This will run each user message separately, allowing the LLM's context window to focus entirely on one message at a time
                if st.button("Run Each", help="Generate a response for each message in the chat history", use_container_width=True):
                    # Generate LLM response without adding new user message
                    with st.spinner("Thinking..."):
                        generate_for_each_message(messages_container)
                        st.session_state.response_streaming = True
                        # Rerun to show the new message
                        st.rerun()

            with col4:
                # Add "Edit Text" button
                if st.button("Edit Text", help="Open the full context history in a text editor", use_container_width=True):
                    # Create a temporary file to store the context history
                    temp_file_text = " ".join([message.message_text for message in st.session_state.chat_messages_display])
                    with open("temp_context.txt", "w") as temp_file:
                        # Write the context history to the file
                        temp_file.write(temp_file_text)
                    st.session_state.viewer_content["type"] = "edit_context"
                    st.session_state.viewer_content["data"] = temp_file_text
                    st.rerun()

            # Chat input for new messages
            if prompt := st.chat_input("Say something..."):
                # Create and store user message in database
                user_message_id = uuid.uuid4()
                create_message(
                    id=user_message_id,
                    message_type="user", 
                    message_text=prompt, 
                    message_length=len(prompt), 
                    context_id=st.session_state.current_context_id
                )
                st.session_state.chat_messages_display = get_messages_by_context_id(st.session_state.current_context_id)

                with messages_container.chat_message("user"):
                    st.markdown(prompt)
                

                # Only generate LLM response if "No Response" is not checked
                if not no_response:
                    # Generate LLM response
                    with st.spinner("Thinking..."):
                        # generate_new_message(messages_container)
                        generate_new_message(messages_container)

                # Rerun to show the new messages
                st.rerun()
                
        else:
            st.session_state.current_context_id = None
            st.error("Selected context not found in database.")
    else:
        st.info("Please select a context from the sidebar to start chatting.")