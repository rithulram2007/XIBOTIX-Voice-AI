import whisper
import sounddevice as sd
import soundfile as sf

MODEL = whisper.load_model("tiny")

SAMPLE_RATE = 16000
DURATION = 5


def record_audio():

    global audio_buffer

    audio_buffer = []

    print("🎤 Listening...")

    silence_counter = 0

    chunk_duration = 0.1       # 100 milliseconds

    chunk_size = int(SAMPLE_RATE * chunk_duration)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        callback=audio_callback,
        blocksize=chunk_size,
        dtype="float32",
    ):

        while True:

            if len(audio_buffer) == 0:
                continue

            latest_chunk = audio_buffer[-1]

            volume = calculate_volume(latest_chunk)

            if volume > THRESHOLD:

                silence_counter = 0

            else:

                silence_counter += chunk_duration

            if silence_counter >= SILENCE_DURATION:

                break

    audio = np.concatenate(audio_buffer, axis=0)

    sf.write("speech/input.wav", audio, SAMPLE_RATE)

    print("✅ Recording Saved")

def speech_to_text():

    result = MODEL.transcribe("speech/input.wav")

    return result["text"].strip()