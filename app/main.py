from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from jyotishganit import calculate_birth_chart

app = FastAPI(title="Vedstone Astrology API")

geolocator = Nominatim(user_agent="vedstone_astrology_api")
timezone_finder = TimezoneFinder()


class BirthDetails(BaseModel):
    name: Optional[str] = None
    dob: str
    place: str
    intention: Optional[str] = None


SIGN_LORDS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NAKSHATRA_LORDS = {
    "Ashwini": "Ketu",
    "Bharani": "Venus",
    "Krittika": "Sun",
    "Rohini": "Moon",
    "Mrigashira": "Mars",
    "Ardra": "Rahu",
    "Punarvasu": "Jupiter",
    "Pushya": "Saturn",
    "Ashlesha": "Mercury",
    "Magha": "Ketu",
    "Purva Phalguni": "Venus",
    "Uttara Phalguni": "Sun",
    "Hasta": "Moon",
    "Chitra": "Mars",
    "Swati": "Rahu",
    "Vishakha": "Jupiter",
    "Anuradha": "Saturn",
    "Jyeshtha": "Mercury",
    "Mula": "Ketu",
    "Purva Ashadha": "Venus",
    "Uttara Ashadha": "Sun",
    "Shravana": "Moon",
    "Dhanishta": "Mars",
    "Shatabhisha": "Rahu",
    "Purva Bhadrapada": "Jupiter",
    "Uttara Bhadrapada": "Saturn",
    "Revati": "Mercury",
}

INTENTION_BOOSTS = {
    "success": {
        "Jupiter": 2,
        "Sun": 2,
        "Mars": 1
    },

    "love_marriage": {
        "Venus": 2,
        "Moon": 2,
        "Jupiter": 1
    },

    "peace": {
        "Moon": 2,
        "Jupiter": 2
    },

    "health": {
        "Sun": 2,
        "Moon": 1,
        "Mars": 1
    },

    "clarity": {
        "Mercury": 2,
        "Moon": 1
    },

    "spiritual_growth": {
        "Jupiter": 2,
        "Moon": 1
    }
}

PLANET_STONES = {
    "Sun": {
        "stone": "Carnelian",
        "slug": "carnelian-necklace",
        "meaning": "confidence, vitality, and self-expression",
    },
    "Moon": {
        "stone": "Pearl",
        "slug": "pearl-necklace",
        "meaning": "emotional balance, calmness, and inner clarity",
    },
    "Mars": {
        "stone": "Red Jasper",
        "slug": "red-jasper-necklace",
        "meaning": "courage, action, and grounded strength",
    },
    "Mercury": {
        "stone": "Green Onyx",
        "slug": "green-onyx-necklace",
        "meaning": "clarity, communication, and focus",
    },
    "Jupiter": {
        "stone": "Citrine",
        "slug": "citrine-necklace",
        "meaning": "growth, wisdom, abundance, and optimism",
    },
    "Venus": {
        "stone": "White Zircon",
        "slug": "white-zircon-necklace",
        "meaning": "love, beauty, harmony, and grace",
    },
    "Saturn": {
        "stone": "Amethyst",
        "slug": "amethyst-necklace",
        "meaning": "grounding, discipline, and spiritual steadiness",
    },
}

RESTRICTED_PLANETS = ["Rahu", "Ketu"]

FALLBACK_ORDER = {
    "Rahu": ["Mercury", "Saturn", "Moon"],
    "Ketu": ["Jupiter", "Moon", "Venus"],
}


def geocode_place(place: str):
    location = geolocator.geocode(place)
    if not location:
        raise HTTPException(status_code=400, detail=f"Could not find birthplace: {place}")

    lat = location.latitude
    lon = location.longitude

    timezone_name = timezone_finder.timezone_at(lat=lat, lng=lon)
    if not timezone_name:
        timezone_name = "Asia/Kolkata"

    return lat, lon, timezone_name


def get_timezone_offset_hours(dt: datetime, timezone_name: str) -> float:
    tz = ZoneInfo(timezone_name)
    localized = dt.replace(tzinfo=tz)
    offset = localized.utcoffset()
    return offset.total_seconds() / 3600


def normalize_nakshatra_name(name: str) -> str:
    if not name:
        return ""
    return name.strip().replace("Nakshatra", "").strip()


def pick_display_planet(sorted_scores: List[Tuple[str, int]]):
    internal_primary_planet, internal_primary_score = sorted_scores[0]

    if internal_primary_planet not in RESTRICTED_PLANETS:
        return internal_primary_planet, internal_primary_planet, internal_primary_score, False

    fallback_candidates = FALLBACK_ORDER.get(internal_primary_planet, [])

    for preferred in fallback_candidates:
        if preferred in PLANET_STONES:
            return preferred, internal_primary_planet, internal_primary_score, True

    for planet, score in sorted_scores:
        if planet in PLANET_STONES:
            return planet, internal_primary_planet, internal_primary_score, True

    return "Moon", internal_primary_planet, internal_primary_score, True


@app.get("/health")
def health():
    return {"status": "ok", "service": "vedstone-astrology-api"}


