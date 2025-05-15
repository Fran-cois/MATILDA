import argparse
import logging
import sys
import shutil
import datetime
import signal
import threading
from pathlib import Path
from typing import List, Optional

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

# Importer uniquement MATILDA
from algorithms.matilda import MATILDA

from database.alchemy_utility import AlchemyUtility
from utils.logging_utils import configure_global_logger
from utils.monitor import ResourceMonitor
from utils.rules import RuleIO


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments specific to FD discovery using MATILDA.
    """
    parser = argparse.ArgumentParser(
        description="Run functional dependency discovery on Bupa database using MATILDA."
    )
    return parser.parse_args()


def initialize_directories(results_dir: Path, log_dir: Path) -> None:
    """
    Ensures that results and logs directories exist.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)


class FDProcessor:
    """Handles FD discovery and result logging using MATILDA."""

    def __init__(
        self,
        database_name: Path,
        database_path: Path,
        results_dir: Path,
        logger: logging.Logger,
        use_mlflow: bool = False
    ):
        self.database_name = database_name
        self.database_path = database_path
        self.results_dir = results_dir
        self.logger = logger
        self.use_mlflow = use_mlflow
        
        # Configuration fixe pour MATILDA en mode FD
        self.search_algorithm = "dfs"
        self.max_table = 2  # FDs are typically single-table
        self.max_vars = 2
        self.dependency_type = "fd"  # Force FD type for this script
        self.discovery_mode = "fd"   # Force FD discovery mode
        self.compatibility_mode = "fd"  # Use strict compatibility for FDs
    
    def discover_rules(self) -> int:
        """Runs MATILDA for FD discovery."""
        # Si database_name contient déjà un chemin complet ou relatif
        if isinstance(self.database_name, Path) and str(self.database_name).find('/') != -1:
            db_file_path = self.database_name
        else:
            # Sinon, combine avec database_path comme avant
            db_file_path = self.database_path / self.database_name
            
        # Convertir en chemin absolu pour SQLAlchemy
        db_file_path = db_file_path.resolve()
        db_uri = f"sqlite:///{db_file_path}"
        
        try:
            self.logger.info(f"Using database URI: {db_uri}")
            settings = {
                "search_algorithm": self.search_algorithm,
                "discovery_mode": self.discovery_mode,
                "compatibility_mode": self.compatibility_mode,
                "dependency_type": self.dependency_type,
                "max_table": self.max_table,
                "max_vars": self.max_vars,
            }
            self.logger.info(f"MATILDA settings for FD discovery: {settings}")
            
            with AlchemyUtility(db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                matilda = MATILDA(db_util, settings=settings)
                
                # Configurer MATILDA spécifiquement pour la découverte de FDs
                matilda.set_compatibility_mode(self.compatibility_mode)
                rules = []

                self.logger.debug("Starting FD discovery with MATILDA...")
                for rule in matilda.discover_rules(results_dir=str(self.results_dir)):
                    self.logger.info(f"Discovered FD: {rule}")
                    rules.append(rule)

                json_file_name = f"MATILDA_{self.database_name.stem}_fd_results.json"
                result_path = self.results_dir / json_file_name

                self.logger.debug(f"Saving FDs to {result_path}")
                number_of_rules = RuleIO.save_rules_to_json(rules, result_path)

                self.logger.info(f"Discovered {number_of_rules} functional dependencies with MATILDA.")
                self.generate_report(number_of_rules, result_path, [])

                if self.use_mlflow:
                    mlflow.log_param("algorithm", "MATILDA")
                    mlflow.log_param("database", self.database_name.name)
                    mlflow.log_metric("number_of_fds", number_of_rules)

                return number_of_rules

        except Exception as e:
            self.logger.error(f"An error occurred during FD discovery with MATILDA: {e}", exc_info=True)
            if self.use_mlflow:
                mlflow.log_param("error", str(e))
            raise

    def clean_up(self, temp_dirs: Optional[List[Path]] = None) -> None:
        """Cleans up temporary directories."""
        temp_dirs = temp_dirs or [
            self.database_path / "prolog_tmp",  # MATILDA peut créer des fichiers temporaires
        ]
        for directory in temp_dirs:
            if directory.exists() and directory.is_dir():
                shutil.rmtree(directory)
                self.logger.info(f"Cleaned up temporary directory: {directory}")

    def generate_report(self, number_of_rules: int, result_path: Path, top_rules: List[dict]) -> None:
        """Generates a report of the FD discovery run."""
        report_content = f"""
# FD Discovery Report with MATILDA

**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Algorithm:** MATILDA (configured for FDs)
**Database:** {self.database_name.name}
**Number of FDs Discovered:** {number_of_rules}
**Results Path:** {result_path}

## Summary
- **Algorithm:** MATILDA
- **Database:** {self.database_name.name}
- **Search Algorithm:** {self.search_algorithm}
- **Discovery Mode:** {self.discovery_mode}
- **Compatibility Mode:** {self.compatibility_mode}
- **Dependency Type:** {self.dependency_type}
- **Max Table:** {self.max_table}
- **Max Variables:** {self.max_vars}
- **Number of FDs Discovered:** {number_of_rules}
- **Results Path:** {result_path}

## Details
The functional dependency discovery process was completed successfully using MATILDA. 
The discovered FDs have been saved to the specified results path.
"""

        report_file_name = f"fd_report_MATILDA_{self.database_name.stem}.md"
        report_path = self.results_dir / report_file_name

        with report_path.open('w') as report_file:
            report_file.write(report_content)

        self.logger.info(f"Generated FD report: {report_path}")

        if self.use_mlflow:
            mlflow.log_artifact(str(report_path))
            self.logger.info("Logged report as MLflow artifact.")


def setup_signal_handlers(monitor: ResourceMonitor, logger: logging.Logger) -> None:
    """
    Sets up signal handlers for graceful shutdown.
    """
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main() -> None:
    """Main entry point for FD discovery using MATILDA."""
    parse_arguments()
    
    # Paramètres fixes sans configuration
    threshold = 10 * 1024 * 1024 * 1024  # 10GB
    timeout = 1800  # 30 minutes
    
    # Utiliser directement la base de données Bupa
    database_path = Path("/Users/famat/PycharmProjects/MATILDA_ALL/MATILDA/src/")
    database_name = Path("Bupa2.db")
    
    log_dir = Path("results_fd/")
    results_dir = Path("results_fd/")

    # Initialize directories
    initialize_directories(results_dir, log_dir)

    # Configure logger
    logger = configure_global_logger(log_dir)

    # Pas de MLflow
    use_mlflow = False

    # Initialize Resource Monitor
    monitor = ResourceMonitor(threshold, timeout)
    monitor_thread = threading.Thread(target=monitor.monitor, daemon=True)
    monitor_thread.start()
    logger.debug("Resource monitor started.")

    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(monitor, logger)

    # Initialize FDProcessor with MATILDA
    processor = FDProcessor(
        database_name=database_name,
        database_path=database_path,
        results_dir=results_dir,
        logger=logger,
        use_mlflow=use_mlflow
    )

    logger.info(f"Starting FD discovery with MATILDA on {database_name}")

    try:
        number_of_fds = processor.discover_rules()
        processor.clean_up()
        logger.info(f"FD discovery with MATILDA completed successfully. Found {number_of_fds} functional dependencies.")

    except Exception as e:
        logger.error("An error occurred during the FD discovery process with MATILDA.", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
