from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, TypeVar

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
OUTPUT_DIR = APP_DIR / "projects"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
NVIDIA_API_BASE_URL = "https://integrate.api.nvidia.com/v1"
AGENT_STAGES = (
    (
        "BA",
        "Business Analyst",
        "Analyzing the requirement; drafting the BRD and user stories",
        "BRD and User Stories",
    ),
    (
        "PM",
        "Project Manager",
        "Planning epics and breaking the BA scope into work packages",
        "Epic Plan and WBS",
    ),
    (
        "SA",
        "Solutions Architect",
        "Designing the solution and documenting architecture decisions",
        "Architecture and ADR",
    ),
)

console = Console()


class BAArtifacts(BaseModel):
    project_name: str = Field(description="A concise, human-readable project name.")
    project_slug: str = Field(description="A lowercase, hyphen-separated project slug.")
    brd: str = Field(
        description="Complete Business Requirements Document in Markdown."
    )
    user_stories: str = Field(
        description="Prioritized user stories with acceptance criteria in Markdown."
    )


class PMArtifacts(BaseModel):
    epic_plan: str = Field(
        description="Epic plan with scope, sequence, and outcomes in Markdown."
    )
    wbs: str = Field(
        description="Hierarchical work breakdown structure in Markdown."
    )


class SAArtifacts(BaseModel):
    architecture: str = Field(
        description="Solution architecture document in Markdown."
    )
    adr: str = Field(description="Architecture decision record in Markdown.")


OutputModel = TypeVar("OutputModel", bound=BaseModel)


def display_workflow_header() -> None:
    agents = Table(box=None, pad_edge=False)
    agents.add_column("Agent", style="bold cyan")
    agents.add_column("Responsibility")
    agents.add_row("BA", "BRD + User Stories")
    agents.add_row("PM", "Epic Plan + WBS (uses BA outputs)")
    agents.add_row("SA", "Architecture + ADR (uses BA and PM outputs)")
    console.print(
        Panel(
            agents,
            title="[bold cyan]CrewAI Requirements-to-Delivery Crew[/]",
            subtitle=f"[dim]Sequential handoff: BA -> PM -> SA | {MODEL_ID}[/]",
            border_style="cyan",
        )
    )


def make_task_progress_callback(
    progress: Progress, progress_task_id: int, output_console: Console
) -> Callable[[Any], None]:
    completed = 0

    def on_task_complete(_task_output: Any) -> None:
        nonlocal completed
        code, name, _description, outputs = AGENT_STAGES[completed]
        completed += 1
        progress.advance(progress_task_id)
        output_console.print(
            f"[bold green]Completed {code} - {name}[/] "
            f"[dim]({outputs} ready for the next handoff)[/]"
        )
        if completed < len(AGENT_STAGES):
            next_code, next_name, next_description, _next_outputs = AGENT_STAGES[
                completed
            ]
            progress.update(
                progress_task_id,
                description=(
                    f"[bold cyan]{next_code} - {next_name}[/] | {next_description}"
                ),
            )
        else:
            progress.update(
                progress_task_id,
                description=(
                    "[bold green]All agents finished; validating and saving artifacts"
                ),
            )

    return on_task_complete


def kickoff_with_progress(crew: Crew, requirement: str) -> None:
    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=8,
    ) as progress:
        progress_task_id = progress.add_task(
            (
                f"[bold cyan]{AGENT_STAGES[0][0]} - {AGENT_STAGES[0][1]}[/] | "
                f"{AGENT_STAGES[0][2]}"
            ),
            total=len(AGENT_STAGES),
        )
        crew.task_callback = make_task_progress_callback(
            progress, progress_task_id, console
        )
        console.print(
            "[dim]Crew started. PM will receive BA's artifacts; SA will receive "
            "both BA and PM artifacts. The spinner remains active during each "
            "model request.[/]"
        )
        crew.kickoff(inputs={"requirement": requirement})


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")[:80].rstrip("-")
    if not slug:
        raise ValueError("The BA agent did not provide a usable project name or slug.")
    return slug


def get_task_artifacts(task: Task, model: type[OutputModel]) -> OutputModel:
    if task.output is None or not isinstance(task.output.pydantic, model):
        raise RuntimeError(
            f"CrewAI did not return valid structured output for task {task.name!r}."
        )
    return task.output.pydantic


def save_artifacts(
    ba: BAArtifacts, pm: PMArtifacts, sa: SAArtifacts, output_dir: Path = OUTPUT_DIR
) -> Path:
    project_slug = slugify(ba.project_slug or ba.project_name)
    project_dir = output_dir / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    documents = {
        "BRD.md": ba.brd,
        "User_Stories.md": ba.user_stories,
        "Epic_Plan.md": pm.epic_plan,
        "WBS.md": pm.wbs,
        "Architecture.md": sa.architecture,
        "ADR.md": sa.adr,
    }
    for filename, content in documents.items():
        if not content.strip():
            raise ValueError(f"The generated artifact {filename} is empty.")
        (project_dir / filename).write_text(content.strip() + "\n", encoding="utf-8")
    return project_dir


