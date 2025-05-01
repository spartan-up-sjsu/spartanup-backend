from fastapi import APIRouter, HTTPException, Form
from bson import ObjectId, errors
from app.config import logger
from app.config import (
    conversations_collection,
    items_collection,
    messages_collection,
    user_collection,
)
from typing import Optional
import json
from app.routers.dependencies import get_current_user_id
from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.schemas.conversation_schema import (
    list_serialize_conversations,
    serialize_conversation,
)
from app.schemas.message_schema import list_serialize_messages
from datetime import datetime
from app.websockets.manager import ws_manager
import asyncio
from fastapi.params import Depends
from fastapi import Query, Depends, BackgroundTasks
import time

router = APIRouter()

# Cache for user conversations (key: user_id, value: conversation data)
# This will expire after 30 seconds to ensure data freshness
conversation_cache = {}
CACHE_EXPIRY = 30  # seconds


# Background task to refresh the cache
async def refresh_conversation_cache(user_id: str):
    try:
        # Fetch conversations directly without going through the endpoint
        conversations_list = list(
            conversations_collection.find(
                {
                    "$or": [
                        {"seller_id": ObjectId(user_id)},
                        {"buyer_id": ObjectId(user_id)},
                    ]
                }
            )
        )

        if not conversations_list:
            conversation_cache[user_id] = {
                "message": "No conversations found",
                "data": [],
                "timestamp": time.time(),
            }
            return

        serialized_conversations = [
            serialize_conversation(conv) for conv in conversations_list
        ]

        # Process in batches to avoid overwhelming the database
        batch_size = 10
        for i in range(0, len(conversations_list), batch_size):
            batch = conversations_list[i : i + batch_size]
            tasks = []

            for conversation in batch:
                tasks.append(fetch_seller_details(conversation["seller_id"]))
                tasks.append(fetch_latest_message(conversation["_id"]))

            results = await asyncio.gather(*tasks)

            for j, conv_index in enumerate(
                range(i, min(i + batch_size, len(serialized_conversations)))
            ):
                seller_index = j * 2
                message_index = j * 2 + 1

                serialized_conversations[conv_index]["seller_details"] = results[
                    seller_index
                ]
                serialized_conversations[conv_index]["latest_message"] = results[
                    message_index
                ]

        # Update the cache
        conversation_cache[user_id] = {
            "message": "Conversations retrieved successfully",
            "data": serialized_conversations,
            "timestamp": time.time(),
        }
        logger.info(f"Cache refreshed for user {user_id}")
    except Exception as e:
        logger.error(f"Error refreshing cache for user {user_id}: {str(e)}")


@router.post("/")
async def create_conversation(
    item_id: str = Form(...),
    initial_message: str = Form(...),
    user_id=Depends(get_current_user_id),
):
    try:
        logger.info("Creating conversation")
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if item is None:
            logger.error("Item not found")
            raise HTTPException(status_code=404, detail="Item not found")

        # Check if buyer is trying to create a conversation with themselves (as the seller)
        if str(user_id) == str(item["seller_id"]):
            logger.error("Cannot create conversation with yourself")
            raise HTTPException(
                status_code=400, detail="Cannot create conversation with yourself"
            )

        conversation = Conversation(
            item_id=str(item_id),
            seller_id=str(item["seller_id"]),
            buyer_id=str(user_id),
        )

        conversation_data = conversation.model_dump()
        conversation_data["item_id"] = ObjectId(conversation_data["item_id"])
        conversation_data["seller_id"] = ObjectId(conversation_data["seller_id"])
        conversation_data["buyer_id"] = ObjectId(conversation_data["buyer_id"])

        inserted_conversation = conversations_collection.insert_one(conversation_data)
        conversation_id = str(inserted_conversation.inserted_id)

        # Sending initial message
        message = Message(
            conversation_id=conversation_id, sender_id=user_id, message=initial_message
        )
        message_data = message.model_dump()
        message_data["conversation_id"] = ObjectId(message_data["conversation_id"])
        message_data["sender_id"] = ObjectId(message_data["sender_id"])
        messages_collection.insert_one(message_data)

        await ws_manager.send_message(
            str(user_id),
            {
                "type": "notification",
                "message": "New conversation started",
                "conversation_id": conversation_id,
                "item_id": str(conversation.item_id),
                "seller_id": str(conversation.seller_id),
                "created_at": datetime.utcnow().isoformat(),
            },
        )
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


