"""
XIBOTIX Voice Interface — frontend only.

Backend is untouched: this file imports and calls run_assistant() from
assistant.py exactly as before. run_assistant() is a single blocking call
(record -> transcribe -> LLM -> speak, all inside assistant.py), so this
file has no way to know the *real* boundary between those internal steps.

Design decision: run_assistant() executes on a background thread. The main
thread drives the status pill / orb through time-boxed stages instead of
true callback-driven progress:

  - "Recording audio..."   -> exactly DURATION seconds (speech_to_text.DURATION
                               is a real constant, so this stage is accurate,
                               not a guess).
  - "Transcribing speech..." / "Generating response..." / "Speaking..."
                            -> illustrative estimates, because assistant.py
                               gives no signal for when each of those finishes.
                               The loop polls the worker thread every 200ms and
                               breaks out of a stage the moment the thread
                               actually completes, so the UI can never get
                               "stuck" narrating a stage that's already over.

This is the honest tradeoff available without editing assistant.py. If real
per-stage progress is ever needed, assistant.py would need to yield/callback
after each internal step -- that's a backend change, out of scope here.
"""

import threading
import queue
import time

import gradio as gr

from assistant import run_assistant
from speech.speech_to_text import DURATION as RECORD_SECONDS

history = []


# ---------------------------------------------------------------------------
# Status pill + voice-orb HTML fragments
# Each state is a distinct visual (color + animation class), not just a
# text swap, so the interface reads as "the system is doing X" rather than
# a generic spinner.
# ---------------------------------------------------------------------------

def _panel(state: str, label: str) -> str:
    return f"""
    <div class="status-row status-row-{state}">
        <div class="status-dot dot-{state}"></div>
        <div class="status-text">{label}</div>
    </div>
    """


def _orb(state: str) -> str:
    return f"""
    <div class="orb-wrap">
        <div class="orb orb-{state}">
            <div class="orb-ring ring-1"></div>
            <div class="orb-ring ring-2"></div>
            <div class="orb-core"></div>
        </div>
    </div>
    """


STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_TRANSCRIBING = "transcribing"
STATE_GENERATING = "generating"
STATE_SPEAKING = "speaking"
STATE_READY = "ready"
STATE_ERROR = "error"

STATE_LABELS = {
    STATE_IDLE: "System Idle",
    STATE_LISTENING: "Recording audio...",
    STATE_TRANSCRIBING: "Transcribing speech...",
    STATE_GENERATING: "Generating response...",
    STATE_SPEAKING: "Speaking...",
    STATE_READY: "Awaiting Voice Input",
    STATE_ERROR: "Error — see conversation log",
}


def render_state(state: str):
    return _panel(state, STATE_LABELS[state]), _orb(state)


# ---------------------------------------------------------------------------
# Backend worker. run_assistant() is synchronous and blocking, so it is
# executed on its own thread. Results (or exceptions) are handed back
# through a queue rather than a return value, since threading.Thread has
# no return channel of its own.
# ---------------------------------------------------------------------------
def _backend_worker(result_queue: "queue.Queue"):
    try:
        question, answer, running = run_assistant()
        result_queue.put(("ok", question, answer, running))
    except Exception as exc:  # noqa: BLE001 - surface any backend failure to the UI
        result_queue.put(("error", str(exc)))


# Post-recording stages, each with an illustrative duration in seconds.
# These do not reflect measured timings from assistant.py (it exposes none) —
# they exist so the interface narrates *something* plausible while it waits,
# and every wait is interruptible the instant the thread actually finishes.
_ESTIMATED_STAGES = [
    (STATE_TRANSCRIBING, 1.5),
    (STATE_GENERATING, 2.0),
    (STATE_SPEAKING, 1.5),
]
_POLL_INTERVAL = 0.2


