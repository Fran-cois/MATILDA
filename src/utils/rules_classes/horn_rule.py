import json
from dataclasses import asdict, dataclass
from typing import Tuple, Optional, List
from .base_rule import Predicate, Rule
from .predicate_utils import PredicateUtils  # Assurez-vous que PredicateUtils existe

@dataclass(frozen=True)
class HornRule(Rule):
    """
    Représente une règle de Horn.
    
    Une règle de Horn est une règle logique de la forme:
    body1 ∧ body2 ∧ ... ∧ bodyN → head
    où body et head sont des prédicats.
    """
    body: Tuple[Predicate]
    head: Predicate
    display: str
    correct: Optional[bool] = None
    compatible: Optional[bool] = None

    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette règle de Horn au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
        """
        with open(filepath, 'a+') as f:
            json.dump({
                "body": [str(pred) for pred in self.body],
                "head": str(self.head),
                "display": self.display,
                "correct": self.correct,
                "compatible": self.compatible
            }, f, indent=4)

    def __eq__(self, other) -> bool:
        """
        Compare cette règle de Horn avec une autre.
        
        Args:
            other: L'objet à comparer avec cette règle
            
        Returns:
            True si les règles sont équivalentes, False sinon
        """
        list1 = list(self.body + (self.head,))
        if not isinstance(other, HornRule):
            # Si other est une TGDRule, on peut comparer les body et head
            if hasattr(other, 'body') and hasattr(other, 'head'):
                # Pour TGDRule, la tête est une liste de prédicats
                if isinstance(other.head, tuple) or isinstance(other.head, list):
                    list2 = list(other.body + other.head)
                else:
                    # Pour gérer le cas où head est un seul prédicat
                    list2 = list(other.body + (other.head,))
                return PredicateUtils.compare_lists(list1, list2)
            return NotImplemented
        list2 = list(other.body + (other.head,))
        return PredicateUtils.compare_lists(list1, list2)
