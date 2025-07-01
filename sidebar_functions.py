import streamlit as st
from database import get_file_list, get_context_list, create_file, create_context, get_context_by_id, get_all_prompts
from web_client import WebClient
import pprint as pp
import os
from utility_functions import get_file_cache_list, get_token_length, replace_unicode_chars

# --- Sidebar Button Functions ---
def listen_to_audio_button():
    """Logic for the Listen to Audio button."""
    # Display a list of .wav file names from the tmp_audio/ directory, with a play button next to each file
    audio_files = [f for f in os.listdir("tmp_audio/") if f.endswith(".wav")]
    if audio_files:
        st.session_state.viewer_content = {
            "type": "play_audio_files",
            "data": audio_files
        }
    st.rerun()

def new_context_button():
    """Logic for the New Context button."""
    # Create a new context using the database function
    try:
        new_context = create_context("", st.session_state.current_client.context_length)
        if new_context:
            st.session_state.current_context_id = new_context.id  # Store only the ID
        else:
            st.error("Failed to create new context.")
            return

        # Retrieve the context from the database using the ID
        current_context = get_context_by_id(st.session_state.current_context_id)

        # Display the messages of the current context in the viewer
        if current_context and current_context.messages:
            # Format messages for display
            messages_display = f"### Context Messages\n**Context ID:** {current_context.id}\n\n"
            
            for i, message in enumerate(current_context.messages, 1):
                messages_display += f"**Message {i} ({message['message_type']}):**\n"
                messages_display += f"{message['message_text']}\n\n"
                messages_display += "---\n\n"
            
            st.session_state.viewer_content = {
                "type": "context_messages",
                "data": {
                    "context_id": current_context.id,
                    "messages_markdown": messages_display
                }
            }
        elif current_context:
            # No messages in the context yet
            context_info = f"### New Context Created\n"
            context_info += f"**Context ID:** {current_context.id}\n"
            context_info += f"**Context Size:** {current_context.context_size}\n"
            context_info += f"**Summary:** {current_context.summary or 'No summary'}\n"
            context_info += f"**Group ID:** {current_context.context_group_id or 'No group'}\n\n"
            context_info += "**Messages:** No messages yet. Start chatting to add messages to this context."
            
            st.session_state.viewer_content = {
                "type": "markdown",
                "data": context_info
            }
        else:
            st.error("Could not retrieve context from database.")
        
        st.rerun()
    except Exception as e:
        # Handle any errors that might occur during context creation
        st.error(f"Failed to create new context: {str(e)}")

def list_models_button():
    """Logic for the List Models button."""
    # Call the actual list_installed_models method from your Ollama client
    models_list = st.session_state.current_client.list_installed_models()
    
    if models_list and isinstance(models_list[0], str) and "Error" in models_list[0]:
        # If an error message was returned
        display_content = f"### Error Listing Models:\n{models_list[0]}"
        viewer_type = "markdown" # Still markdown for error messages
        st.session_state.viewer_content = {
            "type": viewer_type,
            "data": display_content
        }
    else:
        # Format the list of models nicely for display
        if models_list:
            model_names = [model_data['model'] for model_data in models_list]
            st.session_state.viewer_content = {
                "type": "model_list",
                "data": model_names
            }
            st.session_state.content_viewer_title = "Available Models"
        else:
            st.session_state.viewer_content = {
                "type": "markdown",
                "data": "### No Ollama models found.\nMake sure Ollama is running and you have pulled some models (e.g., `ollama pull gemma3:12b`)."
            }
    st.rerun()

def list_contexts_button():
    """Logic for the List Contexts button."""
    try:
        context_list = get_context_list()
        if context_list:
            # Assign the context_list to the viewer content
            st.session_state.viewer_content = {
                "type": "context_list",
                "data": context_list
            }
            st.session_state.content_viewer_title = "Contexts"
            st.rerun()  # Refresh the app to update the viewer with the new context list
        else:
            st.session_state.viewer_content = {
                "type": "markdown",
                "data": "### No contexts found."
            }
            st.session_state.content_viewer_title = "Contexts"
            st.rerun()
    except Exception as e:
        st.error(f"Failed to list contexts: {str(e)}")

def list_files_button():
    try:
        file_list = get_file_list() 
        if file_list:
            st.session_state.viewer_content = {
                "type": "file_list",
                "data": file_list,
            }
        else:
            st.session_state.viewer_content = {
                "type": "markdown",
                "data": "### No files found."
            }
        st.rerun()
    except Exception as e:
        st.error(f"Failed to list files: {str(e)}")

def import_file_button():
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "csv", "json", "htm", "html"])
    
    if uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded_file:
        create_file(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.size)
        st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        st.session_state.last_uploaded_file = uploaded_file.name
    
    if st.button("Close"):
        st.session_state.show_file_uploader = False
        st.rerun()

