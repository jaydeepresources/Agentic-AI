# NVIDIA Math Agent with LangGraph

This folder ports the math agent from `4_Langchain` to a small LangGraph
workflow. It uses a graph for the model/tool loop, LangGraph interrupts for
human approval, and an in-memory checkpointer for conversation history. Each
tool call is shown and must be approved individually before it can run.

The agent exposes the same three tools as the earlier examples:

- `evaluate_math` evaluates supported arithmetic, algebra, and calculus with
  SymPy using a restricted Python AST. Generated Python code is never executed.
- `out_of_scope` handles requests unrelated to mathematics.
- `handle_errors` explains errors returned by the math evaluator.

The model is NVIDIA `nvidia/nemotron-3.5-super-vl-120b-a12b`, accessed through
NVIDIA's OpenAI-compatible chat-completions endpoint. Conversation messages and
tool results remain available to follow-up questions for the lifetime of the
running program. History is in memory and is cleared when the program exits.

## Setup

From the project root on macOS or Linux:

```bash
python3 -m venv 5_Langraph/.venv
source 5_Langraph/.venv/bin/activate
python -m pip install -r 5_Langraph/requirements.txt
```

The program reads `NVIDIA_AI_KEY` or `NVIDIA_API_KEY` from the existing
project-root `.env`. No additional API-key file is needed.

## Run

From the project root:

```bash
python 5_Langraph/math_agent.py
```

Try a math question, then ask a follow-up such as `What was the answer to my
previous question?` Each requested tool call pauses and displays its name and
arguments; enter `y` to run it or `n` to reject it. A rejected call is reported
to the model and is not executed. Type `/exit` or `/quit` to end the session.

The graph limits each user question to 10 tool calls.

## Tests

The tests do not make NVIDIA requests:

```bash
python -m unittest discover -s 5_Langraph -p 'test_*.py'
```
