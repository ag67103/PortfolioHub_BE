import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.base import created_at_col, updated_at_col, uuid_pk


class Message(Base):
    """Attribute names keep the API's camelCase; database columns are snake_case."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Groups related messages between two participants
    conversationId: Mapped[uuid.UUID] = mapped_column("conversation_id", Uuid, index=True)
    senderName: Mapped[Optional[str]] = mapped_column("sender_name", String(500))
    senderEmail: Mapped[Optional[str]] = mapped_column("sender_email", String(320), index=True)
    senderUserId: Mapped[Optional[uuid.UUID]] = mapped_column(
        "sender_user_id", Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    recipientUserId: Mapped[uuid.UUID] = mapped_column(
        "recipient_user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    recipientEmail: Mapped[Optional[str]] = mapped_column("recipient_email", String(320), index=True)
    recipientName: Mapped[Optional[str]] = mapped_column("recipient_name", String(500))
    messageSubject: Mapped[Optional[str]] = mapped_column("message_subject", Text)
    messageContent: Mapped[str] = mapped_column("message_content", Text)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
    isDeletedForSender: Mapped[bool] = mapped_column("is_deleted_for_sender", Boolean, default=False, server_default=false())
    isDeletedForRecipient: Mapped[bool] = mapped_column("is_deleted_for_recipient", Boolean, default=False, server_default=false())
    isRead: Mapped[bool] = mapped_column("is_read", Boolean, default=False, server_default=false())
