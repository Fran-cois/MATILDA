import json
from dataclasses import asdict, dataclass
from typing import Dict, Tuple, Union, Optional

from .base_rule import Rule


@dataclass(frozen=True)
class DCCondition:
    """
    Représente une condition dans une contrainte de négation.
    
    Une condition est composée d'une colonne, d'un opérateur, d'une valeur 
    et d'un indicateur de négation.
    """
    column_1: str
    operator: str
    value: Union[str, Tuple[str, str]]
    negation: bool = False

    def __str__(self) -> str:
        """
        Représentation en chaîne de caractères de cette condition.
        
        Returns:
            Une chaîne formatée représentant la condition
        """
        negation_str = "NOT " if self.negation else ""
        return f"{self.column_1} {negation_str}{self.operator} {self.value}"


@dataclass(frozen=True)
class DenialConstraint(Rule):
    """
    Représente une contrainte de négation.
    
    Une contrainte de négation (Denial Constraint) exprime qu'une certaine combinaison
    de valeurs n'est pas autorisée dans une table.
    Format : ¬(condition1 ∧ condition2 ∧ ... ∧ conditionN)
    """
    table: str
    conditions: Tuple[DCCondition]
    correct: Optional[bool] = None
    compatible: Optional[bool] = None

    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette contrainte de négation au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
        """
        with open(filepath, "a+") as f:
            json.dump(self.to_dict(), f, indent=4)
    
    def to_dict(self) -> Dict:
        """
        Convertit cette contrainte de négation en dictionnaire pour sérialisation.
        
        Returns:
            Un dictionnaire représentant cette contrainte de négation
        """
        return {
            "type": "DenialConstraint",
            "table": self.table,
            "conditions": [asdict(cond) for cond in self.conditions],
            "correct": self.correct,
            "compatible": self.compatible
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'DenialConstraint':
        """
        Crée une instance de DenialConstraint à partir d'un dictionnaire.
        
        Args:
            d: Dictionnaire contenant les propriétés de la règle
            
        Returns:
            Une instance de DenialConstraint
            
        Raises:
            ValueError: Si le dictionnaire ne contient pas les champs requis
        """
        if "table" not in d or "conditions" not in d:
            raise ValueError("Missing required fields in DenialConstraint dictionary.")
        
        # Convertir les conditions
        conditions = []
        for cond_data in d["conditions"]:
            if isinstance(cond_data, str):
                # Parsing simplifié pour les chaînes de caractères
                parts = cond_data.split()
                if len(parts) >= 3:
                    column_1 = parts[0]
                    operator = parts[1]
                    value = parts[2]
                    negation = "NOT" in cond_data.upper()
                    conditions.append(DCCondition(column_1, operator, value, negation))
            elif isinstance(cond_data, dict):
                # Parsing des dictionnaires
                conditions.append(DCCondition(
                    column_1=cond_data.get("column_1"),
                    operator=cond_data.get("operator"),
                    value=cond_data.get("value"),
                    negation=cond_data.get("negation", False)
                ))
        
        return cls(
            table=d["table"],
            conditions=tuple(conditions),
            correct=d.get("correct"),
            compatible=d.get("compatible")
        )
