from abc import ABC, abstractmethod
import json
from typing import Dict, NamedTuple, Optional, Tuple
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class Predicate:
    """
    Représente un prédicat dans une règle logique.
    
    Un prédicat est formé d'une relation entre deux variables, généralement 
    représenté comme relation(variable1, variable2).
    """
    variable1: str
    relation: str
    variable2: str
    
    def __str__(self) -> str:
        return f"{self.relation}({self.variable1}, {self.variable2})"


class Rule(ABC):
    """
    Classe abstraite pour représenter une règle.
    
    Toutes les classes de règles spécifiques doivent hériter de cette classe
    et implémenter ses méthodes abstraites.
    """
    correct: Optional[bool] = None
    compatible: Optional[bool] = None
    
    @abstractmethod
    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette règle au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
            
        Raises:
            IOError: Si l'écriture dans le fichier échoue
        """
        raise NotImplementedError("La méthode export_to_json doit être implémentée dans les classes dérivées.")
