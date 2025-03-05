from fastapi import APIRouter, HTTPException, Form
from bson import ObjectId, errors
from app.config import logger
from app.config import conversations_collection, items_collection
from typing import Optional
import json

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
            item_id=ObjectId(item_id),
            seller_id=ObjectId(item["seller_id"]),
            buyer_id=ObjectId(buyer_id)
        )
        conversations_collection.insert_one(conversation.dict())
        #this is where you send the notification to the buyer, use the websocket to do it.
        return conversation
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format") 
    except Exception as e:
        logger.error("Error creating conversation: " + str(e)) 
        raise HTTPException(status_code=500, detail="Cannot create conversation")


#this function sends a message to a conversation
@router.post("/{conversation_id}")
async def send_message(conversation_id: str, message: str = Form(...)):
    try:
        logger.info(f"Sending message to conversation with ID: {conversation_id}")
        conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        if conversation is None:
            logger.error("Conversation not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        message = Message(
            conversation_id=ObjectId(conversation_id),
            sender_id=ObjectId(conversation["buyer_id"]),
            message=message
        )
        messages_collection.insert_one(message.dict())
        #this is where the notification should go, using websockets example json payload here with multiplexing in mine:
        """
            {
                "type": "message", // type of update
                "data": { // data of the update
                    "conversation_id": str(message.conversation_id),
                    "sender_id": str(message.sender_id),
                    "message": message.message
                }
            }
        """
        return {"message": "Message sent successfully"}
    except errors.InvalidId:
        logger.error("Invalid conversation ID format")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

#this function retrieves all conversations from the database
@router.get("/")
async def get_conversations():
    try: 
        logger.info("Retrieving all conversations from mongodb")
        conversations = list_serialize_conversations(conversations_collection.find())
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
        
        # Retrieve relevant messages
        messages = list(messages_collection.find({"conversation_id": object_id}))
        
        logger.info("Fetching conversation with messages")
        return {
            "message": "Conversation and messages retrieved successfully",
            "data": {
                "conversation": conversation,
                "messages": messages
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