def run_turn():
    """
    Generator-based click handler. Gradio 5.x supports yielding multiple
    UI updates from a single event handler, which is what makes the staged
    status possible without blocking the UI thread on the full backend call.
    """

    # --- Stage: recording -------------------------------------------------
    # This is the one stage we can time precisely, because DURATION is a
    # real constant read from speech_to_text.py (not modified, just imported).
    status_html, orb_html = render_state(STATE_LISTENING)
    busy_btn = gr.update(value="Listening...", interactive=False)
    yield history, status_html, orb_html, busy_btn

    result_queue: "queue.Queue" = queue.Queue()
    worker = threading.Thread(target=_backend_worker, args=(result_queue,), daemon=True)
    worker.start()

    # Wait out the known recording duration (or until the thread somehow
    # finishes early, e.g. an immediate exception before recording starts).
    elapsed = 0.0
    while elapsed < RECORD_SECONDS and worker.is_alive():
        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL

    # --- Stages: transcribing / generating / speaking ----------------------
    for state, budget in _ESTIMATED_STAGES:
        status_html, orb_html = render_state(state)
        yield history, status_html, orb_html, busy_btn

        stage_elapsed = 0.0
        while stage_elapsed < budget and worker.is_alive():
            time.sleep(_POLL_INTERVAL)
            stage_elapsed += _POLL_INTERVAL

        if not worker.is_alive():
            break  # backend finished early — stop narrating stages that are already over

    worker.join()

    # --- Resolve result ------------------------------------------------
    try:
        outcome = result_queue.get_nowait()
    except queue.Empty:
        # Should not happen (worker always puts exactly one result), but
        # guarded so a race condition can never leave the UI hanging.
        outcome = ("error", "No response received from the assistant backend.")

    if outcome[0] == "error":
        error_message = outcome[1]
        history.append({
            "role": "assistant",
            "content": f"⚠ Backend error: {error_message}",
        })
        status_html, orb_html = render_state(STATE_ERROR)
        ready_btn = gr.update(value="Start Conversation", interactive=True)
        yield history, status_html, orb_html, ready_btn
        return

    _, question, answer, running = outcome

    if question is not None:
        history.append({"role": "user", "content": question})
    if answer is not None:
        history.append({"role": "assistant", "content": answer})

    final_state = STATE_READY if running else STATE_IDLE
    status_html, orb_html = render_state(final_state)
    ready_btn = gr.update(value="Start Conversation", interactive=True)
    yield history, status_html, orb_html, ready_btn


def clear_history():
    history.clear()
    status_html, orb_html = render_state(STATE_IDLE)
    return [], status_html, orb_html


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root{
    --bg:            #101115;
    --panel:         #1f232c;
    --panel-2:       #262b35;
    --border:        #3c414d;
    --text:          #e7e8ec;
    --text-dim:      #8b8f9a;
    --text-faint:    #565a64;
    --accent:        #ffb020;
    --accent-dim:    #6b4d16;
    --accent-glow:   rgba(255,176,32,0.18);
    --user-accent:   #6fb1ff;
    --gen-accent:    #b48cff;
    --gen-glow:      rgba(180,140,255,0.20);
    --speak-accent:  #58c98f;
    --speak-glow:    rgba(88,201,143,0.20);
    --danger:        #e2574c;
    --danger-glow:   rgba(226,87,76,0.20);
    --ok:            #58c98f;
    --ok-glow:       rgba(88,201,143,0.20);
    --radius:        10px;
    --font-display:  'Space Grotesk', sans-serif;
    --font-body:     'Inter', sans-serif;
    --font-mono:     'IBM Plex Mono', monospace;
}

.gradio-container{
    background:
        linear-gradient(var(--bg), var(--bg)),
        repeating-linear-gradient(0deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 34px),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 34px);
    font-family: var(--font-body);
    color: var(--text);
    max-width:100% !important;
    padding:24px 35px !important;
    margin: 0 !important;
    width:100% !important;
}

footer{ display:none !important; }

