from speech.speech_to_text import record_audio, speech_to_text
from speech.text_to_speech import speak
from llm.chatbot import ask_llm


def run_assistant():

    record_audio()

    question = speech_to_text()

    print(f"\n🧑 You: {question}")

    if question.lower() in [
        "exit",
        "quit",
        "bye",
        "goodbye",
        "stop"
    ]:

        response = "Goodbye! Have a wonderful day."

        speak(response)

        return question, response, False

    response = ask_llm(question)

    print(f"\n🤖 Assistant: {response}")

    speak(response)

    return question, response, True