import json
from dataclasses import asdict, dataclass, field
from typing import Dict, Tuple, Union, Optional

@dataclass(frozen=True)
class DCCondition:
    column_1: str
    operator: str
    value: Union[str, Tuple[str, str]]
    negation: bool = False

    def __str__(self):
        negation_str = "NOT " if self.negation else ""
        return f"{self.column_1} {negation_str}{self.operator} {self.value}"


@dataclass(frozen=True)
class DenialConstraint:
    table: str
    conditions: Tuple[DCCondition]
    correct: Optional[bool] = None
    compatible: Optional[bool] = None

    def export_to_json(self, filepath: str):
        with open(filepath, "a+") as f:
            json.dump(
                {
                    "table": self.table,
                    "conditions": [asdict(cond) for cond in self.conditions],
                    "correct": self.correct,
                    "compatible": self.compatible
                },
                f,
                indent=4,
            )
