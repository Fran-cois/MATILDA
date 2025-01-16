import json
import logging
import os
import sys
import glob
from typing import Dict, List, Union
from collections import defaultdict, deque

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/utils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from rules import RuleIO

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)

class RuleCompatibilityChecker:
    def __init__(
        self,
        results_dir="results",
        compatible_dir="matilda",
        compatibility_sep="_",
        debug="",
    ):
        self.results_dir = results_dir
        self.compatible_dir = compatible_dir
        self.compatibility_sep = compatibility_sep
        self.debug = debug
        self.compatibility_files = {}
        self.load_compatibility_files()

    def load_compatibility_files(self):
        pattern = os.path.join(self.debug + self.results_dir, "*/matilda/compatibility_*.json")
        for filepath in glob.glob(pattern):
            database_name = os.path.basename(filepath).split(self.compatibility_sep)[-1].split('.')[0]
            with open(filepath, 'r') as file:
                self.compatibility_files[database_name] = json.load(file)
        logging.info(f"Loaded {len(self.compatibility_files)} compatibility files.")

    def is_rule_compatible(self, rule, compatibility_dict: Dict[str, List[str]]) -> bool:
        def clean_up_relation(relation):
            return relation.split("___sep___")[0]
            #return relation.split("___sep___")[0].replace("_", "") + "___sep___" + relation.split("___sep___")[1]

        if isinstance(rule, dict):
            body = rule.get("body", [])
            head = rule.get("head", [])
        else:
            body = rule.body
            head = rule.head

        indexes = {}
        for predicate in body:
            if predicate.variable2 not in indexes:
                indexes[predicate.variable2] = []
            indexes[predicate.variable2].append(clean_up_relation(predicate.relation))

        for predicate in head:
            if predicate.variable2 not in indexes:
                indexes[predicate.variable2] = []
            indexes[predicate.variable2].append(clean_up_relation(predicate.relation))

        compatibility_dict = {
            clean_up_relation(k): [clean_up_relation(rel) for rel in v]
            for k, v in compatibility_dict.items()
        }

        for variable, relations in indexes.items():
            for sub_relation in relations:
                if sub_relation not in compatibility_dict:
                    return False
                for other_relation in relations:
                    if other_relation != sub_relation and other_relation not in compatibility_dict[sub_relation]:
                        return False
        return True

    def check_rule_compatibility(self, filepath: str, compatibility_dict: Dict[str, List[str]]) -> List[Dict[str, Union[Dict, bool]]]:
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
        except Exception as e:
            logging.error(f"Error reading JSON file {filepath}: {e}")
            return []

        results = []
        for rule_dict in data:
            rule = RuleIO.rule_from_dict(rule_dict)
            try:
                compatible = self.is_rule_compatible(rule, compatibility_dict)
                rule_dict["compatible"] = compatible
                results.append(rule_dict)
            except Exception as e:
                logging.error(f"Error processing rule: {e}. Rule data: {rule_dict}")
                rule_dict["compatible"] = False
                results.append(rule_dict)
        return results

    def save_compatibility_results(self, filepath: str, results: List[Dict[str, Union[Dict, bool]]]):
        try:
            with open(filepath, 'w') as file:
                json.dump(results, file, indent=4)
            logging.info(f"Compatibility results written to {filepath}")
        except Exception as e:
            logging.error(f"Error writing compatibility results to {filepath}: {e}")
    def process_matilda_results(self):
        input_pattern = os.path.join(self.debug + self.results_dir, "*/matilda/matilda_*_results.json")
        for input_filepath in glob.glob(input_pattern):
            database_name = os.path.basename(input_filepath).split(self.compatibility_sep)[-2].split('_')[0]
            if database_name in self.compatibility_files:
                compatibility_dict = self.compatibility_files[database_name]
                results = self.check_rule_compatibility(input_filepath, compatibility_dict)
                self.save_compatibility_results(input_filepath, results)
            else:
                logging.warning(f"No matching compatibility file for {input_filepath}")
    def process_amie3_results(self):
        input_pattern = os.path.join(self.debug + self.results_dir, "*/amie3/amie3_*_results.json")
        for input_filepath in glob.glob(input_pattern):
            database_name = os.path.basename(input_filepath).split(self.compatibility_sep)[-2].split('_')[0]
            if database_name in self.compatibility_files:
                compatibility_dict = self.compatibility_files[database_name]
                results = self.check_rule_compatibility(input_filepath, compatibility_dict)
                self.save_compatibility_results(input_filepath, results)
            else:
                logging.warning(f"No matching compatibility file for {input_filepath}")
    def process_spider_results(self):
        input_pattern = os.path.join(self.debug + self.results_dir, "*/spider/spider_*_results.json")
        for input_filepath in glob.glob(input_pattern):
            database_name = os.path.basename(input_filepath).split(self.compatibility_sep)[-2].split('_')[0]
            if database_name in self.compatibility_files:
                compatibility_dict = self.compatibility_files[database_name]
                results = self.check_rule_compatibility(input_filepath, compatibility_dict)
                self.save_compatibility_results(input_filepath, results)
            else:
                logging.warning(f"No matching compatibility file for {input_filepath}")
    def process_ilp_results(self):
        input_pattern = os.path.join(self.debug + self.results_dir, "*/ilp/ilp_*_results.json")
        for input_filepath in glob.glob(input_pattern):
            database_name = os.path.basename(input_filepath).split(self.compatibility_sep)[-2].split('_')[0]
            if database_name in self.compatibility_files:
                compatibility_dict = self.compatibility_files[database_name]
                results = self.check_rule_compatibility(input_filepath, compatibility_dict)
                self.save_compatibility_results(input_filepath, results)
            else:
                logging.warning(f"No matching compatibility file for {input_filepath}")
    def process_files(self):
        self.process_ilp_results()
        self.process_spider_results()
        self.process_amie3_results()
        self.process_matilda_results()

        # input_pattern = os.path.join(self.debug + self.results_dir, "*/matilda/matilda_*_results.json")
        # for input_filepath in glob.glob(input_pattern):
        #     database_name = os.path.basename(input_filepath).split(self.compatibility_sep)[-2].split('_')[0]
        #     if database_name in self.compatibility_files:
        #         compatibility_dict = self.compatibility_files[database_name]
        #         results = self.check_rule_compatibility(input_filepath, compatibility_dict)
        #         self.save_compatibility_results(input_filepath, results)
        #     else:
        #         logging.warning(f"No matching compatibility file for {input_filepath}")

if __name__ == "__main__":
    results_dir="../main/data/results/"
    checker = RuleCompatibilityChecker(
        results_dir=results_dir,
        compatible_dir=results_dir,
        compatibility_sep="_",
        debug=""
    )
    checker.process_files()
