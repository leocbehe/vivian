# database.py
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, joinedload, scoped_session
from sqlalchemy.sql import func # For default timestamps
from sqlalchemy.exc import SQLAlchemyError

# Import models
from models import Base, File, ContextGroup, Context, Message, Prompt

# --- PostgreSQL Database Configuration ---
# IMPORTANT: Replace these with your actual PostgreSQL credentials
# Example: postgresql://user:password@host:port/database_name
DATABASE_URL = "postgresql://postgres:p4ssword@localhost:5432/vivian_db"

# Create the SQLAlchemy Engine
# The engine is the entry point to the database
# echo=True will print SQL statements to the console (useful for debugging)
engine = create_engine(DATABASE_URL, echo=False) # Set echo=True for debugging SQL queries

# Create a scoped session factory
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

"""
ALL FUNCTION HEADERS:
def create_tables():
def get_session():
def close_session():
def initialize_database():
def create_file(file_name: str, file_content: bytes, file_size: int, file_summary: Optional[str] = None) -> Optional[File]:
def get_file_by_id(file_id: uuid.UUID) -> Optional[File]:
def get_file_list() -> List[File]:
def update_file(file_id: uuid.UUID, file_name: Optional[str] = None, 
                file_content: Optional[bytes] = None, file_summary: Optional[str] = None) -> bool:
def delete_file(file_id: uuid.UUID) -> bool:
def create_context_group(file_id: uuid.UUID, group_name: Optional[str] = None) -> Optional[ContextGroup]:
def get_context_group_by_id(group_id: uuid.UUID) -> Optional[ContextGroup]:
def get_context_groups_by_file_id(file_id: uuid.UUID) -> List[ContextGroup]:
def delete_context_group(group_id: uuid.UUID) -> bool:
def create_context(total_contents: str, context_size: int, 
                  context_group_id: Optional[uuid.UUID] = None, 
                  summary: Optional[str] = None) -> Optional[Context]:
def get_context_by_id(id: uuid.UUID) -> Optional[Context]:
def get_context_messages(id: uuid.UUID) -> List[Message]:
def get_contexts_by_group_id(context_group_id: uuid.UUID) -> List[Context]:
def get_context_list() -> List[Context]:
def update_context(context: Context) -> bool:
def delete_context(id: uuid.UUID) -> bool:
def create_message(message_type: str, message_text: str, message_length: int, id: uuid.UUID) -> Optional[Message]:
def get_message_by_id(id: uuid.UUID) -> Optional[Message]:
def get_messages_by_id(id: uuid.UUID) -> List[Message]:
def get_messages_by_type(message_type: str) -> List[Message]:
def update_message(id: uuid.UUID, message_type: Optional[str] = None,
                  message_text: Optional[str] = None) -> bool:
def delete_message(id: uuid.UUID) -> bool:
"""

def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_session():
    """Get a database session."""
    return SessionLocal()

def close_session():
    """Close the scoped session."""
    SessionLocal.remove()

def initialize_database():
    """Initialize the database by creating all tables if they don't exist."""
    try:
        print("initializing...\n")
        create_tables()
        return True
    except SQLAlchemyError as e:
        print(f"Error initializing database: {e}")
        return False


# --- FILE CRUD OPERATIONS ---
def create_file(file_name: str, file_content: bytes, file_size: int, file_summary: Optional[str] = None, file_id: Optional[uuid.UUID] = uuid.uuid4()) -> Optional[File]:
    """
    Create a new file record.
    
    Args:
        file_name: Name of the file
        file_content: Text content of the file
        file_size: Size of the file in bytes
        file_summary: Optional summary of the file
        
    Returns:
        File object if successful, None otherwise
    """
    session = get_session()
    try:
        new_file = File(
            file_name=file_name,
            file_content=file_content,
            file_size=file_size,
            file_summary=file_summary,
            file_id=file_id
        )
        session.add(new_file)
        session.commit()
        return new_file
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error creating file: {e}")
        return None
    finally:
        session.close()

def get_file_by_id(file_id: uuid.UUID) -> Optional[File]:
    """
    Retrieve a file by its ID.
    
    Args:
        file_id: UUID of the file
        
    Returns:
        File object if found, None otherwise
    """
    session = get_session()
    try:
        return session.query(File).filter(File.file_id == file_id).first()
    except SQLAlchemyError as e:
        print(f"Error retrieving file: {e}")
        return None
    finally:
        session.close()

def get_file_list() -> List[File]:
    """
    Retrieve all files.
    
    Returns:
        List of File objects
    """
    session = get_session()
    try:
        return session.query(File).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving files: {e}")
        return []
    finally:
        session.close()