# this function sends a message to a conversation
@router.post("/{conversation_id}")
async def send_message(
    conversation_id: str,
    message: str = Form(...),
    sender_id=Depends(get_current_user_id),
):
    try:
        logger.info(f"Sending message to conversation with ID: {conversation_id}")
        conversation = conversations_collection.find_one(
            {"_id": ObjectId(conversation_id)}
        )
        if conversation is None:
            logger.error("Conversation not found")
            raise HTTPException(status_code=404, detail="Conversation not found")

        recipient_id = (
            str(conversation["seller_id"])
            if sender_id == str(conversation["buyer_id"])
            else str(conversation["buyer_id"])
        )
        
        # Create timestamp for both fields
        current_time = datetime.utcnow()
        
        message = Message(
            conversation_id=conversation_id,  # This will stay a string for validation
            sender_id=str(sender_id),  # Convert ObjectId to string for validation
            message=message,
            created_at=current_time,
            updated_at=current_time
        )

        # Insert the message into MongoDB with ObjectId
        message_data = message.dict()
        message_data["conversation_id"] = ObjectId(
            message_data["conversation_id"]
        )  # Convert to ObjectId for MongoDB
        message_data["sender_id"] = ObjectId(
            message_data["sender_id"]
        )  # Convert to ObjectId for MongoDB
        
        # Ensure timestamps are included in the database document
        message_data["created_at"] = current_time
        message_data["updated_at"] = current_time

        result = messages_collection.insert_one(message_data)
        
        # this is where the notification should go, using websockets example json payload here with multiplexing in mine:
        notification_payload = {
            "type": "message",
            "data": {
                "conversation_id": str(message.conversation_id),
                "sender_id": str(message.sender_id),
                "message": message.message,
                "created_at": current_time.isoformat(),  # Include timestamp in notification
            },
        }
        await ws_manager.send_message(recipient_id, notification_payload)
        return {"message": "Message sent successfully", "message_id": str(result.inserted_id)}
    except errors.InvalidId:
        logger.error("Invalid conversation ID format")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send message")


