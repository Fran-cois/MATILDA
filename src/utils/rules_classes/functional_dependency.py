import json
from dataclasses import asdict, dataclass, field
from typing import Dict, Tuple, Optional, List, Any, Set

from .base_rule import Rule


@dataclass(frozen=True)
class FDCompatibilitySettings:
    """
    Paramètres de compatibilité pour les dépendances fonctionnelles.
    Ces paramètres déterminent comment une FD est validée et utilisée.
    """
    # Seuil minimal de confiance (0.0-1.0) pour qu'une FD soit considérée valide
    min_confidence: float = 0.95
    
    # Seuil minimal de support (nombre minimum de tuples ou pourcentage)
    min_support: float = 10
    
    # Précision minimale des valeurs pour la validation
    min_precision: float = 0.9
    
    # Tolérance aux erreurs (pourcentage de violations autorisé)
    error_tolerance: float = 0.05
    
    # Si True, les valeurs NULL sont considérées égales entre elles
    null_equals_null: bool = False
    
    # Si True, la validation est plus stricte et rejette toute exception
    strict_validation: bool = False


@dataclass(frozen=True)
class FDAlgorithmSettings:
    """
    Paramètres pour les algorithmes de découverte de dépendances fonctionnelles.
    """
    # Algorithme à utiliser: 'tane', 'fd_mine', 'dfd', etc.
    algorithm: str = 'tane'
    
    # Paramètres spécifiques à l'algorithme
    algorithm_params: Dict[str, Any] = field(default_factory=dict)
    
    # Nombre maximum de déterminants à considérer
    max_lhs_size: int = 5
    
    # Nombre maximum de colonnes dépendantes à considérer
    max_rhs_size: int = 1
    
    # Colonnes à exclure de l'analyse
    excluded_columns: List[str] = field(default_factory=list)
    
    # Limite du temps d'exécution en secondes (0 = pas de limite)
    time_limit_seconds: int = 0
    
    # Limite de mémoire en Mo (0 = pas de limite)
    memory_limit_mb: int = 0
    
    # Focus sur des colonnes spécifiques comme déterminants
    focus_columns: List[str] = field(default_factory=list)
    
    # Utilisation du parallélisme lors de la découverte
    use_parallelism: bool = True
    
    # Nombre de threads/processus à utiliser (0 = auto)
    n_jobs: int = 0


class FunctionalDependency(Rule):
    """
    Représente une dépendance fonctionnelle (FD) de la forme X → Y où X est un ensemble d'attributs
    et Y est un attribut déterminé par X.
    """
    
    def __init__(self, table, lhs, rhs, support=0.0, confidence=1.0):
        """
        Initialise une dépendance fonctionnelle.
        
        :param table: Nom de la table contenant les attributs
        :param lhs: Liste des attributs du côté gauche (déterminants)
        :param rhs: Attribut du côté droit (déterminé)
        :param support: Support de la règle (ratio des tuples qui satisfont la FD)
        :param confidence: Confiance de la règle (toujours 1.0 pour une FD valide)
        """
        super().__init__()
        self.table = table
        self.lhs = lhs if isinstance(lhs, list) else [lhs]
        self.rhs = rhs
        self.support = support
        self.confidence = confidence
        
        # Une FD est considérée comme un type de règle EGD
        self.rule_type = "fd"
        
        # Pour compatibilité avec l'interface Rule
        self.body = [f"{table}({', '.join(self.lhs)})"]
        self.head = [f"{table}({self.rhs})"]
        self.accuracy = support
        
        # Créer une représentation textuelle
        self._generate_display()
    
    def _generate_display(self):
        """Génère une représentation textuelle de la FD."""
        lhs_str = ', '.join(self.lhs)
        self.display = f"{self.table}: {lhs_str} → {self.rhs}"
        
    def __str__(self):
        return self.display
        
    def __repr__(self):
        return f"FD({self.display}, support={self.support:.2f}, confidence={self.confidence:.2f})"
        
    def export_to_json(self, filepath):
        """Exporte la dépendance fonctionnelle au format JSON."""
        import json
        data = {
            "table": self.table,
            "lhs": self.lhs,
            "rhs": self.rhs,
            "support": self.support,
            "confidence": self.confidence,
            "display": self.display
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def __eq__(self, other):
        """Vérifie si deux dépendances fonctionnelles sont égales."""
        if not isinstance(other, FunctionalDependency):
            return False
        return (self.table == other.table and 
                set(self.lhs) == set(other.lhs) and 
                self.rhs == other.rhs)