/* ---------- top bar ---------- */
.topbar{
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:16px 4px 12px 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
}
.brand{ display:flex; align-items:center; gap:12px; }
.brand-mark{
    width:34px; height:34px;
    border:1.5px solid var(--accent);
    position:relative;
    transform: rotate(45deg);
    flex-shrink:0;
}
.brand-mark::after{
    content:"";
    position:absolute;
    inset:6px;
    background: var(--accent);
    opacity:0.85;
}
.brand-text{ line-height:1.15; }
.brand-title{
    font-family: var(--font-display);
    font-weight:700;
    font-size:42px;
    letter-spacing:.03em;
    color:#ffffff;
}
.brand-white{ color:#ffffff; }
.brand-accent{ color: var(--accent); }
.brand-sub{
    font-family: var(--font-mono);
    font-size:15px;
    line-height:1.8;
    color:#9ca3af;
    max-width:420px;
    margin-top:4px;
}

/* ---------- status pill ---------- */
.status-row{
    display:flex; align-items:center; gap:9px;
    font-family: var(--font-mono);
    font-size:13px;
    letter-spacing:0.09em;
    color:#F8FAFC;
    border:1px solid var(--border);
    background: var(--panel);
    padding:10px 18px;
    border-radius: 100px;
    width:fit-content;
    margin:0 auto 20px auto;
    margin-bottom:24px;
    transition: border-color 0.25s ease, background 0.25s ease;
}
.status-row-idle,
.status-row-ready{
    border-color: rgba(88,201,143,0.45);
    background: rgba(88,201,143,0.08);
}
.status-row-listening{
    border-color: rgba(255,176,32,0.45);
    background: rgba(255,176,32,0.08);
}
.status-row-transcribing{
    border-color: rgba(111,177,255,0.45);
    background: rgba(111,177,255,0.08);
}
.status-row-generating{
    border-color: rgba(180,140,255,0.45);
    background: rgba(180,140,255,0.08);
}
.status-row-speaking{
    border-color: rgba(88,201,143,0.45);
    background: rgba(88,201,143,0.08);
}
.status-row-error{
    border-color: rgba(226,87,76,0.45);
    background: rgba(226,87,76,0.08);
}
.status-text{

    color:#F8FAFC !important;

    font-weight:600 !important;

    opacity:1 !important;

}
.status-dot{ width:7px; height:7px; border-radius:50%; background:var(--text-faint); }
.dot-idle{ background: var(--ok); box-shadow:0 0 0 0 var(--ok-glow); animation: dotpulse 1.6s ease-out infinite; }
.dot-listening{ background: var(--accent); box-shadow:0 0 0 0 var(--accent-glow); animation: dotpulse 1.1s ease-out infinite; }
.dot-transcribing{ background: var(--user-accent); animation: dotblink 0.6s ease-in-out infinite; }
.dot-generating{ background: var(--gen-accent); animation: dotblink 0.6s ease-in-out infinite; }
.dot-speaking{ background: var(--speak-accent); box-shadow:0 0 0 0 var(--speak-glow); animation: dotpulse 0.9s ease-out infinite; }
.dot-ready{ background: var(--ok); box-shadow:0 0 0 0 var(--ok-glow); animation: dotpulse 1.1s ease-out infinite; }
.dot-error{ background: var(--danger); box-shadow:0 0 0 0 var(--danger-glow); animation: dotpulse 1.1s ease-out infinite; }
@keyframes dotpulse{
    0%{ box-shadow: 0 0 0 0 currentColor; }
    70%{ box-shadow: 0 0 0 8px rgba(0,0,0,0); }
    100%{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }
}
@keyframes dotblink{ 0%,100%{ opacity:1; } 50%{ opacity:0.25; } }

/* ---------- left control panel ---------- */
.control-panel{

    background:var(--panel);

    border:1px solid var(--border);

    border-radius:14px;

    padding:22px;

    text-align:center;

    overflow:visible;

    height:600px;

    display:flex;

    flex-direction:column;

    justify-content:flex-start;

    align-items:center;

    gap:22px;
}
.control-panel > *{
    width:100%;
}

.control-panel .gr-button{
    width:100%;
}
.control-panel::-webkit-scrollbar,
.control-col::-webkit-scrollbar{
    display:none;
}
.control-panel *{
    overflow: visible !important;
    scrollbar-width: none !important;
}
.control-panel{
    overflow: hidden;
    scrollbar-width: none !important;
}
.control-panel *::-webkit-scrollbar{
    display:none !important;
    width:0 !important;
    height:0 !important;
}
.control-col{
    overflow:visible !important;
    scrollbar-width:none;
}
.conversation-col{
    display:flex;
    flex-direction:column;
}


.orb-wrap{

    display:flex;

    justify-content:center;

    align-items:center;

    width:100%;

    height:140px;

    margin:0 auto;

    padding:0;

    overflow:visible;
}
.orb{

    width:110px;

    height:110px;

    position:relative;

    display:flex;

    justify-content:center;

    align-items:center;

    margin:0 auto;
}
.orb-core{
    width:34px; height:34px; border-radius:50%;
    background: var(--text-faint);
    transition: background 0.3s ease, box-shadow 0.3s ease;
    box-shadow:

    0 0 15px rgba(88,201,143,.25),

    0 0 35px rgba(88,201,143,.18),

    0 0 60px rgba(88,201,143,.12);
}
.orb-ring{
    position:absolute; border-radius:50%; border:1px solid var(--border);
    opacity:0.6;
}
.ring-1{ width:64px; height:64px; }
.ring-2{ width:96px; height:96px; }

.orb-idle .orb-core{
    background:#ffffff;
    box-shadow:
        0 0 20px rgba(88,201,143,.35),
        0 0 40px rgba(88,201,143,.25),
        0 0 70px rgba(88,201,143,.12);
}
.orb-idle .ring-1{ border-color: rgba(88,201,143,.35); }
.orb-idle .ring-2{ border-color: rgba(88,201,143,.22); }

.orb-listening .orb-core{ background: var(--accent); box-shadow:0 0 22px var(--accent-glow); }
.orb-listening .ring-1{ border-color: var(--accent-dim); animation: ringpulse 1.4s ease-out infinite; }
.orb-listening .ring-2{ border-color: var(--accent-dim); animation: ringpulse 1.4s ease-out infinite 0.35s; }
@keyframes ringpulse{
    0%{ transform: scale(0.7); opacity:0.75; }
    100%{ transform: scale(1.25); opacity:0; }
}

.orb-transcribing .orb-core{ background: var(--user-accent); }
.orb-transcribing .ring-1{ border-color: transparent; border-top-color: var(--user-accent); animation: spin 0.9s linear infinite; }
.orb-transcribing .ring-2{ border-color: transparent; border-bottom-color: var(--user-accent); animation: spin 1.6s linear infinite reverse; }

.orb-generating .orb-core{ background: var(--gen-accent); box-shadow:0 0 22px var(--gen-glow); }
.orb-generating .ring-1{ border-color: transparent; border-top-color: var(--gen-accent); animation: spin 0.7s linear infinite; }
.orb-generating .ring-2{ border-color: transparent; border-bottom-color: var(--gen-accent); animation: spin 1.3s linear infinite reverse; }
@keyframes spin{ 100%{ transform: rotate(360deg); } }

.orb-speaking .orb-core{ background: var(--speak-accent); box-shadow:0 0 22px var(--speak-glow); animation: corepulse 0.8s ease-in-out infinite; }
.orb-speaking .ring-1{ border-color: var(--speak-accent); opacity:0.35; animation: ringpulse 1s ease-out infinite; }
.orb-speaking .ring-2{ border-color: var(--speak-accent); opacity:0.25; animation: ringpulse 1s ease-out infinite 0.3s; }
@keyframes corepulse{ 0%,100%{ transform: scale(1); } 50%{ transform: scale(1.15); } }

.orb-ready .orb-core{ box-shadow:

0 0 20px rgba(88,201,143,.25),

0 0 40px rgba(88,201,143,.18),

0 0 70px rgba(88,201,143,.08); background: var(--ok);}
.orb-ready .ring-1{ border-color: rgba(88,201,143,.35); }
.orb-ready .ring-2{ border-color: rgba(88,201,143,.22); }

.orb-error .orb-core{ background: var(--danger); box-shadow:0 0 18px var(--danger-glow); }
.orb-error .ring-1{ border-color: var(--danger); opacity:0.3; }
.orb-error .ring-2{ border-color: var(--danger); opacity:0.2; }

.control-caption{

    font-family:var(--font-mono);

    font-size:14px;

    color:#8B8F9A;

    line-height:1.8;

    text-align:center;

    margin:0;
}

/* ---------- buttons ---------- */
/* ---------- buttons ---------- */

#listen_btn{
    background: var(--accent) !important;
    color: #1a1200 !important;
    border:none !important;

    font-family: var(--font-display) !important;
    font-weight:600 !important;
    font-size:15px !important;
    letter-spacing:0.02em;

    height:56px !important;

    border-radius:12px !important;

    box-shadow:0 0 0 1px var(--accent-dim);

    margin-top:auto;
}