def update_file(file_id: uuid.UUID, file_name: Optional[str] = None, 
                file_content: Optional[bytes] = None, file_summary: Optional[str] = None) -> bool:
    """
    Update a file record.
    
    Args:
        file_id: UUID of the file to update
        file_name: New file name (optional)
        file_content: New file content (optional)
        file_summary: New file summary (optional)
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        file_obj = session.query(File).filter(File.file_id == file_id).first()
        if not file_obj:
            return False
            
        if file_name is not None:
            file_obj.file_name = file_name
        if file_content is not None:
            file_obj.file_content = file_content
        if file_summary is not None:
            file_obj.file_summary = file_summary
            
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error updating file: {e}")
        return False
    finally:
        session.close()

def delete_file(file_id: uuid.UUID) -> bool:
    """
    Delete a file record.
    
    Args:
        file_id: UUID of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        file_obj = session.query(File).filter(File.file_id == file_id).first()
        if not file_obj:
            return False
            
        session.delete(file_obj)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error deleting file: {e}")
        return False
    finally:
        session.close()

# --- CONTEXT GROUP CRUD OPERATIONS ---

def create_context_group(file_id: uuid.UUID, group_name: Optional[str] = None) -> Optional[ContextGroup]:
    """
    Create a new context group.
    
    Args:
        file_id: UUID of the associated file
        group_name: Optional name for the group
        
    Returns:
        ContextGroup object if successful, None otherwise
    """
    session = get_session()
    try:
        new_group = ContextGroup(
            file_id=file_id,
            group_name=group_name
        )
        session.add(new_group)
        session.commit()
        return new_group
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error creating context group: {e}")
        return None
    finally:
        session.close()

def get_context_group_by_id(group_id: uuid.UUID) -> Optional[ContextGroup]:
    """
    Retrieve a context group by its ID.
    
    Args:
        group_id: UUID of the context group
        
    Returns:
        ContextGroup object if found, None otherwise
    """
    session = get_session()
    try:
        return session.query(ContextGroup).filter(ContextGroup.group_id == group_id).first()
    except SQLAlchemyError as e:
        print(f"Error retrieving context group: {e}")
        return None
    finally:
        session.close()

def get_context_groups_by_file_id(file_id: uuid.UUID) -> List[ContextGroup]:
    """
    Retrieve all context groups for a specific file.
    
    Args:
        file_id: UUID of the file
        
    Returns:
        List of ContextGroup objects
    """
    session = get_session()
    try:
        return session.query(ContextGroup).filter(ContextGroup.file_id == file_id).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving context groups: {e}")
        return []
    finally:
        session.close()

def delete_context_group(group_id: uuid.UUID) -> bool:
    """
    Delete a context group.
    
    Args:
        group_id: UUID of the context group to delete
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        group_obj = session.query(ContextGroup).filter(ContextGroup.group_id == group_id).first()
        if not group_obj:
            return False
            
        session.delete(group_obj)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error deleting context group: {e}")
        return False
    finally:
        session.close()

# --- CONTEXT CRUD OPERATIONS ---

def create_context(total_contents: str, context_size: int, 
                  context_group_id: Optional[uuid.UUID] = None, 
                  summary: Optional[str] = None) -> Optional[Context]:
    """
    Create a new context record.
    
    Args:
        total_contents: The content of the context
        context_size: Size of the context
        context_group_id: Optional UUID of the associated context group
        summary: Optional summary of the context
        
    Returns:
        Context object if successful, None otherwise
    """
    session = get_session()
    try:
        new_context = Context(
            total_contents=total_contents,
            context_size=context_size,
            context_group_id=context_group_id,
            summary=summary
        )
        session.add(new_context)
        session.commit()
        
        # Access the messages attribute to load it while session is active
        messages = new_context.messages  # This will be an empty list for new contexts
        group = new_context.context_group  # This will be None for new contexts
        
        return new_context
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error creating context: {e}")
        return None
    finally:
        session.close()

def get_context_by_id(id: uuid.UUID) -> Optional[Context]:
    """
    Retrieve a context by its ID with eagerly loaded messages.
    
    Args:
        id: UUID of the context
        
    Returns:
        Context object if found, None otherwise
    """
    session = get_session()
    try:
        context = session.query(Context).options(joinedload(Context.messages)).filter(Context.id == id).first()
        if context:
            # Expunge from session to avoid detached instance errors
            session.expunge_all()
        return context
    except SQLAlchemyError as e:
        print(f"Error retrieving context: {e}")
        return None
    finally:
        session.close()

def get_contexts_by_group_id(context_group_id: uuid.UUID) -> List[Context]:
    """
    Retrieve all contexts for a specific context group.
    
    Args:
        context_group_id: UUID of the context group
        
    Returns:
        List of Context objects
    """
    session = get_session()
    try:
        return session.query(Context).filter(Context.context_group_id == context_group_id).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving contexts: {e}")
        return []
    finally:
        session.close()

def get_context_list() -> List[Context]:
    """
    Retrieve all contexts.
    
    Returns:
        List of Context objects
    """
    session = get_session()
    try:
        return session.query(Context).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving contexts: {e}")
        return []
    finally:
        session.close()

def update_context(context: Context) -> bool:
    """
    Update a context record.
    
    Args:
        id: UUID of the context to update
        total_contents: New content (optional)
        context_size: New context size (optional)
        summary: New summary (optional)
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        context_obj = session.query(Context).filter(Context.id == context.id).first()
        if not context_obj:
            return False
            
        if context.total_contents is not None:
            context_obj.total_contents = context.total_contents
        if context.context_size is not None:
            context_obj.context_size = context.context_size
        if context.summary is not None:
            context_obj.summary = context.summary
            
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error updating context: {e}")
        return False
    finally:
        session.close()

