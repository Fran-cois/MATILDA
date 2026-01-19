# algorithms/spider.py

import ast
import os
from datetime import datetime
import logging

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import InclusionDependency, Rule
from utils.run_cmd import run_cmd

logger = logging.getLogger(__name__)


class Spider(BaseAlgorithm):
    def discover_rules(self, **kwargs) -> Rule:
        rules = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))

        #results_path = kwargs.get("results_dir", "results")
        algorithm_name = "SPIDER"
        classPath = "de.metanome.algorithms.spider.SPIDERFile"
        rule_type = "inds"
        params = " --table-key INPUT_FILES"
        
        # Get CSV files from database
        csv_dir = self.database.base_csv_dir
        csv_files = [
            f"/data/{t}"
            for t in os.listdir(csv_dir)
            if t.endswith('.csv')
        ]
        csv_files_str = " ".join(csv_files)
        
        current_time = datetime.now()
        file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}'
        
        # Get absolute paths for Docker volume mounting
        csv_dir_abs = os.path.abspath(csv_dir)
        results_dir_abs = os.path.abspath("results")
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir_abs, exist_ok=True)
        
        # Docker command to run SPIDER with Java 11
        cmd_string = (
            f"docker run --rm "
            f"-v {csv_dir_abs}:/data "
            f"-v {results_dir_abs}:/app/results "
            f"matilda-spider:latest "
            f"--algorithm {classPath} "
            f"--files {csv_files_str} "
            f"{params} "
            f"--separator \",\" "
            f"--output file:{file_name} "
            f"--header"
        )
        
        logger.info(f"Running SPIDER with Docker: {cmd_string}")
        
        if not run_cmd(cmd_string):
            logger.error("SPIDER execution failed")
            return rules
        # print(f"Rules discovered by {algorithm_name} algorithm saved to {file_name}")
        result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
        try:
            with open(result_file_path, mode="r") as f:
                raw_rules = [line for line in f if line.strip()]
        except FileNotFoundError:
            # If the result file does not exist, return empty rules
            return rules

        if os.path.exists(result_file_path):
            os.remove(result_file_path)

        for raw_rule in raw_rules:
            try:
                raw_rule = ast.literal_eval(raw_rule)
            except (ValueError, SyntaxError) as e:
                # Log the error if logging is set up, or pass to skip invalid rule
                # Example: logging.warning(f"Invalid rule format: {raw_rule} - {e}")
                continue  # Skip invalid rule formats

            try:
                table_dependant = raw_rule["dependant"]["columnIdentifiers"][0]["tableIdentifier"].replace(".csv", "")
                columns_dependant = (
                    raw_rule["dependant"]["columnIdentifiers"][0]["columnIdentifier"],
                )
                table_referenced = raw_rule["referenced"]["columnIdentifiers"][0]["tableIdentifier"].replace(".csv", "")
                columns_referenced = (
                    raw_rule["referenced"]["columnIdentifiers"][0]["columnIdentifier"],
                )
                inclusion_dependency = InclusionDependency(
                    table_dependant=table_dependant,
                    columns_dependant=columns_dependant,
                    table_referenced=table_referenced,
                    columns_referenced=columns_referenced,
                )
                rules[inclusion_dependency] = (1, 1)
            except (KeyError, IndexError, AttributeError) as e:
                # Log the error if logging is set up, or pass to skip malformed rule
                # Example: logging.warning(f"Malformed rule data: {raw_rule} - {e}")
                continue  # Skip malformed rule data

        return rules