#listen_btn:hover{
    filter:brightness(1.08);
}

#listen_btn:disabled{
    opacity:.6 !important;
    filter:none !important;
    cursor:not-allowed !important;
}



#clear_btn{
    background:transparent !important;
    border:1px solid var(--border) !important;

    color:var(--text-dim) !important;

    font-family:var(--font-body) !important;

    height:50px !important;

    font-size:15px !important;

    border-radius:12px !important;

    margin-top:0;
}

#clear_btn:hover{
    border-color:var(--danger) !important;
    color:var(--danger) !important;
}

/* ---------- conversation log ---------- */
.log-header{
    display:flex; justify-content:space-between; align-items:baseline;
    padding: 0 2px 0 2px;
}
.log-title{
    font-family:var(--font-display);
    font-weight:600;
    font-size:14px;

    text-transform:uppercase;

    color:#ffffff !important;

    opacity:1 !important;

    margin:0;
    padding:0 0 12px 0;
}
.log-hint{
    font-family: var(--font-mono);
    font-size:11px;
    color: var(--text-faint);
}
.main{

padding:0 !important;

margin:0 !important;

}

#chat_log{

    background:var(--panel) !important;

    border:1px solid var(--border) !important;

    border-radius:18px !important;
    margin-top:0 !important;
    padding-top:0 !important;
    height:600px !important;

}

