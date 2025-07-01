import streamlit as st
from database import create_message, get_file_by_id
from utility_functions import get_token_length, replace_unicode_chars, normalize_unicode_text, get_file_text
import uuid
import os
import dotenv

def add_file_to_context(file_id: uuid.UUID, max_message_size: int = 8192) -> bool:
    """Adds a file to the current context, splitting into multiple messages if too large."""
    try:
        # Check if there's a current context ID
        if 'current_context_id' not in st.session_state or st.session_state.current_context_id is None:
            print("No active context found. Please create or select a context first.")
            return False
        
        # Retrieve the file from the database using file_id
        try:
            file_obj = get_file_by_id(file_id)
            if file_obj is None:
                print(f"File with ID {file_id} not found in database.")
                return False
        except Exception as e:
            print(f"Error retrieving file from database: {str(e)}")
            return False
        
        file_content = get_file_text(file_obj.file_name, file_obj.file_content)
        
        # Split content into multiple messages if needed
        token_length = get_token_length(file_content)[0]
        
        # Get context ID
        context_id = st.session_state.current_context_id
        
        # If the content fits in one message, create it directly
        if len(file_content) <= max_message_size:
            file_message = create_message(
                id=uuid.uuid4(), 
                message_type="file", 
                message_text=file_content, 
                message_length=token_length, 
                context_id=context_id
            )            
            if file_message is None:
                print("Failed to save message to database.")
                return False
        else:
            # Calculate how many messages we need
            num_messages = (len(file_content) + max_message_size - 1) // max_message_size  # Ceiling division
            
            # Split content into words
            words = file_content.split()
            total_words = len(words)
            
            # Calculate words per message (distribute evenly)
            words_per_message = total_words // num_messages
            extra_words = total_words % num_messages  # Some messages will get one extra word
            
            # Create messages by dividing words evenly
            word_index = 0
            for i in range(num_messages):
                # Calculate how many words this message should get
                words_in_this_message = words_per_message
                if i < extra_words:  # First 'extra_words' messages get one additional word
                    words_in_this_message += 1
                
                # Extract the words for this message
                message_words = words[word_index:word_index + words_in_this_message]
                message_text = " ".join(message_words)
                
                # Create database entry for this message
                message_token_length = get_token_length(message_text)[0]
                file_message = create_message(
                    id=uuid.uuid4(),
                    message_type="file",
                    message_text=message_text,
                    message_length=message_token_length,
                    context_id=context_id
                )
                
                if file_message is None:
                    print(f"Failed to save message part {i+1} to database.")
                    return False
                
                word_index += words_in_this_message
            

        st.success(f"File '{file_obj.file_name}' added to context successfully!")
        return True
        
    except Exception as e:
        print(f"Error adding file to context: {str(e)}")
        return False
    
def run_audio_generation(file_id: uuid.UUID):
    import subprocess
                        
    file_to_convert = get_file_by_id(file_id)
    if file_to_convert:
        file_name = file_to_convert.file_name
        file_string = file_to_convert.file_content.decode('utf-8')
    else:
        print("File not found in the database.")
        return
    
    # replace any uncommon characters with their ascii equivalents
    file_string = replace_unicode_chars(file_string)
    file_string = normalize_unicode_text(file_string)
    
    file_name = os.path.splitext(file_name)[0] + ".txt"
    TEMP_TEXT_FILE_DIR = dotenv.get_key('.env', 'TEMP_TEXT_FILE_DIR')
    file_path = os.path.join(TEMP_TEXT_FILE_DIR, file_name)
    with open(file_path, 'w') as file:
        file.write(file_string)
    
    try:
        # Run convert_file_to_audio in a separate process and capture output
        python_code = f'from audio_generation import convert_file_to_audio; convert_file_to_audio("{file_name}")'
        
        result = subprocess.run([
            "py", "-3.10", "-c", python_code
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            st.success(f"Audio generation completed for {file_name}")
            if result.stdout:
                print(f"Output: {result.stdout}")
        else:
            print(f"Audio generation failed for {file_name}")
            if result.stderr:
                print(f"Error: {result.stderr}")
                print(f"Error Printout: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print(f"Audio generation timed out for {file_name}")
    except Exception as e:
        print(f"Failed to start audio generation: {str(e)}")


    print("Audio generation completed")