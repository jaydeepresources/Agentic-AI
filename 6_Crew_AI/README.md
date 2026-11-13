# Requirements-to-Project Artifacts with CrewAI

This example uses three CrewAI agents in a sequential workflow:

1. **Business Analyst (BA):** creates a BRD and prioritized user stories with
   acceptance criteria.
2. **Project Manager (PM):** uses the BA output to create an epic plan and WBS.
3. **Solutions Architect (SA):** uses the BA and PM outputs to create an
   architecture document and ADR.

The six Markdown artifacts are written to
`6_Crew_AI/projects/<inferred-project-slug>/`. Existing files with the same
slug are replaced when the workflow is run again.

## Requirements

- Python 3.10-3.13 (the current CrewAI release does not support Python 3.14)
- NVIDIA API key with access to the configured model
- Internet access

The requirement is sent to NVIDIA's API for processing. Do not paste secrets
or sensitive customer information unless you are authorized to share it with
that service.

## Configure API access

Set `NVIDIA_AI_KEY` or `NVIDIA_API_KEY` in the project-root `.env` file,
alongside the `6_Crew_AI` folder. This matches the key configuration used by
the other examples in this workspace. The workflow uses
`nvidia/nemotron-3.5-super-vl-120b-a12b` through NVIDIA's OpenAI-compatible
endpoint.

## Setup (macOS/Linux)

Run these commands from the workspace root:

```bash
python3.13 -m venv 6_Crew_AI/.venv
source 6_Crew_AI/.venv/bin/activate
python -m pip install -r 6_Crew_AI/requirements.txt
```

## Run

From the workspace root with the virtual environment activated:

```bash
python 6_Crew_AI/crew_ai_agents.py
```

Paste the software requirement into the console. Submit a blank line to finish
the input and start the three-agent workflow. Rich displays the active agent,
elapsed time, progress, and completed handoffs while the model runs. Generated
files appear in a slug-named folder under `6_Crew_AI/projects/`.

## Tests

```bash
python -m unittest discover -s 6_Crew_AI -p 'test_*.py'
```
