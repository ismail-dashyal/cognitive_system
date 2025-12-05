# capture/voice_module.py
import random
import time

def get_voice_emotion(duration=5, out_wav=None, sr=16000):
    """
    Safe stub: simulates recording briefly and returns a simple label.
    Avoids loading heavy HF models.
    """
    # simulate brief recording
    time.sleep(0.2)
    labels = ["neu", "calm", "happy", "stress", "angry"]
    # bias to neutral/calm
    r = random.random()
    if r < 0.65:
        return "neu"
    if r < 0.85:
        return "calm"
    return random.choice(["happy", "stress", "angry"])
