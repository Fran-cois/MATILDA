import json
import logging
from typing import Dict, List, Union
from dataclasses import asdict

from .rules import (
    Rule, InclusionDependency, FunctionalDependency, DenialConstraint,
    HornRule, TGDRule, EGDRule, DCCondition, PredicateUtils
)


class RuleIO:
    """
    Classe utilitaire pour la sérialisation/désérialisation des règles.
    Permet l'import et l'export des règles depuis/vers des fichiers JSON.
    """

    @staticmethod
    def rule_to_dict(rule: Rule) -> Dict:
        if isinstance(rule, InclusionDependency):
            return {"type": "InclusionDependency", **asdict(rule)}
        elif isinstance(rule, FunctionalDependency):
            return {"type": "FunctionalDependency", **asdict(rule)}
        elif isinstance(rule, DenialConstraint):
            return {
                "type": "DenialConstraint",
                "table": rule.table,
                "conditions": [str(cond) for cond in rule.conditions],
                "correct": rule.correct,
                "compatible": rule.compatible
            }
        elif isinstance(rule, HornRule):
            return {
                "type": "HornRule",
                "body": [str(pred) for pred in rule.body],
                "head": str(rule.head),
                "display": rule.display,
                "correct": rule.correct,
                "compatible": rule.compatible
            }
        elif isinstance(rule, TGDRule):
            return {
                "type": "TGDRule",
                "body": [str(pred) for pred in rule.body],
                "head": [str(pred) for pred in rule.head],
                "display": rule.display,
                "accuracy": rule.accuracy,
                "confidence": rule.confidence,
                "correct": rule.correct,
                "compatible": rule.compatible
            }
        elif isinstance(rule, EGDRule):
            return {
                "type": "EGDRule",
                "body": [str(pred) for pred in rule.body],
                "head": [str(pred) for pred in rule.head],
                "display": rule.display,
                "accuracy": rule.accuracy,
                "confidence": rule.confidence,
                "correct": rule.correct,
                "compatible": rule.compatible,
                "head_variables": [list(eq) for eq in rule.head_variables],
                "equality_vars": list(rule.equality_vars) if rule.equality_vars else []
            }
        else:
            raise ValueError(f"Unknown rule type: {type(rule).__name__}")

    @staticmethod
    def rule_from_dict(d: Dict) -> Rule:
        try:
            rule_type = d.get("type")
            if not rule_type:
                raise ValueError("Missing rule type in dictionary.")
                
            if rule_type == "InclusionDependency":
                return InclusionDependency(
                    table_dependant=d.get("table_dependant"),
                    columns_dependant=tuple(d.get("columns_dependant")),
                    table_referenced=d.get("table_referenced"),
                    columns_referenced=tuple(d.get("columns_referenced")),
                    display=d.get("display"),
                    correct=d.get("correct"),
                    compatible=d.get("compatible"),
                    accuracy=d.get("accuracy"),
                    confidence=d.get("confidence")
                )
            elif rule_type == "FunctionalDependency":
                return FunctionalDependency(
                    table=d.get("table"),
                    determinant=tuple(d.get("determinant")),
                    dependent=tuple(d.get("dependent")),
                    correct=d.get("correct"),
                    compatible=d.get("compatible"),
                    converted_from_egd=d.get("converted_from_egd"),
                    original_egd=d.get("original_egd")
                )
            elif rule_type == "DenialConstraint":
                conditions = []
                for cond_str in d.get("conditions", []):
                    # Parsing simplified for brevity - you would implement a proper parser here
                    parts = cond_str.split()
                    if len(parts) >= 3:
                        column_1 = parts[0]
                        operator = parts[1]
                        value = parts[2]
                        negation = "NOT" in cond_str.upper()
                        conditions.append(DCCondition(column_1, operator, value, negation))
                        
                return DenialConstraint(
                    table=d.get("table"),
                    conditions=tuple(conditions),
                    correct=d.get("correct"),
                    compatible=d.get("compatible")
                )
            elif rule_type == "HornRule":
                if "body" not in d or "head" not in d:
                    raise ValueError("Missing required fields in HornRule.")
                body = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["body"])
                head = PredicateUtils.str_to_predicate(d["head"])
                return HornRule(
                    body=body,
                    head=head,
                    display=d.get("display"),
                    correct=d.get("correct"),
                    compatible=d.get("compatible")
                )
            elif rule_type == "TGDRule":
                if "body" not in d or "head" not in d:
                    raise ValueError("Missing required fields in TGDRule.")
                body = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["body"])
                head = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["head"])
                return TGDRule(
                    body=body,
                    head=head,
                    display=d.get("display"),
                    accuracy=d.get("accuracy", 0.0),
                    confidence=d.get("confidence", 0.0),
                    correct=d.get("correct"),
                    compatible=d.get("compatible")
                )
            elif rule_type == "EGDRule":
                if "body" not in d or "head" not in d:
                    raise ValueError("Missing required fields in EGDRule.")
                body = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["body"])
                head = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["head"])
                
                # Traiter les head_variables s'ils existent
                head_variables = tuple(tuple(eq) for eq in d.get("head_variables", []))
                equality_vars = tuple(d.get("equality_vars", []))
                
                return EGDRule(
                    body=body,
                    head=head,
                    display=d.get("display"),
                    accuracy=d.get("accuracy", 0.0),
                    confidence=d.get("confidence", 0.0),
                    correct=d.get("correct"),
                    compatible=d.get("compatible"),
                    head_variables=head_variables,
                    equality_vars=equality_vars
                )
            else:
                raise ValueError(f"Unknown rule type: {rule_type}")
        except Exception as e:
            logging.error(f"Error converting rule from dict: {e}. Rule data: {d}")
            raise

    @staticmethod
    def save_yieled_rules_to_json(rule: Rule, filepath: str) -> None:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except Exception:
            data = []

        data.append(RuleIO.rule_to_dict(rule))
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def save_rules_to_json(rules: List[Rule], filepath: str) -> int:
        try:
            rules_generated = [RuleIO.rule_to_dict(rule) for rule in rules]
            with open(filepath, "w") as f:
                json.dump(rules_generated, f, indent=4)
            return len(rules_generated)
        except Exception as e:
            raise e

    @staticmethod
    def save_yielded_rule_to_json(rule: Rule, filepath: str) -> None:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []

        data.append(RuleIO.rule_to_dict(rule))

        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_rules_from_json(filepath: str) -> List[Rule]:
        with open(filepath, "r") as f:
            return [RuleIO.rule_from_dict(d) for d in json.load(f)]
