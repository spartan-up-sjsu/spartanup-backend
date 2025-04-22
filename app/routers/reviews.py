from fastapi import APIRouter, HTTPException
from ..models.review_model import Review
from bson import ObjectId
from app.config import reviews_collection

router = APIRouter()

@router.post("/")
async def review_post(review: Review):
    try: 
        review_data= { 
            "item_id": ObjectId(review.item_id),
            "reviewer_id": ObjectId(review.reviewer_id),
            "seller_id": ObjectId(review.seller_id),
            "rating": review.rating,
            "comment": review.comment
        }
        reviews_collection.insert_one(review_data)
        return {"message": "Post reviewed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail = str(e))

@router.get("/{user_id}")
def get_user_reviews(user_id: str):
    user_object_id = ObjectId(user_id)
    reviews = list(reviews_collection.find({"seller_id": user_object_id}))

    if not reviews:
        return {"reviews": [], "average_rating": 0}

    reviews_list = [
        {
            **review,
            "_id": str(review["_id"]),
            "item_id": str(review["item_id"]),
            "reviewer_id": str(review["reviewer_id"]),
            "seller_id": str(review["seller_id"]),
        }
        for review in reviews
    ]


    total_rating = sum(review["rating"] for review in reviews)
    average_rating = total_rating / len(reviews)

    return {"reviews": reviews_list, "average_rating": round(average_rating, 1)}
