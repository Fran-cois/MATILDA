import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List, NamedTuple, Tuple, Union, Optional, Any
import re
import logging
from collections import Counter

# Import des classes dédiées
from .rules_classes.base_rule import Predicate, Rule
from .rules_classes.tgd_rule import TGDRule
from .rules_classes.egd_rule import EGDRule
from .rules_classes.horn_rule import HornRule
from .rules_classes.dc_condition import DCCondition,DenialConstraint
from .rules_classes.predicate_utils import PredicateUtils
from .rules_classes.inclusion_dependency import InclusionDependency
from .rules_classes.functional_dependency import FunctionalDependency
from .rules_classes.tgd_factory import TGDRuleFactory

from .rule_io import RuleIO



Rule = Union[
    InclusionDependency, FunctionalDependency, DenialConstraint, HornRule, TGDRule, EGDRule
]

# Ajouter la classe FunctionalDependency si elle n'existe pas déjà

# class FunctionalDependency(Rule):
#     """
#     Représente une dépendance fonctionnelle (FD) de la forme X → Y où X est un ensemble d'attributs
#     et Y est un attribut déterminé par X.
#     """
    
#     def __init__(self, table, lhs, rhs, support=0.0, confidence=1.0):
#         """
#         Initialise une dépendance fonctionnelle.
        
#         :param table: Nom de la table contenant les attributs
#         :param lhs: Liste des attributs du côté gauche (déterminants)
#         :param rhs: Attribut du côté droit (déterminé)
#         :param support: Support de la règle (ratio des tuples qui satisfont la FD)
#         :param confidence: Confiance de la règle (toujours 1.0 pour une FD valide)
#         """
#         super().__init__()
#         self.table = table
#         self.lhs = lhs if isinstance(lhs, list) else [lhs]
#         self.rhs = rhs
#         self.support = support
#         self.confidence = confidence
        
#         # Une FD est considérée comme un type de règle EGD
#         self.rule_type = "fd"
        
#         # Pour compatibilité avec l'interface Rule
#         self.body = [f"{table}({', '.join(self.lhs)})"]
#         self.head = [f"{table}({self.rhs})"]
#         self.accuracy = support
        
#         # Créer une représentation textuelle
#         self._generate_display()
    
#     def _generate_display(self):
#         """Génère une représentation textuelle de la FD."""
#         lhs_str = ', '.join(self.lhs)
#         self.display = f"{self.table}: {lhs_str} → {self.rhs}"
        
#     def __str__(self):
#         return self.display
        
#     def __repr__(self):
#         return f"FD({self.display}, support={self.support:.2f}, confidence={self.confidence:.2f})"


