# 🎙️ XIBOTIX Voice AI Assistant

An enterprise-grade conversational Voice AI Assistant built using modern AI technologies including Whisper Speech Recognition, Groq Llama 3.3, Microsoft Edge Neural Text-to-Speech, and Gradio.

Developed as part of the **AI Engineering Internship Assignment** for **XIBOTIX Pvt. Ltd.**

---

# Overview

XIBOTIX Voice AI Assistant enables users to interact with an AI assistant completely through voice. The system captures speech from the microphone, converts it into text using Whisper, processes the conversation using Groq Llama 3.3 while maintaining conversation memory, synthesizes a natural spoken response using Microsoft Edge Neural TTS, and presents everything through a modern enterprise-inspired web interface.

The project follows a modular architecture that separates speech processing, language model interaction, frontend, configuration management, and conversation handling into independent components.

---

# Features

## Speech Recognition

* Whisper-based Speech-to-Text
* Real-time microphone input
* High transcription accuracy
* Noise-tolerant speech processing

## Intelligent Conversation

* Powered by Groq Llama 3.3
* Context-aware responses
* Multi-turn conversation memory
* Fast inference

## Voice Response

* Microsoft Edge Neural Text-to-Speech
* Natural human-like voice
* Automatic audio playback

## Enterprise Frontend

* Professional dark interface
* Animated Voice AI orb
* Live conversation panel
* Assistant status indicator
* Technology badges
* Responsive layout
* ChatGPT-inspired user experience

## Modular Architecture

* Independent speech module
* Independent LLM module
* Configuration management
* Environment variable support
* Reusable backend components

---

# Technology Stack

| Category               | Technology         |
| ---------------------- | ------------------ |
| Language               | Python 3.11+       |
| Frontend               | Gradio             |
| Speech Recognition     | OpenAI Whisper     |
| Large Language Model   | Groq Llama 3.3     |
| Text-to-Speech         | Microsoft Edge TTS |
| Environment Management | python-dotenv      |
| Audio Processing       | FFmpeg             |
| API Communication      | Requests           |

---

# Project Architecture

```
                 User

                  │
                  ▼

          🎤 Microphone Input

                  │
                  ▼

      Whisper Speech-to-Text Engine

                  │
                  ▼

        Conversation Memory Manager

                  │
                  ▼

          Groq Llama 3.3 API

                  │
                  ▼

      Microsoft Edge Neural TTS

                  │
                  ▼

          🔊 Generated Speech

                  │
                  ▼

          Gradio Web Interface
```

---

# Project Structure

```
XIBOTIX-Voice-AI/
│
├── assistant.py
├── web_app_final.py
├── config.py
├── .env
├── requirements.txt
├── README.md
│
├── llm/
│   ├── groq_client.py
│   ├── memory.py
│   └── __init__.py
│
├── speech/
│   ├── speech_to_text.py
│   ├── text_to_speech.py
│   └── __init__.py
│
├── assets/
│
├── screenshots/
│
└── docs/
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/XIBOTIX-Voice-AI.git

cd XIBOTIX-Voice-AI
```

---

## Create Virtual Environment

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file in the project root.

```
GROQ_API_KEY=your_api_key_here
```

---

## Run Application

```bash
python web_app_final.py
```

Open the Gradio URL shown in the terminal.

---

# Workflow

1. User speaks into the microphone.
2. Whisper converts speech into text.
3. Conversation memory stores previous interactions.
4. Groq Llama 3.3 generates a response.
5. Microsoft Edge Neural TTS converts the response into speech.
6. Gradio displays the conversation and plays the generated voice.

---

# Design Principles

* Modular architecture
* Separation of concerns
* Reusable components
* Enterprise UI
* Maintainable codebase
* Scalable project structure
* Environment-based configuration
* Clean documentation

---

# Future Improvements

* Streaming responses
* Wake-word detection
* Multiple voice profiles
* Local LLM support
* User authentication
* Conversation history database
* Voice customization
* Docker deployment

---

# Screenshots

Add screenshots of:

* Home Interface
* Conversation Window
* Assistant Status
* Voice Orb Animation
* Response Generation

---

# Acknowledgements

* OpenAI Whisper
* Groq API
* Microsoft Edge TTS
* Gradio
* Python Community

---

# Author

**Varanasi Rithul Ram**

B.Tech Information Technology
Vellore Institute of Technology (VIT), Vellore

AI Engineering Internship Project for **XIBOTIX Pvt. Ltd.**

---

# License

This project has been developed for educational purposes as part of an internship assignment.
