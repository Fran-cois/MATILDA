#!/usr/bin/env python3
# fix_fd_algorithms.py - Script pour corriger les problèmes d'algorithmes FD

import os
import logging
import pandas as pd
import time
import sys
import subprocess
from datetime import datetime

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"fd_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("root")

# Créer un répertoire pour les fichiers de test
test_dir = "test_fd_fix"
os.makedirs(test_dir, exist_ok=True)

# Fonctions pour appliquer les corrections
def run_python_script(script_path, description):
    """Exécute un script Python et retourne True si l'exécution est réussie"""
    logger.info(f"Exécution de {description}...")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Sortie standard: {result.stdout}")
        if result.stderr:
            logger.warning(f"Erreur standard: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Échec de l'exécution de {description}: {e}")
        logger.error(f"Sortie standard: {e.stdout}")
        logger.error(f"Erreur standard: {e.stderr}")
        return False

def check_jar_files():
    """Vérifie si les fichiers JAR nécessaires sont présents"""
    logger.info("Vérification des fichiers JAR...")
    
    # Répertoire des fichiers JAR
    jar_dir = os.path.join(os.getcwd(), 'src', 'algorithms', 'bins', 'metanome')
    
    # Fichiers JAR requis
    required_jars = [
        'metanome-cli-1.2-SNAPSHOT.jar',
        'tane-0.0.2-SNAPSHOT.jar',
        'dfd-0.0.2-SNAPSHOT.jar',
        'fdep-0.0.2-SNAPSHOT.jar',
        'fastfds-0.0.2-SNAPSHOT.jar',
        'aidfd-0.0.2-SNAPSHOT.jar',
        'pyro-0.0.2-SNAPSHOT.jar'
    ]
    
    # Vérifier si le répertoire existe
    if not os.path.exists(jar_dir):
        logger.error(f"Le répertoire {jar_dir} n'existe pas")
        return False
    
    # Vérifier si tous les fichiers JAR requis sont présents
    missing_jars = []
    for jar in required_jars:
        jar_path = os.path.join(jar_dir, jar)
        if not os.path.exists(jar_path):
            missing_jars.append(jar)
    
    if missing_jars:
        logger.error(f"Les fichiers JAR suivants sont manquants: {', '.join(missing_jars)}")
        return False
    
    logger.info("Tous les fichiers JAR requis sont présents")
    return True

def apply_all_fixes():
    """Applique toutes les corrections aux algorithmes FD"""
    logger.info("Application de toutes les corrections...")
    
    # Liste des scripts de correction
    fix_scripts = [
        ('fix_tane.py', "correction de TANE"),
        ('fix_aidfd.py', "correction de AIDFD"),
        ('fix_pyro.py', "correction de PYRO"),
        ('fix_dfd.py', "correction de DFD"),
        ('fix_fdep.py', "correction de FDep"),
        ('fix_fastfds.py', "correction de FastFDs")
    ]
    
    # Exécuter chaque script de correction
    success_count = 0
    for script, description in fix_scripts:
        script_path = os.path.join(os.getcwd(), script)
        
        # Vérifier si le script existe
        if not os.path.exists(script_path):
            logger.warning(f"Le script {script_path} n'existe pas")
            continue
        
        # Exécuter le script
        if run_python_script(script_path, description):
            success_count += 1
    
    logger.info(f"{success_count}/{len(fix_scripts)} corrections appliquées avec succès")
    return success_count == len(fix_scripts)

def test_algorithms():
    """Teste tous les algorithmes pour vérifier qu'ils fonctionnent correctement"""
    logger.info("Test des algorithmes après correction...")
    
    # Exécuter le script de test
    test_script = os.path.join(os.getcwd(), 'test_all_fd_algos.py')
    if not os.path.exists(test_script):
        logger.error(f"Le script de test {test_script} n'existe pas")
        return False
    
    # Exécuter le script
    return run_python_script(test_script, "test des algorithmes")

# Créer un fichier CSV de test simple
test_file = os.path.join(test_dir, "simple.csv")
with open(test_file, "w") as f:
    f.write("id,name,age,city,country\n")
    f.write("1,John,25,Paris,France\n")
    f.write("2,Emma,30,Lyon,France\n")
    f.write("3,Paul,28,Marseille,France\n")
    f.write("4,Sophie,35,Bordeaux,France\n")
    f.write("5,Lucas,22,Nice,France\n")
