import pyttsx3

def speak(text):
    print(">>> SPEAK FUNCTION CALLED")

    engine = pyttsx3.init()

    engine.say(text)

    engine.runAndWait()

    engine.stop()

    print(">>> SPEAK FINISHED")