#chat_log .message-wrap{ gap:8px !important; }

#chat_log .message{
    font-family: var(--font-body) !important;
    border:1px solid var(--border) !important;
    padding:9px 14px !important;
    font-size:14px !important;
    line-height:1.45 !important;
    border-radius:14px !important;
    transition:all .2s ease;
    color:#F8FAFC !important;
    
}

#chat_log .message.user{

    background:#1E293B !important;

    border-left:5px solid #60A5FA !important;

}
#chat_log .message.bot{

    background:#232933 !important;

    border-left:5px solid #FBBF24 !important;

}
/* ===============================
   Chat Text Color
================================== */

#chat_log .message{
    color: #F3F4F6 !important;
}

#chat_log .message p{
    color: #F3F4F6 !important;
}

#chat_log .message span{
    color: #F3F4F6 !important;
}

#chat_log .message div{
    color: #F3F4F6 !important;
}

#chat_log .message *{
    color:#F3F4F6 !important;
}

/* ---------- empty conversation placeholder ---------- */
.empty-chat{
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:8px;
    padding:60px 20px;
    color: var(--text-dim);
}
.empty-chat-icon{
    font-size:30px;
    opacity:0.55;
    margin-bottom:6px;
}
.empty-chat-title{
    font-family: var(--font-body);
    font-weight:600;
    font-size:16px;
    color: var(--text);
}
.empty-chat-sub{
    font-family: var(--font-mono);
    font-size:13px;
    color: var(--text-faint);
}

