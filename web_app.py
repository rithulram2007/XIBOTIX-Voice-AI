import gradio as gr
from assistant import run_assistant


def chat():

    question, answer, running = run_assistant()

    return question, answer


with gr.Blocks(title="XIBOTIX AI Voice Assistant") as demo:

    gr.Markdown(
        """
        # 🤖 XIBOTIX AI Voice Assistant

        Click the button and start speaking.
        """
    )

    user_text = gr.Textbox(
        label="You",
        interactive=False
    )

    assistant_text = gr.Textbox(
        label="Assistant",
        interactive=False,
        lines=6
    )

    listen_btn = gr.Button("🎤 Start Listening")

    listen_btn.click(
        fn=chat,
        outputs=[
            user_text,
            assistant_text
        ]
    )

demo.launch()