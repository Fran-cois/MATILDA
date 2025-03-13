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


@dataclass(frozen=True)
class FunctionalDependency(Rule):
    """
    Représente une dépendance fonctionnelle entre colonnes d'une table.
    
    Une dépendance fonctionnelle (FD) exprime que les valeurs d'un ensemble d'attributs (le déterminant)
    déterminent de façon unique les valeurs d'un autre ensemble d'attributs (le dépendant).
    Format : table: determinant → dependent
    """
    table: str
    determinant: Tuple[str, ...]  # Colonnes déterminantes (partie gauche)
    dependent: Tuple[str, ...]    # Colonnes dépendantes (partie droite)
    
    # Métadonnées de validation
    correct: Optional[bool] = None      # Règle validée comme correcte
    compatible: Optional[bool] = None   # Règle compatible avec le schéma
    
    # Métriques de qualité
    confidence: Optional[float] = None  # Confiance de la règle (0.0-1.0)
    support: Optional[float] = None     # Support de la règle (nb tuples ou %)
    coverage: Optional[float] = None    # Couverture des données
    accuracy: Optional[float] = None    # Précision de la règle
    # Statistiques de violation
    n_violations: Optional[int] = None  # Nombre de violations constatées
    violation_examples: Optional[List[Dict[str, Any]]] = None  # Exemples de violations
    
    # Attributs pour le suivi de conversion depuis EGD
    converted_from_egd: Optional[bool] = None
    original_egd: Optional[str] = None
    
    # Paramètres de l'algorithme et de compatibilité
    algorithm_settings: Optional[FDAlgorithmSettings] = None
    compatibility_settings: Optional[FDCompatibilitySettings] = None
    
    # Alias possibles pour la même dépendance (noms alternatifs des colonnes)
    aliases: Optional[Set[str]] = None
    display: Optional[str] = None

    
    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette dépendance fonctionnelle au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
        """
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)
    
    def to_dict(self) -> Dict:
        """
        Convertit cette dépendance fonctionnelle en dictionnaire pour sérialisation.
        
        Returns:
            Un dictionnaire représentant cette dépendance fonctionnelle
        """
        # Conversion de base avec asdict
        fd_dict = {
            "type": "FunctionalDependency",
            "table": self.table,
            "determinant": list(self.determinant),
            "dependent": list(self.dependent),
            "correct": self.correct,
            "compatible": self.compatible,
            "confidence": self.confidence,
            "support": self.support,
            "coverage": self.coverage,
            "n_violations": self.n_violations,
            "converted_from_egd": self.converted_from_egd,
            "original_egd": self.original_egd
        }
        
        # Ajout des exemples de violation s'ils existent
        if self.violation_examples:
            fd_dict["violation_examples"] = self.violation_examples
            
        # Ajout des paramètres d'algorithme s'ils existent
        if self.algorithm_settings:
            fd_dict["algorithm_settings"] = asdict(self.algorithm_settings)
            
        # Ajout des paramètres de compatibilité s'ils existent
        if self.compatibility_settings:
            fd_dict["compatibility_settings"] = asdict(self.compatibility_settings)
            
        # Ajout des alias s'ils existent
        if self.aliases:
            fd_dict["aliases"] = list(self.aliases)
            
        return fd_dict
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'FunctionalDependency':
        """
        Crée une instance de FunctionalDependency à partir d'un dictionnaire.
        
        Args:
            d: Dictionnaire contenant les propriétés de la règle
            
        Returns:
            Une instance de FunctionalDependency
            
        Raises:
            ValueError: Si le dictionnaire ne contient pas les champs requis
        """
        # Vérifier les champs obligatoires
        if "table" not in d or "determinant" not in d or "dependent" not in d:
            raise ValueError("Missing required fields in FunctionalDependency dictionary.")
        
        # Extraction des paramètres d'algorithme
        algorithm_settings = None
        if "algorithm_settings" in d:
            algorithm_settings = FDAlgorithmSettings(**d["algorithm_settings"])
        
        # Extraction des paramètres de compatibilité
        compatibility_settings = None
        if "compatibility_settings" in d:
            compatibility_settings = FDCompatibilitySettings(**d["compatibility_settings"])
        
        # Conversion des aliases en set s'ils existent
        aliases = set(d.get("aliases", [])) if d.get("aliases") else None
        
        return cls(
            table=d["table"],
            determinant=tuple(d["determinant"]),
            dependent=tuple(d["dependent"]),
            correct=d.get("correct"),
            compatible=d.get("compatible"),
            confidence=d.get("confidence"),
            support=d.get("support"),
            coverage=d.get("coverage"),
            n_violations=d.get("n_violations"),
            violation_examples=d.get("violation_examples"),
            converted_from_egd=d.get("converted_from_egd"),
            original_egd=d.get("original_egd"),
            algorithm_settings=algorithm_settings,
            compatibility_settings=compatibility_settings,
            aliases=aliases
        )
            
    def __eq__(self, other):
        """
        Compare cette dépendance fonctionnelle avec une autre.
        
        Deux FDs sont égales si elles ont la même table, le même déterminant 
        (indépendamment de l'ordre) et le même dépendant (indépendamment de l'ordre).
        
        Args:
            other: L'autre FD à comparer
            
        Returns:
            True si les FDs sont équivalentes, False sinon
        """
        if not isinstance(other, FunctionalDependency):
            return NotImplemented
            
        # Comparer la table
        if self.table != other.table:
            return False
            
        # Comparer les déterminants (ensembles)
        if set(self.determinant) != set(other.determinant):
            return False
            
        # Comparer les dépendants (ensembles)
        if set(self.dependent) != set(other.dependent):
            return False
            
        return True
    
    def __hash__(self):
        """
        Calcule un hash cohérent avec la méthode __eq__.
        
        Cela permet d'utiliser des FDs comme clés de dictionnaires et dans des ensembles.
        
        Returns:
            Valeur de hash
        """
        # Utiliser un tuple contenant la table et les versions triées des déterminants et dépendants
        return hash((self.table, tuple(sorted(self.determinant)), tuple(sorted(self.dependent))))
    
    def to_display_string(self) -> str:
        """
        Retourne une représentation lisible de la dépendance fonctionnelle.
        
        Returns:
            Une chaîne formatée représentant la dépendance
        """
        lhs = ", ".join(self.determinant)
        rhs = ", ".join(self.dependent)
        
        # Ajouter les métriques si disponibles
        metrics = []
        if self.confidence is not None:
            metrics.append(f"conf={self.confidence:.2f}")
        if self.support is not None:
            metrics.append(f"supp={self.support:.2f}")
        
        metrics_str = f" [{', '.join(metrics)}]" if metrics else ""
        
        return f"{self.table}: {lhs} → {rhs}{metrics_str}"
    
    def __str__(self) -> str:
        return self.to_display_string()
    
    def is_minimal(self, all_fds: List['FunctionalDependency']) -> bool:
        """
        Vérifie si cette dépendance fonctionnelle est minimale.
        Une FD est minimale si:
        1. Aucun sous-ensemble de son déterminant ne détermine ses dépendants
        2. On ne peut pas réduire les dépendants sans changer la sémantique
        
        Args:
            all_fds: Liste de toutes les FDs pour vérifier la minimalité
            
        Returns:
            True si la FD est minimale, False sinon
        """
        # Vérifier si un sous-ensemble du déterminant suffit
        if len(self.determinant) > 1:
            for i in range(len(self.determinant)):
                # Créer un sous-ensemble en omettant l'élément i
                sub_determinant = tuple(col for j, col in enumerate(self.determinant) if j != i)
                
                # Vérifier si une FD avec ce sous-ensemble existe déjà
                for fd in all_fds:
                    if (fd.table == self.table and 
                        set(fd.determinant) == set(sub_determinant) and 
                        set(fd.dependent).issuperset(set(self.dependent))):
                        return False
        
        # Vérifier si on peut réduire les dépendants
        if len(self.dependent) > 1:
            # Pour chaque dépendant, vérifier s'il est déterminé indépendamment
            for dep in self.dependent:
                for fd in all_fds:
                    if (fd.table == self.table and 
                        set(fd.determinant) == set(self.determinant) and 
                        len(fd.dependent) == 1 and dep in fd.dependent):
                        # Nous avons trouvé une FD plus spécifique
                        return False
        
        return True
