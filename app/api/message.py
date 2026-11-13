from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db
from ..models.message import Message
from ..schemas.message import MessageCreatedByAuthenticatedUser, MessageCreatedByUnauthenticatedUser, MessageCreatedResponse, MessageResponse, MessageCountResponse, ReadMessageBody
from app.utils.auth import get_current_user
from ..models.user import User
from datetime import datetime, timezone
from app.schemas.error import Error
from app.websocket import manager

router = APIRouter()

# Simple in-memory limit for the public contact form: per IP, per hour (resets on restart)
_PUBLIC_MESSAGE_LIMIT = 5
_PUBLIC_MESSAGE_WINDOW_S = 3600
_public_message_log: dict = {}


def _check_public_rate_limit(ip: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    recent = [t for t in _public_message_log.get(ip, []) if now - t < _PUBLIC_MESSAGE_WINDOW_S]
    if len(recent) >= _PUBLIC_MESSAGE_LIMIT:
        raise HTTPException(status_code=429, detail=Error(message="Too many messages. Please try again later.", status_code=429).model_dump())
    recent.append(now)
    _public_message_log[ip] = recent
    if len(_public_message_log) > 10_000:  # keep memory bounded
        for key in [k for k, v in _public_message_log.items() if not v or now - v[-1] > _PUBLIC_MESSAGE_WINDOW_S]:
            del _public_message_log[key]

def evaluate_message_read_status(messages: List[Message], current_user: User):
    # Sent messages are always considered read. Only the response is affected (not saved).
    return [
        MessageResponse.model_validate(m).model_copy(update={"isRead": m.isRead or m.senderUserId == current_user.id})
        for m in messages
    ]


def serialize_message(message: Message) -> dict:
    return {
        "id": str(message.id),
        "_id": str(message.id),
        "conversationId": str(message.conversationId),
        "senderName": message.senderName,
        "senderEmail": message.senderEmail,
        "senderUserId": str(message.senderUserId) if message.senderUserId else None,
        "recipientUserId": str(message.recipientUserId),
        "recipientEmail": message.recipientEmail,
        "recipientName": message.recipientName,
        "messageSubject": message.messageSubject,
        "messageContent": message.messageContent,
        "isDeletedForSender": message.isDeletedForSender,
        "isDeletedForRecipient": message.isDeletedForRecipient,
        "isRead": message.isRead,
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
    }


async def find_or_create_conversation_id(
    db: AsyncSession,
    sender_email: str,
    recipient_email: str,
    sender_user_id: Optional[UUID] = None,
    recipient_user_id: Optional[UUID] = None
) -> UUID:
    """
    Find existing conversationId between two participants, or create a new one.
    Looks for messages where participants match (by email or userId).
    Always returns a conversationId.
    """
    # Match by email addresses (bidirectional)
    conditions = [
        and_(Message.senderEmail == sender_email, Message.recipientEmail == recipient_email),
        and_(Message.senderEmail == recipient_email, Message.recipientEmail == sender_email),
    ]

    # If we have user IDs, also match by them (bidirectional)
    if sender_user_id and recipient_user_id:
        conditions.append(and_(Message.senderUserId == sender_user_id, Message.recipientUserId == recipient_user_id))
        conditions.append(and_(Message.senderUserId == recipient_user_id, Message.recipientUserId == sender_user_id))

    # Most recent message between these participants
    existing_id = (await db.execute(
        select(Message.conversationId).where(or_(*conditions)).order_by(Message.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    # No existing conversation found -> create a new conversationId
    return existing_id or uuid4()


async def notify_new_message(message_doc: Message, recipient_user_id: str, sender_user_id: Optional[str] = None):
    payload = {
        "event": "message:new",
        "payload": serialize_message(message_doc)
    }
    await manager.send_personal_message(recipient_user_id, payload)
    if sender_user_id and sender_user_id != recipient_user_id:
        await manager.send_personal_message(sender_user_id, payload)


async def notify_messages_read(message_ids: List[str], user_ids: List[str]):
    payload = {
        "event": "message:read",
        "payload": {
            "messageIds": message_ids
        }
    }
    for user_id in user_ids:
        await manager.send_personal_message(user_id, payload)

@router.post('/send', response_model=MessageCreatedResponse)
async def message(message: MessageCreatedByAuthenticatedUser, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a new authenticated user message"""
    recipient_user = (await db.execute(select(User).where(User.email == message.recipientEmail))).scalars().first()
    if not recipient_user:
        raise HTTPException(
            status_code=404, 
            detail=Error(
                message="Recipient user not found", 
                status_code=404
            ).model_dump()
        )
    
    if recipient_user.id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail=Error(
                message="You cannot send a message to yourself", 
                status_code=400
            ).model_dump()
        )
    
    # Build sender name from user's first and last name, fallback to username
    sender_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    if not sender_name:
        sender_name = current_user.username

    # Find or create conversationId (always returns a conversationId)
    conversation_id = await find_or_create_conversation_id(
        db,
        sender_email=current_user.email,
        recipient_email=recipient_user.email,
        sender_user_id=current_user.id,
        recipient_user_id=recipient_user.id
    )

    # Use subject from frontend (or None if not provided)
    message_subject = message.messageSubject if message.messageSubject and message.messageSubject.strip() else None

    # Create message with explicit timestamps
    current_time = datetime.now(timezone.utc)
    new_message = {
        **message.model_dump(),
        'conversationId': conversation_id,
        'messageSubject': message_subject,  # Use what frontend provides, or None
        'senderUserId': current_user.id,
        'senderName': sender_name,
        'senderEmail': current_user.email,
        'recipientUserId': recipient_user.id,
        'recipientEmail': recipient_user.email,
        'recipientName': f"{recipient_user.first_name or ''} {recipient_user.last_name or ''}".strip(),
        'created_at': current_time,
        'updated_at': current_time,
    }
    message_created = Message(**new_message)
    db.add(message_created)
    await db.commit()
    await notify_new_message(message_created, str(recipient_user.id), str(current_user.id))
    return message_created

@router.post('/send/unauthenticated', response_model=MessageCreatedResponse)
async def unauthenticated_message(message: MessageCreatedByUnauthenticatedUser, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new unauthenticated user message"""
    if (message.website or '').strip():
        # Honeypot filled in: pretend it worked so bots don't retry, but store nothing
        return MessageCreatedResponse(id=uuid4())
    _check_public_rate_limit(request.client.host if request.client else 'unknown')
    recipient_user = await db.get(User, message.recipientUserId)
    if not recipient_user:
        raise HTTPException(
            status_code=404, 
            detail=Error(
                message="Recipient user not found", 
                status_code=404
            ).model_dump()
        )
    
    # Find or create conversationId (always returns a conversationId)
    conversation_id = await find_or_create_conversation_id(
        db,
        sender_email=message.senderEmail,
        recipient_email=recipient_user.email,
        sender_user_id=None,  # Unauthenticated sender has no userId
        recipient_user_id=recipient_user.id
    )

    # Use subject from frontend (or None if not provided)
    message_subject = message.messageSubject if message.messageSubject and message.messageSubject.strip() else None

    # Create message with explicit timestamps
    current_time = datetime.now(timezone.utc)
    new_message = {
        **message.model_dump(),
        'conversationId': conversation_id,
        'messageSubject': message_subject,  # Use what frontend provides, or None
        'recipientEmail': recipient_user.email,
        'recipientName': f"{recipient_user.first_name or ''} {recipient_user.last_name or ''}".strip(),
        'created_at': current_time,
        'updated_at': current_time
    }

    message_created = Message(**new_message)
    db.add(message_created)
    await db.commit()
    await notify_new_message(message_created, str(recipient_user.id))
    return message_created

@router.get('', response_model=List[MessageResponse])
async def get_all_messages_list_for_user(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all messages sent or received by the current user"""
    messages = (await db.execute(
        select(Message).where(or_(
            and_(Message.recipientUserId == current_user.id, Message.isDeletedForRecipient.is_(False)),
            and_(Message.senderUserId == current_user.id, Message.isDeletedForSender.is_(False)),
        )).order_by(Message.created_at)
    )).scalars().all()

    return evaluate_message_read_status(list(messages), current_user)

@router.get("/count", response_model=MessageCountResponse)
async def get_message_count(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get count of messages by the current user"""
    async def count(*conditions) -> int:
        return (await db.execute(select(func.count()).select_from(Message).where(*conditions))).scalar_one()

    recipient_total = await count(Message.recipientUserId == current_user.id, Message.isDeletedForRecipient.is_(False))
    sender_total = await count(Message.senderUserId == current_user.id, Message.isDeletedForSender.is_(False))

    # Received messages not yet read (sent messages are always considered read)
    unread_count = await count(
        Message.recipientUserId == current_user.id,
        Message.isRead.is_(False),
        Message.isDeletedForRecipient.is_(False),
    )

    total_count = recipient_total + sender_total
    return MessageCountResponse(
        read=total_count - unread_count,
        unread=unread_count,
        total=total_count
    )

@router.put('/read', response_model=dict)
async def mark_message_as_read(read_message_body: ReadMessageBody, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Mark all messages in the list as read"""
    message_ids = list(read_message_body.messageIds)

    await db.execute(
        update(Message)
        .where(
            Message.id.in_(message_ids),
            Message.recipientUserId == current_user.id,
            Message.isDeletedForRecipient.is_(False),
        )
        .values(isRead=True, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()

    updated_messages = (await db.execute(select(Message).where(Message.id.in_(message_ids)))).scalars().all()
    message_ids_str = [str(msg.id) for msg in updated_messages]
    participant_ids = {str(current_user.id)}
    for message in updated_messages:
        if message.senderUserId:
            participant_ids.add(str(message.senderUserId))

    await notify_messages_read(message_ids_str, list(participant_ids))

    return {"message": "Messages marked as read successfully"}

@router.delete("/{message_id}", response_model=dict)
async def delete_message(message_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a message"""
    message = (await db.execute(
        select(Message).where(
            Message.id == message_id,
            or_(Message.senderUserId == current_user.id, Message.recipientUserId == current_user.id),
        )
    )).scalars().first()
    message_found = False

    # Message is sent by the current user
    if (message and message.senderUserId == current_user.id and not message.isDeletedForSender):
        message_found = True
        message.isDeletedForSender = True
    
    elif (message and message.recipientUserId == current_user.id and not message.isDeletedForRecipient):
        message_found = True
        message.isDeletedForRecipient = True

    if not message_found:
        raise HTTPException(
            status_code=400, 
            detail=Error(
                message="Message is not found", 
                status_code=400
            ).model_dump()
        )

    if message.isDeletedForSender and message.isDeletedForRecipient:
        await db.delete(message)
    else:
        message.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Message deleted successfully"}

@router.delete("/conversation/{conversation_id}", response_model=dict)
async def delete_conversation(conversation_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete all messages in a conversation"""
    # Find all messages in this conversation where the current user is a participant
    messages = (await db.execute(
        select(Message).where(
            Message.conversationId == conversation_id,
            or_(Message.senderUserId == current_user.id, Message.recipientUserId == current_user.id),
        )
    )).scalars().all()
    
    if not messages:
        raise HTTPException(
            status_code=404,
            detail=Error(
                message="Conversation not found or you don't have access to it",
                status_code=404
            ).model_dump()
        )
    
    deleted_count = 0
    
    # Process each message in the conversation
    for message in messages:
        message_updated = False
        
        # If current user is the sender, mark as deleted for sender
        if message.senderUserId == current_user.id and not message.isDeletedForSender:
            message.isDeletedForSender = True
            message_updated = True
        
        # If current user is the recipient, mark as deleted for recipient
        if message.recipientUserId == current_user.id and not message.isDeletedForRecipient:
            message.isDeletedForRecipient = True
            message_updated = True
        
        # Only update/delete if message was actually modified
        if message_updated:
            # Count all messages deleted from user's end
            deleted_count += 1
            
            # If both parties have deleted it, permanently delete the message
            if message.isDeletedForSender and message.isDeletedForRecipient:
                await db.delete(message)
            else:
                # Otherwise, just update the flags (soft delete)
                message.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {
        "message": f"Conversation deleted successfully",
        "deleted_count": deleted_count
    }