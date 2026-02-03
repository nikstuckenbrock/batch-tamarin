"""Recipe command for generating and editing recipes."""
from batch_tamarin.modules.config_manager import ConfigManager
from collections import defaultdict
from distlib.resources import Resource
from batch_tamarin.model.batch import Resources

import typer

from pathlib import Path
from ..modules.report_generator import ReportGenerator
from ..model.report_data import ReportData, TaskSummary
from ..model.tamarin_recipe import TamarinRecipe, Task, GlobalConfig

recipe_command = typer.Typer(name="recipe", help="Craft or edit recipes")


@recipe_command.command()
async def craft(results_directory: Path, config_file: Path, output_file: Path) -> None:
    
    recipe: TamarinRecipe = await ConfigManager.load_json_recipe(config_file)
    
    report_generator = ReportGenerator()
    report_generator.validate_results_directory(results_directory)
    
    reports: list[ReportData] = []

    current_directory = results_directory
    current_report = current_directory / "execution_report.json"
    while current_directory.is_dir() and current_report.exists():
        # TODO: format type
        reports.append(ReportData.from_execution_report(
            current_report, results_directory, "md"
        ))
        current_directory = current_directory / "rerun"
        current_report = current_directory / "execution_report.json"

    summarized: dict[str, dict[str, dict[str, Resources]]] = {}
    config: GlobalConfig = GlobalConfig(
        global_max_cores=0,
        global_max_memory=0,
        default_timeout=0,
        output_directory=""
    )
    
    for report in reports:
        for task in report.tasks:
            for result in task.results:
                new = Resources(
                    cores=result.cores if result.cores else 0,
                    memory=round(result.peak_memory),
                    timeout=round(result.runtime),
                )
                if existing is None or (
                    new.cores < existing.cores or
                    (new.cores == existing.cores and new.memory < existing.memory) or
                    (new.cores == existing.cores and new.memory == existing.memory and new.timeout < existing.timeout)
                ):
                    summarized[task.name][result.lemma][result.tamarin_version] = new
                
    # find the loest for each tamarin version and then use the highest for them
    
    # durch alle reports und alle tasks durchgehen
    # korrekte durchläufe betrachten
    # existiert ein durchlaufn icht, dann hinzufügen
    # existiert er dann schaue ob die specs besser (geringer) sind und nutze diese
    # gebe am ende fehlerhafte ding e aus

    with output_file.open("w", encoding="utf-8") as f:
        f.write(recipe.model_dump_json(indent=2, exclude_none=True))
