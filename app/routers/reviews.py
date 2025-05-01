from fastapi import APIRouter, HTTPException
from ..models.review_model import Review
from bson import ObjectId
from app.config import reviews_collection

router = APIRouter()

@router.post("/")
async def review_post(review: Review):
    try: 
        review_data = { 
            "item_id": ObjectId(review.item_id),
            "reviewer_id": ObjectId(review.reviewer_id),
            "seller_id": ObjectId(review.seller_id),
            "rating": review.rating,
            "review_text": review.review_text,
            "tags": [tag.value for tag in review.tags] if review.tags else None
        }
        reviews_collection.insert_one(review_data)
        return {"message": "Review posted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail = str(e))

@router.get("/{user_id}")
def get_user_reviews(user_id: str):
    user_object_id = ObjectId(user_id)
    
    # Aggregation pipeline to get the last 10 reviews with reviewer info
    pipeline = [
        # Match reviews for the specified seller
        {"$match": {"seller_id": user_object_id}},
        # Sort by most recent first (assuming _id contains timestamp)
        {"$sort": {"_id": -1}},
        # Limit to last 10 reviews
        {"$limit": 10},
        # Lookup reviewer information from users collection
        {"$lookup": {
            "from": "users",
            "localField": "reviewer_id",
            "foreignField": "_id",
            "as": "reviewer_info"
        }},
        # Unwind the reviewer_info array
        {"$unwind": {"path": "$reviewer_info", "preserveNullAndEmptyArrays": True}},
        # Project only the fields we need
        {"$project": {
            "_id": 1,
            "item_id": 1,
            "reviewer_id": 1,
            "seller_id": 1,
            "rating": 1,
            "review_text": 1,
            "tags": 1,
            "reviewer_name": "$reviewer_info.name",
            "reviewer_profile_pic": "$reviewer_info.picture"
        }}
    ]
    
    # Execute the aggregation pipeline
    reviews = list(reviews_collection.aggregate(pipeline))
    
    if not reviews:
        return {"reviews": [], "average_rating": 0}
    
    # Convert ObjectId to string for JSON serialization
    reviews_list = [
        {
            **{k: str(v) if isinstance(v, ObjectId) else v for k, v in review.items() if k not in ["reviewer_name", "reviewer_profile_pic"]},
            "reviewer_name": review.get("reviewer_name", "Unknown User"),
            "reviewer_profile_pic": review.get("reviewer_profile_pic", None)
        }
        for review in reviews
    ]
    
    # Calculate average rating from all reviews (not just the last 10)
    all_ratings = list(reviews_collection.find({"seller_id": user_object_id}, {"rating": 1}))
    
    if not all_ratings:
        average_rating = 0
    else:
        total_rating = sum(review["rating"] for review in all_ratings)
        average_rating = total_rating / len(all_ratings)
    
    return {"reviews": reviews_list, "average_rating": round(average_rating, 1)}
