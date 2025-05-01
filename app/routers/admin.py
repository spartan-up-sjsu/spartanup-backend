from fastapi import APIRouter, Request, HTTPException, Depends, Body
from app.config import (
    user_collection,
    reports_collection,
    items_collection,
    conversations_collection,
)
from bson import ObjectId
from app.core.security import verify_access_token
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os

router = APIRouter()


class AdminResponse:
    @staticmethod
    def success(
        data: Any = None, message: str = "Success", meta: Optional[Dict] = None
    ) -> Dict:
        response = {"success": True, "message": message, "data": data}
        if meta:
            response["meta"] = meta
        return response

    @staticmethod
    def error(message: str, code: str, details: Optional[Dict] = None) -> Dict:
        response = {"success": False, "message": message, "error": {"code": code}}
        if details:
            response["error"]["details"] = details
        return response


async def checkRole(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_access_token(token)
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("is_admin", False):
        raise HTTPException(status_code=401, detail="Admins only")
    return True


@router.get("/stats")
async def get_dashboard_stats(admin_check: bool = Depends(checkRole)):
    try:
        # Get total users
        total_users = user_collection.count_documents({})

        # Get active items
        active_items = items_collection.count_documents({"status": "active"})

        # Get pending reports
        pending_reports = reports_collection.count_documents({"status": "pending"})

        # Get active messages (conversations)
        active_messages = conversations_collection.count_documents({"status": "active"})

        # Get recent activity (last 24 hours)
        one_day_ago = datetime.now() - timedelta(days=1)

        recent_activity = []

        # Recent user registrations
        recent_users = user_collection.find(
            {"created_at": {"$gte": one_day_ago}},
            {"_id": 1, "name": 1, "created_at": 1},
        ).limit(5)
        for user in recent_users:
            recent_activity.append(
                {
                    "type": "user",
                    "action": "registration",
                    "timestamp": user["created_at"],
                    "details": {
                        "user_id": str(user["_id"]),
                        "full_name": user.get("name"),
                    },
                }
            )

        # Recent reported items
        recent_reports = reports_collection.find(
            {"created_at": {"$gte": one_day_ago}},
            {"_id": 1, "type": 1, "created_at": 1},
        ).limit(5)
        for report in recent_reports:
            recent_activity.append(
                {
                    "type": "report",
                    "action": "created",
                    "timestamp": report["created_at"],
                    "details": {
                        "report_id": str(report["_id"]),
                        "type": report["type"],
                    },
                }
            )

        stats = {
            "total_users": total_users,
            "active_items": active_items,
            "pending_reports": pending_reports,
            "active_messages": active_messages,
            "recent_activity": recent_activity,
        }

        return AdminResponse.success(data=stats)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch dashboard statistics",
            code="STATS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.get("/reported_items")
async def get_reported_items(admin_check: bool = Depends(checkRole)):
    reported_items = reports_collection.find({"status": "pending"})
    reported_items_list = [
        {
            **post,
            "_id": str(post["_id"]),
            "entity_id": str(post["entity_id"]),
            "reported_by": str(post["reported_by"]),
        }
        for post in reported_items
    ]
    return {"reported_items": reported_items_list}


@router.delete("/reported_items")
async def delete_reported_items(
    entity_id: str, type: str, admin_check: bool = Depends(checkRole)
):
    try:
        obj_id = ObjectId(entity_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entity_id format")

    if type == "items":
        deleted_item = items_collection.delete_one({"_id": obj_id})

        if deleted_item.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Post not found")

    reports_collection.update_many(
        {"entity_id": obj_id}, {"$set": {"status": "resolved"}}
    )

    return {"message": "Post deleted and report resolved"}


@router.get("/users")
async def list_users(
    admin_check: bool = Depends(checkRole),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "created_at:desc",
):
    try:
        # Build query
        query = {}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]

        # Parse sort parameter
        sort_field, sort_order = sort.split(":")
        sort_direction = -1 if sort_order == "desc" else 1

        # Calculate skip
        skip = (page - 1) * limit

        # Get total count
        total = user_collection.count_documents(query)

        # Get users
        users = (
            user_collection.find(query, {"password": 0})  # Exclude password field
            .sort(sort_field, sort_direction)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string
        users_list = []
        for user in users:
            user["_id"] = str(user["_id"])
            users_list.append(user)

        return AdminResponse.success(
            data=users_list, meta={"total": total, "page": page, "limit": limit}
        )

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch users",
            code="USERS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.get("/users/{user_id}")
async def get_user(user_id: str, admin_check: bool = Depends(checkRole)):
    try:
        user = user_collection.find_one(
            {"_id": ObjectId(user_id)}, {"password": 0}  # Exclude password field
        )

        if not user:
            return AdminResponse.error(message="User not found", code="USER_NOT_FOUND")

        user["_id"] = str(user["_id"])
        return AdminResponse.success(data=user)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch user",
            code="USER_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: dict = Body(...),  # This will accept the JSON body
    admin_check: bool = Depends(checkRole),
):
    try:
        # Extract values from the JSON body
        is_admin = update_data.get("is_admin")
        is_banned = update_data.get("is_banned")

        # Build update document
        update_doc = {}
        if is_admin is not None:
            update_doc["is_admin"] = is_admin
        if is_banned is not None:
            update_doc["is_banned"] = is_banned

        if not update_doc:
            return AdminResponse.error(
                message="No valid fields to update", code="NO_FIELDS_TO_UPDATE"
            )

        # Update user
        result = user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_doc}
        )

        if result.matched_count == 0:
            return AdminResponse.error(message="User not found", code="USER_NOT_FOUND")

        return AdminResponse.success(message="User updated successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to update user",
            code="USER_UPDATE_ERROR",
            details={"error": str(e)},
        )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_check: bool = Depends(checkRole)):
    try:
        # Soft delete by updating status
        result = user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"status": "deleted"}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(message="User not found", code="USER_NOT_FOUND")

        return AdminResponse.success(message="User deleted successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to delete user",
            code="USER_DELETE_ERROR",
            details={"error": str(e)},
        )