@app.post("/recommend-stone")
def recommend_stone(details: BirthDetails):
    try:
        lat, lon, timezone_name = geocode_place(details.place)

        # MVP choice: no birth time.
        # Use default local noon for Moon sign + Nakshatra calculation.
        birth_date = datetime.fromisoformat(details.dob)
        default_birth_datetime = datetime(
            birth_date.year,
            birth_date.month,
            birth_date.day,
            12,
            0,
            0,
        )

        timezone_offset = get_timezone_offset_hours(default_birth_datetime, timezone_name)

        chart = calculate_birth_chart(
            birth_date=default_birth_datetime,
            latitude=lat,
            longitude=lon,
            timezone_offset=timezone_offset,
            location_name=details.place,
            name=details.name or "Guest",
        )

        moon_sign = chart.d1_chart.planets[1].sign
        nakshatra = normalize_nakshatra_name(chart.panchanga.nakshatra)

        moon_lord = SIGN_LORDS.get(moon_sign)
        nakshatra_lord = NAKSHATRA_LORDS.get(nakshatra)

        scores: Dict[str, int] = {}

        if nakshatra_lord:
            scores[nakshatra_lord] = scores.get(nakshatra_lord, 0) + 5

        if moon_lord:
            scores[moon_lord] = scores.get(moon_lord, 0) + 3

        intention = (details.intention or "").strip().lower()
        boosts = INTENTION_BOOSTS.get(intention, {})

        for planet, boost in boosts.items():
            scores[planet] = scores.get(planet, 0) + boost

        if not scores:
            scores["Moon"] = 1

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        display_planet, internal_primary_planet, internal_primary_score, displayed_as_alternative = pick_display_planet(sorted_scores)

        stone_data = PLANET_STONES[display_planet]
        max_possible_score = 10
        confidence_score = min(round(sorted_scores[0][1] / max_possible_score, 2), 0.95)

        explanation = (
            f"Based on your birth date and birthplace, your Moon sign is {moon_sign} "
            f"and your Nakshatra is {nakshatra}. This creates a strong {internal_primary_planet} influence. "
            f"For a balanced daily-wear gemstone, we recommend {stone_data['stone']}, "
            f"traditionally associated with {stone_data['meaning']}."
        )

        if displayed_as_alternative:
            explanation = (
                f"Your birth profile shows a strong transformational {internal_primary_planet} influence. "
                f"For gentle daily alignment, we recommend {stone_data['stone']}, "
                f"traditionally associated with {stone_data['meaning']}."
            )

        return {
            "recommended_stone": stone_data["stone"],
            "planet": display_planet,
            "meaning": stone_data["meaning"],
            "explanation": explanation,
            "product_slug": stone_data["slug"],
            "confidence_score": confidence_score,
            "internal_primary_planet": internal_primary_planet,
            "internal_primary_score": internal_primary_score,
            "displayed_as_alternative": displayed_as_alternative,
            "debug": {
                "moon_sign": moon_sign,
                "nakshatra": nakshatra,
                "moon_lord": moon_lord,
                "nakshatra_lord": nakshatra_lord,
                "scores": scores,
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone_name,
                "used_default_time": "12:00"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/birth-reflection")
def birth_reflection(details: BirthDetails):
    try:
        lat, lon, timezone_name = geocode_place(details.place)

        birth_date = datetime.fromisoformat(details.dob)
        default_birth_datetime = datetime(
            birth_date.year,
            birth_date.month,
            birth_date.day,
            12,
            0,
            0,
        )

        timezone_offset = get_timezone_offset_hours(default_birth_datetime, timezone_name)

        chart = calculate_birth_chart(
            birth_date=default_birth_datetime,
            latitude=lat,
            longitude=lon,
            timezone_offset=timezone_offset,
            location_name=details.place,
            name=details.name or "Guest",
        )

        moon_sign = chart.d1_chart.planets[1].sign
        nakshatra = normalize_nakshatra_name(chart.panchanga.nakshatra)

        moon_lord = SIGN_LORDS.get(moon_sign)
        nakshatra_lord = NAKSHATRA_LORDS.get(nakshatra)

        dominant_planet = nakshatra_lord or moon_lord or "Moon"

        reflection_templates = {
            "Sun": "Your birth imprint carries a solar quality — warm, purposeful, and drawn toward recognition and forward movement.",
            "Moon": "Your birth imprint carries a lunar sensitivity — intuitive, emotionally aware, and deeply connected to inner rhythm.",
            "Mars": "Your birth imprint carries a martial spark — courageous, direct, and naturally drawn toward action and momentum.",
            "Mercury": "Your birth imprint carries a mercurial clarity — thoughtful, expressive, and naturally tuned toward learning and communication.",
            "Jupiter": "Your birth imprint carries a Jupiterian expansiveness — wise, hopeful, and drawn toward growth, guidance, and abundance.",
            "Venus": "Your birth imprint carries a Venusian softness — harmony-seeking, beauty-aware, and deeply connected to love and refinement.",
            "Saturn": "Your birth imprint carries a Saturnian steadiness — grounded, patient, and shaped by discipline, responsibility, and inner strength.",
            "Rahu": "Your birth imprint carries a transformational quality — curious, ambitious, and drawn toward change, reinvention, and new directions.",
            "Ketu": "Your birth imprint carries a contemplative quality — inward-looking, intuitive, and drawn toward meaning beyond the obvious."
        }

        return {
            "planet": dominant_planet,
            "moonSign": moon_sign,
            "nakshatra": nakshatra,
            "reflection": reflection_templates.get(dominant_planet, reflection_templates["Moon"]),
            "debug": {
                "moon_lord": moon_lord,
                "nakshatra_lord": nakshatra_lord,
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone_name,
                "used_default_time": "12:00"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
