# Agentic AI

Learning examples that progress from direct LLM interactions to agents,
frameworks, and tool interoperability.

## Repository structure

The `main` branch contains this overview and the branch guide. Each numbered
topic is developed on its own branch; switch to a branch to view its project
files.

```text
Agentic-AI/
├── README.md
└── .gitignore
```

## Branch guide

| Branch | Topic | Overview |
|---|---|---|
| [`1_Chat_Agent`](https://github.com/jaydeepresources/Agentic-AI/tree/1_Chat_Agent) | Chat agents | Groq and NVIDIA API examples for model discovery, greetings, story generation, and interactive chat. |
| [`2_RAG`](https://github.com/jaydeepresources/Agentic-AI/tree/2_RAG) | Retrieval-augmented generation | HR-policy PDF retrieval with cosine similarity, plus an NVIDIA-backed reranking, cited-answer, and verification workflow. |
| [`3_Tool_Calls`](https://github.com/jaydeepresources/Agentic-AI/tree/3_Tool_Calls) | Tool calling | A custom NVIDIA ReAct-style math agent using restricted SymPy tools. |
| [`4_Langchain`](https://github.com/jaydeepresources/Agentic-AI/tree/4_Langchain) | LangChain | The math-agent workflow implemented with LangChain tool orchestration and a tool-call limit. |
| [`5_Langraph`](https://github.com/jaydeepresources/Agentic-AI/tree/5_Langraph) | LangGraph | A graph-based math agent with in-memory conversation history and per-tool-call human approval. |
| [`6_Crew_AI`](https://github.com/jaydeepresources/Agentic-AI/tree/6_Crew_AI) | CrewAI | A sequential team of analyst, project manager, and architect agents that produces project artifacts. |
| [`7_MCP`](https://github.com/jaydeepresources/Agentic-AI/tree/7_MCP) | Model Context Protocol | An MCP math server and NVIDIA-backed client communicating over Streamable HTTP. |

## Safety and setup notes

- API keys belong in a local `.env` file and are excluded from Git.
- Python virtual environments, bytecode, editor settings, and generated RAG
  embeddings are excluded from Git.
- The HR Manual PDF in the `2_RAG` branch is included as requested; verify
  redistribution rights before sharing or reusing its contents.
- Each topic branch contains its own README with setup, usage, and test
  instructions.