@router.get("/reports")
async def list_reports(
    admin_check: bool = Depends(checkRole),
    type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
):
    try:
        # Build query
        query = {}
        if type:
            query["type"] = type
        if status:
            query["status"] = status

        # Calculate skip
        skip = (page - 1) * limit

        # Get total count
        total = reports_collection.count_documents(query)

        # Get reports
        reports = (
            reports_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string
        reports_list = []
        for report in reports:
            report["_id"] = str(report["_id"])
            report["entity_id"] = str(report["entity_id"])
            report["reported_by"] = str(report["reported_by"])
            reports_list.append(report)

        return AdminResponse.success(
            data=reports_list, meta={"total": total, "page": page, "limit": limit}
        )

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch reports",
            code="REPORTS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.get("/reports/{report_id}")
async def get_report(report_id: str, admin_check: bool = Depends(checkRole)):
    try:
        report = reports_collection.find_one({"_id": ObjectId(report_id)})

        if not report:
            return AdminResponse.error(
                message="Report not found", code="REPORT_NOT_FOUND"
            )

        report["_id"] = str(report["_id"])
        report["entity_id"] = str(report["entity_id"])
        report["reported_by"] = str(report["reported_by"])

        return AdminResponse.success(data=report)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch report",
            code="REPORT_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.patch("/reports/{report_id}")
async def update_report_status(
    report_id: str, status: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Validate status
        if status not in ["pending", "resolved", "dismissed", "escalated"]:
            return AdminResponse.error(message="Invalid status", code="INVALID_STATUS")

        # Update report
        result = reports_collection.update_one(
            {"_id": ObjectId(report_id)}, {"$set": {"status": status}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(
                message="Report not found", code="REPORT_NOT_FOUND"
            )

        return AdminResponse.success(message="Report status updated successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to update report",
            code="REPORT_UPDATE_ERROR",
            details={"error": str(e)},
        )


@router.post("/reports/{report_id}/actions")
async def take_action_on_report(
    report_id: str, action: str, notes: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Validate action
        if action not in ["ban_user", "remove_item", "delete_message"]:
            return AdminResponse.error(message="Invalid action", code="INVALID_ACTION")

        # Get report
        report = reports_collection.find_one({"_id": ObjectId(report_id)})
        if not report:
            return AdminResponse.error(
                message="Report not found", code="REPORT_NOT_FOUND"
            )

        # Take action based on type
        if action == "ban_user":
            user_collection.update_one(
                {"_id": ObjectId(report["entity_id"])},
                {"$set": {"status": "suspended"}},
            )
        elif action == "remove_item":
            items_collection.update_one(
                {"_id": ObjectId(report["entity_id"])}, {"$set": {"status": "removed"}}
            )
        elif action == "delete_message":
            # Implementation depends on your message storage structure
            pass

        # Update report status and add action notes
        reports_collection.update_one(
            {"_id": ObjectId(report_id)},
            {
                "$set": {
                    "status": "resolved",
                    "action_taken": action,
                    "action_notes": notes,
                    "resolved_at": datetime.now(),
                }
            },
        )

        return AdminResponse.success(message="Action taken successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to take action on report",
            code="REPORT_ACTION_ERROR",
            details={"error": str(e)},
        )


@router.get("/items")
async def list_items(
    admin_check: bool = Depends(checkRole),
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
):
    try:
        # Build query
        query = {}
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]
        if category:
            query["category"] = category
        if status:
            query["status"] = status

        # Calculate skip
        skip = (page - 1) * limit

        # Get total count
        total = items_collection.count_documents(query)

        # Get items with specific field selection
        items = (
            items_collection.find(
                query,
                {
                    "title": 1,
                    "price": 1,
                    "status": 1,
                    "condition": 1,
                    "image_url": 1,
                    "seller_id": 1,
                    "created_at": 1,
                    "category": 1,
                },
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string and format response
        items_list = []
        for item in items:
            items_list.append(
                {
                    "_id": str(item["_id"]),
                    "title": item.get("title", ""),
                    "price": float(item.get("price", 0)),
                    "status": item.get("status", "inactive"),
                    "condition": item.get("condition", ""),
                    "image_url": item.get("image_url", ""),
                    "seller_id": (
                        str(item["seller_id"]) if "seller_id" in item else None
                    ),
                    "category": item.get("category", ""),
                    "created_at": item.get("created_at", None),
                }
            )

        return AdminResponse.success(
            data=items_list,
            meta={
                "total": total,
                "page": page,
                "limit": limit,
                "categories": [
                    "All Categories",
                    "Books",
                    "Electronics",
                    "Furniture",
                    "Other",
                ],  # Add your actual categories
            },
        )

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch items",
            code="ITEMS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.get("/items/{item_id}")
async def get_item(item_id: str, admin_check: bool = Depends(checkRole)):
    try:
        item = items_collection.find_one({"_id": ObjectId(item_id)})

        if not item:
            return AdminResponse.error(message="Item not found", code="ITEM_NOT_FOUND")

        item["_id"] = str(item["_id"])
        item["seller_id"] = str(item["seller_id"])

        return AdminResponse.success(data=item)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch item",
            code="ITEM_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.patch("/items/{item_id}")
async def update_item_status(
    item_id: str, status: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Validate status
        if status not in ["active", "removed", "flagged"]:
            return AdminResponse.error(message="Invalid status", code="INVALID_STATUS")

        # Update item
        result = items_collection.update_one(
            {"_id": ObjectId(item_id)}, {"$set": {"status": status}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(message="Item not found", code="ITEM_NOT_FOUND")

        return AdminResponse.success(message="Item status updated successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to update item",
            code="ITEM_UPDATE_ERROR",
            details={"error": str(e)},
        )


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, admin_check: bool = Depends(checkRole)):
    try:
        # Soft delete by updating status
        result = items_collection.update_one(
            {"_id": ObjectId(item_id)}, {"$set": {"status": "removed"}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(message="Item not found", code="ITEM_NOT_FOUND")

        return AdminResponse.success(message="Item deleted successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to delete item",
            code="ITEM_DELETE_ERROR",
            details={"error": str(e)},
        )


@router.get("/messages")
async def list_conversations(
    admin_check: bool = Depends(checkRole),
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
):
    try:
        # Build query
        query = {}
        if search:
            query["$or"] = [
                {"participants.name": {"$regex": search, "$options": "i"}},
                {"messages.content": {"$regex": search, "$options": "i"}},
            ]
        if status:
            query["status"] = status

        # Calculate skip
        skip = (page - 1) * limit

        # Get total count
        total = conversations_collection.count_documents(query)

        # Get conversations
        conversations = (
            conversations_collection.find(query)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # Convert ObjectId to string
        conversations_list = []
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
            conv["participants"] = [str(p) for p in conv["participants"]]
            conversations_list.append(conv)

        return AdminResponse.success(
            data=conversations_list, meta={"total": total, "page": page, "limit": limit}
        )

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch conversations",
            code="CONVERSATIONS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.get("/messages/{conversation_id}")
async def get_conversation(
    conversation_id: str, admin_check: bool = Depends(checkRole)
):
    try:
        conversation = conversations_collection.find_one(
            {"_id": ObjectId(conversation_id)}
        )

        if not conversation:
            return AdminResponse.error(
                message="Conversation not found", code="CONVERSATION_NOT_FOUND"
            )

        conversation["_id"] = str(conversation["_id"])
        conversation["participants"] = [str(p) for p in conversation["participants"]]

        return AdminResponse.success(data=conversation)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch conversation",
            code="CONVERSATION_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.patch("/messages/{conversation_id}")
async def update_conversation_status(
    conversation_id: str, status: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Validate status
        if status not in ["active", "blocked", "resolved"]:
            return AdminResponse.error(message="Invalid status", code="INVALID_STATUS")

        # Update conversation
        result = conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)}, {"$set": {"status": status}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(
                message="Conversation not found", code="CONVERSATION_NOT_FOUND"
            )

        return AdminResponse.success(message="Conversation status updated successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to update conversation",
            code="CONVERSATION_UPDATE_ERROR",
            details={"error": str(e)},
        )


@router.delete("/messages/{conversation_id}")
async def delete_conversation(
    conversation_id: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Soft delete by updating status
        result = conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)}, {"$set": {"status": "deleted"}}
        )

        if result.matched_count == 0:
            return AdminResponse.error(
                message="Conversation not found", code="CONVERSATION_NOT_FOUND"
            )

        return AdminResponse.success(message="Conversation deleted successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to delete conversation",
            code="CONVERSATION_DELETE_ERROR",
            details={"error": str(e)},
        )


@router.delete("/messages/{conversation_id}/messages/{message_id}")
async def delete_message(
    conversation_id: str, message_id: str, admin_check: bool = Depends(checkRole)
):
    try:
        # Update conversation to mark message as deleted
        result = conversations_collection.update_one(
            {"_id": ObjectId(conversation_id), "messages._id": ObjectId(message_id)},
            {
                "$set": {
                    "messages.$.status": "deleted",
                    "messages.$.deleted_at": datetime.now(),
                }
            },
        )

        if result.matched_count == 0:
            return AdminResponse.error(
                message="Message not found", code="MESSAGE_NOT_FOUND"
            )

        return AdminResponse.success(message="Message deleted successfully")

    except Exception as e:
        return AdminResponse.error(
            message="Failed to delete message",
            code="MESSAGE_DELETE_ERROR",
            details={"error": str(e)},
        )


@router.get("/settings")
async def get_settings(admin_check: bool = Depends(checkRole)):
    try:
        # Get settings from environment variables
        settings = {
            "site_name": os.getenv("SITE_NAME", "SpartanUp"),
            "contact_email": os.getenv("CONTACT_EMAIL", "support@spartanup.app"),
            "auto_moderation": os.getenv("AUTO_MODERATION", "true").lower() == "true",
            "report_threshold": int(os.getenv("REPORT_THRESHOLD", "3")),
            "notification_settings": {
                "email_notifications": os.getenv("EMAIL_NOTIFICATIONS", "true").lower()
                == "true",
                "urgent_alerts": os.getenv("URGENT_ALERTS", "true").lower() == "true",
            },
        }

        return AdminResponse.success(data=settings)

    except Exception as e:
        return AdminResponse.error(
            message="Failed to fetch settings",
            code="SETTINGS_FETCH_ERROR",
            details={"error": str(e)},
        )


@router.patch("/settings")
async def update_settings(
    site_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    auto_moderation: Optional[bool] = None,
    report_threshold: Optional[int] = None,
    email_notifications: Optional[bool] = None,
    urgent_alerts: Optional[bool] = None,
    admin_check: bool = Depends(checkRole),
):
    try:
        # Build update document
        update_doc = {}

        if site_name is not None:
            update_doc["SITE_NAME"] = site_name
        if contact_email is not None:
            update_doc["CONTACT_EMAIL"] = contact_email
        if auto_moderation is not None:
            update_doc["AUTO_MODERATION"] = str(auto_moderation).lower()
        if report_threshold is not None:
            update_doc["REPORT_THRESHOLD"] = str(report_threshold)
        if email_notifications is not None:
            update_doc["EMAIL_NOTIFICATIONS"] = str(email_notifications).lower()
        if urgent_alerts is not None:
            update_doc["URGENT_ALERTS"] = str(urgent_alerts).lower()

        # Update environment variables
        for key, value in update_doc.items():
            os.environ[key] = value

        # Get updated settings
        settings = {
            "site_name": os.getenv("SITE_NAME", "SpartanUp"),
            "contact_email": os.getenv("CONTACT_EMAIL", "support@spartanup.app"),
            "auto_moderation": os.getenv("AUTO_MODERATION", "true").lower() == "true",
            "report_threshold": int(os.getenv("REPORT_THRESHOLD", "3")),
            "notification_settings": {
                "email_notifications": os.getenv("EMAIL_NOTIFICATIONS", "true").lower()
                == "true",
                "urgent_alerts": os.getenv("URGENT_ALERTS", "true").lower() == "true",
            },
        }

        return AdminResponse.success(
            data=settings, message="Settings updated successfully"
        )

    except Exception as e:
        return AdminResponse.error(
            message="Failed to update settings",
            code="SETTINGS_UPDATE_ERROR",
            details={"error": str(e)},
        )