# main entry point for any webpage interaction. all code should use this function to interact with webclient.
def download_webpage(url, text_only=False):
    """
    Download webpage content and save to tmp_files/ directory.
    
    Args:
        url: The URL to download
        
    Returns:
        webpage_content: the content of the webpage
    """
    try:
        aggressive = True
        # Ensure tmp_files directory exists
        tmp_files_dir = "tmp_files"
        os.makedirs(tmp_files_dir, exist_ok=True)
        
        # Create WebClient with tmp_files directory as output
        web_client = WebClient(output_dir=tmp_files_dir, aggressive_html_cleaning=aggressive)
        if text_only:
            response, webpage_content = web_client.get_webpage_text(url)
            if webpage_content:
                return response, webpage_content
            else:
                return response, None
        else:
            response, webpage_content = web_client.get_webpage_file(url)
            if webpage_content:
                return response, webpage_content
            else:
                return response, None
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"Error: {str(e)}", None

def get_webpage_button():
    """Logic for the Get Webpage button."""
    # Initialize session state for URL input if not exists
    if 'webpage_url' not in st.session_state:
        st.session_state.webpage_url = ""
    
    # URL input field
    url = st.text_input(
        "Enter URL to download:",
        value=st.session_state.webpage_url,
        placeholder="https://example.com",
        key="url_input"
    )

    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        # Download button
        if st.button("Get Page", key="bt_get_webpage", use_container_width=True):
            if url.strip():
                result, webpage_content = download_webpage(url, text_only=False)
                token_length = get_token_length(webpage_content)[0]
                st.session_state.webpage_url = url.strip()
                
                if not webpage_content:
                    st.error(f"Failed to download webpage: {result}")
                    st.session_state.viewer_content = {
                        "type": "markdown",
                        "data": f"### Error Downloading Webpage\n**URL:** {url}\n**Error:** {result}"
                    }
                else:
                    # Success - show simplified download results
                    success_message = f"**Content Length:** {token_length} tokens\n"
                    success_message += "---\n\n"
                    
                    # Combine success message with webpage content
                    combined_content = success_message + webpage_content
                    
                    st.success(f"File downloaded successfully from URL: {result.url}")
                    
                    st.session_state.content_viewer_title = "Webpage Response"
                    st.session_state.viewer_content = {
                        "type": "webpage",
                        "data": combined_content
                    }
                    
                    # Store the URL for potential reuse
                    st.session_state.webpage_url = url.strip()
                
                st.rerun()
    with col2:
        # Only download page text
        if st.button("Get Text", key="bt_download_page_text", use_container_width=True):
            if url.strip():
                result, webpage_content = download_webpage(url, text_only=True)
                token_length = get_token_length(webpage_content)[0]
                st.session_state.webpage_url = url.strip()

                if not webpage_content:
                    st.error(f"Failed to download page text: {result}")
                    st.session_state.viewer_content = {
                        "type": "markdown",
                        "data": f"### Error Downloading Webpage Text\n**URL:** {url}\n**Error:** {result}"
                    }
                else:
                    # Success - show simplified download results
                    success_message = f"**Content Length:** {token_length} tokens\n"
                    success_message += "---"

                    combined_content = success_message + webpage_content
                    st.success(f"Webpage text downloaded successfully!")
                    st.session_state.content_viewer_title = "Webpage Text Response"
                    st.session_state.viewer_content = {
                        "type": "webpage_text",
                        "data": combined_content
                    }

                st.rerun()
    
    with col3:
        # Close button
        if st.button("Close", key="bt_close_webpage", use_container_width=True):
            st.session_state.show_webpage_downloader = False
            st.rerun()

def list_cached_files_button():
    st.session_state.content_viewer_title = "Cached Files"
    st.session_state.viewer_content = {
        "type": "file_cache",
        "data": get_file_cache_list(),
    }
    st.rerun()

def view_context_button():
    st.session_state.content_viewer_title = "Current Context"
    if not st.session_state.current_context_id:
        st.warning("No context selected. Please select a context.")
    else:
        current_context = get_context_by_id(st.session_state.current_context_id)
        if current_context:
            st.session_state.viewer_content = {
                "type": "context",
                "data": current_context
            }
        else:
            st.error(f"Could not retrieve context with ID: {st.session_state.current_context_id}")
        st.rerun()

def list_files_for_audio_generation():
    """Logic for listing files for audio generation."""
    try:
        file_list = get_file_list()
        for f in file_list:
            print(f"File: {f}")
        if file_list:
            st.session_state.viewer_content = {
                "type": "files_to_audio",
                "data": file_list
            }
        else:
            st.session_state.viewer_content = {
                "type": "files_to_audio", 
                "data": []
            }
    except Exception as e:
        print(f"Failed to list files for audio generation: {str(e)}")
    st.rerun()

def view_saved_prompts_button():
    st.session_state.content_viewer_title = "Saved Prompts"
    st.session_state.viewer_content = {
        "type": "saved_prompts",
        "data": [{'name': p.name, 'content': p.content} for p in get_all_prompts()]
    }
    st.rerun()

def save_new_prompt_button():
    st.session_state.content_viewer_title = "Save New Prompt"
    st.session_state.viewer_content = {
        "type": "save_new_prompt",
        "data": {}
    }
    st.rerun()