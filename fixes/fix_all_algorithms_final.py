#!/usr/bin/env python3
# fix_all_algorithms_final.py - Correction globale des algorithmes Java

import os
import sys
import logging
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_algorithm_file(file_path, algorithm_name):
    """
    Corrige le fichier d'implémentation d'un algorithme Java spécifique
    
    Args:
        file_path: Le chemin du fichier à corriger
        algorithm_name: Le nom de l'algorithme (pour les messages de log)
    """
    logger.info(f"Correction du fichier {algorithm_name}: {file_path}")
    
    try:
        # Lire le contenu du fichier
        with open(file_path, 'r') as f:
            content = f.read()
            
        # 1. Correction de la commande Java principale
        # Simplifier la commande en utilisant uniquement les paramètres essentiels
        new_content = re.sub(
            r'cmd_string\s*=\s*\(\s*f"""java.*?--output file:{file_name}.*?"""\s*\)',
            f'''cmd_string = (
            f"""java -Xmx4g -cp {{jar_path}}*.jar """
            f"""de.metanome.cli.App --algorithm {{classPath}} --files {{csv_file}} """
            f"""--file-key INPUT_FILES --separator "," --header """
            f"""--output file:{{file_name}}"""
        )''',
            content,
            flags=re.DOTALL
        )
        
        # 2. Simplifier la vérification des fichiers JAR
        # Supprimer les vérifications de fichiers JAR spécifiques
        new_content = re.sub(
            r'# Vérifier l\'existence des fichiers JAR.*?continue\s*\n\s*\n',
            f'# Utiliser tous les JAR du répertoire\n',
            new_content,
            flags=re.DOTALL
        )
        
        # 3. Pour AIDFD spécifiquement, ajouter la configuration d'algorithme
        if algorithm_name.lower() == "aidfd":
            new_content = re.sub(
                r'(--output file:{file_name})"""\s*\)',
                r'\1 """'
                r'\n            f"""--algorithm-config min_support:{self.min_support},min_confidence:{self.min_confidence},max_lhs_size:{self.max_lhs_size}"""'
                r'\n        )',
                new_content
            )
        
        # 4. Correction spécifique pour PYRO (problème de dépendance MetacrateClient)
        if algorithm_name.lower() == "pyro":
            new_content = re.sub(
                r'classPath = ".*?"',
                r'classPath = "de.hpi.isg.pyro.core.ProfilingAlgorithm"',
                new_content
            )
        
        # 5. Correction spécifique pour FastFDs (problème de constructeur)
        if algorithm_name.lower() == "fastfds":
            new_content = re.sub(
                r'classPath = ".*?"',
                r'classPath = "de.metanome.algorithms.fastfds.FastFD"',
                new_content
            )
        
        # 6. Correction spécifique pour TANE (problème de columnNames null)
        if algorithm_name.lower() == "tane":
            new_content = re.sub(
                r'classPath = ".*?"',
                r'classPath = "de.metanome.algorithms.tane.TaneAlgorithm"',
                new_content
            )
            
        # Écrire le contenu modifié dans le fichier
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ Corrections appliquées à {algorithm_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de {algorithm_name}: {str(e)}")
        return False

def main():
    """Fonction principale pour corriger tous les algorithmes"""
    
    logger.info("Début de la correction des algorithmes Java")
    
    # Répertoire de base des algorithmes
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "algorithms")
    
    # Liste des algorithmes à corriger
    algorithms = {
        "aidfd": "AIDFD",
        "pyro": "Pyro",
        "dfd": "DFD",
        "fdep": "FDep",
        "fastfds": "FastFDs",
        "tane": "Tane"
    }
    
    # Corriger chaque algorithme
    for file_name, algo_name in algorithms.items():
        file_path = os.path.join(base_dir, f"{file_name}.py")
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ Fichier non trouvé pour {algo_name}: {file_path}")
            continue
            
        success = fix_algorithm_file(file_path, algo_name)
        if success:
            logger.info(f"✅ {algo_name} corrigé avec succès")
        else:
            logger.error(f"❌ Échec de la correction de {algo_name}")
    
    logger.info("Fin de la correction des algorithmes Java")
    
    # Créer un test simple pour vérifier que les JAR sont disponibles
    create_jar_test_script()

def create_jar_test_script():
    """Crée un script de test pour vérifier les JAR disponibles"""
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_jars.py")
    
    content = """#!/usr/bin/env python3
# check_jars.py - Vérifie les JAR disponibles pour les algorithmes Metanome

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_jars():
    '''Vérifie les JAR disponibles pour les algorithmes Metanome'''
    
    # Répertoire des JAR
    jar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "algorithms", "bins", "metanome")
    
    if not os.path.exists(jar_dir):
        logger.error(f"❌ Répertoire de JAR non trouvé: {jar_dir}")
        return False
    
    # Liste des fichiers JAR
    jar_files = [f for f in os.listdir(jar_dir) if f.endswith('.jar')]
    
    if not jar_files:
        logger.error("❌ Aucun fichier JAR trouvé dans le répertoire")
        return False
    
    logger.info(f"✅ {len(jar_files)} fichiers JAR trouvés:")
    for jar_file in jar_files:
        file_size = os.path.getsize(os.path.join(jar_dir, jar_file))
        logger.info(f"  - {jar_file} ({file_size} octets)")
    
    # Vérifier si les fichiers JAR essentiels sont présents
    essential_jars = [
        "metanome-cli-1.2-SNAPSHOT.jar"
    ]
    
    for jar in essential_jars:
        if jar not in jar_files:
            logger.warning(f"⚠️ JAR essentiel manquant: {jar}")
        else:
            logger.info(f"✅ JAR essentiel présent: {jar}")
    
    # Si les fichiers JAR sont présents mais vides, les télécharger
    for jar_file in jar_files:
        file_path = os.path.join(jar_dir, jar_file)
        if os.path.getsize(file_path) < 1000:  # Moins de 1 Ko, probablement un fichier vide
            logger.warning(f"⚠️ Le fichier JAR {jar_file} semble vide ou invalide")
    
    return True

if __name__ == "__main__":
    check_jars()
"""
    
    with open(script_path, 'w') as f:
        f.write(content)
    
    # Rendre le script exécutable
    os.chmod(script_path, 0o755)
    
    logger.info(f"✅ Script de test des JAR créé: {script_path}")

if __name__ == "__main__":
    main()
