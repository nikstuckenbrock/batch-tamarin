"""Report command for generating execution reports."""

from pathlib import Path

from .. import __version__
from ..modules.report_generator import ReportGenerator
from ..utils.notifications import notification_manager


class ReportCommand:
    """Report command for generating execution reports."""

    @staticmethod
    def run(
        results_directory: Path,
        output: Path,
        format_type: str,
    ) -> None:
        """Execute the report generation command."""
        # Initialize report generator
        report_generator = ReportGenerator()

        # Validate results directory structure
        report_generator.validate_results_directory(results_directory)

        # Format type validation
        available_formats = report_generator.get_available_formats()
        if format_type not in available_formats:
            raise ValueError(
                f"Unsupported format type '{format_type}'. Supported formats are: {', '.join(available_formats)}."
            )

        # Check template availability
        if not report_generator.check_template_availability(format_type):
            raise ValueError(f"Template for format '{format_type}' is not available.")

        # Output file validation
        if not output.suffix:
            output = output.with_suffix(f".{format_type}")
        if (
            output.suffix not in [f".{fmt}" for fmt in available_formats]
            or output.suffix != f".{format_type}"
        ):
            notification_manager.warning(
                f"Output file {output} has a different suffix ({output.suffix}) than the specified format type '{format_type}'."
            )
        output.parent.mkdir(parents=True, exist_ok=True)

        notification_manager.info(
            f"Generating report from {results_directory} to {output.absolute()} in {format_type} format"
        )

        # Generate the report
        report_generator.generate_report(
            results_directory=results_directory,
            output_path=output,
            format_type=format_type,
            version=__version__,
        )
