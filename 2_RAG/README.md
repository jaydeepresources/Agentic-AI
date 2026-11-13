# HR Policy Search and RAG Agents

This folder contains two interactive ways to search HR policy PDFs:

- `hr_policy_bot.py` embeds passages with NVIDIA's
  `nvidia/nemotron-3.5-embed-8b`, ranks them using **only NumPy cosine
  similarity**, and displays the best matching passages and scores. It does
  not rerank with an LLM or generate an answer.
- `hr_policy_rag_agent.py` starts with the same cosine retrieval, then uses an
  NVIDIA chat model to rerank the retrieved passages, generate a cited answer,
  and check the draft against the retrieved evidence.

Both scripts share the same settings, PDF documents, and JSON embedding cache.

## Setup (macOS/Linux)

Run these commands from the project root:

```bash
python3 -m venv 2_RAG/.venv
source 2_RAG/.venv/bin/activate
python -m pip install -r 2_RAG/requirements.txt
```

The scripts read `NVIDIA_AI_KEY` (or `NVIDIA_API_KEY`) from the existing
project-root `.env`. Keep the API key there; do not duplicate it in
`2_RAG/.env`. That file is for retrieval settings:

```env
TOP_K=5
SIMILARITY_THRESHOLD=0.20
```

`TOP_K` controls how many results/passages are used in the final output.
`SIMILARITY_THRESHOLD` is an inclusive cosine score in `[-1, 1]`; higher
scores mean more similar vectors. Command-line options override these values
for an individual run. Both scripts also accept `--rebuild-index`.

## Cosine-only search

```bash
python 2_RAG/hr_policy_bot.py
python 2_RAG/hr_policy_bot.py --top-k 3 --threshold 0.35
python 2_RAG/hr_policy_bot.py --rebuild-index
```

The bot displays the matching policy text, source, page, and cosine score.
Type `/exit` or `/quit` to end the session.

## Generation, reranking, and verification

```bash
python 2_RAG/hr_policy_rag_agent.py
python 2_RAG/hr_policy_rag_agent.py --top-k 3 --threshold 0.35
python 2_RAG/hr_policy_rag_agent.py --rebuild-index
```

The RAG agent first filters passages by cosine threshold and considers up to
three times `TOP_K` candidates for reranking. The candidate pool is normally
capped at 30; when `TOP_K` is greater than 30, it still includes at least
`TOP_K` candidates. NVIDIA's `nvidia/nemotron-3.5-super-vl-120b-a12b` reranks
the passages, drafts an answer using the selected evidence, and performs a
separate verification/correction pass. Answers cite evidence IDs such as
`[S1]`; the terminal displays their source, page, and original cosine score.
If the verifier rejects the draft, its corrected answer is labeled as such.

This mode makes additional NVIDIA chat-completion calls. The cosine-only
script remains independent and does not make those calls.

## Embedding cache and documents

On the first run, the selected script extracts text from PDFs under
`2_RAG/docs`, splits it into overlapping passages, requests embeddings, and
saves the passages and vectors to `2_RAG/embeddings.json`. Later runs load the
vectors from that JSON file. The cache is rebuilt if a source PDF or embedding
model changes, or if `--rebuild-index` is passed.

Scanned/image-only PDFs need OCR before they can be searched. The first
embedding run and each query require internet access and a valid NVIDIA API
key.

## Tests

From the project root, with the virtual environment activated:

```bash
python -m unittest discover -s 2_RAG -p 'test_*.py'
```
