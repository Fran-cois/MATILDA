
import logging
import yaml
from pathlib import Path
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

class RuleCoverageCalculator:
    def __init__(self, rules_dir: Path, coverage_output_dir: Path, report_dir: Path):
        self.rules_dir = rules_dir
        self.coverage_output_dir = coverage_output_dir
        self.report_dir = report_dir
        self.logger = logging.getLogger("RuleCoverageCalculator")
        self.logger.handlers = []
        handler = logging.StreamHandler()
        handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.successes = []
        self.failures = []

    def calculate_coverage(self):
        """Calculate the coverage of the rules."""
        try:
            self.logger.info(f"Calculating rule coverage from {self.rules_dir} and saving to {self.coverage_output_dir}")
            # Exemple de calcul de couverture des règles
            coverage_data = {}
            for rule_file in self.rules_dir.glob("filtered_*_rules.yaml"):
                with open(rule_file, "r") as file:
                    rules = yaml.safe_load(file)
                coverage = self._compute_rule_coverage(rules)
                coverage_data[rule_file.stem] = coverage
                self.logger.info(f"Coverage calculated for {rule_file.name}: {coverage}%")
            
            # Sauvegarder les données de couverture
            coverage_output_file = self.coverage_output_dir / "rule_coverage.yaml"
            with open(coverage_output_file, "w") as file:
                yaml.dump(coverage_data, file, default_flow_style=False, sort_keys=False)
            
            self.successes.append("Rule coverage calculated successfully.")
            self.logger.info("Rule coverage calculated successfully.")
        except Exception as e:
            self.failures.append(f"RuleCoverageCalculator failed: {e}")
            self.logger.error(f"RuleCoverageCalculator failed: {e}")

    def _compute_rule_coverage(self, rules: list) -> float:
        """Compute the coverage percentage of the given rules."""
        pass 
        # if not rules:
        #     return 0.0
        # total_rules = len(rules)
        # # Supposons que chaque règle a un attribut 'coverage' entre 0 et 100
        # covered_rules = sum(rule.get("coverage", 0) > 50 for rule in rules)
        # coverage_percentage = (covered_rules / total_rules) * 100
        # return round(coverage_percentage, 2)

    def generate_report(self):
        """Generate a Markdown report summarizing the coverage calculations."""
        report_path = self.report_dir / "4_step_compute_coverage_report.md"
        try:
            with open(report_path, "w") as report:
                report.write("# Rapport de Calcul de la Couverture des Règles\n\n")
                
                report.write("## Succès\n")
                for s in self.successes:
                    report.write(f"- {s}\n")
                
                report.write("\n## Échecs\n")
                for f in self.failures:
                    report.write(f"- {f}\n")
            
            self.logger.info(f"Report generated at {report_path}")
            self.successes.append("Coverage report generated successfully.")
        except Exception as e:
            self.failures.append(f"Report generation failed: {e}")
            self.logger.error(f"Report generation failed: {e}")

    def main(self):
        """Main method to execute the coverage calculation."""
        self.calculate_coverage()
        self.generate_report()