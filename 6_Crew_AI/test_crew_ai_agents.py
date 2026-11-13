from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rich.console import Console
from rich.progress import Progress

from crew_ai_agents import (
    BAArtifacts,
    PMArtifacts,
    SAArtifacts,
    make_task_progress_callback,
    read_requirement,
    save_artifacts,
    slugify,
)


class ReadRequirementTests(unittest.TestCase):
    @patch("builtins.input", side_effect=["Build a portal", "with reports", ""])
    def test_reads_multiline_console_paste(self, _input: object) -> None:
        self.assertEqual(read_requirement(), "Build a portal\nwith reports")

    @patch("builtins.input", return_value="")
    def test_rejects_empty_requirement(self, _input: object) -> None:
        with self.assertRaises(ValueError):
            read_requirement()


class ProgressCallbackTests(unittest.TestCase):
    def test_advances_and_announces_the_next_agent(self) -> None:
        output_console = Console(file=StringIO())
        with Progress(console=Console(file=StringIO()), auto_refresh=False) as progress:
            progress_task_id = progress.add_task("Starting", total=3)
            callback = make_task_progress_callback(
                progress, progress_task_id, output_console
            )

            callback(None)

            task = progress.tasks[0]
            self.assertEqual(task.completed, 1)
            self.assertIn("Project Manager", task.description)
            self.assertIn("Completed BA", output_console.file.getvalue())


class SlugifyTests(unittest.TestCase):
    def test_creates_safe_lowercase_slug(self) -> None:
        self.assertEqual(slugify("  Customer Portal / V2! "), "customer-portal-v2")

    def test_rejects_text_without_ascii_slug_characters(self) -> None:
        with self.assertRaises(ValueError):
            slugify("你好")


class SaveArtifactsTests(unittest.TestCase):
    def test_saves_all_six_markdown_artifacts_under_project_slug(self) -> None:
        ba = BAArtifacts(
            project_name="Customer Portal",
            project_slug="../../Customer Portal",
            brd="# BRD",
            user_stories="# User Stories",
        )
        pm = PMArtifacts(epic_plan="# Epics", wbs="# WBS")
        sa = SAArtifacts(architecture="# Architecture", adr="# ADR")

        with tempfile.TemporaryDirectory() as temporary_directory:
            project_dir = save_artifacts(
                ba, pm, sa, output_dir=Path(temporary_directory)
            )

            self.assertEqual(project_dir.name, "customer-portal")
            self.assertEqual(
                {path.name for path in project_dir.iterdir()},
                {
                    "BRD.md",
                    "User_Stories.md",
                    "Epic_Plan.md",
                    "WBS.md",
                    "Architecture.md",
                    "ADR.md",
                },
            )
            self.assertEqual((project_dir / "BRD.md").read_text(), "# BRD\n")


if __name__ == "__main__":
    unittest.main()
