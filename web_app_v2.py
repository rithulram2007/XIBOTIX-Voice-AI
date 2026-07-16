import gradio as gr
from assistant import run_assistant

history=[]

def listen():

    question,answer,running=run_assistant()

    history.append(
        {
            "role":"user",
            "content":question
        }
    )

    history.append(
        {
            "role":"assistant",
            "content":answer
        }
    )

    return history


def clear():

    history.clear()

    return []


with open("assets/style.css") as f:

    css=f.read()


with gr.Blocks(

    title="XIBOTIX Voice AI",

    css=css,

    theme=gr.themes.Base()

) as demo:

    gr.HTML("""

<div class="main-card">

<div class="title">

XIBOTIX Voice AI

</div>

<div class="subtitle">

Real-time Conversational Assistant for Robotics &
Rehabilitation Technologies

</div>

</div>

""")

    status=gr.HTML("""

<div class="status">

Status : Ready

</div>

""")

    chatbot=gr.Chatbot(

        type="messages",

        height=520,

        show_label=False
    )

    with gr.Row():

        listen_btn=gr.Button(

            "Start Listening",

            variant="primary",

            scale=4

        )

        clear_btn=gr.Button(

            "Clear Conversation",

            scale=1

        )

    gr.Markdown("""

---

### Technology Stack

Whisper

Groq Llama 3.3

Microsoft Edge TTS

Gradio

""")

    listen_btn.click(

        fn=listen,

        outputs=chatbot

    )

    clear_btn.click(

        fn=clear,

        outputs=chatbot

    )

demo.launch()