def build_crew(api_key: str) -> tuple[Crew, tuple[Task, Task, Task]]:
    llm = LLM(
        model=f"openai/{MODEL_ID}",
        api_key=api_key,
        base_url=NVIDIA_API_BASE_URL,
        temperature=0.2,
        timeout=180,
    )

    ba_agent = Agent(
        role="Business Analyst",
        goal=(
            "Turn the customer's software requirement into clear, testable business "
            "requirements and user stories."
        ),
        backstory=(
            "You are a pragmatic senior business analyst. Preserve the customer's "
            "intent, distinguish stated facts from assumptions, and flag unresolved "
            "questions instead of inventing requirements."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
    pm_agent = Agent(
        role="Project Manager",
        goal=(
            "Create a delivery-oriented epic plan and WBS grounded in the BA artifacts."
        ),
        backstory=(
            "You are an experienced software project manager. Organize work into "
            "sequenced, estimable work packages, identify dependencies and risks, "
            "and do not add scope unsupported by the requirements."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
    sa_agent = Agent(
        role="Solutions Architect",
        goal=(
            "Design a practical solution architecture and record its key decisions."
        ),
        backstory=(
            "You are a senior solutions architect. Base the design on the BA and PM "
            "artifacts, make assumptions explicit, and avoid presenting speculative "
            "technology choices as customer requirements."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    ba_task = Task(
        name="business_analysis",
        description=(
            "Analyze the customer's software requirement:\n\n{requirement}\n\n"
            "Produce exactly the requested BA fields. The BRD should cover purpose, "
            "scope, stakeholders, functional and non-functional requirements, "
            "constraints, assumptions, dependencies, and open questions as applicable. "
            "User stories must be prioritized and include measurable acceptance "
            "criteria. Do not invent facts; mark missing information as an open "
            "question or assumption. Infer a concise project name and lowercase "
            "hyphen-separated slug."
        ),
        expected_output=(
            "Structured BA artifacts containing a project name, project slug, "
            "BRD in Markdown, and prioritized user stories in Markdown."
        ),
        output_pydantic=BAArtifacts,
        agent=ba_agent,
        markdown=True,
    )
    pm_task = Task(
        name="project_planning",
        description=(
            "Using the original customer requirement ({requirement}) and the "
            "Business Analyst's preceding BRD and user stories, create an epic plan "
            "and a WBS. Keep scope traceable to those inputs. Include sequencing, "
            "dependencies, deliverables, and risks where supported. Label estimates "
            "as indicative when the inputs do not provide enough detail."
        ),
        expected_output=(
            "Structured project-management artifacts containing an epic plan and "
            "a hierarchical WBS, both in Markdown."
        ),
        output_pydantic=PMArtifacts,
        agent=pm_agent,
        context=[ba_task],
        markdown=True,
    )
    sa_task = Task(
        name="solution_architecture",
        description=(
            "Using the original customer requirement ({requirement}), the BA's BRD "
            "and user stories, and the PM's epic plan and WBS, create the solution "
            "architecture and an ADR. Describe components, interactions, data, "
            "security, deployment, and quality attributes only as far as the inputs "
            "justify; explicitly label assumptions and unresolved choices. The ADR "
            "must state its context, decision, alternatives, consequences, and status."
        ),
        expected_output=(
            "Structured solution-architecture and architecture-decision-record "
            "artifacts, both in Markdown."
        ),
        output_pydantic=SAArtifacts,
        agent=sa_agent,
        context=[ba_task, pm_task],
        markdown=True,
    )
    crew = Crew(
        agents=[ba_agent, pm_agent, sa_agent],
        tasks=[ba_task, pm_task, sa_task],
        process=Process.sequential,
        verbose=False,
    )
    return crew, (ba_task, pm_task, sa_task)


def read_requirement() -> str:
    console.print(
        "Paste the software requirement. Submit an empty line when finished:"
    )
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line)
    requirement = "\n".join(lines).strip()
    if not requirement:
        raise ValueError("The software requirement cannot be empty.")
    return requirement


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        console.print(
            Panel(
                "Set NVIDIA_AI_KEY or NVIDIA_API_KEY in the project-root .env file.",
                title="[bold red]NVIDIA API key not found[/]",
                border_style="red",
            )
        )
        return 1

    display_workflow_header()
    try:
        requirement = read_requirement()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Input cancelled.[/]")
        return 1
    except ValueError as error:
        console.print(f"[bold red]Invalid input:[/] {error}")
        return 2

    crew, tasks = build_crew(api_key)
    kickoff_with_progress(crew, requirement)
    ba = get_task_artifacts(tasks[0], BAArtifacts)
    pm = get_task_artifacts(tasks[1], PMArtifacts)
    sa = get_task_artifacts(tasks[2], SAArtifacts)
    project_dir = save_artifacts(ba, pm, sa)

    artifacts = Table(
        title=f"Generated artifacts for {ba.project_name}",
        header_style="bold cyan",
    )
    artifacts.add_column("Owner")
    artifacts.add_column("Artifact")
    artifacts.add_row("BA", str(project_dir / "BRD.md"))
    artifacts.add_row("BA", str(project_dir / "User_Stories.md"))
    artifacts.add_row("PM", str(project_dir / "Epic_Plan.md"))
    artifacts.add_row("PM", str(project_dir / "WBS.md"))
    artifacts.add_row("SA", str(project_dir / "Architecture.md"))
    artifacts.add_row("SA", str(project_dir / "ADR.md"))
    console.print(Panel(artifacts, border_style="green"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
