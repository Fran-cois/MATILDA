#!/usr/bin/env python3
"""
Script pour inspecter le contenu des fichiers JAR et identifier les classes principales.
Ce script liste les fichiers de classe dans chaque JAR du dossier bins/metanome.
"""

import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JAR_DIRECTORY = os.path.join('src', 'algorithms', 'bins', 'metanome')

def list_jar_contents(jar_path):
    """Liste le contenu d'un fichier JAR."""
    try:
        result = subprocess.run(['jar', 'tf', jar_path], capture_output=True, text=True, check=True)
        return result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'inspection du JAR {jar_path}: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return []

def find_main_classes(jar_files):
    """Tente de trouver les classes principales dans chaque JAR."""
    algorithm_classes = {}
    
    for jar_file in jar_files:
        jar_name = os.path.basename(jar_file)
        logger.info(f"Inspection du fichier JAR: {jar_name}")
        
        # Extraction du nom de base de l'algorithme à partir du nom du JAR
        algo_name = jar_name.split('-')[0].lower()
        if algo_name == 'fdep_algorithm':
            algo_name = 'fdep'
        elif algo_name == 'fastfds_algorithm':
            algo_name = 'fastfds'
        elif 'pyro' in algo_name:
            algo_name = 'pyro'
        
        contents = list_jar_contents(jar_file)
        
        # Filtrer les fichiers .class, convertir le chemin en nom de classe
        class_files = [f for f in contents if f.endswith('.class')]
        class_names = [c.replace('/', '.').replace('.class', '') for c in class_files]
        
        # Chercher des indices de classes principales
        potential_mains = []
        for class_name in class_names:
            # Chercher des classes qui contiennent le nom de l'algorithme ou des mots-clés comme "Main", "Algorithm"
            name_lower = class_name.lower()
            if (algo_name in name_lower or 
                "algorithm" in name_lower or 
                "main" in name_lower or 
                "runner" in name_lower or 
                "execute" in name_lower):
                potential_mains.append(class_name)
        
        # Si on a trouvé des classes potentielles, les trier par pertinence
        if potential_mains:
            # Prioriser les classes qui contiennent à la fois le nom de l'algorithme et "algorithm"
            sorted_mains = sorted(potential_mains, 
                                 key=lambda x: (
                                     "algorithm" in x.lower() and algo_name in x.lower(),
                                     "main" in x.lower(),
                                     len(x)  # Préférer les noms plus courts
                                 ), 
                                 reverse=True)
            algorithm_classes[algo_name] = sorted_mains
        else:
            # Si aucune classe potentielle n'est trouvée, inclure toutes les classes
            algorithm_classes[algo_name] = class_names
    
    return algorithm_classes

def main():
    # Obtenir la liste de tous les fichiers JAR
    jar_directory = os.path.abspath(JAR_DIRECTORY)
    if not os.path.exists(jar_directory):
        logger.error(f"Le répertoire {jar_directory} n'existe pas.")
        return
    
    jar_files = [os.path.join(jar_directory, f) for f in os.listdir(jar_directory) 
                if f.endswith('.jar')]
    
    if not jar_files:
        logger.error(f"Aucun fichier JAR trouvé dans {jar_directory}")
        return
    
    logger.info(f"Fichiers JAR trouvés: {', '.join(os.path.basename(j) for j in jar_files)}")
    
    # Analyser le contenu des JARs
    algorithm_classes = find_main_classes(jar_files)
    
    # Afficher les résultats
    logger.info("\n===== Classes principales potentielles pour chaque algorithme =====")
    for algo, classes in algorithm_classes.items():
        logger.info(f"\nAlgorithme: {algo.upper()}")
        for i, class_name in enumerate(classes[:5]):  # Limiter à 5 classes pour la lisibilité
            logger.info(f"  {i+1}. {class_name}")
        if len(classes) > 5:
            logger.info(f"  ... et {len(classes) - 5} autres classes")

if __name__ == "__main__":
    main()