# this function retrieves all conversations for a specific user from the database
@router.get("/")
async def get_conversations(
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    force_refresh: bool = Query(False),
):
    try:
        logger.info(
            f"Retrieving conversations for user {user_id} (limit: {limit}, skip: {skip})"
        )

        # Check if we have a valid cache entry
        cache_entry = conversation_cache.get(user_id)
        cache_valid = (
            cache_entry is not None
            and time.time() - cache_entry["timestamp"] < CACHE_EXPIRY
            and not force_refresh
        )

        # If we have a valid cache entry, use it
        if cache_valid:
            logger.info(f"Using cached conversations for user {user_id}")
            data = cache_entry["data"][skip : skip + limit]
            return {"message": "Conversations retrieved successfully", "data": data}

        # If no valid cache, fetch from database with aggregation pipeline
        # This does everything in a single MongoDB query
        pipeline = [
            # Match conversations where the user is either seller or buyer
            {
                "$match": {
                    "$or": [
                        {"seller_id": ObjectId(user_id)},
                        {"buyer_id": ObjectId(user_id)},
                    ]
                }
            },
            # Sort by updated_at or created_at to get most recent conversations first
            {"$sort": {"updated_at": -1}},
            # Apply pagination
            {"$skip": skip},
            {"$limit": limit},
            # Lookup to get the seller details
            {
                "$lookup": {
                    "from": "users",
                    "localField": "seller_id",
                    "foreignField": "_id",
                    "as": "seller_details",
                }
            },
            # Lookup to get buyer details
            {
                "$lookup": {
                    "from": "users",
                    "localField": "buyer_id",
                    "foreignField": "_id",
                    "as": "buyer_details",
                }
            },
            # Unwind the seller_details array (will be empty if no seller found)
            {
                "$unwind": {
                    "path": "$seller_details",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            # Lookup to get the item details
            {
                "$lookup": {
                    "from": "items",
                    "localField": "item_id",
                    "foreignField": "_id",
                    "as": "item_details",
                }
            },
            # Unwind the item_details array (will be empty if no item found)
            {"$unwind": {"path": "$item_details", "preserveNullAndEmptyArrays": True}},
            # Lookup to get the latest message
            {
                "$lookup": {
                    "from": "messages",
                    "let": {"conv_id": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$conversation_id", "$$conv_id"]}
                            }
                        },
                        {"$sort": {"timestamp": -1, "created_at": -1}},
                        {"$limit": 1},
                    ],
                    "as": "latest_messages",
                }
            },
            # Unwind the latest_messages array (will be empty if no messages)
            {
                "$unwind": {
                    "path": "$latest_messages",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            # Project only the fields we need
            {
                "$project": {
                    "_id": 1,
                    "seller_id": 1,
                    "buyer_id": 1,
                    "item_id": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "status": 1,
                    "seller_details": {
                        "_id": "$seller_details._id",
                        "email": "$seller_details.email",
                        "name": "$seller_details.name",
                        "picture": "$seller_details.picture",
                    },
                    "item_details": {
                        "_id": "$item_details._id",
                        "title": "$item_details.title",
                        "price": "$item_details.price",
                        "image": {"$arrayElemAt": ["$item_details.images", 0]},
                        "images": "$item_details.images",
                        "condition": "$item_details.condition",
                    },
                    "latest_message": {
                        "_id": "$latest_messages._id",
                        "sender_id": "$latest_messages.sender_id",
                        "message": "$latest_messages.message",
                        "content": "$latest_messages.content",
                        "created_at": "$latest_messages.created_at",
                        "timestamp": "$latest_messages.timestamp",
                    },
                }
            },
        ]

        # Execute the aggregation pipeline
        try:
            conversations_with_details = await asyncio.to_thread(
                list, conversations_collection.aggregate(pipeline)
            )
            logger.debug(
                f"Aggregation pipeline returned {len(conversations_with_details)} conversations"
            )
        except Exception as e:
            logger.error(f"Error in aggregation pipeline: {str(e)}")
            # Fall back to the previous method if aggregation fails
            return await get_conversations_fallback(user_id, limit, skip)

        if not conversations_with_details:
            # Schedule a background refresh for next time
            background_tasks.add_task(refresh_conversation_cache, user_id)
            return {"message": "No conversations found", "data": []}

        # Serialize the results
        serialized_conversations = []
        for conv in conversations_with_details:
            serialized_conv = serialize_conversation(conv)

            # Handle seller details
            if (
                "seller_details" in conv
                and conv["seller_details"]
                and "_id" in conv["seller_details"]
            ):
                seller_details = conv["seller_details"]
                serialized_conv["seller_details"] = {
                    "id": str(seller_details["_id"]),
                    "email": seller_details.get("email", ""),
                    "name": seller_details.get("name", ""),
                    "picture": seller_details.get("picture", ""),
                }
            else:
                serialized_conv["seller_details"] = None

            # Handle item details
            if (
                "item_details" in conv
                and conv["item_details"]
                and "_id" in conv["item_details"]
            ):
                item_details = conv["item_details"]
                serialized_conv["item_details"] = {
                    "id": str(item_details["_id"]),
                    "title": item_details.get("title", ""),
                    "price": item_details.get("price", 0),
                    "image": item_details.get("image", ""),
                    "images": item_details.get("images", []),
                    "condition": item_details.get("condition", ""),
                }
            else:
                serialized_conv["item_details"] = None

            # Handle latest message
            if (
                "latest_message" in conv
                and conv["latest_message"]
                and "_id" in conv["latest_message"]
            ):
                latest_msg = conv["latest_message"]
                content = latest_msg.get("message", latest_msg.get("content", ""))
                timestamp = latest_msg.get(
                    "timestamp", latest_msg.get("created_at", "")
                )

                serialized_conv["latest_message"] = {
                    "id": str(latest_msg["_id"]),
                    "sender_id": str(latest_msg["sender_id"]),
                    "content": content,
                    "timestamp": (
                        timestamp.isoformat()
                        if isinstance(timestamp, datetime)
                        else str(timestamp)
                    ),
                }
            else:
                serialized_conv["latest_message"] = None

            serialized_conversations.append(serialized_conv)

        # Update the cache with the results
        # We're only caching what we've fetched, not the full dataset
        conversation_cache[user_id] = {
            "message": "Conversations retrieved successfully",
            "data": serialized_conversations,
            "timestamp": time.time(),
        }

        # Schedule a background refresh of the full cache if needed
        if len(serialized_conversations) == limit:  # There might be more data
            background_tasks.add_task(refresh_conversation_cache, user_id)

        return {
            "message": "Conversations retrieved successfully",
            "data": serialized_conversations,
        }
    except Exception as e:
        logger.error(f"Unable to retrieve conversations: {str(e)}")
        # Fall back to the previous method if anything goes wrong
        return await get_conversations_fallback(user_id, limit, skip)


# Fallback method in case the aggregation pipeline fails
async def get_conversations_fallback(user_id, limit, skip):
    try:
        logger.info(
            f"Using fallback method to retrieve conversations for user {user_id}"
        )

        # Get conversations with pagination
        conversations_list = list(
            conversations_collection.find(
                {
                    "$or": [
                        {"seller_id": ObjectId(user_id)},
                        {"buyer_id": ObjectId(user_id)},
                    ]
                }
            )
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )

        if not conversations_list:
            return {"message": "No conversations found", "data": []}

        serialized_conversations = [
            serialize_conversation(conv) for conv in conversations_list
        ]

        # Fetch details concurrently
        tasks = []
        for conversation in conversations_list:
            tasks.append(fetch_seller_details(conversation["seller_id"]))
            tasks.append(fetch_latest_message(conversation["_id"]))

        results = await asyncio.gather(*tasks)

        for i, serialized_conv in enumerate(serialized_conversations):
            seller_index = i * 2
            message_index = i * 2 + 1

            serialized_conv["seller_details"] = results[seller_index]
            serialized_conv["latest_message"] = results[message_index]

        return {
            "message": "Conversations retrieved successfully",
            "data": serialized_conversations,
        }
    except Exception as e:
        logger.error(f"Fallback method failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Cannot retrieve conversations: {str(e)}"
        )


# Helper function to fetch seller details
async def fetch_seller_details(seller_id):
    # Run the synchronous MongoDB operation in a thread pool
    seller = await asyncio.to_thread(user_collection.find_one, {"_id": seller_id})
    if seller:
        return {
            "id": str(seller["_id"]),
            "email": seller.get("email", ""),
            "name": seller.get("name", ""),
            "picture": seller.get("picture", ""),
        }
    return None


# Helper function to fetch latest message
async def fetch_latest_message(conversation_id):
    # Run the synchronous MongoDB operation in a thread pool
    latest_message = await asyncio.to_thread(
        lambda: messages_collection.find_one(
            {"conversation_id": conversation_id},
            sort=[
                ("timestamp", -1)
            ],  # Sort by timestamp in descending order to get the latest message
        )
    )

    if latest_message:
        return {
            "id": str(latest_message["_id"]),
            "sender_id": str(latest_message["sender_id"]),
            "content": latest_message.get(
                "message", ""
            ),  # Handle different field names
            "timestamp": (
                latest_message.get(
                    "timestamp", latest_message.get("created_at", "")
                ).isoformat()
                if isinstance(
                    latest_message.get(
                        "timestamp", latest_message.get("created_at", "")
                    ),
                    datetime,
                )
                else str(
                    latest_message.get(
                        "timestamp", latest_message.get("created_at", "")
                    )
                )
            ),
        }
    return None


# this function retrieves a conversation from the database, along side with the messages
@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        logger.info(f"Finding conversation in MongoDB with ID: {conversation_id}")
        object_id = ObjectId(conversation_id)
        
        # Use aggregation pipeline to get conversation with all related data in one query
        pipeline = [
            # Match the specific conversation
            {"$match": {"_id": object_id}},
            
            # Lookup seller details
            {
                "$lookup": {
                    "from": "users",
                    "localField": "seller_id",
                    "foreignField": "_id",
                    "as": "seller_details"
                }
            },
            # Unwind seller details (convert array to object)
            {"$unwind": {"path": "$seller_details", "preserveNullAndEmptyArrays": True}},
            
            # Lookup buyer details
            {
                "$lookup": {
                    "from": "users",
                    "localField": "buyer_id",
                    "foreignField": "_id",
                    "as": "buyer_details"
                }
            },
            # Unwind buyer details
            {"$unwind": {"path": "$buyer_details", "preserveNullAndEmptyArrays": True}},
            
            # Lookup item details
            {
                "$lookup": {
                    "from": "items",
                    "localField": "item_id",
                    "foreignField": "_id",
                    "as": "item_details"
                }
            },
            # Unwind item details
            {"$unwind": {"path": "$item_details", "preserveNullAndEmptyArrays": True}},
            
            # Project only the fields we need
            {
                "$project": {
                    "_id": 1,
                    "seller_id": 1,
                    "buyer_id": 1,
                    "item_id": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "status": 1,
                    "seller_details": {
                        "_id": "$seller_details._id",
                        "email": "$seller_details.email",
                        "name": "$seller_details.name",
                        "picture": "$seller_details.picture",
                    },
                    "buyer_details": {
                        "_id": "$buyer_details._id",
                        "email": "$buyer_details.email",
                        "name": "$buyer_details.name",
                        "picture": "$buyer_details.picture",
                    },
                    "item_details": {
                        "_id": "$item_details._id",
                        "title": "$item_details.title",
                        "price": "$item_details.price",
                        "description": "$item_details.description",
                        "images": "$item_details.images",
                        "status": "$item_details.status",
                        "condition": "$item_details.condition",
                        "category": "$item_details.category",
                    }
                }
            }
        ]
        
        # Execute the aggregation pipeline
        conversation_result = await asyncio.to_thread(
            lambda: list(conversations_collection.aggregate(pipeline))
        )
        
        if not conversation_result:
            logger.error("Unable to find conversation")
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        conversation = conversation_result[0]
        
        # Get messages for this conversation
        messages = await asyncio.to_thread(
            lambda: list(messages_collection.find({"conversation_id": object_id}).sort("created_at", 1))
        )
        
        # Process messages
        serialized_messages = list_serialize_messages(messages)
        
        # Get latest message
        latest_message = None
        if serialized_messages:
            latest_message = serialized_messages[-1]  # Already sorted by created_at
        
        # Serialize conversation
        serialized_conversation = {
            "id": str(conversation["_id"]),
            "seller_id": str(conversation["seller_id"]),
            "buyer_id": str(conversation["buyer_id"]),
            "item_id": str(conversation["item_id"]),
            "created_at": conversation.get("created_at", datetime.utcnow()).isoformat(),
            "updated_at": conversation.get("updated_at", datetime.utcnow()).isoformat(),
            "status": conversation.get("status", "active"),
            "seller_details": {
                "id": str(conversation["seller_details"]["_id"]) if conversation.get("seller_details") else None,
                "email": conversation.get("seller_details", {}).get("email", ""),
                "name": conversation.get("seller_details", {}).get("name", ""),
                "picture": conversation.get("seller_details", {}).get("picture", ""),
            } if conversation.get("seller_details") else None,
            "buyer_details": {
                "id": str(conversation["buyer_details"]["_id"]) if conversation.get("buyer_details") else None,
                "email": conversation.get("buyer_details", {}).get("email", ""),
                "name": conversation.get("buyer_details", {}).get("name", ""),
                "picture": conversation.get("buyer_details", {}).get("picture", ""),
            } if conversation.get("buyer_details") else None,
            "item_details": {
                "id": str(conversation["item_details"]["_id"]) if conversation.get("item_details") else None,
                "title": conversation.get("item_details", {}).get("title", ""),
                "price": conversation.get("item_details", {}).get("price", 0),
                "description": conversation.get("item_details", {}).get("description", ""),
                "images": conversation.get("item_details", {}).get("images", []),
                "status": conversation.get("item_details", {}).get("status", "active"),
                "condition": conversation.get("item_details", {}).get("condition", ""),
                "category": conversation.get("item_details", {}).get("category", ""),
            } if conversation.get("item_details") else None,
            "latest_message": latest_message
        }
        
        logger.info("Fetching conversation with messages")
        return {
            "message": "Conversation and messages retrieved successfully",
            "data": {
                "conversation": serialized_conversation,
                "messages": serialized_messages,
            },
        }
    except errors.InvalidId:
        logger.error(f"Invalid ObjectId format: {conversation_id}")
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    except Exception as e:
        logger.error(f"Unexpected error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# this function deletes a conversation from the database
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
