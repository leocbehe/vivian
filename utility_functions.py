import os
from typing import Optional
from database import create_file, create_message, get_context_by_id
from models import Context, Message
from datetime import datetime
import unicodedata
import PyPDF2
import io
import pytz
import shutil
import uuid

# Use tiktoken instead of transformers
_tokenizer = None

# Method 1: Unicode normalization and ASCII transliteration
def normalize_unicode_text(text):
    # Normalize Unicode characters to their closest ASCII equivalents
    normalized = unicodedata.normalize('NFKD', text)
    # Remove diacritical marks and keep only ASCII characters
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text

# Method 2: More comprehensive character replacement
def replace_unicode_chars(text: str) -> str:
    # Common Unicode replacements
    replacements = {
        # Single quotes
        '\u2019': '\u0027',  # Right single quotation mark → Apostrophe
        '\u2018': '\u0027',  # Left single quotation mark → Apostrophe
        '\u201a': '\u0027',  # Single low-9 quotation mark → Apostrophe
        '\u201b': '\u0027',  # Single high-reversed-9 quotation mark → Apostrophe
        '\u2032': '\u0027',  # Prime → Apostrophe
        '\u00b4': '\u0027',  # Acute accent → Apostrophe
        '\u0060': '\u0027',  # Grave accent → Apostrophe (or keep as backtick if preferred)
        
        # Double quotes
        '\u201c': '\u0022',  # Left double quotation mark → Quotation mark
        '\u201d': '\u0022',  # Right double quotation mark → Quotation mark
        '\u201e': '\u0022',  # Double low-9 quotation mark → Quotation mark
        '\u201f': '\u0022',  # Double high-reversed-9 quotation mark → Quotation mark
        '\u2033': '\u0022',  # Double prime → Quotation mark
        '\u00ab': '\u0022',  # Left-pointing double angle quotation mark → Quotation mark
        '\u00bb': '\u0022',  # Right-pointing double angle quotation mark → Quotation mark
        
        # Backticks (if you want to keep backticks separate, change the grave accent above)
        # '\u0060': '\u0060',  # Grave accent (already ASCII backtick)
        
        # Dashes
        '\u2014': '\u002d',  # Em dash → Hyphen-minus
        '\u2013': '\u002d',  # En dash → Hyphen-minus
        '\u2015': '\u002d',  # Horizontal bar → Hyphen-minus
        '\u2212': '\u002d',  # Minus sign → Hyphen-minus
        '\u00ad': '\u002d',  # Soft hyphen → Hyphen-minus
        '\u2010': '\u002d',  # Hyphen → Hyphen-minus
        '\u2011': '\u002d',  # Non-breaking hyphen → Hyphen-minus
        
        # Slashes
        '\u2044': '\u002f',  # Fraction slash → Solidus
        '\u2215': '\u002f',  # Division slash → Solidus
        '\u29f8': '\u002f',  # Big solidus → Solidus
        '\u2216': '\u005c',  # Set minus → Reverse solidus (backslash)
        '\u29f9': '\u005c',  # Big reverse solidus → Reverse solidus
        '\u27cd': '\u005c',  # Mathematical falling diagonal → Reverse solidus
        
        # Brackets
        '\u2329': '\u003c',  # Left-pointing angle bracket → Less-than sign
        '\u232a': '\u003e',  # Right-pointing angle bracket → Greater-than sign
        '\u27e8': '\u003c',  # Mathematical left angle bracket → Less-than sign
        '\u27e9': '\u003e',  # Mathematical right angle bracket → Greater-than sign
        '\u3008': '\u003c',  # Left angle bracket → Less-than sign
        '\u3009': '\u003e',  # Right angle bracket → Greater-than sign
        '\u2772': '\u005b',  # Light left tortoise shell bracket ornament → Left square bracket
        '\u2773': '\u005d',  # Light right tortoise shell bracket ornament → Right square bracket
        '\u27e6': '\u005b',  # Mathematical left white square bracket → Left square bracket
        '\u27e7': '\u005d',  # Mathematical right white square bracket → Right square bracket
        '\uff3b': '\u005b',  # Fullwidth left square bracket → Left square bracket
        '\uff3d': '\u005d',  # Fullwidth right square bracket → Right square bracket
        '\u2774': '\u007b',  # Medium left curly bracket ornament → Left curly bracket
        '\u2775': '\u007d',  # Medium right curly bracket ornament → Right curly bracket
        '\uff5b': '\u007b',  # Fullwidth left curly bracket → Left curly bracket
        '\uff5d': '\u007d',  # Fullwidth right curly bracket → Right curly bracket
        
        # Parentheses
        '\uff08': '\u0028',  # Fullwidth left parenthesis → Left parenthesis
        '\uff09': '\u0029',  # Fullwidth right parenthesis → Right parenthesis
        '\u2768': '\u0028',  # Medium left parenthesis ornament → Left parenthesis
        '\u2769': '\u0029',  # Medium right parenthesis ornament → Right parenthesis
        '\u276a': '\u0028',  # Medium flattened left parenthesis ornament → Left parenthesis
        '\u276b': '\u0029',  # Medium flattened right parenthesis ornament → Right parenthesis
        
        # Other characters from original
        '\u2022': '\u002a',  # Bullet → Asterisk
        '\u0301': '\u0060',  # Combining acute accent → Grave accent
        '\u0000': '\u2400',  # Null → Symbol for null
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
        print(f"Replaced {unicode_char} with {replacement}")
    
    return text

def get_tokenizer():
    """
    Lazy load tiktoken tokenizer to avoid import-time issues.
    """
    global _tokenizer
    if _tokenizer is None:
        try:
            import tiktoken
            # Use GPT-2 encoding which is similar to what you were using
            _tokenizer = tiktoken.get_encoding("gpt2")
        except Exception as e:
            print(f"Warning: Could not load tiktoken: {e}")
            _tokenizer = "failed"
    return _tokenizer if _tokenizer != "failed" else None

def get_token_length(input_text, tokenizer=None):
    """
    Returns the number of tokens in the given text using tiktoken.
    input_text should either be a string or a list of strings.
    """
    # check if input is a string or a list of strings
    if isinstance(input_text, str):
        input_text = [input_text]
    elif not isinstance(input_text, list):
        raise ValueError("Input must be a string or a list of strings.")
    
    token_length_list = []
    
    if not tokenizer:
        tokenizer = get_tokenizer()
    
    # If tokenizer loading failed, use approximation
    if tokenizer is None:
        for text in input_text:
            # Simple approximation: average ~4 characters per token
            approximate_tokens = max(1, len(text) // 4)
            token_length_list.append(approximate_tokens)
        return token_length_list
    
    # Use tiktoken tokenizer
    for text in input_text:
        try:
            tokens = tokenizer.encode(text)
            token_length_list.append(len(tokens))
        except Exception as e:
            print(f"Warning: Tokenization failed, using approximation: {e}")
            approximate_tokens = max(1, len(text) // 4)
            token_length_list.append(approximate_tokens)
    
    return token_length_list

def human_readable_size(size_in_bytes):
    """
    Converts a size in bytes to a human-readable format (KB, MB, GB).
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} Bytes"
    elif size_in_bytes < 1024 ** 2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024 ** 3:
        return f"{size_in_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_in_bytes / (1024 ** 3):.2f} GB"
    
def get_file_cache_list():
    """
    Returns a list of all the filenames in the tmp_files/ directory.
    """
    directory = "tmp_files/"
    try:
        filenames = os.listdir(directory)
        file_info_list = []
        for filename in filenames:
            filepath = os.path.join(directory, filename)
            filesize = os.path.getsize(filepath)
            file_info_list.append((filename, filesize))
        return file_info_list
    except FileNotFoundError:
        return []
    
def ingest_cache(context_id):
    """
    Iterates through each of the file names in the file cache and adds each of them to the database using the create_file function.
    """
    directory = "tmp_files/"
    try:
        filenames = os.listdir(directory)
        for filename in filenames:
            filepath = os.path.join(directory, filename)
            filesize = os.path.getsize(filepath)
            with open(filepath, "rb") as f:
                file_content = f.read()

            file_id = uuid.uuid4()
            # first create the file itself
            create_file(
                file_name=filename, 
                file_content=file_content, 
                file_size=filesize,
                file_id=file_id,
                )
            file_content = get_file_text(filename, file_content)
            # then create the messages
            for c in split_content_to_chunks(file_content):
                create_message(
                    id=uuid.uuid4(),
                    message_type="file",
                    message_text=c,
                    message_length=len(c),
                    file_id=file_id,
                    )
        clear_cache()
    except FileNotFoundError:
        print("tmp_files/ directory not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def clear_cache():
    """
    Deletes all the files from the tmp_files/ directory.
    """
    directory = "tmp_files/"
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            try:
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    os.unlink(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            except Exception as e:
                print(f'Failed to delete {filepath}. Reason: {e}')
    except FileNotFoundError:
        print("tmp_files/ directory not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def split_content_to_chunks(content: str, max_message_size: int = 8192) -> list[str]:
    """
    Creates Message object(s) from content and saves them to the database.
    If content exceeds max_message_size, it will be split into multiple messages
    with words divided evenly between them.
    
    Args:
        content (str): Content to add to the context
        context_id (uuid.UUID): UUID of the context to add the content to
        max_message_size (int): Maximum size in characters for each message
    """
    content_chunks = []
    
    # Calculate how many messages we need
    num_messages = (len(content) + max_message_size - 1) // max_message_size  # Ceiling division
    
    # Split content into words
    words = content.split()
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
        
        content_chunks.append(message_text)
        
        word_index += words_in_this_message

    return content_chunks

def human_readable_date(dt: datetime) -> str:
    """
    Converts a datetime object to a human-readable format "YYYY/MM/DD HH:MM" in UTC.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: Formatted date string in "YYYY/MM/DD HH:MM" format
    """
    # Convert to UTC if the datetime is timezone-aware
    if dt.tzinfo is not None:
        utc_dt = dt.astimezone(pytz.UTC)
    else:
        # Assume naive datetime is already in UTC
        utc_dt = dt.replace(tzinfo=pytz.UTC)
    
    # Format as "YYYY/MM/DD HH:MM"
    return utc_dt.strftime("%Y/%m/%d %H:%M")

def get_file_text(filename, file_bytes):
    # Get file extension
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Convert file content from LargeBinary to string
    try:
        if isinstance(file_bytes, bytes):
            if file_extension == '.pdf':
                # Handle PDF files - convert to text
                try:
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    file_content = ""
                    for page in pdf_reader.pages:
                        file_content += page.extract_text() + "\nEND PAGE\n"
                    if not file_content.strip():
                        file_content = f"[PDF file content could not be extracted - {filename}]"
                except Exception as pdf_error:
                    print(f"Error extracting PDF content: {str(pdf_error)}")
                    file_content = f"[PDF file content extraction failed - {filename}]"
            else:
                # Handle non-PDF files
                try:
                    file_content = file_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    file_content = f"[Binary file content - {filename}]"
        else:
            file_content = str(file_bytes)
    except Exception as e:
        print(f"Error processing file content: {str(e)}")
        return "[Error processing file content]"

    file_content = replace_unicode_chars(file_content)

    return file_content