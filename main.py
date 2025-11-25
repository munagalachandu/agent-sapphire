from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Agentic AI Backend")

# -------------------------
# INTERNAL STATE (SIMULATED)
# -------------------------

# TEST DATA FOR MEDIUM PRIORITY "stress_spike"
# resting_hr = 70, baseline_rmssd = 40
# hr (88) > resting_hr + 15 (85) ✓
# rmssd (28) < baseline_rmssd * 0.75 (30) ✓
latest_data = {
  "heart_rate": 89,           # Elevated (70 + 18)
  "rmssd": 28,                # Below 75% of baseline (40 * 0.75 = 30)
  "breath_rate": 16,
  "activity_level": 0.3,
  "resting_hr": 70,
  "baseline_rmssd": 40,
  "avg_hr_recent": 70
}

# Initialize Groq client
client = Groq(api_key="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")  # <<< PUT YOUR KEY HERE


# -------------------------
# RULE-BASED DETECTION (NON-CLASHING)
# -------------------------

def detect_case(data):
    hr = data["heart_rate"]
    hrv = data["rmssd"]
    br = data["breath_rate"]
    activity = data["activity_level"]
    resting_hr = data["resting_hr"]
    baseline_hrv = data["baseline_rmssd"]
    avg_recent = data["avg_hr_recent"]

    # ---------------- HIGH PRIORITY ----------------

    # 1. Panic pattern
    if hr > resting_hr + 40 and hrv < baseline_hrv * 0.55 and br > 22 and activity < 0.1:
        return "panic_warning", "high"

    # 2. Acute anxiety spike
    if hr > resting_hr + 30 and hrv < baseline_hrv * 0.6:
        return "anxiety_flag", "high"

    # 3. Hyperventilation
    if br > 26 and activity < 0.2:
        return "rapid_breathing", "high"

    # 4. Severe low HRV
    if hrv < 15:
        return "very_low_hrv", "high"

    # ---------------- MEDIUM PRIORITY ----------------

    # Stress trend
    if hr > resting_hr + 15 and hrv < baseline_hrv * 0.75:
        return "stress_spike", "medium"

    # Fatigue trend
    if hrv < baseline_hrv * 0.65 and hr > resting_hr + 5:
        return "fatigue_trend", "medium"

    # ---------------- LOW PRIORITY ----------------

    if hr > avg_recent + 10:
        return "mild_stress", "low"

    if hrv < baseline_hrv * 0.85:
        return "slight_hrv_drop", "low"

    # ---------------- LOG ONLY ----------------

    if resting_hr > 90 and hrv < 25:
        return "hypertension_risk", "log"

    return None, "none"


# -------------------------
# GROQ LLM FOR MEDIUM PRIORITY
# -------------------------

def generate_notification(case):
    prompt = (
        f"The user is experiencing {case}. Generate a short supportive notification (under 25 words) "
        f"that suggests checking out ONE of these app features: Chatbot, Friend, Therapist, or Journal. "
        f"Use a warm, helpful tone. Example: 'Feeling stressed? Chat with our AI Friend for support.'"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Updated to current model
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0.7
    )

    return response.choices[0].message.content


# -------------------------
# STATUS ENDPOINT
# -------------------------

@app.get("/status")
def get_status():
    case, priority = detect_case(latest_data)

    # HIGH PRIORITY → no notification popup
    if priority == "high":
        return {
            "case": case,
            "priority": "high",
            "notification_needed": False,
            "notification_text": None
        }

    # MEDIUM PRIORITY → generate Groq LLM notification
    if priority == "medium":
        notif_text = generate_notification(case)
        return {
            "case": case,
            "priority": "medium",
            "notification_needed": True,
            "notification_text": notif_text
        }

    # LOW PRIORITY
    if priority == "low":
        return {
            "case": case,
            "priority": "low",
            "notification_needed": False,
            "notification_text": None
        }

    # NONE / LOG ONLY
    return {
        "case": case,
        "priority": "none",
        "notification_needed": False,
        "notification_text": None
    }


# -------------------------
# UPDATE WEARABLE DATA
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
