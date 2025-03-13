import json
import re
import logging
import random
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Tuple, Optional, ClassVar
from .base_rule import Rule, Predicate


@dataclass(frozen=True)
class TGDRule(Rule):
    """
    Représente une dépendance qui génère des tuples (Tuple-Generating Dependency).
    
    Une TGD est une règle logique qui peut générer de nouveaux tuples lorsqu'elle est appliquée.
    Format typique: ∀ x1...xn: body(x1...xn) ⇒ ∃ y1...ym: head(x1...xn, y1...ym)
    """
    body: Tuple[Predicate]  # Le corps de la règle (conjonction de prédicats)
    head: Tuple[Predicate]  # La tête de la règle (conjonction de prédicats)
    display: str            # Représentation textuelle de la règle
    accuracy: float         # Mesure de précision/support
    confidence: float       # Mesure de confiance
    correct: Optional[bool] = None       # Indique si la règle est correcte
    compatible: Optional[bool] = None    # Indique si la règle est compatible
    
    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette TGD au format JSON dans le fichier spécifié.
        
        Args:
            filepath: Chemin du fichier où la règle sera enregistrée
        """
        with open(filepath, 'w') as f:
            json.dump({
                "body": [str(pred) for pred in self.body],
                "head": [str(pred) for pred in self.head],
                "display": self.display,
                "accuracy": self.accuracy,
                "confidence": self.confidence,
                "correct": self.correct,
                "compatible": self.compatible
            }, f, indent=4)
    
    @staticmethod
    def str_to_tgd(tgd_str: str, support: float = 0.0, confidence: float = 0.0) -> 'TGDRule':
        """
        Convertit une chaîne représentant une TGD en objet TGDRule.
        
        Args:
            tgd_str: Chaîne représentant une TGD
            support: Valeur de support de la TGD
            confidence: Valeur de confiance de la TGD
            
        Returns:
            Un objet TGDRule
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
        """
        # Importer ici pour éviter les importations circulaires
        from ..rules import PredicateUtils
        
        # Logger pour enregistrer les avertissements
        logger = logging.getLogger(__name__)
        
        # Regex pour le format standard avec quantificateurs universels et existentiels
        pattern = r"∀ (.*): (.*?) ⇒ (∃.*:)?(.*?)$"
        match = re.match(pattern, tgd_str)

        if match:
            variables_str, body_str, variables_head_str, head_str = match.groups()

            # Traiter le corps
            body_predicates = []
            for split in body_str.split(" \u2227 "):  # \u2227 est le symbole unicode pour ∧
                body_pred = PredicateUtils.str_to_predicate(split)
                body_predicates.append(body_pred)
            body = tuple(body_predicates)

            # Traiter la tête
            head_predicates = []
            for split in head_str.split(" \u2227 "):
                head_pred = PredicateUtils.str_to_predicate(split)
                head_predicates.append(head_pred)
            head = tuple(head_predicates)

            # Créer et retourner l'objet TGDRule
            return TGDRule(
                body=body,
                head=head,
                display=tgd_str,
                accuracy=support,
                confidence=confidence
            )
        else:
            # Format alternatif sans quantificateurs: corps ⇒ tête
            pattern = r"(.*?) ⇒ (.*?)$"
            match = re.match(pattern, tgd_str)
            
            if match:
                body_str, head_str = match.groups()
                
                # Traiter le corps
                body_predicates = []
                for split in body_str.split(" \u2227 "):
                    try:
                        body_pred = PredicateUtils.str_to_predicate(split)
                        body_predicates.append(body_pred)
                    except ValueError as e:
                        logger.warning(f"Error parsing body predicate '{split}': {e}")
                body = tuple(body_predicates)
                
                # Traiter la tête
                head_predicates = []
                for split in head_str.split(" \u2227 "):
                    try:
                        head_pred = PredicateUtils.str_to_predicate(split)
                        head_predicates.append(head_pred)
                    except ValueError as e:
                        logger.warning(f"Error parsing head predicate '{split}': {e}")
                head = tuple(head_predicates)
                
                # Créer et retourner l'objet TGDRule
                return TGDRule(
                    body=body,
                    head=head,
                    display=tgd_str,
                    accuracy=support,
                    confidence=confidence
                )
                
            # Corps vide, représenté par ⊤
            pattern = r"⊤\s*⇒\s*(.*?)$"
            match = re.match(pattern, tgd_str)
            
            if match:
                head_str = match.group(1)
                
                # Traiter la tête
                head_predicates = []
                for split in head_str.split(" \u2227 "):
                    try:
                        head_pred = PredicateUtils.str_to_predicate(split)
                        head_predicates.append(head_pred)
                    except ValueError as e:
                        logger.warning(f"Error parsing head predicate '{split}': {e}")
                head = tuple(head_predicates)
                
                # Créer et retourner l'objet TGDRule avec un corps vide
                return TGDRule(
                    body=tuple(),
                    head=head,
                    display=tgd_str,
                    accuracy=support,
                    confidence=confidence
                )
            
            raise ValueError(f"Invalid TGD string format: {tgd_str}")


@dataclass(frozen=True)
class HornRule(Rule):
    """
    Représente une règle de Horn.
    
    Une règle de Horn a un corps (body) et une seule tête atomique (head).
    Format: body ⇒ head
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
            json.dump(self.to_dict(), f, indent=4)
    
    def to_dict(self) -> Dict:
        """
        Convertit cette règle de Horn en dictionnaire pour sérialisation.
        
        Returns:
            Un dictionnaire représentant cette règle de Horn
        """
        return {
            "type": "HornRule",
            "body": [str(pred) for pred in self.body],
            "head": str(self.head),
            "display": self.display,
            "correct": self.correct,
            "compatible": self.compatible
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'HornRule':
        """
        Crée une instance de HornRule à partir d'un dictionnaire.
        
        Args:
            d: Dictionnaire contenant les propriétés de la règle
            
        Returns:
            Une instance de HornRule
            
        Raises:
            ValueError: Si le dictionnaire ne contient pas les champs requis
        """
        from ..rules_classes import PredicateUtils  # Import here to avoid circular imports
        
        if "body" not in d or "head" not in d:
            raise ValueError("Missing required fields in HornRule dictionary.")
            
        body = tuple(PredicateUtils.str_to_predicate(pred) for pred in d["body"])
        head = PredicateUtils.str_to_predicate(d["head"])
        
        return cls(
            body=body,
            head=head,
            display=d.get("display", ""),
            correct=d.get("correct"),
            compatible=d.get("compatible")
        )

    def __eq__(self, other):
        from ..rules_classes import PredicateUtils  # Import here to avoid circular imports
        
        list1 = list(self.body + (self.head,))
        if not isinstance(other, HornRule):
            if isinstance(other, TGDRule):
                list2 = list(other.body + other.head)
                return PredicateUtils.compare_lists(list1, list2)
            return NotImplemented
        list2 = list(other.body + (other.head,))
        return PredicateUtils.compare_lists(list1, list2)


class TGDRuleFactory:
    """
    Factory class pour créer des objets TGDRule à partir de chaînes de caractères.
    """

    @staticmethod
    def str_to_tgd(tgd_str: str, support: float, confidence: float) -> TGDRule:
        """
        Méthode déléguée à TGDRule.str_to_tgd.
        """
        return TGDRule.str_to_tgd(tgd_str, support, confidence)

    @classmethod
    def create_from_ilp_display(cls, display: str, accuracy: float) -> TGDRule:
        """
        Crée un objet TGDRule à partir d'une chaîne de format ILP.
        
        Args:
            display: Chaîne représentant une règle au format ILP
            accuracy: Valeur de précision de la règle
            
        Returns:
            Un objet TGDRule
        """
        factory = cls()
        head_str, body_str = factory._get_head_body(display)

        head_predicates = factory._create_predicates_from_relation(head_str)
        if not head_predicates:
            logging.warning(f"No head predicates extracted from: {head_str}")

        body_pattern = r"\b\w+\([^)]*\)"
        body_relations = re.findall(body_pattern, body_str)
        if not body_relations:
            logging.warning(f"No body relations extracted from: {body_str}")

        body_predicates = []
        for relation_str in body_relations:
            body_predicates.extend(factory._create_predicates_from_relation(relation_str))

        body_predicates = factory._filter_predicates(body_predicates, head_predicates)
        head_predicates = factory._filter_predicates(head_predicates, body_predicates)

        if not head_predicates:
            logging.warning("After filtering, no valid head predicates remain.")
        if not body_predicates:
            logging.warning("After filtering, no valid body predicates remain.")

        return TGDRule(
            body=tuple(body_predicates),
            head=tuple(head_predicates),
            display=display,
            accuracy=accuracy,
            confidence=-1
        )

    def _get_head_body(self, disp: str) -> Tuple[str, str]:
        """
        Parse une chaîne de caractères pour extraire la tête et le corps de la règle.
        
        Args:
            disp: Chaîne représentant une règle au format ILP
            
        Returns:
            Tuple contenant la tête et le corps de la règle
        """
        if ":-" not in disp:
            raise ValueError(f"Invalid rule display, expected ':-' in: {disp}")
        head_str, body_str = disp.split(":-")
        head_str = head_str.strip()
        body_str = body_str.strip()
        if body_str.endswith('.'):
            body_str = body_str[:-1].strip()
        return head_str, body_str

    def _create_predicates_from_relation(self, relation_str: str) -> List[Predicate]:
        """
        Convertit une chaîne de relation en liste de prédicats.
        
        Args:
            relation_str: Chaîne représentant une relation (ex: "Employe(id=X, nom=Y)")
            
        Returns:
            Liste de prédicats correspondant à la relation
        """
        sep_relation_variable = "___sep___"
        match = re.match(r"(\w+)\(([^)]*)\)", relation_str.strip())
        if not match:
            raise ValueError(f"Invalid relation string: {relation_str}")
        relation, vars_str = match.groups()
        
        # Extraire les attributs et leurs valeurs
        assignments = [var.strip() for var in vars_str.split(',')]
        predicates = []
        
        # Générer un identifiant unique pour la table (pour éviter les conflits)
        random_id = str(random.randint(1000, 9999))
        
        # Variable représentant l'instance de table
        table_var = f"t_{relation}_{random_id}"
        
        for assignment in assignments:
            # Si le format est "attribut=variable"
            if "=" in assignment:
                attribute, variable = assignment.split('=', 1)
                attribute = attribute.strip()
                variable = variable.strip()
                
                # Créer un nom de relation complet avec séparateur
                relation_name = f"{relation}{sep_relation_variable}{attribute}".lower()
                
                # Créer le prédicat
                predicates.append(
                    Predicate(
                        variable1=table_var,
                        relation=relation_name,
                        variable2=variable
                    )
                )
            else:
                # Si le format est juste une variable sans attribution explicite d'attribut
                variable = assignment.strip()
                if variable:
                    # Utiliser un nom d'attribut générique
                    attribute = "value"
                    relation_name = f"{relation}{sep_relation_variable}{attribute}".lower()
                    
                    # Créer le prédicat
                    predicates.append(
                        Predicate(
                            variable1=table_var,
                            relation=relation_name,
                            variable2=variable
                        )
                    )
        
        return predicates
    
    def _filter_predicates(self, source_predicates: List[Predicate], 
                          reference_predicates: List[Predicate]) -> List[Predicate]:
        """
        Filtre une liste de prédicats en fonction d'une liste de référence.
        
        Cette méthode peut être utilisée pour éliminer les prédicats qui ne sont pas
        pertinents pour la règle en fonction de variables partagées.
        
        Args:
            source_predicates: Liste de prédicats à filtrer
            reference_predicates: Liste de prédicats de référence
            
        Returns:
            Liste filtrée de prédicats
        """
        if not source_predicates or not reference_predicates:
            return source_predicates
            
        # Collecter toutes les variables de référence
        reference_vars = set()
        for pred in reference_predicates:
            reference_vars.add(pred.variable1)
            reference_vars.add(pred.variable2)
            
        # Filtrer les prédicats source qui ont au moins une variable en commun
        # avec les variables de référence
        filtered_predicates = []
        for pred in source_predicates:
            if pred.variable1 in reference_vars or pred.variable2 in reference_vars:
                filtered_predicates.append(pred)
                
        # Si aucun prédicat n'a de variable en commun, retourner la liste originale
        # (pour éviter de perdre toute information)
        if not filtered_predicates and source_predicates:
            return source_predicates
            
        return filtered_predicates