def delete_context(id: uuid.UUID) -> bool:
    """
    Delete a context record.
    
    Args:
        id: UUID of the context to delete
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        context_obj = session.query(Context).filter(Context.id == id).first()
        if not context_obj:
            return False
            
        session.delete(context_obj)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error deleting context: {e}")
        return False
    finally:
        session.close()

# --- MESSAGE CRUD OPERATIONS ---

def create_message(id: uuid.UUID, message_type: str, message_text: str, message_length: int, context_id: Optional[uuid.UUID] = None, file_id: Optional[uuid.UUID] = None) -> Optional[Message]:
    """
    Create a new message record.
    
    Args:
        message_type: Type of message (e.g., "user", "assistant")
        message_text: Content of the message
        id: UUID of the associated context
        
    Returns:
        Message object if successful, None otherwise
    """
    session = get_session()
    try:
        new_message = Message(
            id=id,
            message_type=message_type,
            message_text=message_text,
            message_length=message_length,
            message_created_at=datetime.now(timezone.utc),
            context_id=context_id if context_id else None,
            file_id=file_id if file_id else None
        )
        session.add(new_message)
        session.commit()
        return new_message
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error creating message: {e}")
        return None
    finally:
        session.close()

def get_message_by_id(id: uuid.UUID) -> Optional[Message]:
    """
    Retrieve a message by its ID.
    
    Args:
        id: UUID of the message
        
    Returns:
        Message object if found, None otherwise
    """
    session = get_session()
    try:
        return session.query(Message).filter(Message.id == id).first()
    except SQLAlchemyError as e:
        print(f"Error retrieving message: {e}")
        return None
    finally:
        session.close()

def get_messages_by_context_id(context_id: uuid.UUID) -> List[Message]:
    """
    Retrieve all messages for a specific context.
    
    Args:
        context_id: UUID of the context
        
    Returns:
        List of Message objects
    """
    session = get_session()
    try:
        return session.query(Message).filter(Message.context_id == context_id).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving messages: {e}")
        return []
    finally:
        session.close()

def get_messages_by_file_id(file_id: uuid.UUID) -> List[Message]:
    """
    Retrieve all messages for a specific file.

    Args:
        file_id: UUID of the file

    Returns:
        List of Message objects
    """
    session = get_session()
    try:
        return session.query(Message).filter(Message.file_id == file_id).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving messages: {e}")
        return []
    finally:
        session.close()

def get_messages_by_type(message_type: str) -> List[Message]:
    """
    Retrieve all messages of a specific type.
    
    Args:
        message_type: Type of messages to retrieve
        
    Returns:
        List of Message objects
    """
    session = get_session()
    try:
        return session.query(Message).filter(Message.message_type == message_type).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving messages by type: {e}")
        return []
    finally:
        session.close()

def update_message(id: uuid.UUID, message_type: Optional[str] = None, message_text: Optional[str] = None) -> bool:
    """
    Update a message record.
    
    Args:
        id: UUID of the message to update
        message_type: New message type (optional)
        message_text: New message text (optional)
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        message_obj = session.query(Message).filter(Message.id == id).first()
        if not message_obj:
            return False
            
        if message_type is not None:
            message_obj.message_type = message_type
        if message_text is not None:
            message_obj.message_text = message_text
            
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error updating message: {e}")
        return False
    finally:
        session.close()

def delete_message(id: uuid.UUID) -> bool:
    """
    Delete a message record.
    
    Args:
        id: UUID of the message to delete
        
    Returns:
        True if successful, False otherwise
    """
    session = get_session()
    try:
        message_obj = session.query(Message).filter(Message.id == id).first()
        if not message_obj:
            return False
            
        session.delete(message_obj)
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error deleting message: {e}")
        return False
    finally:
        session.close()

# --- PROMPT CRUD OPERATIONS ---
def create_prompt(id: uuid.UUID, content: str, created_at: datetime, name: str = "") -> Optional[Prompt]:
    """
    Create a new prompt record.

    Args:
        content: Content of the prompt
        created_at: Timestamp of prompt creation

    Returns:
        Prompt object if successful, None otherwise
    """
    session = get_session()
    print(f"new prompt name: {name}")
    try:
        print(f"saving new prompt with name: {name}")
        new_prompt = Prompt(
            id=id,
            content=content,
            created_at=created_at,
            name=name
        )
        session.add(new_prompt)
        session.commit()
        return new_prompt
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error creating prompt: {e}")
        return None
    finally:
        session.close()

def get_all_prompts() -> List[Prompt]:
    """
    Retrieve all prompts.
    Returns:
        List of Prompt objects
    """
    session = get_session()
    try:
        return session.query(Prompt).all()
    except SQLAlchemyError as e:
        print(f"Error retrieving prompts: {e}")
        return []
    finally:
        session.close()
