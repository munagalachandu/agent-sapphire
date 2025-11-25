from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import openai  # or Groq or any LLM client

app = FastAPI(title="Agentic AI Backend")

# -------------------------
# INTERNAL STATE (SIMULATED)
# -------------------------

# Assume only 1 user
latest_data ={
  "heart_rate": 95,
  "rmssd": 20,
  "breath_rate": 16,
  "activity_level": 0.3,
  "resting_hr": 70,
  "baseline_rmssd": 40,
  "avg_hr_recent": 75
}



last_detected_case = None
last_priority = None
last_notification_needed = False
last_notification_text = None


# -------------------------
# RULE-BASED DETECTION
# -------------------------

def detect_case(data):
    hr = data["heart_rate"]
    hrv = data["rmssd"]
    br = data["breath_rate"]
    activity = data["activity_level"]
    resting_hr = data["resting_hr"]
    baseline_hrv = data["baseline_rmssd"]
    avg_recent = data["avg_hr_recent"]

    # HIGH PRIORITY CASES (Immediate popup)
    if hr > 120 and hrv < 20 and br > 20 and activity < 0.1:
        return "panic_warning", "high"

    if hr > resting_hr + 15 and hrv < baseline_hrv * 0.7:
        return "anxiety_flag", "high"

    if br > 22:
        return "rapid_breathing", "high"

    if activity < 0.1 and hr > 100:
        return "idle_hr_spike", "high"

    if hrv < 15:
        return "very_low_hrv", "high"

    # MEDIUM PRIORITY
    if hr > avg_recent + 15 and hrv < baseline_hrv:
        return "stress_spike", "medium"

    if hrv < baseline_hrv * 0.6 and hr > resting_hr:
        return "fatigue_trend", "medium"

    # LOW PRIORITY
    # (Example: mild stress but not requiring popup)
    if hr > avg_recent + 5:
        return "mild_stress", "low"

    # LOG ONLY
    if resting_hr > 85 and hrv < 25:
        return "hypertension_risk", "log"

    return None, "none"


# -------------------------
# INTERNAL LLM FOR MEDIUM PRIORITY
# -------------------------

def generate_notification(case):
    prompt = f"""
    Generate a short (under 20 words) supportive notification for case: {case}.
    Tone: gentle, calming, non-medical, non-diagnostic.
    Examples:
    - stress_spike: "You're a bit stressed. Try a calming breath or talk to our assistant."
    - fatigue_trend: "You've been tired lately. A short break may help."
    """

    # Replace with your model: Groq, OpenAI, etc.
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


# -------------------------
# STATUS ENDPOINT (FRONTEND ONLY CALLS THIS)
# -------------------------

@app.get("/status")
def get_status():
    global last_detected_case, last_priority, last_notification_needed, last_notification_text

    # Run detection on latest wearable data
    case, priority = detect_case(latest_data)

    # HIGH PRIORITY → breathing screen only
    if priority == "high":
        return {
            "case": case,
            "priority": "high",
            "notification_needed": False,
            "notification_text": None
        }

    # MEDIUM PRIORITY → show popup with generated text
    if priority == "medium":
        notif_text = generate_notification(case)
        return {
            "case": case,
            "priority": "medium",
            "notification_needed": True,
            "notification_text": notif_text
        }

    # LOW PRIORITY → send to chatbot but no popup
    if priority == "low":
        return {
            "case": case,
            "priority": "low",
            "notification_needed": False,
            "notification_text": None
        }

    # LOG ONLY or NO EVENTS
    return {
        "case": case,
        "priority": "none",
        "notification_needed": False,
        "notification_text": None
    }


# -------------------------
# OPTIONAL: UPDATE WEARABLE DATA FROM EXTERNAL SOURCE
# -------------------------

class WearableUpdate(BaseModel):
    heart_rate: float
    rmssd: float
    breath_rate: float
    activity_level: float
    resting_hr: float
    baseline_rmssd: float
    avg_hr_recent: float


@app.post("/update-wearable")
def update_data(data: WearableUpdate):
    global latest_data
    latest_data = data.dict()
    return {"status": "updated"}
