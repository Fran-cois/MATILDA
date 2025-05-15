#!/usr/bin/env python3
# check_java_classes.py - Vérifier les classes Java dans les fichiers JAR

import os
import subprocess
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire des JAR
JAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "algorithms", "bins", "metanome")

def check_jar_content(jar_file, search_term=None):
    """Vérifier le contenu d'un fichier JAR pour trouver les classes Java"""
    if not os.path.exists(jar_file):
        logger.error(f"Fichier JAR non trouvé: {jar_file}")
        return []
    
    try:
        cmd = ["jar", "tf", jar_file]
        output = subprocess.check_output(cmd, universal_newlines=True)
        classes = [line.strip() for line in output.splitlines() if line.endswith(".class")]
        
        # Convertir le chemin de fichier en chemin de classe Java
        java_classes = []
        for cls in classes:
            if cls.endswith(".class"):
                java_class = cls.replace("/", ".").replace(".class", "")
                
                # Filtrer si un terme de recherche est fourni
                if search_term and search_term.lower() in java_class.lower():
                    java_classes.append(java_class)
                elif not search_term:
                    java_classes.append(java_class)
        
        return java_classes
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution de jar tf {jar_file}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du JAR {jar_file}: {e}")
        return []

def find_java_classes(search_terms):
    """Rechercher des classes Java spécifiques dans les fichiers JAR"""
    if not os.path.exists(JAR_DIR):
        logger.error(f"Répertoire JAR non trouvé: {JAR_DIR}")
        return
    
    jar_files = [f for f in os.listdir(JAR_DIR) if f.endswith('.jar')]
    if not jar_files:
        logger.error(f"Aucun fichier JAR trouvé dans {JAR_DIR}")
        return
    
    logger.info(f"Recherche des classes dans {len(jar_files)} fichiers JAR")
    
    for term in search_terms:
        logger.info(f"\n=== Recherche de classes contenant '{term}' ===")
        found = False
        
        for jar_file in jar_files:
            jar_path = os.path.join(JAR_DIR, jar_file)
            classes = check_jar_content(jar_path, term)
            
            if classes:
                found = True
                logger.info(f"Fichier JAR: {jar_file}")
                for cls in classes:
                    logger.info(f"  Classe: {cls}")
        
        if not found:
            logger.warning(f"Aucune classe contenant '{term}' trouvée dans les JAR")

def main():
    """Fonction principale"""
    # Termes de recherche pour les différents algorithmes
    search_terms = [
        "aidfd",
        "pyro",
        "dfd",
        "fdep",
        "fastfds",
        "tane"
    ]
    
    find_java_classes(search_terms)

if __name__ == "__main__":
    main()
