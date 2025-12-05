# capture/face_module.py
import random
import time

def get_face_emotion(device_index=0, read_timeout=2):
    """
    Safe fast stub for demo: returns one of common emotions.
    Replaces heavy ML model with deterministic/random fallback.
    """
    # Simulate short capture delay
    time.sleep(0.2)
    labels = ["neutral", "happy", "sad", "angry", "surprise", "fear", "disgust", "calm"]
    # random choice but biased to neutral for stable demo
    r = random.random()
    if r < 0.6:
        return "neutral"
    if r < 0.8:
        return random.choice(["happy", "calm", "surprise"])
    return random.choice(["sad", "angry", "fear", "disgust"])
