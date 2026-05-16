from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Vedstone Astrology API")


class BirthDetails(BaseModel):
    name: Optional[str] = None
    dob: str
    time: str
    place: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    intention: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "vedstone-astrology-api"}


@app.post("/recommend-stone")
def recommend_stone(details: BirthDetails):
    # Temporary mock recommendation.
    # Later we will replace this with JyotishGanit + real stone logic.
    return {
        "recommended_stone": "Pearl",
        "planet": "Moon",
        "meaning": "Emotional balance and inner calm",
        "explanation": "Pearl is traditionally associated with Moon energy, calmness, emotional grounding, and intuitive clarity.",
        "product_slug": "pearl-necklace",
        "confidence_score": 0.82
    }
