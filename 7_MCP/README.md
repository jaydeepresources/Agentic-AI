# Rich MCP Math Server and Client

This project contains two separate console applications that demonstrate the
Model Context Protocol (MCP):

- `math_server.py` exposes `evaluate_math`, `out_of_scope`, and `handle_errors`
  over MCP Streamable HTTP and displays startup information and tool calls in a
  Rich console. `evaluate_math` uses the same restricted Python AST and SymPy
  approach as the math-agent example; it never executes model-generated code.
- `math_client.py` connects to the server, discovers its tools, and sends
  natural-language math questions to NVIDIA Nemotron. It uses NVIDIA's
  OpenAI-compatible chat-completions API and a ReAct-style tool-calling loop;
  tool execution happens on the MCP server.

The client uses the NVIDIA model also used by the LangChain examples:
`nvidia/nemotron-3.5-super-vl-120b-a12b`. No Groq or LangChain package is used.

## Architecture

```text
Natural-language question
        |
        v
Rich MCP client ---- NVIDIA chat-completions API
        |
        | MCP Streamable HTTP
        v
Rich MCP server ---- math tools
```

The server listens on one local HTTP port (default `8000`). The client is an
outbound console application, so it does not open a second listening port.
Both programs run locally in separate terminals.

## Requirements

- Python 3.13 recommended
- An NVIDIA API key
- Internet access for NVIDIA chat-completions requests

The MCP SDK depends on `cryptography`. On Apple Silicon, use a native ARM64
Python rather than an x86_64 Python running under Rosetta; otherwise pip may try
to compile `cryptography` from source.

The client reads `NVIDIA_AI_KEY` or `NVIDIA_API_KEY` from the existing
project-root `.env` file. No additional key file is required.

## Setup

From the project root on Apple Silicon, verify that Homebrew's Python is
running natively and create a fresh environment with it:

```bash
/opt/homebrew/bin/python3.13 -c 'import platform; print(platform.machine())'
/opt/homebrew/bin/python3.13 -m venv 7_MCP/.venv-py313
source 7_MCP/.venv-py313/bin/activate
python -m pip install -r 7_MCP/requirements.txt
```

The first command should print `arm64`. On Intel macOS or Linux, use a native
Python 3.13 executable for the first two commands instead. If an environment
was created with x86_64 Python under Rosetta, do not reuse it; activate the
fresh `.venv-py313` environment above.

Make sure the project-root `.env` contains one of these variables:

```env
NVIDIA_AI_KEY="your-nvidia-api-key"
```

Keep `.env` private.

## Run

Start the server in the first terminal:

```bash
python 7_MCP/math_server.py
```

It listens at `http://127.0.0.1:8000/mcp`. To choose another local port:

```bash
python 7_MCP/math_server.py --port 8001
```

Start the client in a second terminal:

```bash
python 7_MCP/math_client.py
```

If the server uses a different port, pass its MCP endpoint:

```bash
python 7_MCP/math_client.py --server-url http://127.0.0.1:8001/mcp
```

Try questions such as `What is 18% of 250?`, `What is the derivative of x
cubed?`, or `Solve x squared minus 4 equals 0.` The client displays each
model-selected MCP tool call and result. Enter `/exit` or `/quit` to end the
session.

## Exposed tools

| Tool | Purpose |
|---|---|
| `evaluate_math` | Evaluate arithmetic, algebra, equations, common functions, derivatives, integrals, and limits with SymPy. |
| `out_of_scope` | Respond to requests unrelated to mathematics. |
| `handle_errors` | Explain an error returned by a math tool. |

## Troubleshooting

| Message or symptom | What to check |
|---|---|
| `cryptography` wheel build fails | Create a fresh environment with native Python 3.13. On Apple Silicon, verify `platform.machine()` reports `arm64`; avoid Python running under Rosetta. |
| `ModuleNotFoundError: No module named 'mcp'` | The package install did not complete. Activate the fresh virtual environment and rerun `python -m pip install -r 7_MCP/requirements.txt`. |

## Tests

The tests do not make NVIDIA requests:

```bash
python -m unittest discover -s 7_MCP -p 'test_*.py'
```
