from typing import List, Dict
import re
from .base_rule import Predicate

class PredicateUtils:
    """
    Classe utilitaire pour manipuler et comparer des prédicats.
    """
    
    @staticmethod
    def sort_and_rename_variables(lst: List[Predicate], skip: int = 0) -> List[Predicate]:
        """
        Trie et renomme les variables dans une liste de prédicats.
        
        Args:
            lst: Liste de prédicats à traiter
            skip: Nombre d'éléments à sauter lors du tri
            
        Returns:
            Liste de prédicats avec variables renommées
        """
        try:
            lst.sort(key=lambda x: x.relation)
        except Exception:
            return lst

        variable_mapping = {}
        counter = 0

        for i in range(len(lst)):
            index_lst = i + skip
            if index_lst >= len(lst):
                index_lst = index_lst - len(lst)
            predicate = lst[index_lst]

            if predicate.variable1 not in variable_mapping:
                variable_mapping[predicate.variable1] = f"x_{counter}"
                counter += 1
            if predicate.variable2 not in variable_mapping:
                variable_mapping[predicate.variable2] = f"x_{counter}"
                counter += 1

            lst[index_lst] = Predicate(
                variable_mapping[predicate.variable1],
                predicate.relation,
                variable_mapping[predicate.variable2],
            )
        return lst

    @staticmethod
    def compare_lists(list1: List[Predicate], list2: List[Predicate]) -> bool:
        """
        Compare deux listes de prédicats en tenant compte des équivalences de variables.
        
        Args:
            list1: Première liste de prédicats
            list2: Deuxième liste de prédicats
            
        Returns:
            True si les listes sont équivalentes, False sinon
        """
        list1 = PredicateUtils.sort_and_rename_variables(list1)
        for skip in range(len(list1)):
            list2 = PredicateUtils.sort_and_rename_variables(list2, skip)
            if len(list1) != len(list2):
                return False

            links1 = [(p.variable1, p.relation, p.variable2) for p in list1]
            links2 = [(p.variable1, p.relation, p.variable2) for p in list2]

            if links1 == links2:
                return True

        # Complex comparison logic for variable equivalences
        for skip in range(len(list1)):
            list2 = PredicateUtils.sort_and_rename_variables(list2, skip)
            links1 = [(p.variable1, p.relation, p.variable2) for p in list1]
            links2 = [(p.variable1, p.relation, p.variable2) for p in list2]
            links1.sort(key=lambda x: x[1])
            links2.sort(key=lambda x: x[1])
            ok_links1 = []
            equivalence = {}
            for pred1 in links1:
                for pred2 in links2:
                    if pred1 == pred2:
                        ok_links1.append(pred1)
                        equivalence[pred1[2]] = pred1[0]
                    else:
                        if pred1[1] == pred2[1] and pred1[2] == pred2[2]:
                            if equivalence.get(pred1[0]) == pred2[0]:
                                ok_links1.append(pred1)

            if ok_links1 == links1 or list(set(ok_links1)) == links1:
                return True

            ok_links2 = []
            equivalence = {}
            for pred2 in links2:
                for pred1 in links1:
                    if pred2 == pred1:
                        ok_links2.append(pred2)
                        equivalence[pred1[2]] = pred1[0]
                    else:
                        if pred2[1] == pred1[1] and pred2[2] == pred1[2]:
                            if equivalence.get(pred2[0]) == pred1[0]:
                                ok_links2.append(pred2)

            if ok_links2 == links2 or list(set(ok_links2)) == links2:
                return True
        return False

    @staticmethod
    def str_to_predicate(s: str) -> Predicate:
        """
        Convertit une chaîne de caractères en objet Predicate.
        
        Args:
            s: Chaîne représentant un prédicat
            
        Returns:
            Objet Predicate correspondant
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
        """
        s = s.strip()

        # 1. Try the old format: Predicate(variable1='x', relation='relates_to', variable2='y')
        match = re.match(
            r"Predicate\(variable1='(.*?)', relation='(.*?)', variable2='(.*?)'\)", s
        )
        if match:
            variable1, relation, variable2 = match.groups()
            return Predicate(variable1, relation, variable2)

        # 2. Try the new format with argument names: relates_to(arg1=x, arg2=y)
        match = re.match(r"^([A-Za-z0-9_]+)\(([^=]+)=([^)]*)\)$", s)
        if match:
            relation, variable1, variable2 = match.groups()
            return Predicate(variable1.strip(), relation.strip(), variable2.strip())

        # 3. Try the alternate new format: rel1(x, y)
        match = re.match(r"^([A-Za-z0-9_]+)\(([^,]+),\s*([^)]+)\)$", s)
        if match:
            relation, variable1, variable2 = match.groups()
            return Predicate(variable1.strip(), relation.strip(), variable2.strip())

        raise ValueError(f"Invalid Predicate string: {s}")

    @staticmethod
    def str_to_predicates_for_egd(s: str) -> List[Predicate]:
        """
        Convertit une chaîne de caractères représentant des prédicats d'une règle EGD en liste d'objets Predicate.
        
        Args:
            s: Chaîne représentant un ensemble de prédicats
            
        Returns:
            Liste d'objets Predicate
            
        Raises:
            ValueError: Si le format de la chaîne est invalide
        """
        result = []
        s = s.strip()
        
        # Vérifier et corriger les parenthèses manquantes
        open_parens = s.count('(')
        close_parens = s.count(')')
        if open_parens > close_parens:
            # Ajouter les parenthèses fermantes manquantes
            s += ')' * (open_parens - close_parens)
        
        # Format avec arg1 et arg2 dans n'importe quel ordre
        special_predicates_normal = re.findall(r'([a-zA-Z0-9_]+)\s*\(\s*arg1\s*=\s*([a-zA-Z0-9_]+)\s*,?\s*arg2\s*=\s*([a-zA-Z0-9_]+)\s*\)', s)
        for relation, var1, var2 in special_predicates_normal:
            result.append(Predicate(var1.strip(), relation.strip(), var2.strip()))
            # Retirer ce prédicat de la chaîne pour éviter qu'il soit traité deux fois
            s = s.replace(f"{relation}(arg1={var1}, arg2={var2})", "", 1)
            s = s.replace(f"{relation}(arg1={var1},arg2={var2})", "", 1)
        
        # Format avec arg2 avant arg1
        special_predicates_inverted = re.findall(r'([a-zA-Z0-9_]+)\s*\(\s*arg2\s*=\s*([a-zA-Z0-9_]+)\s*,?\s*arg1\s*=\s*([a-zA-Z0-9_]+)\s*\)', s)
        for relation, var2, var1 in special_predicates_inverted:
            result.append(Predicate(var1.strip(), relation.strip(), var2.strip()))
            # Retirer ce prédicat de la chaîne pour éviter qu'il soit traité deux fois
            s = s.replace(f"{relation}(arg2={var2}, arg1={var1})", "", 1)
            s = s.replace(f"{relation}(arg2={var2},arg1={var1})", "", 1)
        
        # Format spécial partiel: relation(arg1=x1)
        special_partial_arg1 = re.findall(r'([a-zA-Z0-9_]+)\s*\(\s*arg1\s*=\s*([a-zA-Z0-9_]+)\s*\)', s)
        for relation, var1 in special_partial_arg1:
            result.append(Predicate(var1.strip(), relation.strip(), "unknown"))
            s = s.replace(f"{relation}(arg1={var1})", "", 1)
        
        # Format spécial partiel: relation(arg2=x2)
        special_partial_arg2 = re.findall(r'([a-zA-Z0-9_]+)\s*\(\s*arg2\s*=\s*([a-zA-Z0-9_]+)\s*\)', s)
        for relation, var2 in special_partial_arg2:
            result.append(Predicate("unknown", relation.strip(), var2.strip()))
            s = s.replace(f"{relation}(arg2={var2})", "", 1)
        
        # Pour les prédicats restants, essayer la méthode standard
        # Séparer les prédicats (ils peuvent être séparés par virgules ou espaces)
        remaining = s.strip()
        if remaining:
            # Amélioration de la séparation des prédicats
            predicates_str = re.split(r'(?<=[)])\s*(?:∧|,|\s)\s*|\s+(?=[a-zA-Z0-9_]+\()', remaining)
            
            for pred_str in predicates_str:
                if pred_str.strip():  # Ignorer les chaînes vides
                    try:
                        result.append(PredicateUtils.str_to_predicate(pred_str.strip()))
                    except ValueError as e:
                        # Si nous ne pouvons pas parser ce prédicat, essayons d'extraire manuellement
                        manual_match = re.match(r'([a-zA-Z0-9_]+)\s*\(\s*([a-zA-Z0-9_]+)\s*(?:,\s*([a-zA-Z0-9_]+)\s*)?\)?', pred_str.strip())
                        if manual_match:
                            relation, var1, var2 = manual_match.groups()
                            var2 = var2 if var2 else "unknown"
                            result.append(Predicate(var1.strip(), relation.strip(), var2.strip()))
                        else:
                            raise ValueError(f"Invalid predicate in EGD rule: {pred_str}. Error: {str(e)}")
        
        return result
