# capture/fusion_module.py
import random

def compute_cognitive_state(face_emotion, voice_emotion):
    # normalize
    f = (face_emotion or "neutral").lower()
    v = (voice_emotion or "neu").lower()

    emotion_to_stress = {
        "angry": 0.9, "fear": 0.8, "sad": 0.7,
        "neutral": 0.3, "happy": 0.2, "surprise": 0.5, "calm": 0.2, "neu": 0.3, "disgust": 0.7
    }
    emotion_to_fatigue = {
        "neutral": 0.4, "sad": 0.8, "angry": 0.6,
        "happy": 0.2, "surprise": 0.3, "fear": 0.7, "calm": 0.3, "neu": 0.4, "disgust": 0.5
    }

    stress = (emotion_to_stress.get(f, 0.5) + emotion_to_stress.get(v, 0.5)) / 2
    fatigue = (emotion_to_fatigue.get(f, 0.5) + emotion_to_fatigue.get(v, 0.5)) / 2

    # small random noise for demo variability
    stress += random.uniform(-0.05, 0.05)
    fatigue += random.uniform(-0.05, 0.05)

    stress = min(max(stress, 0.0), 1.0)
    fatigue = min(max(fatigue, 0.0), 1.0)
    attention = round(max(0.0, min(1.0, 1 - (stress + fatigue) / 2)), 2)

    return {"stress": round(stress, 2), "fatigue": round(fatigue, 2), "attention": attention}
