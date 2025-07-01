import uuid
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

# Base class for declarative models
Base = declarative_base()

class File(Base):
    """
    Represents files stored for use by the LLM.
    """
    __tablename__ = 'files'

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    file_summary = Column(String, nullable=True)
    file_content = Column(LargeBinary, nullable=False)
    file_size = Column(Integer, nullable=False)  # New column for file size

    # Relationship to ContextGroup table
    # If a File is deleted, its associated ContextGroups should also be deleted.
    context_groups = relationship(
        "ContextGroup", 
        back_populates="original_file",
        cascade="all, delete-orphan")
    messages = relationship(
        'Message',
        backref='file',
        cascade='all, delete-orphan',
        lazy='joined', # Ensures eager loading
        order_by='Message.id' # Optional: Orders messages when fetched with the file
    )


class ContextGroup(Base):
    """
    Represents a logical grouping of Context objects, typically originating from a single large File.
    """
    __tablename__ = 'context_groups'

    group_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String, nullable=True) # Optional name for the group (e.g., "Segments of Report XYZ")
    
    # Foreign key to the original File
    file_id = Column(UUID(as_uuid=True), ForeignKey('files.file_id'), nullable=False)
    
    # Relationships
    original_file = relationship("File", back_populates="context_groups")
    
    # Relationship to Context table
    # If a ContextGroup is deleted, its associated Contexts should also be deleted.
    contexts = relationship("Context", back_populates="context_group",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return (f"<ContextGroup(group_id='{self.group_id}', "
                f"group_name='{self.group_name if self.group_name else 'N/A'}', "
                f"file_id='{self.file_id}')>")


class Context(Base):
    """
    Represents the content of an LLM's context window.
    """
    __tablename__ = 'contexts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_contents = Column(String, nullable=False)
    context_size = Column(Integer, nullable=False)
    summary = Column(String, nullable=True)
    
    # Foreign key to ContextGroup (nullable, as not all contexts need a group)
    context_group_id = Column(UUID(as_uuid=True), ForeignKey('context_groups.group_id'), nullable=True)
    
    # Relationships
    context_group = relationship("ContextGroup", back_populates="contexts")
    messages = relationship(
        'Message',
        backref='context',
        cascade='all, delete-orphan',
        lazy='joined', # Ensures eager loading
        order_by='Message.id' # Optional: Orders messages when fetched with the context
    )
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        group_id_str = str(self.context_group_id)[:8] + '...' if self.context_group_id else 'None'
        return (f"<Context(id='{self.id}', "
                f"group_id='{group_id_str}', "
                f"context_size={self.context_size}, "
                f"summary='{self.summary[:50] if self.summary else 'N/A'}...', "
                f"total_contents='{self.total_contents[:50]}...')>")


class Message(Base):
    """
    Represents an individual message within a Context.
    """
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_type = Column(String, nullable=False)  # e.g., "user", "assistant"
    message_text = Column(String, nullable=False)
    message_length = Column(Integer, nullable=False) # length in tokens
    message_created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    context_id = Column(UUID(as_uuid=True), ForeignKey('contexts.id'), nullable=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey('files.file_id'), nullable=True)

    def __repr__(self):
         return (f"<Message(id='{self.id}', "
                f"message_type='{self.message_type}', "
                f"message_text='{self.message_text[:50]}...', "
                f"id='{self.id}')>")
    
class Prompt(Base):
    """
    Represents a text prompt given to an LLM.
    """
    __tablename__ = 'prompts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Prompt(id='{self.id}', content='{self.content[:50]}...')>"
