from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# -------------------------
# Conversation Memory
# -------------------------

messages = [

    {
        "role": "system",
        "content":
        "You are a friendly AI Voice Assistant. Keep answers concise, natural and conversational."
    }

]


def ask_llm(prompt):
    global messages

    messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    response = client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=messages,

        temperature=0.7,

        max_tokens=512

    )

    answer = response.choices[0].message.content

    messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
    # Keep only the last 10 conversation turns
    if len(messages) > 21:
        messages = [messages[0]] + messages[-20:]
 
    return answer