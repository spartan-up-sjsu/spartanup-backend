from app.models.message_model import Message
def serialize_message(message: Message):
    return {
        "id": str(message["_id"]),
        "conversation_id": str(message["conversation_id"]),
        "sender_id": str(message["sender_id"]),
        "message": message["message"],
        "created_at": message["created_at"].isoformat(),
        "updated_at": message["updated_at"].isoformat()
    }

def list_serialize_messages(messages):
    return [serialize_message(msg) for msg in messages]
