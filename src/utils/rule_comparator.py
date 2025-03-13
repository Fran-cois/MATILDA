import logging
from typing import List, Dict, Tuple, Set, Any, Optional, Union

from utils.rules import FunctionalDependency, Rule, EGDRule, TGDRule

class RuleComparator:
    """
    Classe utilitaire pour comparer différents types de règles de dépendance:
    - Dépendances fonctionnelles (FDs)
    - Dépendances génératrices d'égalité (EGDs)
    - Dépendances génératrices de tuples (TGDs)
    
    Cette classe permet d'identifier les relations entre les règles telles que:
    - Équivalence (deux règles expriment la même contrainte)
    - Implication (une règle implique l'autre)
    - Contradiction (deux règles ne peuvent pas être satisfaites simultanément)
    - Redondance (une règle est couverte par d'autres règles)
    """
    
    def __init__(self, logger=None):
        """
        Initialise le comparateur de règles.
        
        :param logger: Logger optionnel pour les messages de débogage et d'information
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def are_equivalent(self, rule1: Rule, rule2: Rule) -> bool:
        """
        Vérifie si deux règles sont équivalentes (expriment la même contrainte).
        
        :param rule1: Première règle à comparer
        :param rule2: Deuxième règle à comparer
        :return: True si les règles sont équivalentes, False sinon
        """
        # Si les deux règles sont du même type, utiliser une comparaison spécifique au type
        if isinstance(rule1, FunctionalDependency) and isinstance(rule2, FunctionalDependency):
            return self._are_fds_equivalent(rule1, rule2)
        elif isinstance(rule1, EGDRule) and isinstance(rule2, EGDRule):
            return self._are_egds_equivalent(rule1, rule2)
        elif isinstance(rule1, TGDRule) and isinstance(rule2, TGDRule):
            return self._are_tgds_equivalent(rule1, rule2)
        
        # Si les règles sont de types différents, vérifier si elles peuvent être équivalentes
        if isinstance(rule1, FunctionalDependency) and isinstance(rule2, EGDRule):
            return self._is_fd_equivalent_to_egd(rule1, rule2)
        elif isinstance(rule1, EGDRule) and isinstance(rule2, FunctionalDependency):
            return self._is_fd_equivalent_to_egd(rule2, rule1)
        
        # Par défaut, des règles de types différents ne sont pas considérées comme équivalentes
        return False
    
    def _are_fds_equivalent(self, fd1: FunctionalDependency, fd2: FunctionalDependency) -> bool:
        """
        Vérifie si deux dépendances fonctionnelles sont équivalentes.
        Deux FDs sont équivalentes si elles portent sur la même table
        et ont les mêmes ensembles d'attributs déterminants et dépendants.
        
        :param fd1: Première dépendance fonctionnelle
        :param fd2: Deuxième dépendance fonctionnelle
        :return: True si les FDs sont équivalentes, False sinon
        """
        try:
            # Vérifier si les FDs concernent la même table
            if hasattr(fd1, 'table_dependant') and hasattr(fd2, 'table_dependant'):
                same_table = fd1.table_dependant == fd2.table_dependant
            else:
                # Cas où la structure est différente, essayer d'autres attributs
                table1 = getattr(fd1, 'table', None)
                table2 = getattr(fd2, 'table', None)
                same_table = table1 == table2
            
            # Vérifier si les ensembles d'attributs sont les mêmes
            if hasattr(fd1, 'columns_dependant') and hasattr(fd2, 'columns_dependant'):
                same_determinant = set(fd1.columns_dependant) == set(fd2.columns_dependant)
                same_dependent = set(fd1.columns_referenced) == set(fd2.columns_referenced)
            else:
                # Utiliser les noms d'attributs corrects de la classe FunctionalDependency
                determinant1 = getattr(fd1, 'determinant', ())
                determinant2 = getattr(fd2, 'determinant', ())
                dependent1 = getattr(fd1, 'dependent', ())
                dependent2 = getattr(fd2, 'dependent', ())
                
                # Comparer les ensembles d'attributs
                same_determinant = set(determinant1) == set(determinant2)
                same_dependent = set(dependent1) == set(dependent2)
            
            return same_table and same_determinant and same_dependent
            
        except (AttributeError, TypeError) as e:
            self.logger.warning(f"Erreur lors de la comparaison de FDs: {e}")
            return False
    
    def _are_egds_equivalent(self, egd1: EGDRule, egd2: EGDRule) -> bool:
        """
        Vérifie si deux EGDs sont équivalentes.
        Deux EGDs sont équivalentes si leurs conditions (body) et leurs égalités sont les mêmes.
        
        :param egd1: Première dépendance génératrice d'égalité
        :param egd2: Deuxième dépendance génératrice d'égalité
        :return: True si les EGDs sont équivalentes, False sinon
        """
        try:
            # Vérifier si les corps des règles sont équivalents (mêmes prédicats)
            body1_preds = sorted(str(p) for p in egd1.body)
            body2_preds = sorted(str(p) for p in egd2.body)
            same_body = body1_preds == body2_preds
            
            # Vérifier si les contraintes d'égalité sont les mêmes en utilisant head_variables
            # Créer des ensembles de paires pour une comparaison indépendante de l'ordre
            eq_vars1 = {frozenset((a, b)) for a, b in egd1.head_variables}
            eq_vars2 = {frozenset((a, b)) for a, b in egd2.head_variables}
            same_equality = eq_vars1 == eq_vars2
            
            return same_body and same_equality
            
        except (AttributeError, TypeError) as e:
            self.logger.warning(f"Erreur lors de la comparaison d'EGDs: {e}")
            return False
    
    def _are_tgds_equivalent(self, tgd1: TGDRule, tgd2: TGDRule) -> bool:
        """
        Vérifie si deux TGDs sont équivalentes.
        
        :param tgd1: Première dépendance génératrice de tuples
        :param tgd2: Deuxième dépendance génératrice de tuples
        :return: True si les TGDs sont équivalentes, False sinon
        """
        try:
            # Vérifier si les corps des règles sont équivalents
            body1_preds = sorted(str(p) for p in tgd1.body)
            body2_preds = sorted(str(p) for p in tgd2.body)
            same_body = body1_preds == body2_preds
            
            # Vérifier si les têtes des règles sont équivalentes
            head1_preds = sorted(str(p) for p in tgd1.head)
            head2_preds = sorted(str(p) for p in tgd2.head)
            same_head = head1_preds == head2_preds
            
            return same_body and same_head
            
        except (AttributeError, TypeError) as e:
            self.logger.warning(f"Erreur lors de la comparaison de TGDs: {e}")
            return False
    
    def _is_fd_equivalent_to_egd(self, fd: FunctionalDependency, egd: EGDRule) -> bool:
        """
        Vérifie si une dépendance fonctionnelle est équivalente à une EGD.
        Une FD peut être exprimée comme une EGD spéciale.
        
        :param fd: Dépendance fonctionnelle
        :param egd: Dépendance génératrice d'égalité
        :return: True si la FD est équivalente à l'EGD, False sinon
        """
        # Cette fonction nécessite une analyse sémantique des règles
        # qui est complexe et dépend fortement de la structure spécifique des règles
        # Implémentation simplifiée qui considère quelques cas d'équivalence possibles
        
        try:
            # Une FD X → Y peut être exprimée comme une EGD ∀x,y,z (R(x,y,z) ∧ R(x,y',z') → y=y')
            # où x représente les attributs déterminants et y les attributs dépendants
            
            # Pour l'instant, retournons False car cette analyse précise nécessite
            # une connaissance détaillée de la structure des EGDs et FDs dans le système
            return False
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la comparaison FD-EGD: {e}")
            return False

    def implicitly_contains(self, rules: List[Rule], rule: Rule) -> bool:
        """
        Vérifie si une règle est implicitement contenue (ou impliquée) par un ensemble de règles.
        
        :param rules: Liste de règles à vérifier
        :param rule: Règle dont on veut savoir si elle est impliquée
        :return: True si la règle est impliquée, False sinon
        """
        # Vérification directe d'équivalence avec une règle existante
        for existing_rule in rules:
            if self.are_equivalent(existing_rule, rule):
                return True
        
        # Vérification d'implication par un ensemble de règles
        # (cette vérification dépend fortement du type de règles et nécessite 
        # un raisonnement logique qui n'est pas implémenté ici)
        return False
    
    def find_redundant_rules(self, rules: List[Rule]) -> List[Rule]:
        """
        Identifie les règles redondantes dans une liste de règles.
        Une règle est redondante si elle est impliquée par d'autres règles.
        
        :param rules: Liste de règles à analyser
        :return: Liste des règles redondantes
        """
        redundant_rules = []
        
        for i, rule in enumerate(rules):
            # Créer une liste de toutes les règles sauf celle à vérifier
            other_rules = rules[:i] + rules[i+1:]
            
            # Vérifier si la règle est impliquée par les autres
            if self.implicitly_contains(other_rules, rule):
                redundant_rules.append(rule)
        
        return redundant_rules
    
    def convert_fd_to_egd(self, fd: FunctionalDependency) -> Optional[EGDRule]:
        """
        Convertit une dépendance fonctionnelle en dépendance génératrice d'égalité équivalente.
        
        :param fd: La dépendance fonctionnelle à convertir
        :return: Une EGD équivalente ou None si la conversion n'est pas possible
        """
        # Cette conversion nécessiterait une connaissance détaillée du modèle de données
        # et de la structure spécifique des règles EGD dans le système
        self.logger.warning("Conversion de FD en EGD non implémentée")
        return None
    
    def convert_egd_to_fd(self, egd: EGDRule) -> Optional[FunctionalDependency]:
        """
        Tente de convertir une EGD en dépendance fonctionnelle équivalente, si possible.
        
        :param egd: La dépendance génératrice d'égalité à convertir
        :return: Une FD équivalente ou None si la conversion n'est pas possible
        """
        # Cette conversion n'est possible que pour certaines EGD spécifiques
        self.logger.warning("Conversion d'EGD en FD non implémentée")
        return None

    def sort_rules_by_complexity(self, rules: List[Rule]) -> List[Rule]:
        """
        Trie les règles par ordre croissant de complexité.
        
        :param rules: Liste des règles à trier
        :return: Liste des règles triées
        """
        def rule_complexity(rule: Rule) -> int:
            """Calcule un score de complexité pour une règle"""
            if isinstance(rule, FunctionalDependency):
                try:
                    # Pour une FD, la complexité est liée au nombre d'attributs impliqués
                    det_cols = getattr(rule, 'columns_dependant', None) or getattr(rule, 'determinant_columns', [])
                    dep_cols = getattr(rule, 'columns_referenced', None) or getattr(rule, 'dependent_columns', [])
                    return len(det_cols) + len(dep_cols)
                except (AttributeError, TypeError):
                    return 1
            elif isinstance(rule, (EGDRule, TGDRule)):
                # Pour une EGD/TGD, la complexité est liée au nombre de prédicats et variables
                body_size = len(getattr(rule, 'body', []))
                head_size = len(getattr(rule, 'head', []))
                return body_size + head_size
            return 0
            
        return sorted(rules, key=rule_complexity)
    
    def group_rules_by_type(self, rules: List[Rule]) -> Dict[str, List[Rule]]:
        """
        Groupe les règles par type (FD, EGD, TGD).
        
        :param rules: Liste de règles à grouper
        :return: Dictionnaire avec les types comme clés et les listes de règles comme valeurs
        """
        groups = {
            "fd": [],
            "egd": [],
            "tgd": [],
            "other": []
        }
        
        for rule in rules:
            if isinstance(rule, FunctionalDependency):
                groups["fd"].append(rule)
            elif isinstance(rule, EGDRule):
                groups["egd"].append(rule)
            elif isinstance(rule, TGDRule):
                groups["tgd"].append(rule)
            else:
                groups["other"].append(rule)
                
        return groups
    
    def compare_rule_sets(self, rules1: List[Rule], rules2: List[Rule]) -> Dict[str, Any]:
        """
        Compare deux ensembles de règles et retourne des statistiques sur leurs similitudes et différences.
        
        :param rules1: Premier ensemble de règles
        :param rules2: Deuxième ensemble de règles
        :return: Dictionnaire avec des statistiques de comparaison
        """
        results = {
            "total_rules_set1": len(rules1),
            "total_rules_set2": len(rules2),
            "common_rules": 0,
            "unique_to_set1": 0,
            "unique_to_set2": 0,
            "rule_types_set1": {},
            "rule_types_set2": {}
        }
        
        # Compter les types de règles dans chaque ensemble
        grouped1 = self.group_rules_by_type(rules1)
        grouped2 = self.group_rules_by_type(rules2)
        
        for rule_type, rules in grouped1.items():
            results["rule_types_set1"][rule_type] = len(rules)
            
        for rule_type, rules in grouped2.items():
            results["rule_types_set2"][rule_type] = len(rules)
        
        # Identifier les règles communes et uniques
        common_rules = []
        unique_to_set1 = []
        
        for rule1 in rules1:
            found_equivalent = False
            for rule2 in rules2:
                if self.are_equivalent(rule1, rule2):
                    common_rules.append((rule1, rule2))
                    found_equivalent = True
                    break
            if not found_equivalent:
                unique_to_set1.append(rule1)
        
        unique_to_set2 = [rule2 for rule2 in rules2 if not any(self.are_equivalent(rule1, rule2) for rule1 in rules1)]
        
        results["common_rules"] = len(common_rules)
        results["unique_to_set1"] = len(unique_to_set1)
        results["unique_to_set2"] = len(unique_to_set2)
        
        return results
