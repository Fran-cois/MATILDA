import os
import logging
import pandas as pd
import tempfile
import subprocess
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional

from algorithms.rule_discovery_algorithm import RuleDiscoveryAlgorithm
from utils.rules_classes.functional_dependency import FunctionalDependency
from utils.run_cmd import run_cmd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Pyro(RuleDiscoveryAlgorithm):
    """
    Implémentation d'une interface pour l'algorithme Pyro qui utilise un binaire externe
    pour la découverte de dépendances fonctionnelles.
    """
    
    def __init__(self, database):
        """
        Initialise l'interface de l'algorithme Pyro.
        
        Args:
            database: La base de données à analyser
        """
        super().__init__(database)
        self.min_support = 0.7
        self.max_lhs_size = 5  # Taille maximale des déterminants
        
        # Chemin vers le binaire Pyro
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.bin_path = current_dir / "bins" / "pyro" / "pyro"
        
        # Vérifier que le binaire existe et est exécutable
        if not os.path.isfile(self.bin_path) or not os.access(self.bin_path, os.X_OK):
            logger.warning(f"Le binaire Pyro n'a pas été trouvé ou n'est pas exécutable: {self.bin_path}")
        else:
            logger.info(f"Binaire Pyro trouvé: {self.bin_path}")
        
    def discover_rules(self, **kwargs) -> List[FunctionalDependency]:
        """
        Découvre les dépendances fonctionnelles en utilisant le binaire Pyro.
        
        Args:
            **kwargs: Paramètres optionnels:
                - min_support: Support minimum (défaut: 0.7)
                - max_lhs_size: Taille maximale des déterminants (défaut: 5)
                
        Returns:
            List[FunctionalDependency]: Liste des dépendances fonctionnelles découvertes
        """
        self.min_support = kwargs.get("min_support", self.min_support)
        self.max_lhs_size = kwargs.get("max_lhs_size", self.max_lhs_size)
        
        all_fds = []
        
        # Analyser chaque table de la base de données
        for table_name in self.database.get_table_names():
            logger.info(f"Analysing table {table_name} for functional dependencies using Pyro binary")
            
            # Charger les données de la table
            df = self.database.get_table_data(table_name)
            if df is None or df.empty:
                logger.warning(f"Table {table_name} is empty or cannot be loaded")
                continue
                
            # Exécuter Pyro sur cette table et récupérer les FDs
            table_fds = self._run_pyro_binary(table_name, df)
            all_fds.extend(table_fds)
            
        return all_fds
    
    def _run_pyro_binary(self, table_name: str, df: pd.DataFrame) -> List[FunctionalDependency]:
        """
        Exécute le binaire Pyro sur les données d'une table.
        
        Args:
            table_name: Nom de la table
            df: DataFrame contenant les données de la table
            
        Returns:
            List[FunctionalDependency]: Liste des dépendances fonctionnelles découvertes
        """
        # Vérifier à nouveau que le binaire existe
        if not os.path.isfile(self.bin_path):
            logger.error(f"Le binaire Pyro n'existe pas: {self.bin_path}")
            return []
        
        # Préparer un fichier temporaire pour les données CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_csv:
            temp_csv_path = temp_csv.name
            logger.debug(f"Enregistrement des données dans le fichier temporaire: {temp_csv_path}")
            df.to_csv(temp_csv_path, index=False)
        
        # Préparer un fichier temporaire pour les résultats
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # Construire la commande pour exécuter Pyro
            # Note: Les options peuvent varier selon les paramètres acceptés par votre binaire Pyro
            cmd = [
                str(self.bin_path),
                "-i", temp_csv_path,
                "-o", temp_output_path,
                "-s", str(self.min_support),
                "-l", str(self.max_lhs_size)
            ]
            
            logger.info(f"Exécution de la commande Pyro: {' '.join(cmd)}")
            
            # Exécuter la commande
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Erreur lors de l'exécution de Pyro: {result.stderr}")
                return []
            
            # Lire et parser les résultats
            fds = self._parse_pyro_output(table_name, temp_output_path)
            logger.info(f"Pyro a découvert {len(fds)} dépendances fonctionnelles pour la table {table_name}")
            
            return fds
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de Pyro: {e}")
            return []
        
        finally:
            # Nettoyer les fichiers temporaires
            if os.path.exists(temp_csv_path):
                os.unlink(temp_csv_path)
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
    
    def _parse_pyro_output(self, table_name: str, output_file: str) -> List[FunctionalDependency]:
        """
        Parse les résultats du binaire Pyro.
        
        Args:
            table_name: Nom de la table
            output_file: Chemin vers le fichier de sortie de Pyro
            
        Returns:
            List[FunctionalDependency]: Liste des dépendances fonctionnelles découvertes
        """
        fds = []
        
        try:
            with open(output_file, 'r') as f:
                lines = f.readlines()
                
                for line in lines:
                    # Le format exact dépend de la sortie de votre binaire Pyro
                    # Cet exemple suppose un format: "lhs1,lhs2,...->rhs (support: X.XX)"
                    line = line.strip()
                    if "->" not in line:
                        continue
                        
                    parts = line.split("->")
                    if len(parts) != 2:
                        continue
                        
                    lhs_str, rhs_with_support = parts
                    
                    # Extraction de la partie droite (RHS) et du support
                    if "(" in rhs_with_support:
                        rhs_parts = rhs_with_support.split("(")
                        rhs = rhs_parts[0].strip()
                        
                        # Extraire le support si disponible
                        support = 1.0
                        if len(rhs_parts) > 1 and "support:" in rhs_parts[1]:
                            try:
                                support_str = rhs_parts[1].split("support:")[1].strip().rstrip(")").strip()
                                support = float(support_str)
                            except (ValueError, IndexError):
                                logger.warning(f"Format de support non reconnu dans: {line}")
                    else:
                        rhs = rhs_with_support.strip()
                        support = 1.0
                    
                    # Extraction de la partie gauche (LHS)
                    lhs = [col.strip() for col in lhs_str.split(",")]
                    
                    # Créer l'objet FunctionalDependency
                    fd = FunctionalDependency(
                        table=table_name,
                        lhs=lhs,
                        rhs=rhs,
                        support=support,
                        confidence=1.0  # Les FDs ont toujours une confiance de 1.0
                    )
                    
                    fds.append(fd)
                    
        except Exception as e:
            logger.error(f"Erreur lors du parsing des résultats de Pyro: {e}")
            
        return fds
