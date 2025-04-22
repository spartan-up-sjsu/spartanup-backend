from app.models.conversation_model import Conversation

def serialize_conversation(conversation: Conversation):
    return {
        "id": str(conversation["_id"]),
        "item_id": str(conversation["item_id"]),
        "seller_id": str(conversation["seller_id"]),
        "buyer_id": str(conversation["buyer_id"]),
        "status": conversation["status"],
        "created_at": conversation["created_at"].isoformat(), 
        "updated_at": conversation["updated_at"].isoformat(),
    }

def list_serialize_conversations(conversations):
    return [serialize_conversation(conv) for conv in conversations]