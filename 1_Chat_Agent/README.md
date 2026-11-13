# Groq and NVIDIA Python API Examples

This folder contains Python examples for listing models, sending greeting
requests, generating short stories, and chatting with Groq and NVIDIA models.
The scripts read API keys from the `.env` file at the project root.

## 📂 Directory Structure

```text
SICSR-FDP-2/
├── .env
└── 1_Chat_Agent/
    ├── README.md
    ├── Hands_On.md
    ├── requirements.txt
    ├── list_groq_models.py
    ├── list_nvidia_models.py
    ├── say_hello_groq.py
    ├── say_hello_nvidia.py
    ├── write_story_groq.py
    ├── write_story_nvidia.py
    ├── chat_groq.py
    └── chat_nvidia.py
```

| File | Purpose |
|---|---|
| `Hands_On.md` | Five AI-agent projects in increasing difficulty, from story generation to notes-based question answering. |
| `list_groq_models.py` | Lists models available to the Groq API key. |
| `list_nvidia_models.py` | Lists models available to the NVIDIA API key. |
| `say_hello_groq.py` | Sends a greeting request to each model returned by Groq. |
| `say_hello_nvidia.py` | Sends one greeting request to the NVIDIA Nemotron model. |
| `write_story_groq.py` | Writes a story of at most 100 words using Groq. |
| `write_story_nvidia.py` | Writes a story of at most 100 words using NVIDIA. |
| `chat_groq.py` | Starts a Rich-formatted chat with Groq. |
| `chat_nvidia.py` | Starts a Rich-formatted chat with NVIDIA. |
| `requirements.txt` | Lists the Python packages used by the examples. |

## Requirements

- Python 3.10 or later
- A Groq API key for Groq scripts
- An NVIDIA API key for NVIDIA scripts
- Internet access

The chat scripts use [Rich](https://rich.readthedocs.io/) for the terminal
interface. All required Python packages are listed in `requirements.txt`.

## Configure API keys

Create a `.env` file in the project root, next to the `1_Chat_Agent` folder:

```env
GROQ_API_KEY="your-groq-api-key"
NVIDIA_AI_KEY="your-nvidia-api-key"
```

The scripts accept `GROQ_API_KEY` or `Groq` for Groq. NVIDIA scripts accept
`NVIDIA_AI_KEY` or `NVIDIA_API_KEY`. You only need to configure the key for the
provider you plan to use.

Keep `.env` private. Do not share it or commit it to source control.

## Setup

Run these commands from the project root directory.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r 1_Chat_Agent\requirements.txt
```

If PowerShell prevents environment activation, you can use Command Prompt
instead:

```cmd
py -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r 1_Chat_Agent\requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 1_Chat_Agent/requirements.txt
```

## Run a script

Run commands from the project root with the virtual environment activated.

### List available models

```bash
python 1_Chat_Agent/list_groq_models.py
python 1_Chat_Agent/list_nvidia_models.py
```

The results depend on the API key and models currently available to that
account.

### Send greeting requests

```bash
python 1_Chat_Agent/say_hello_groq.py
python 1_Chat_Agent/say_hello_nvidia.py
```

The Groq greeting script asks before sending a request to each model returned
by the model-list endpoint. Some models may not support chat completions. The
NVIDIA greeting script asks before sending one request to
`nvidia/nemotron-3.5-super-vl-120b-a12b`.

### Generate a short story

```bash
python 1_Chat_Agent/write_story_groq.py
python 1_Chat_Agent/write_story_nvidia.py
```

Each script prompts for a phrase and asks its model for a complete story of at
most 100 words with a natural ending. The script checks the returned word count
and requests one rewrite if needed. If the second response is still over 100
words, it reports an error instead of printing an overlong story.

| Provider | Model |
|---|---|
| Groq | `openai/gpt-oss-120b` |
| NVIDIA | `nvidia/nemotron-3.5-super-vl-120b-a12b` |

### Start an interactive chat

```bash
python 1_Chat_Agent/chat_groq.py
python 1_Chat_Agent/chat_nvidia.py
```

Each chat has a Rich-styled terminal interface and keeps the conversation
history for up to 10 user messages that receive a non-empty reply. Enter
`/exit` or `/quit` to end early. Empty messages and failed requests do not use a
turn.

The Groq chat uses `openai/gpt-oss-120b`. The NVIDIA chat uses
`nvidia/nemotron-3.5-super-vl-120b-a12b` with model thinking disabled for
concise conversational replies.

## Troubleshooting

| Message or symptom | What to check |
|---|---|
| API key not found | Make sure `.env` is in the project root, the variable name is correct, and the value is not commented out. |
| HTTP 401 or authentication error | Check that the key is valid for the provider and has not been revoked. |
| Request timed out or connection failed | Check your internet connection and try again later. |
| Model returned no reply text | Check the model ID, API availability, and provider limits; then retry. |
| `ModuleNotFoundError` for a dependency | Activate the virtual environment and run `python -m pip install -r 1_Chat_Agent/requirements.txt`. |
| `externally-managed-environment` on macOS | Install packages inside the virtual environment created in the setup section. |

API requests may be subject to provider rate limits or charges.

## Deactivate the virtual environment

When finished, run:

```bash
deactivate
```
