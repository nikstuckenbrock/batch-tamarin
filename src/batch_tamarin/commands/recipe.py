"""Recipe command for generating and editing recipes."""
from markdown_it.presets import default
import asyncio
from ..modules.config_manager import ConfigManager
from ..model.batch import Resources as BatchResources

import typer

from pathlib import Path
from ..modules.report_generator import ReportGenerator
from ..model.report_data import ReportData
from ..model.tamarin_recipe import TamarinRecipe, GlobalConfig, Task, Lemma, Resources
from ..utils.notifications import notification_manager

recipe_command = typer.Typer(name="recipe", help="Craft or edit recipes")

async def craft_command(results_directory: Path, config_file: Path, output_file: Path) -> None:

    
    recipe_old: TamarinRecipe = await ConfigManager.load_json_recipe(config_file)
    
    report_generator = ReportGenerator()
    report_generator.validate_results_directory(results_directory)
    
    reports: list[ReportData] = []

    current_directory = results_directory
    current_report: Path = current_directory / "execution_report.json"
    while current_directory.is_dir() and current_report.exists():
        # TODO: format type
        reports.append(ReportData.from_execution_report(
            current_report, results_directory, "md"
        ))
        current_directory = current_directory / "rerun"
        current_report = current_directory / "execution_report.json"

    recipe: TamarinRecipe = TamarinRecipe(
        config=GlobalConfig(
            default_timeout=1,
            global_max_cores=1,
            global_max_memory=1,
            output_directory=recipe_old.config.output_directory
        ),
        tamarin_versions=recipe_old.tamarin_versions,
        tasks={}
    )
    
    summarized: dict[str, dict[str, dict[str, BatchResources]]] = {}
    for report in reports:
        for task in report.tasks:
            if task.name not in summarized:
                summarized[task.name] = {}
            for result in task.results:
                if result.lemma not in summarized[task.name]:
                    summarized[task.name][result.lemma] = {}
                existing = summarized[task.name][result.lemma][result.tamarin_version] if result.tamarin_version in summarized[task.name][result.lemma] else None
                new = BatchResources(
                    cores=result.cores if result.cores else 1,
                    memory=round(result.peak_memory + 1),
                    timeout=round(result.runtime + 1),
                )
                if existing is None or (
                    new.cores < existing.cores or
                    (new.cores == existing.cores and new.memory < existing.memory) or
                    (new.cores == existing.cores and new.memory == existing.memory and new.timeout < existing.timeout)
                ):
                    summarized[task.name][result.lemma][result.tamarin_version] = new
                    if isinstance(recipe.config.global_max_cores, int) and new.cores > recipe.config.global_max_cores:
                        recipe.config.global_max_cores = new.cores
                    if isinstance(recipe.config.global_max_memory, int) and new.memory > recipe.config.global_max_memory:
                        recipe.config.global_max_memory = new.memory
                    if new.timeout > recipe.config.default_timeout:
                        recipe.config.default_timeout = new.timeout
    
    for task_name, task_data in summarized.items():
        for lemma_name, lemma_data in task_data.items():
            lemmas = []
            for version_name, version_data in lemma_data.items():
                lemmas.append(Lemma(
                    name=lemma_name,
                    tamarin_versions=[version_name],
                    tamarin_options=[],
                    preprocess_flags=[],
                    resources=Resources(
                        max_cores=version_data.cores,
                        max_memory=version_data.memory,
                        timeout=version_data.timeout
                    )
                ))
        recipe.tasks[task_name] = Task(
            theory_file=recipe_old.tasks[task_name].theory_file,
            output_file_prefix=recipe_old.tasks[task_name].output_file_prefix,
            tamarin_versions=recipe_old.tasks[task_name].tamarin_versions,
            tamarin_options=recipe_old.tasks[task_name].tamarin_options,
            preprocess_flags=recipe_old.tasks[task_name].preprocess_flags,
            lemmas=lemmas,
            resources=recipe_old.tasks[task_name].resources
    )
                
    with output_file.open("w", encoding="utf-8") as f:
        f.write(recipe.model_dump_json(indent=2, exclude_none=True))


@recipe_command.command()
def craft(results_directory: Path, config_file: Path, output_file: Path) -> None:
    
    try:
        asyncio.run(craft_command(results_directory, config_file, output_file))
    except Exception as e:
        notification_manager.error(f"Failed to check configuration: {e}")
        raise
