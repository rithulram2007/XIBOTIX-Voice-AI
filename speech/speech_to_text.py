import whisper
import sounddevice as sd
import soundfile as sf

MODEL = whisper.load_model("tiny")

SAMPLE_RATE = 16000
DURATION = 5


def record_audio():

    print("🎤 Speak now...")

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )

    sd.wait()

    sf.write("speech/input.wav", audio, SAMPLE_RATE)

    print("✅ Recording Saved")


def speech_to_text():

    result = MODEL.transcribe("speech/input.wav")

    return result["text"].strip()