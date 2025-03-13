import json
import logging
from dataclasses import asdict, dataclass
from typing import Dict, Tuple, Optional

from .base_rule import Rule


@dataclass(frozen=True)
class InclusionDependency(Rule):
    """
    Représente une dépendance d'inclusion entre colonnes de tables.
    
    Une dépendance d'inclusion (IND) exprime que les valeurs d'un ensemble de colonnes
    d'une table (dépendante) sont contenues dans un ensemble de colonnes d'une autre table (référencée).
    Format : table_dependant(columns_dependant) ⊆ table_referenced(columns_referenced)
    """
    table_dependant: str
    columns_dependant: Tuple[str, ...]
    table_referenced: str
    columns_referenced: Tuple[str, ...]
    display: Optional[str] = None
    correct: Optional[bool] = None
    compatible: Optional[bool] = None
    accuracy: Optional[float] = None
    confidence: Optional[float] = None
    
    def __post_init__(self):
        """
        Validation des attributs après l'initialisation.
        """
        if len(self.columns_dependant) != len(self.columns_referenced):
            raise ValueError(
                f"Les colonnes dépendantes ({len(self.columns_dependant)}) et référencées "
                f"({len(self.columns_referenced)}) doivent avoir la même cardinalité."
            )
    
    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette dépendance d'inclusion au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
            
        Raises:
            IOError: Si l'écriture dans le fichier échoue
        """
        try:
            with open(filepath, 'a+') as f:
                json.dump(self.to_dict(), f, indent=4)
        except IOError as e:
            logging.error(f"Erreur lors de l'écriture dans {filepath}: {str(e)}")
            raise
    
    def to_dict(self) -> Dict:
        """
        Convertit cette dépendance d'inclusion en dictionnaire pour sérialisation.
        
        Returns:
            Un dictionnaire représentant cette dépendance d'inclusion
        """
        return {
            "type": "InclusionDependency",
            **asdict(self)
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'InclusionDependency':
        """
        Crée une instance de InclusionDependency à partir d'un dictionnaire.
        
        Args:
            d: Dictionnaire contenant les propriétés de la règle
            
        Returns:
            Une instance de InclusionDependency
            
        Raises:
            ValueError: Si le dictionnaire ne contient pas les champs requis
        """
        # Vérifier les champs obligatoires
        required_fields = ["table_dependant", "columns_dependant", "table_referenced", "columns_referenced"]
        for field in required_fields:
            if field not in d:
                raise ValueError(f"Missing required field '{field}' in InclusionDependency dictionary")
        
        return cls(
            table_dependant=d["table_dependant"],
            columns_dependant=tuple(d["columns_dependant"]),
            table_referenced=d["table_referenced"],
            columns_referenced=tuple(d["columns_referenced"]),
            display=d.get("display"),
            correct=d.get("correct"),
            compatible=d.get("compatible"),
            accuracy=d.get("accuracy"),
            confidence=d.get("confidence")
        )
    
    def to_display_string(self) -> str:
        """
        Retourne une représentation lisible de la dépendance d'inclusion.
        
        Returns:
            Une chaîne formatée représentant la dépendance
        """
        if self.display:
            return self.display
            
        col_dep = ", ".join(self.columns_dependant)
        col_ref = ", ".join(self.columns_referenced)
        return f"{self.table_dependant}({col_dep}) ⊆ {self.table_referenced}({col_ref})"
    
    def __str__(self) -> str:
        """
        Représentation en chaîne de caractères de cette dépendance d'inclusion.
        
        Returns:
            Une chaîne formatée représentant la dépendance
        """
        return self.to_display_string()
