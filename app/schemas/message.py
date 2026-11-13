from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class MessageCreatedByAuthenticatedUser(BaseModel):
    messageSubject: Optional[str] = None  # Optional subject, will use default if not provided
    messageContent: str
    recipientEmail: EmailStr

class MessageCreatedByUnauthenticatedUser(BaseModel):
    senderName: str = Field(min_length=1, max_length=100)
    senderEmail: EmailStr
    messageSubject: Optional[str] = Field(default=None, max_length=200)  # Optional subject, will use default if not provided
    messageContent: str = Field(min_length=1, max_length=5000)
    recipientUserId: UUID # Portfolio owner's user ID who receives the message
    # Honeypot: hidden from people in the form, so only bots fill it in
    website: Optional[str] = Field(default=None, exclude=True)

class MessageCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversationId: UUID # Conversation ID to group related messages (required)
    senderName: Optional[str] = None
    senderEmail: Optional[str] = None
    senderUserId: Optional[UUID] = None # Sender's user ID (if authenticated)
    recipientUserId: UUID # Portfolio owner's user ID who receives the message
    recipientEmail: Optional[str] = None
    recipientName: Optional[str] = None
    messageSubject: Optional[str] = None  # Optional subject
    messageContent: str
    created_at: datetime = Field(description="UTC timestamp")
    isRead: bool
    updated_at: datetime = Field(description="UTC timestamp")

class MessageCountResponse(BaseModel):
    read: int
    unread: int
    total: int

class ReadMessageBody(BaseModel):
    messageIds: List[UUID] = Field(description="List of message IDs to mark as read")