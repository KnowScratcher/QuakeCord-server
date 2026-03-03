from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
import json
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def wavePage(request:Request):
    context = {
        "request": request,
        "stats": {"hour": 2, "day": 15, "month": 120},
        "stations": {
            "offline": [{"name": "Alishan-01", "id": "AS01"}],
            "suspended": [{"name": "Yushan-04", "id": "YS04"}],
            "online": [{"name": "Chunghua-02", "id": "CH02"}]
        },
        # Used for JavaScript Map markers
        "stations_json": [
            {"lat": 24.06, "lng": 120.50, "name": "Chunghua-02", "status": "online"}
        ],
        "detections": [
            {"id": "evt_101", "intensity": "III", "time": "2026-02-21 11:30:05"}
        ]
    }
    return templates.TemplateResponse("monitor.html", context)        
    # return templates.TemplateResponse(
    #     request=request, name="wave.html", context=context)