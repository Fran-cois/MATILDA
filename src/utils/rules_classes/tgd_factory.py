import re
import logging
from typing import List, Tuple
from .base_rule import Predicate
from .predicate_utils import PredicateUtils
from .tgd_rule import TGDRule

class TGDRuleFactory:
    """
    Une classe factory pour créer des objets TGDRule à partir de chaînes de caractères ILP.
    """

    @staticmethod
    def str_to_tgd(tgd_str: str, support: float, confidence: float) -> TGDRule:
        """
        Convertit une chaîne de caractères TGD en objet TGDRule.
        
        Args:
            tgd_str: Chaîne représentant une TGD (ex: "∀ x, y: R(x, y) ⇒ ∃z: S(x, z)")
            support: Le niveau de support de la règle
            confidence: Le niveau de confiance de la règle
            
        Returns:
            Un objet TGDRule
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
        """
        # Regular expression pattern to match the TGD format
        pattern = r"∀ (.*): (.*?) ⇒ (∃.*:)?(.*?)$"
        match = re.match(pattern, tgd_str)

        if match:
            variables_str, body_str, variables_head_str, head_str = match.groups()

            # Process the body
            body_predicates = []
            for split in body_str.split(" \u2227 "):
                # Each 'split' should represent a single predicate string
                body_pred = PredicateUtils.str_to_predicate(split)
                body_predicates.append(body_pred)
            body = tuple(body_predicates)

            # Process the head
            head_predicates = []
            for split in head_str.split(" \u2227 "):
                head_pred = PredicateUtils.str_to_predicate(split)
                head_predicates.append(head_pred)
            head = tuple(head_predicates)

            # Create and return the TGDRule object
            return TGDRule(
                body=body,
                head=head,
                display=tgd_str,
                accuracy=support,
                confidence=confidence
            )
        else:
            raise ValueError(f"Invalid TGD string format: {tgd_str}")

    @classmethod
    def create_from_ilp_display(cls, display: str, accuracy: float) -> TGDRule:
        """
        Crée un objet TGDRule à partir d'une chaîne de caractères ILP.
        
        Args:
            display: La chaîne ILP (ex: "head_rel(X, Y) :- body_rel1(X, Z), body_rel2(Z, Y).")
            accuracy: Le niveau de précision de la règle
            
        Returns:
            Un objet TGDRule
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
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
        Divise une chaîne ILP en tête et corps.
        
        Args:
            disp: La chaîne ILP
            
        Returns:
            Un tuple contenant la tête et le corps de la règle
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
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
        import random
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