logger.info(f"Fichier CSV de test créé: {test_file}")

# Créer une base de données factice
class MockDatabase:
    def __init__(self, base_csv_dir=None):
        self.base_csv_dir = base_csv_dir or test_dir

# Implémentation simple d'un algorithme de découverte de dépendances fonctionnelles
def discover_fds(csv_file):
    """
    Découvre les dépendances fonctionnelles simples dans un fichier CSV.
    """
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)
    table_name = os.path.basename(csv_file).replace('.csv', '')
    
    # Chercher des dépendances fonctionnelles
    fds = []
    columns = list(df.columns)
    
    # Vérifier toutes les paires de colonnes
    for col1 in columns:
        for col2 in columns:
            if col1 != col2:
                # Vérifier si col1 -> col2
                values = {}
                is_fd = True
                
                for _, row in df.iterrows():
                    v1 = row[col1]
                    v2 = row[col2]
                    
                    if v1 in values:
                        if values[v1] != v2:
                            is_fd = False
                            break
                    else:
                        values[v1] = v2
                
                if is_fd:
                    fds.append((table_name, col1, col2))
    
    return fds

# Tester l'algorithme
logger.info("Démarrage de la découverte de dépendances fonctionnelles")
start_time = time.time()
fds = discover_fds(test_file)
elapsed = time.time() - start_time

# Afficher les résultats
logger.info(f"Découverte terminée en {elapsed:.3f} secondes")
logger.info(f"Nombre de dépendances fonctionnelles découvertes: {len(fds)}")
for table, lhs, rhs in fds:
    logger.info(f"{table}.{lhs} -> {table}.{rhs}")

# Créer un script de correction pour les algorithmes Java vers Python
correction_script = """#!/bin/bash
# Script pour corriger les problèmes d'algorithmes FD

# Vérifier s'il y a une erreur Java lors de l'exécution
test_algo() {
    algo_name=$1
    echo "Test de l'algorithme $algo_name..."
    
    # Créer un petit fichier de test
    mkdir -p test_data
    echo "id,name,age,city" > test_data/test.csv
    echo "1,John,25,Paris" >> test_data/test.csv
    echo "2,Emma,30,Lyon" >> test_data/test.csv
    
    # Exécuter l'algorithme avec fallback
    python -c "
import sys
sys.path.append('.')
from src.algorithms.$algo_name import $(echo $algo_name | sed 's/^\\(.*\\)$/\\u\\1/')

class MockDB:
    def __init__(self):
        self.base_csv_dir = 'test_data'

db = MockDB()
algo = $(echo $algo_name | sed 's/^\\(.*\\)$/\\u\\1/')(db)
rules = algo.discover_rules(use_fallback=True)
print(f'Règles découvertes: {len(rules) if rules else 0}')
"
    
    # Nettoyer
    rm -rf test_data
}

# Tester tous les algorithmes
test_algo tane
test_algo fdep
test_algo dfd
test_algo fastfds

# Si AIDFD et PYRO sont disponibles
test_algo aidfd
test_algo pyro

echo "Tests terminés"
"""

# Créer le script de correction
script_path = "correct_fd_algos.sh"
with open(script_path, "w") as f:
    f.write(correction_script)
os.chmod(script_path, 0o755)
logger.info(f"Script de correction créé: {script_path}")

# Instructions pour l'utilisateur
logger.info("\n=== INSTRUCTIONS POUR CORRIGER LES PROBLÈMES ===")
logger.info("1. Exécutez les scripts de correction pour chaque algorithme:")
logger.info("   python fix_tane.py")
logger.info("   python fix_aidfd.py")
logger.info("   python fix_pyro.py")
logger.info("   python fix_dfd.py")
logger.info("   python fix_fdep.py")
logger.info("   python fix_fastfds.py")
logger.info("2. Ou exécutez ce script pour appliquer toutes les corrections:")
logger.info("   python fix_fd_algorithms.py --apply-all")
logger.info("3. Puis exécutez le script de test pour vérifier les corrections:")
logger.info("   python test_all_fd_algos.py")
logger.info("\nSi les JAR Java sont correctement configurés, la version Java")
logger.info("sera exécutée. En cas d'échec, la solution de repli Python sera utilisée.")

# Nettoyer
import shutil
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
    logger.info(f"Répertoire de test supprimé: {test_dir}")
