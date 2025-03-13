import json
import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set

from .base_rule import Rule, Predicate

@dataclass(frozen=True)
class EGDRule(Rule):
    """
    Représente une dépendance générant l'égalité (Equality-Generating Dependency).
    
    Une EGD a un corps (body) et une ou plusieurs contraintes d'égalité dans sa tête.
    Format typique: ∀ x1...xn: body(x1...xn) ⇒ xi = xj ∧ ...
    """
    body: Tuple[Predicate]  # Le corps de la règle (conjonction de prédicats)
    head: Tuple[Predicate]  # La tête de la règle (conjonction de prédicats d'égalité)
    display: str            # Représentation textuelle de la règle
    accuracy: float         # Mesure de précision/support
    support:float
    confidence: float       # Mesure de confiance
    correct: Optional[bool] = None       # Indique si la règle est correcte
    compatible: Optional[bool] = None    # Indique si la règle est compatible
    head_variables: Tuple[Tuple[str, str], ...] = None  # Paires de variables égales
    equality_vars: Tuple[str, ...] = None  # Liste de toutes les variables impliquées dans des égalités
    body_variables: Tuple[str, ...] = None  # Liste de toutes les variables impliquées dans le corps

    def __post_init__(self):
        # Initialiser head_variables si non fourni
        if self.head_variables is None:
            # Pour l'instant on suppose qu'il n'y a pas de paires d'égalité
            object.__setattr__(self, 'head_variables', ())
        
        # Initialiser equality_vars avec l'ensemble des variables impliquées dans les contraintes d'égalité
        if self.equality_vars is None:
            all_eq_vars = set()
            for var_a, var_b in self.head_variables:
                all_eq_vars.add(var_a)
                all_eq_vars.add(var_b)
            object.__setattr__(self, 'equality_vars', tuple(sorted(all_eq_vars)))
            
        # Initialiser body_variables avec l'ensemble des variables impliquées dans le corps
        if self.body_variables is None:
            all_body_vars = set()
            for pred in self.body:
                if pred.variable1 != 'unknown':
                    all_body_vars.add(pred.variable1)
                if pred.variable2 != 'unknown':
                    all_body_vars.add(pred.variable2)
            object.__setattr__(self, 'body_variables', tuple(sorted(all_body_vars)))

    def export_to_json(self, filepath: str) -> None:
        """
        Exporte cette EGD au format JSON dans le fichier spécifié.
        
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
                "compatible": self.compatible,
                "head_variables": [list(eq) for eq in self.head_variables],
                "equality_vars": list(self.equality_vars) if self.equality_vars else [],
                "body_variables": list(self.body_variables) if self.body_variables else []
            }, f, indent=4)
    
    @staticmethod
    def str_to_egd(egd_str: str, support: float, confidence: float) -> 'EGDRule':
        """
        Convertit une chaîne représentant une EGD en objet EGDRule.
        
        Args:
            egd_str: Chaîne représentant une EGD
            support: Valeur de support de l'EGD
            confidence: Valeur de confiance de l'EGD
            
        Returns:
            Un objet EGDRule
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
        """
        # Import ici pour éviter les importations circulaires
        from ..rules import PredicateUtils
        
        # Regex pour le format standard avec quantificateurs
        pattern = r"∀ (.*?): (.*?) ⇒ (.*?)$"
        match = re.match(pattern, egd_str)
        
        if match:
            variables_str, body_str, equality_str = match.groups()
            
            # Traiter le corps
            body_predicates = []
            for relation_str in body_str.split(" ∧ "):
                predicates = PredicateUtils.str_to_predicates_for_egd(relation_str)
                body_predicates.extend(predicates)
            
            # Traiter les contraintes d'égalité de la tête
            equality_constraints = []
            equality_predicates = []
            
            for eq_part in equality_str.split(" ∧ "):
                eq_cleaned = eq_part.strip()
                eq_match = re.match(r"(.*?) = (.*?)$", eq_cleaned)
                if eq_match:
                    var1, var2 = eq_match.groups()
                    var1, var2 = var1.strip(), var2.strip()
                    equality_constraints.append((var1, var2))
                    
                    # Créer un prédicat d'égalité pour la tête
                    equality_pred = Predicate(var1, "equals", var2)
                    equality_predicates.append(equality_pred)
            
            # S'il n'y a pas de contraintes d'égalité valides
            if not equality_constraints:
                eq_match = re.match(r"(.*?) = (.*?)$", equality_str)
                if eq_match:
                    var1, var2 = eq_match.groups()
                    var1, var2 = var1.strip(), var2.strip()
                    equality_constraints.append((var1, var2))
                    
                    # Créer un prédicat d'égalité pour la tête
                    equality_pred = Predicate(var1, "equals", var2)
                    equality_predicates.append(equality_pred)
                else:
                    raise ValueError(f"Format de chaîne EGD invalide (pas de contrainte d'égalité): {egd_str}")
            
            # Collecter toutes les variables d'égalité
            equality_vars = set()
            for v1, v2 in equality_constraints:
                equality_vars.add(v1)
                equality_vars.add(v2)
            
            # Créer et retourner l'objet EGDRule
            return EGDRule(
                body=tuple(body_predicates),
                head=tuple(equality_predicates),
                display=egd_str,
                accuracy=support,
                confidence=confidence,
                head_variables=tuple(equality_constraints),
                equality_vars=tuple(sorted(equality_vars))
            )
        else:
            # Format alternatif sans quantificateurs: body ⇒ x = y
            pattern = r"(.*?) ⇒ (.*?)$"
            match = re.match(pattern, egd_str)
            
            if not match:
                raise ValueError(f"Format de chaîne EGD invalide: {egd_str}")
                
            body_str, equality_str = match.groups()
            
            # Traiter le corps
            body_predicates = []
            if body_str != "⊤":  # Corps non vide
                for relation_str in body_str.split(" ∧ "):
                    predicates = PredicateUtils.str_to_predicates_for_egd(relation_str)
                    body_predicates.extend(predicates)
            
            # Traiter les contraintes d'égalité
            equality_constraints = []
            equality_predicates = []
            
            # Traiter multiples contraintes ou contrainte unique
            eq_parts = equality_str.split(" ∧ ") if " ∧ " in equality_str else [equality_str]
                
            for eq_part in eq_parts:
                eq_cleaned = eq_part.strip()
                eq_match = re.match(r"(.*?)\s*=\s*(.*?)$", eq_cleaned)
                if eq_match:
                    var1, var2 = eq_match.groups()
                    var1, var2 = var1.strip(), var2.strip()
                    equality_constraints.append((var1, var2))
                    
                    # Créer un prédicat d'égalité
                    equality_pred = Predicate(var1, "equals", var2)
                    equality_predicates.append(equality_pred)
            
            # Vérifier qu'au moins une contrainte d'égalité a été trouvée
            if not equality_constraints:
                raise ValueError(f"Aucune contrainte d'égalité valide trouvée dans: {equality_str}")
            
            # Collecter les variables d'égalité
            equality_vars = set()
            for v1, v2 in equality_constraints:
                equality_vars.add(v1)
                equality_vars.add(v2)
            
            # Créer et retourner l'EGDRule
            return EGDRule(
                body=tuple(body_predicates),
                head=tuple(equality_predicates),
                display=egd_str,
                accuracy=support,
                confidence=confidence,
                head_variables=tuple(equality_constraints),
                equality_vars=tuple(sorted(equality_vars))
            )

    def to_fd(self):
        """
        Convertit cette EGD en une dépendance fonctionnelle (FD).
        
        Une EGD de la forme body(x,y) ⇒ x = y peut être vue comme une FD 
        où les attributs utilisés pour y déterminent fonctionnellement les attributs pour x.
        
        Returns:
            Une FunctionalDependency équivalente à cette EGD
        """
        # Importer ici pour éviter les imports circulaires
        from ..rules import FunctionalDependency
        
        # Logger pour les messages d'avertissement
        logger = logging.getLogger(__name__)
        
        # Extraire le nom de la table et les attributs
        tables = set()
        var_to_attr_map = {}
        var_to_relation_map = {}
        
        # Analyser les prédicats du corps pour construire la correspondance entre variables et attributs
        for pred in self.body:
            # Mapper les variables à leurs relations pour usage ultérieur
            var_to_relation_map[pred.variable2] = pred.relation
            
            # Traiter les relations standard avec séparateur
            parts = pred.relation.split("___sep___")
            if len(parts) == 2:
                table, attribute = parts
                tables.add(table)
                var_to_attr_map[pred.variable2] = attribute
            else:
                # Pour les relations comme mcv_1, considérer la relation elle-même comme attribut
                var_to_attr_map[pred.variable2] = pred.relation
            
            # Traiter également variable1 si définie
            if pred.variable1 != 'unknown':
                var_to_attr_map[pred.variable1] = pred.relation
        
        # Déterminer la table
        table = next(iter(tables)) if tables else "unknown_table"
        
        # Déterminer les attributs déterminants et dépendants à partir des égalités de tête
        determinant_attrs = set()
        dependent_attrs = set()
        
        for var1, var2 in self.head_variables:
            # Les variables dans l'égalité doivent être associées à des attributs
            attr1 = var_to_attr_map.get(var1)
            attr2 = var_to_attr_map.get(var2)
            rel1 = var_to_relation_map.get(var1)
            rel2 = var_to_relation_map.get(var2)
            
            # Si on a des attributs directs, les utiliser
            if attr1 and attr2:
                # En général, la deuxième variable devient déterminante (ex: si x0 = x1, x1 détermine x0)
                determinant_attrs.add(attr2)
                dependent_attrs.add(attr1)
            # Si l'un des deux est manquant, utiliser les relations
            elif rel1 and rel2:
                determinant_attrs.add(rel2)
                dependent_attrs.add(rel1)
            # Si nous avons un seul attribut/relation, l'inclure dans les déterminants
            elif attr1 or rel1:
                determinant_attrs.add(attr1 or rel1)
            elif attr2 or rel2:
                determinant_attrs.add(attr2 or rel2)
        
        # S'assurer que nous avons au moins un attribut déterminant
        if not determinant_attrs:
            # Utiliser tous les attributs du corps comme déterminants par défaut
            for pred in self.body:
                determinant_attrs.add(var_to_attr_map.get(pred.variable2) or pred.relation)
        
        # Convertir en tuples triés
        determinants = tuple(sorted(determinant_attrs))
        dependents = tuple(sorted(dependent_attrs)) if dependent_attrs else tuple()
        
        # Créer la dépendance fonctionnelle
        return FunctionalDependency(
            table=table,
            determinant=determinants,
            dependent=dependents,
            correct=self.correct,
            compatible=self.compatible,
            converted_from_egd=True,
            original_egd=self.display
        )

