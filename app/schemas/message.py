from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class MessageCreatedByAuthenticatedUser(BaseModel):
    messageSubject: Optional[str] = None  # Optional subject, will use default if not provided
    messageContent: str
    recipientEmail: EmailStr

class MessageCreatedByUnauthenticatedUser(BaseModel):
    senderName: str
    senderEmail: EmailStr
    messageSubject: Optional[str] = None  # Optional subject, will use default if not provided
    messageContent: str
    recipientUserId: UUID # Portfolio owner's user ID who receives the message

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