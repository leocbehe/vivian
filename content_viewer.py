import streamlit as st
from datetime import datetime, timezone
import pprint
import uuid
import os
from utility_functions import human_readable_size, ingest_cache, clear_cache, get_file_cache_list, split_content_to_chunks, human_readable_date, get_token_length
from llm_client import get_model_info, LLMClient
from database import delete_context, delete_file, get_file_list, create_file, create_prompt, create_message
from sidebar_functions import list_contexts_button
from content_viewer_functions import add_file_to_context, run_audio_generation
from bs4 import BeautifulSoup
import pandas as pd

def display_content_viewer():
    """
    Defines and renders the content visualization area on the right.
    """
    st.html(f"<div style='text-align:center;font-size:24px;font-family:Verdana'>{st.session_state.content_viewer_title}</div>")
    
    viewer_type = st.session_state.viewer_content["type"]
    viewer_data = st.session_state.viewer_content["data"]

    match viewer_type:
        case "welcome_message":
            st.markdown(f"<div style='text-align:center;'>{viewer_data}</div>", unsafe_allow_html=True)
        case "text":
            st.text(viewer_data)
        case "code":
            language = st.session_state.viewer_content.get("language", "python")
            st.code(viewer_data, language=language)
        case "markdown":
            st.markdown(viewer_data, unsafe_allow_html=True)
        case "json":
            st.json(viewer_data)
        case "context_messages":
            context = viewer_data["context"]
            messages_markdown = viewer_data["messages_markdown"]
            
            st.markdown(messages_markdown)
            
            if context.messages:
                st.subheader("Message Details")
                for i, message in enumerate(context.messages):
                    with st.expander(f"Message {i+1} - {message.message_type.title()}"):
                        st.write(f"**ID:** {message.id}")
                        st.write(f"**Type:** {message.message_type}")
                        st.write(f"**Content:**")
                        st.text_area("", value=message.message_text, height=100, disabled=True, key=f"msg_{message.id}")
        case "model_list":
            for model_name in viewer_data:
                if st.button(f"- `{model_name}`", key=f"viewer_model_{model_name}", use_container_width=True):
                    model_display_dict = get_model_info(model_name).model_dump()
                    display_keys = ['details', 'modelinfo', 'parameters', 'template']
                    model_display_info = {k : model_display_dict[k] for k in model_display_dict.keys() if k in display_keys}
                    # Default context length is 8192. If the model has a different context length, use that instead. If the model
                    # has a context length that's specified in the modelfile, use that preferentially.
                    num_ctx = 8192
                    for k, v in model_display_info['modelinfo'].items():
                        if "context_length" in k or "context_window" in k:
                            print(f"assigning {v} to num_ctx")
                            num_ctx = v
                    for l in model_display_dict.get('parameters', '').splitlines():
                        if "num_ctx" in l:
                            num_ctx = int(l.split()[1])
                    model_display_string = pprint.pformat(model_display_info, indent=4)
                    
                    st.session_state.current_model = model_name
                    st.session_state.current_client = LLMClient(model_name, context_length=num_ctx)
                    print(f"LLMClient {model_name} initialized with num_ctx {num_ctx}")               

                    st.session_state.content_viewer_title = "Model Info"
                    st.session_state.viewer_content = {
                        "type": "model_info",
                        "data": model_display_string
                    }
                    st.rerun()
        case "context_list":
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
            with col1:
                st.write("<div>Context ID</div>", unsafe_allow_html=True)
            with col2:
                st.write("<div style='text-align:center;'>Created</div>", unsafe_allow_html=True)
            with col3:
                st.write("<div style='text-align:center;'>Select</div>", unsafe_allow_html=True)
            with col4:
                st.write("<div style='text-align:center;'>Delete</div>", unsafe_allow_html=True)
            st.html("<hr>")

            for context in viewer_data:
                id = str(context.id)  # Convert UUID to string
                
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                with col1:
                    st.markdown(f"`...{id[-12:]}`")
                with col2:
                    # Ensure both datetimes are timezone-aware and compatible
                    now = datetime.now(timezone.utc)

                    time_difference = now - context.created_at
                    days = time_difference.days
                    hours, remainder = divmod(time_difference.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)

                    if days > 0:
                        time_ago_string = f"{days} days ago"
                    elif hours > 0:
                        time_ago_string = f"{hours} hours ago"
                    else:
                        time_ago_string = f"{minutes} minutes ago"
                    st.markdown(f"<div style='text-align:center;'>{time_ago_string}</div>", unsafe_allow_html=True)
                with col3:
                    if st.button("Select", key=f"select_{id}", use_container_width=True):
                        st.session_state.current_context_id = id
                        st.rerun()
                with col4:
                    if st.button("Delete", key=f"delete_{id}", use_container_width=True):
                        print("Deleting context:", id)
                        delete_context(context.id)
                        list_contexts_button()
        case "file_list":
            col1, col2, col3 = st.columns([7, 2, 4])
            with col1:
                st.html(f"<div style='font-family:Verdana'>File Name</div>")
            with col2:
                st.html(f"<div style='font-family:Verdana'>File Size</div>")
            with col3:
                st.html(f"<div style='font-family:Verdana;text-align:center;'>Actions</div>")
            st.html("<hr>")
            for file in viewer_data:
                col1, col2, col3, col4 = st.columns([12, 3, 4, 3])
                with col1:
                    st.markdown(f"`{file.file_name}`")
                with col2:
                    st.write(human_readable_size(file.file_size))  # Use the helper function
                with col3:
                    if st.button("To Chat", key=f"add_to_context_{file.file_id}", use_container_width=True):
                        if add_file_to_context(file.file_id):
                            st.rerun()
                with col4:
                    if st.button("Delete", key=f"delete_{file.file_id}", use_container_width=True):
                        delete_file(file.file_id)
                        st.session_state.viewer_content = {
                            "type": "file_list",
                            "data": get_file_list(),
                        }
                        st.rerun()
        case "file_cache":
            # First we add buttons for clearing or ingesting the cached files
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Ingest Cache", key="ingest_cache", use_container_width=True):
                    ingest_cache(st.session_state.current_context_id)
                    st.session_state.viewer_content = {
                        "type": "file_cache",
                        "data": get_file_cache_list(),
                    }
                    st.rerun()
            with col2:
                if st.button("Clear Cache", key="clear_cache", use_container_width=True):
                    clear_cache()
                    st.session_state.viewer_content = {
                        "type": "file_cache",
                        "data": get_file_cache_list(),
                    }
                    st.rerun()

            if not viewer_data:
                st.markdown("No files in cache")
                return
            col1, col2 = st.columns([3, 1])
            with col1:
                st.html(f"<div style='font-family:Verdana'>File Name</div>")
            with col2:
                st.html(f"<div style='font-family:Verdana'>File Size</div>")
            for filename in viewer_data:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"`{filename[0]}`")
                with col2:
                    st.markdown(f"`{human_readable_size(filename[1])}`")
        case "table":
            df = pd.DataFrame(viewer_data)
            st.table(df)
        case "model_info":
            st.code(viewer_data, language="json")
        case "webpage":
            webpage_metadata = viewer_data.split("---")[0]
            webpage_content = viewer_data.split("---")[1]
            webpage_soup = BeautifulSoup(webpage_content, "html.parser")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(webpage_metadata)
            with col2:
                if st.button("Add to Context", use_container_width=True):
                    if not st.session_state.current_context_id:
                        st.warning("Please select a context first.")
                    else:                        
                        content_chunks = split_content_to_chunks(webpage_content)
                        for c in content_chunks:
                            create_message(id = uuid.uuid4(), message_type="file", message_text=c, message_length=get_token_length(c)[0], context_id = st.session_state.current_context_id)
                
            st.code(webpage_soup.prettify(), language="xml", line_numbers=True)
        case "webpage_text":
            webpage_metadata = viewer_data.split("---")[0]
            webpage_content = viewer_data.split("---")[1]
            
            st.markdown(webpage_metadata)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Add to Context", use_container_width=True):
                    if not st.session_state.current_context_id:
                        st.warning("Please select a context first.")
                    else:
                        content_chunks = split_content_to_chunks(webpage_content)
                        for c in content_chunks:
                            create_message(id = uuid.uuid4(), message_type="file", message_text=c, message_length=get_token_length(c)[0], context_id = st.session_state.current_context_id)
                        st.rerun()
            with col2:
                if st.button("Add To New Context", use_container_width=True):
                    pass
            with col3:
                if st.button("Ingest Response", use_container_width=True):
                    url = st.session_state.webpage_url
                    filename = url.replace('https://', '').replace('http://', '').replace('/', '_').replace('?', '_').replace('&', '_').replace('.', '_')
                    filename = f"{filename}.txt"
                    
                    # Convert content to bytes
                    content_bytes = webpage_content.encode('utf-8')
                    file_size = len(content_bytes)
                    
                    # Create the file
                    created_file = create_file(
                        file_name=filename,
                        file_content=content_bytes,
                        file_size=file_size,
                        file_summary=f"Webpage content from {url}"
                    )
                    
                    if created_file:
                        st.success(f"File '{filename}' created successfully!")
                    else:
                        st.error("Failed to create file.")
            st.divider()
            st.text(webpage_content)
                    
        case "context":
            current_context = viewer_data   
            if not current_context:
                st.warning("No context selected.")
                return
            # Display context information
            st.markdown(f"**Context ID:** `{current_context.id}`\n\n**Context Size:** `{current_context.context_size}`\n\n**Created At:** `{current_context.created_at}`")
            if current_context.summary:
                st.write(f"**Summary:** {current_context.summary}")
            
            # Display messages if they exist
            if current_context.messages:
                current_context.messages.sort(key=lambda x: x.message_created_at)
                st.write(f"Messages ({len(current_context.messages)})")
                for i, message in enumerate(current_context.messages):
                    message_content_preview = str(message.message_text)[:200]
                    with st.container(key=f"message_{i}", border=True):
                        c1,c2,c3 = st.columns([4, 5, 5])
                        with c1:
                            st.write(f"**ID:** `...{str(message.id)[-12:]}`")
                        with c2:
                            st.write(f"**Length:** {message.message_length} tokens")
                        with c3:
                            st.write(f"**Created At:** {human_readable_date(message.message_created_at)}")
                        st.code(message_content_preview, language="xml", line_numbers=True)
            else:
                st.info("No messages in this context.")
        
        case "files_to_audio":
            if not viewer_data:
                st.markdown("No files available for audio generation")
                return
                
            col1, col2 = st.columns([3, 1])
            with col1:
                st.html(f"<div style='font-family:Verdana'>File Name</div>")
            with col2:
                st.html(f"<div style='font-family:Verdana;text-align:center;'>Action</div>")
            st.html("<hr>")
            
            for file in viewer_data:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"`{file.file_name}`")
                with col2:
                    if st.button("Generate Audio", key=f"generate_audio_{file.file_id}", use_container_width=True):
                        with st.spinner("Please be patient, this may take a minute..."):
                            run_audio_generation(file.file_id)

        case "play_audio_files":
            if not viewer_data:
                st.markdown("No audio files available")
                return
            
            audio_file_dir = os.path.join(os.getcwd(), "tmp_audio")
            col1, col2 = st.columns([1, 1])
            with col1:
                st.html(f"<div style='font-family:Verdana'>File Name</div>")
            with col2:
                st.html(f"<div style='font-family:Verdana;text-align:center;'>Play Audio</div>")
            
            for filename in viewer_data:
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"`{filename}`")
                with col2:
                    filepath = os.path.join(audio_file_dir, filename)
                    st.audio(filepath)

        case "saved_prompts":
            if not viewer_data:
                st.markdown("No saved prompts available")
                return

            col1, col2 = st.columns([1, 3])
            with col1:
                st.html(f"<div style='font-family:Verdana'>Prompt Name</div>")
            with col2:
                st.html(f"<div style='font-family:Verdana;text-align:center;'>Prompt Text</div>")
            
            for prompt in viewer_data:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"`{prompt['name']}`")
                with col2:
                    st.markdown(f"`{prompt['content']}`")

        case "save_new_prompt":
            st.text_area("Prompt Name", key="new_prompt_name", height=68, placeholder="Enter a title...")
            st.text_area("Prompt Text", key="new_prompt_text", height=200, placeholder="Enter your prompt...")
            if st.button("Save Prompt"):
                new_prompt = st.session_state.new_prompt_text
                print(f"new prompt name: {st.session_state.new_prompt_name}")
                new_prompt_name = st.session_state.new_prompt_name
                print(f"new prompt name: {new_prompt_name}")
                saved_prompt = create_prompt(uuid.uuid4(), new_prompt, datetime.now(timezone.utc), name=new_prompt_name)
                if saved_prompt:
                    st.success("Prompt saved successfully!")
                else:
                    st.error("Failed to save prompt.")

        case "edit_context":
            if not viewer_data:
                st.markdown("No context available for editing")
                return
            st.text_area("Edit Context", key="edit_context", height=640, value=viewer_data)
            if st.button("Save To File"):
                # Create a File object with the edited context and save it to the database
                edited_context = st.session_state.edit_context
                edited_context = edited_context.replace("ASSISTANT:", "").replace("USER:", "").replace("SYSTEM:", "").replace("FILE:", "").strip()
                edited_context_bytes = bytes(edited_context.encode('utf-8'))
                edited_context_size = len(edited_context_bytes)
                create_file(f"{edited_context[:12]}.txt", edited_context_bytes, edited_context_size, "")
                st.success("Context saved to file successfully!")
        case _:
            st.warning(f"Unknown viewer type: {viewer_type}")
            st.markdown(viewer_data)