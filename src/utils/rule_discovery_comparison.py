import time
import pandas as pd
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns

from algorithms.rule_discovery_algorithm import RuleDiscoveryAlgorithm
from algorithms.aidfd import AIDFD
from algorithms.pyro import Pyro
from algorithms.amie3 import Amie3
# Importer d'autres algorithmes selon les besoins

class RuleDiscoveryComparison:
    """
    Classe pour comparer différents algorithmes de découverte de règles.
    """
    
    def __init__(self, database):
        """
        Initialise la comparaison avec une base de données.
        
        Args:
            database: La base de données à analyser
        """
        self.database = database
        self.algorithms = {}
        self.results = {}
        
        # Initialiser les algorithmes de découverte de règles
        self._init_algorithms()
    
    def _init_algorithms(self):
        """Initialise les différents algorithmes à comparer."""
        # Algorithmes de découverte de dépendances fonctionnelles
        self.algorithms["AIDFD"] = AIDFD(self.database)
        self.algorithms["Pyro"] = Pyro(self.database)
        
        # Autres algorithmes
        self.algorithms["AMIE3"] = Amie3(self.database)
        # Ajouter d'autres algorithmes ici...
    
    def run_comparison(self, **kwargs):
        """
        Exécute la comparaison entre les différents algorithmes.
        
        Args:
            **kwargs: Paramètres supplémentaires pour la découverte
        """
        for name, algorithm in self.algorithms.items():
            print(f"Running algorithm: {name}")
            start_time = time.time()
            rules = algorithm.discover_rules(**kwargs)
            end_time = time.time()
            
            self.results[name] = {
                "rules": rules,
                "count": len(rules),
                "time": end_time - start_time
            }
            
            print(f"  Found {len(rules)} rules in {end_time - start_time:.2f} seconds")
    
    def get_results_summary(self) -> pd.DataFrame:
        """
        Retourne un résumé des résultats de la comparaison.
        
        Returns:
            pd.DataFrame: Tableau récapitulatif des résultats
        """
        data = []
        for name, result in self.results.items():
            data.append({
                "Algorithm": name,
                "Rule Count": result["count"],
                "Execution Time (s)": result["time"],
                "Rules/Second": result["count"] / result["time"] if result["time"] > 0 else float('inf')
            })
        
        return pd.DataFrame(data)
    
    def plot_comparison(self, save_path=None):
        """
        Génère des graphiques de comparaison.
        
        Args:
            save_path: Chemin où sauvegarder les graphiques (optionnel)
        """
        summary = self.get_results_summary()
        
        # Configurer le style des graphiques
        sns.set(style="whitegrid")
        
        # Créer une figure avec deux sous-graphiques
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Graphique du nombre de règles
        sns.barplot(x="Algorithm", y="Rule Count", data=summary, ax=ax1)
        ax1.set_title("Number of Rules Discovered")
        ax1.set_ylabel("Count")
        ax1.set_xlabel("")
        
        # Graphique du temps d'exécution
        sns.barplot(x="Algorithm", y="Execution Time (s)", data=summary, ax=ax2)
        ax2.set_title("Execution Time")
        ax2.set_ylabel("Time (seconds)")
        ax2.set_xlabel("")
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        
        plt.show()
    
    def get_rule_type_distribution(self) -> pd.DataFrame:
        """
        Analyse la distribution des types de règles découvertes.
        
        Returns:
            pd.DataFrame: Distribution des types de règles par algorithme
        """
        data = []
        
        for name, result in self.results.items():
            # Compter les types de règles
            rule_types = {}
            for rule in result["rules"]:
                rule_type = getattr(rule, "rule_type", type(rule).__name__)
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
            
            # Ajouter à la liste des données
            for rule_type, count in rule_types.items():
                data.append({
                    "Algorithm": name,
                    "Rule Type": rule_type,
                    "Count": count
                })
        
        return pd.DataFrame(data)
    
    def plot_rule_type_distribution(self, save_path=None):
        """
        Génère un graphique de la distribution des types de règles.
        
        Args:
            save_path: Chemin où sauvegarder le graphique (optionnel)
        """
        distribution = self.get_rule_type_distribution()
        
        plt.figure(figsize=(12, 8))
        sns.barplot(x="Algorithm", y="Count", hue="Rule Type", data=distribution)
        plt.title("Distribution of Rule Types by Algorithm")
        plt.ylabel("Count")
        plt.xlabel("")
        plt.legend(title="Rule Type")
        
        if save_path:
            plt.savefig(save_path)
        
        plt.show()
