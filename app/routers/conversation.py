from fastapi import APIRouter, HTTPException, Form
from bson import ObjectId, errors
from app.config import logger
from app.config import conversations_collection, items_collection, messages_collection
from typing import Optional
import json
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.schemas.conversation_schema import list_serialize_conversations, serialize_conversation
from app.schemas.message_schema import list_serialize_messages
from datetime import datetime
from app.websocket_manager import ws_manager

router = APIRouter()


@router.post("/")
async def create_conversation(item_id: str = Form(...), buyer_id: str = Form(...)):
    try: 
        logger.info("Creating conversation")
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if item is None:
            logger.error("Item not found")
            raise HTTPException(status_code=404, detail="Item not found")

        conversation = Conversation(
        item_id=str(item_id),  
        seller_id=str(item["seller_id"]), 
        buyer_id=str(buyer_id)
        )

        conversation_data = conversation.model_dump()
        conversation_data["item_id"] = ObjectId(conversation_data["item_id"])
        conversation_data["seller_id"] = ObjectId(conversation_data["seller_id"])
        conversation_data["buyer_id"] = ObjectId(conversation_data["buyer_id"])
        inserted_conversation = conversations_collection.insert_one(conversation_data)

        conversation_id = str(inserted_conversation.inserted_id)

        await ws_manager.send_message(buyer_id, {
            "type": "notification",
            "message": "New conversation started",
            "conversation_id": str(conversation_id),  
            "item_id": str(conversation.item_id),  
            "seller_id": str(conversation.seller_id),  
            "created_at": datetime.utcnow().isoformat()
        })
        return {"message": "Conversation created", "conversation_id": conversation_id}
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format") 
    except Exception as e:
        logger.error("Error creating conversation: " + str(e)) 
        raise HTTPException(status_code=500, detail="Cannot create conversation")


#this function sends a message to a conversation
@router.post("/{conversation_id}")
async def send_message(conversation_id: str,  sender_id: str = Form(...), message: str = Form(...)):
    try:
        logger.info(f"Sending message to conversation with ID: {conversation_id}")
        conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        if conversation is None:
            logger.error("Conversation not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        recipient_id = (
            str(conversation["seller_id"]) if sender_id
             == str(conversation["buyer_id"]) else str(conversation["buyer_id"])
        )
        sender_id = ObjectId(sender_id)
        message = Message(
            conversation_id=conversation_id,  # This will stay a string for validation
            sender_id=str(sender_id),  # This will stay a string for validation
            message=message
        )

        # Insert the message into MongoDB with ObjectId
        message_data = message.dict()
        message_data["conversation_id"] = ObjectId(message_data["conversation_id"])  # Convert to ObjectId for MongoDB
        message_data["sender_id"] = ObjectId(message_data["sender_id"])  # Convert to ObjectId for MongoDB

        messages_collection.insert_one(message_data)
        #this is where the notification should go, using websockets example json payload here with multiplexing in mine:
        notification_payload = {
            "type": "message",
            "data": {
                "conversation_id": str(message.conversation_id),
                "sender_id": str(message.sender_id),
                "message": message.message
            }
        }
        await ws_manager.send_message(recipient_id, notification_payload)
        return {"message": "Message sent successfully"}
    except errors.InvalidId:
        logger.error("Invalid conversation ID format")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

#this function retrieves all conversations from the database
@router.get("/")
async def get_conversations():
    try: 
        logger.info("Retrieving all conversations from mongodb")
        conversations= list_serialize_conversations(conversations_collection.find())
        return {"message": "Conversations retrieved successfully", "data": conversations}
    except Exception as e: 
        logger.error("Unable to retrieve conversations" + str(e))
        raise HTTPException(status_code=404, detail="Cannot retrieve conversations")


#this function retrieves a conversation from the database, along side with the messages
@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        logger.info(f"Finding conversation in MongoDB with ID: {conversation_id}")
        object_id = ObjectId(conversation_id)
        conversation = conversations_collection.find_one({"_id": object_id})
        if conversation is None:
            logger.error("Unable to find conversation")
            raise HTTPException(status_code=404, detail="Conversation not found")
        serialized_conversation = serialize_conversation(conversation)
        messages = list(messages_collection.find({"conversation_id": object_id}))
        serialized_messages = list_serialize_messages(messages)
        
        logger.info("Fetching conversation with messages")
        return {
            "message": "Conversation and messages retrieved successfully",
            "data": {
                "conversation": serialized_conversation,
                "messages": serialized_messages
            }
        }
    except errors.InvalidId:
        logger.error(f"Invalid ObjectId format: {conversation_id}")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except Exception as e:
        logger.error(f"Unexpected error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

#this function deletes a conversation from the database
@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    try:
        logger.info(f"Deleting conversation with ID: {conversation_id}")
        result = conversations_collection.delete_one({"_id": ObjectId(conversation_id)})
        if result.deleted_count == 0:
            logger.error("Conversation not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted successfully"}
    except errors.InvalidId: 
        logger.error(f"Invalid ObjectId format: {conversation_id}")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot delete conversation")