from fastapi import APIRouter, HTTPException, Form
from app.config import report_collection
from bson import ObjectId
from app.models.report_model import Report
from datetime import datetime

router = APIRouter()

@router.post("/")
async def report_post(report: Report):
    try: 
        report_data= { 
            "entity_id": ObjectId(report.entity_id),
            "reported_by": ObjectId(report.reported_by),
            "reason": report.reason
        }
        report_collection.insert_one(report_data)
        return {"message": "Post reported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail = str(e))
    