/* ---------- footer strip ---------- */
.tech-strip{
    display:flex;
    align-items:center;
    gap:10px;
    flex-wrap:wrap;
    padding: 18px 2px 4px 2px;
    margin-top: 6px;
    border-top: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size:11px;
    letter-spacing:0.06em;
    color: var(--text-faint);
}
.tech-label{
    font-family: var(--font-body);
    font-size:13px;
    color: var(--text-dim);
    margin-right:4px;
}
.tech-strip div.tech-badge{
    display:flex;
    align-items:center;
    gap:7px;
    padding:10px 18px;
    font-weight:500;
    font-size:12px;
    border:1px solid var(--border);
    border-radius:999px;
    background: var(--panel);
    color: var(--text-dim);
}
.tech-icon{ font-size:13px; line-height:1; }

/* ---------- suppress Gradio's default blue "generating" progress bar ---------- */
.control-panel .generating,
.control-panel *.generating,
.status-row.generating,
.orb-wrap.generating{
    border: none !important;
}
.control-panel::before,
.control-panel::after{
    display:none !important;
}
"""


EMPTY_CHAT_HTML = """
<div class="empty-chat">
    <div class="empty-chat-icon">&#128172;</div>
    <div class="empty-chat-title">Your conversation will appear here.</div>
    <div class="empty-chat-sub">Start speaking to begin.</div>
</div>
"""


with gr.Blocks(title="XIBOTIX Voice AI", css=CSS, theme=gr.themes.Base()) as demo:

    gr.HTML("""
    <div class="topbar">
        <div class="brand">
            <div class="brand-mark"></div>
            <div class="brand-text">
                <div class="brand-title"><span class="brand-white">XIBOTIX</span> <span class="brand-accent">VOICE AI</span></div>
                <div class="brand-sub">
                    Intelligent Conversational Assistant for Robotics and
                    Rehabilitation Technologies
                </div>
            </div>
        </div>
    </div>
    """)

    with gr.Row(elem_classes=["main-row"]):

        with gr.Column(scale=1, min_width=260, elem_classes=["control-col"]):
            gr.HTML('<div class="log-title">Assistant Control Center</div>')
            with gr.Column(elem_classes=["control-panel"]):
                status_html = gr.HTML(_panel(STATE_IDLE, STATE_LABELS[STATE_IDLE]))
                orb_html = gr.HTML(_orb(STATE_IDLE))
                gr.HTML(
                    """
                    <div class="control-caption">
                        Speak naturally.<br>
                        The assistant listens, understands
                        and responds in real time.
                    </div>
                    """
                )
                listen_btn = gr.Button(" Start Conversation", elem_id="listen_btn", size="lg")
                clear_btn = gr.Button(" Clear Conversation", elem_id="clear_btn", size="sm")

        with gr.Column(scale=5, elem_classes=["conversation-col"]):
            gr.HTML(
                '<div class="log-header">'
                '<div class="log-title">Conversation</div>'
                '</div>'
            )
            chatbot = gr.Chatbot(
                type="messages",
                height=600,
                show_label=False,
                elem_id="chat_log",
                avatar_images=None,
                placeholder=EMPTY_CHAT_HTML,
            )

    gr.HTML("""
    <div class="tech-strip">
        <div class="tech-label">Powered by</div>
        <div class="tech-badge">Whisper</div>
        <div class="tech-badge">Groq &middot; Llama 3.3</div>
        <div class="tech-badge">Microsoft Edge TTS</div>
        <div class="tech-badge">Gradio</div>
    </div>
    """)

    # Single event chain: run_turn() is a generator, so Gradio streams each
    # yielded state to the browser as it happens rather than waiting for the
    # whole function to return. This is what makes the staged status visible
    # in real time instead of jumping straight from "Recording" to "Ready".
    listen_btn.click(
        fn=run_turn,
        outputs=[chatbot, status_html, orb_html, listen_btn],
        show_progress="hidden",
    )

    clear_btn.click(
        fn=clear_history,
        outputs=[chatbot, status_html, orb_html],
        show_progress="hidden",
    )


if __name__ == "__main__":
    demo.launch()
