from fastapi import APIRouter, HTTPException, Form
from bson import ObjectId, errors
from app.config import logger
from app.config import conversations_collection, items_collection, messages_collection, user_collection
from typing import Optional
import json
from app.routers.dependencies import get_current_user
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.schemas.conversation_schema import list_serialize_conversations, serialize_conversation
from app.schemas.message_schema import list_serialize_messages
from datetime import datetime
from app.websocket_manager import ws_manager
import asyncio
import functools
from fastapi.params import Depends

router = APIRouter()

@router.post("/")
async def create_conversation(item_id: str = Form(...), initial_message: str = Form(...), user_id = Depends(get_current_user)):
    try: 
        logger.info("Creating conversation")
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if item is None:
            logger.error("Item not found")
            raise HTTPException(status_code=404, detail="Item not found")

        # Check if buyer is trying to create a conversation with themselves (as the seller)
        if str(user_id) == str(item["seller_id"]):
            logger.error("Cannot create conversation with yourself")
            raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")

        conversation = Conversation(
            item_id=str(item_id),  
            seller_id=str(item["seller_id"]), 
            buyer_id=str(user_id)
        )

        conversation_data = conversation.model_dump()
        conversation_data["item_id"] = ObjectId(conversation_data["item_id"])
        conversation_data["seller_id"] = ObjectId(conversation_data["seller_id"])
        conversation_data["buyer_id"] = ObjectId(conversation_data["buyer_id"])

        inserted_conversation = conversations_collection.insert_one(conversation_data)
        conversation_id = str(inserted_conversation.inserted_id)

        # Sending initial message
        message = Message(
            conversation_id=conversation_id,
            sender_id=user_id,
            message=initial_message
        )
        message_data = message.model_dump()
        message_data["conversation_id"] = ObjectId(message_data["conversation_id"])
        message_data["sender_id"] = ObjectId(message_data["sender_id"])
        messages_collection.insert_one(message_data)

        await ws_manager.send_message(str(user_id), {
            "type": "notification",
            "message": "New conversation started",
            "conversation_id": conversation_id,  
            "item_id": str(conversation.item_id),  
            "seller_id": str(conversation.seller_id),  
            "created_at": datetime.utcnow().isoformat()
        })
        return {"message": "Conversation created", "conversation_id": conversation_id}
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format") 
    except errors.InvalidId: 
        logger.error("Invalid conversation ID format")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except Exception as e:
        logger.error("Error creating conversation: " + str(e)) 
        raise HTTPException(status_code=500, detail="Cannot create conversation")


#this function sends a message to a conversation
@router.post("/{conversation_id}")
async def send_message(conversation_id: str, message: str = Form(...), sender_id = Depends(get_current_user)):
    try:
        logger.info(f"Sending message to conversation with ID: {conversation_id}")
        conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        if conversation is None:
            logger.error("Conversation not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        recipient_id = (
            str(conversation["seller_id"]) if sender_id == str(conversation["buyer_id"]) else str(conversation["buyer_id"])
        )
        message = Message(
            conversation_id=conversation_id,  # This will stay a string for validation
            sender_id=str(sender_id),  # Convert ObjectId to string for validation
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
        
        # Get all conversations (this is synchronous)
        conversations_list = await asyncio.to_thread(list, conversations_collection.find())
        serialized_conversations = [serialize_conversation(conv) for conv in conversations_list]
        
        # Create tasks for fetching seller details and first messages concurrently
        tasks = []
        
        for conversation in conversations_list:
            # Add task for fetching seller details
            tasks.append(fetch_seller_details(conversation["seller_id"]))
            
            # Add task for fetching first message
            tasks.append(fetch_latest_message(conversation["_id"]))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Process results (they come in pairs: seller details, first message)
        for i, serialized_conv in enumerate(serialized_conversations):
            seller_index = i * 2
            message_index = i * 2 + 1
            
            serialized_conv["seller_details"] = results[seller_index]
            serialized_conv["latest_message"] = results[message_index]
        
        return {"message": "Conversations retrieved successfully", "data": serialized_conversations}
    except Exception as e: 
        logger.error("Unable to retrieve conversations" + str(e))
        raise HTTPException(status_code=404, detail="Cannot retrieve conversations")

# Helper function to fetch seller details
async def fetch_seller_details(seller_id):
    # Run the synchronous MongoDB operation in a thread pool
    seller = await asyncio.to_thread(user_collection.find_one, {"_id": seller_id})
    if seller:
        return {
            "id": str(seller["_id"]),
            "email": seller.get("email", ""),
            "name": seller.get("name", ""),
            "picture": seller.get("picture", "")
        }
    return None

# Helper function to fetch latest message
async def fetch_latest_message(conversation_id):
    # Run the synchronous MongoDB operation in a thread pool
    latest_message = await asyncio.to_thread(
        functools.partial(
            messages_collection.find_one,
            {"conversation_id": conversation_id},
            sort=[("created_at", -1)]  # Sort by created_at in descending order to get the latest message
        )
    )
    if latest_message:
        return {
            "id": str(latest_message["_id"]),
            "sender_id": str(latest_message["sender_id"]),
            "message": latest_message["message"],
            "created_at": latest_message["created_at"].isoformat()
        }
    return None

#this function retrieves a conversation from the database, along side with the messages
@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        logger.info(f"Finding conversation in MongoDB with ID: {conversation_id}")
        object_id = ObjectId(conversation_id)
        
        # Run database operations concurrently
        tasks = [
            asyncio.to_thread(conversations_collection.find_one, {"_id": object_id}),
            asyncio.to_thread(list, messages_collection.find({"conversation_id": object_id}))
        ]
        
        # Wait for all tasks to complete
        conversation, messages = await asyncio.gather(*tasks)
        
        if conversation is None:
            logger.error("Unable to find conversation")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get seller details asynchronously
        seller_id = conversation["seller_id"]
        seller = await asyncio.to_thread(user_collection.find_one, {"_id": seller_id})
        
        seller_details = None
        if seller:
            seller_details = {
                "id": str(seller["_id"]),
                "email": seller.get("email", ""),
                "name": seller.get("name", ""),
                "picture": seller.get("picture", "")
            }
        
        # Process messages
        serialized_messages = list_serialize_messages(messages)
        
        # Get latest message
        latest_message = None
        if serialized_messages:
            # Sort messages by created_at
            sorted_messages = sorted(serialized_messages, key=lambda x: x["created_at"])
            if sorted_messages:
                latest_message = sorted_messages[-1]
        
        # Serialize conversation
        serialized_conversation = serialize_conversation(conversation)
        
        # Add seller details and latest message
        serialized_conversation["seller_details"] = seller_details
        serialized_conversation["latest_message"] = latest_message
        
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