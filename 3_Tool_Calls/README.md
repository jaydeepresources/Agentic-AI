# NVIDIA Math Tool-Calling Agent

This example uses a custom ReAct-style loop and NVIDIA's
`nvidia/nemotron-3.5-super-vl-120b-a12b` chat-completions endpoint. It sends
tools using the OpenAI chat-completions function-calling JSON format; it does
not use the OpenAI SDK, LangChain, or another agent framework. Rich formats the
interactive console with a tool guide, action/result panels, and Markdown answers.

The agent exposes three tools:

- `evaluate_math` converts a restricted, whitelisted Python AST into SymPy
  expressions; it never executes model-generated Python code. This supports
  arithmetic, symbolic algebra, common functions, equation solving,
  differentiation, integration, and limits.
- `out_of_scope` gives a human-friendly response when a request is not about
  mathematics.
- `handle_errors` turns genuine tool errors, such as division by zero, into
  understandable messages.

Each user question is limited to 10 tool calls. The agent can make additional
model requests to complete its ReAct loop; those requests do not increase the
tool-call allowance.

## Setup

From the project root on macOS or Linux:

```bash
python3 -m venv 3_Tool_Calls/.venv
source 3_Tool_Calls/.venv/bin/activate
python -m pip install -r 3_Tool_Calls/requirements.txt
```

The script reads `NVIDIA_AI_KEY` or `NVIDIA_API_KEY` from the existing
project-root `.env`. It does not create or require another API-key file.

## Run

From the project root:

```bash
python 3_Tool_Calls/math_agent.py
```

Try a math question such as `A notebook costs $3.50. How much do 4 cost?`, then
try `What is the derivative of x cubed?` or an unrelated request such as
`Write a travel itinerary`. Enter `/exit` to quit. The terminal prints each
tool call and its result so you can follow the agent's tool-calling steps.

## Tests

The tests do not make NVIDIA requests:

```bash
python -m unittest discover -s 3_Tool_Calls -p 'test_*.py'
```
