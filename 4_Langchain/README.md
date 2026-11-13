# NVIDIA Math Agent with LangChain

This example ports the math agent from `3_Tool_Calls` to LangChain. LangChain
provides the agent loop and tool-call handling; the math tools remain
application-specific and use a restricted Python AST with SymPy. The model
never executes generated Python code.

The agent exposes three tools:

- `evaluate_math` evaluates arithmetic, symbolic algebra, common functions,
  equations, differentiation, integration, and limits.
- `out_of_scope` responds to requests unrelated to mathematics.
- `handle_errors` explains errors returned by the math tool.

LangChain's `ToolCallLimitMiddleware` limits each question to 10 tool calls.
The model is NVIDIA `nvidia/nemotron-3.5-super-vl-120b-a12b`, accessed through
NVIDIA's OpenAI-compatible chat-completions endpoint using `ChatOpenAI`.

## Setup

From the project root on macOS or Linux:

```bash
python3 -m venv 4_Langchain/.venv
source 4_Langchain/.venv/bin/activate
python -m pip install -r 4_Langchain/requirements.txt
```

The script reads `NVIDIA_AI_KEY` or `NVIDIA_API_KEY` from the existing
project-root `.env`. It does not create or require another API-key file.

## Run

From the project root:

```bash
python 4_Langchain/math_agent.py
```

Try a math question such as `A notebook costs $3.50. How much do 4 cost?`, then
try `What is the derivative of x cubed?` or an unrelated request such as
`Write a travel itinerary`. Enter `/exit` to quit.

## Tests

The tests do not make NVIDIA requests:

```bash
python -m unittest discover -s 4_Langchain -p 'test_*.py'
```
