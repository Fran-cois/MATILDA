#!/usr/bin/env python3
# fix_all_algorithms.py - Script pour corriger tous les algorithmes Java Metanome

import os
import re
import logging
import shutil
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chemin des fichiers à corriger
ALGORITHMS_DIR = Path(__file__).parent / "src" / "algorithms"
METANOME_BINS_DIR = ALGORITHMS_DIR / "bins" / "metanome"

# Mappings des chemins de classe corrects pour chaque algorithme
CLASS_PATHS = {
    "aidfd.py": "de.metanome.algorithms.aidfd.AIDFD",
    "dfd.py": "de.metanome.algorithms.dfd.DFD",
    "fdep.py": "de.metanome.algorithms.fdep.FdepAlgorithm",
    "fastfds.py": "de.metanome.algorithms.fastfds.FastFD",
    "pyro.py": "de.hpi.isg.pyro.algorithm.ProfilingAlgorithm",  # Confirmé par l'inspection des JAR
    "tane.py": "de.metanome.algorithms.tane.TaneAlgorithm"
}

# Fichiers JAR corrompus à supprimer
CORRUPTED_JARS = [
    "mdms-tools-0.0.3.jar",
    "mdms-metanome-client-0.0.3.jar",
    "mdms-model-0.0.3.jar"
]

def fix_class_paths():
    """Corriger les chemins de classe Java dans les fichiers Python des algorithmes"""
    for file_name, correct_class_path in CLASS_PATHS.items():
        file_path = ALGORITHMS_DIR / file_name
        if not file_path.exists():
            logger.warning(f"Fichier {file_path} non trouvé")
            continue
        
        logger.info(f"Correction du fichier {file_path}")
        
        # Lire le contenu du fichier
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Rechercher le motif classPath = "..."
        class_path_pattern = r'classPath\s*=\s*"([^"]+)"'
        match = re.search(class_path_pattern, content)
        
        if match:
            current_class_path = match.group(1)
            
            if current_class_path != correct_class_path:
                logger.info(f"Remplacement de '{current_class_path}' par '{correct_class_path}'")
                
                # Remplacer le chemin de classe
                new_content = re.sub(
                    class_path_pattern, 
                    f'classPath = "{correct_class_path}"', 
                    content
                )
                
                # Écrire le contenu modifié
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"✅ Chemin de classe corrigé dans {file_path}")
            else:
                logger.info(f"✅ Le chemin de classe est déjà correct dans {file_path}")
        else:
            logger.warning(f"❌ Motif 'classPath =' non trouvé dans {file_path}")

def fix_indentation_issues():
    """Corriger les problèmes d'indentation dans les fichiers"""
    # Correction spécifique pour FDEP
    fdep_path = ALGORITHMS_DIR / "fdep.py"
    if fdep_path.exists():
        logger.info(f"Vérification de l'indentation dans {fdep_path}")
        
        with open(fdep_path, 'r') as f:
            content = f.read()
        
        # Rechercher le motif d'indentation incorrect et le corriger
        indentation_pattern = r'file_name = f\'.*?\'\s+# Ajouter tous les JAR du répertoire dans le classpath\s+(\w+)'
        if re.search(indentation_pattern, content, re.DOTALL):
            logger.info("Correction de l'indentation dans fdep.py")
            
            # Corriger l'indentation en ajoutant 4 espaces
            new_content = re.sub(
                indentation_pattern,
                r'file_name = f\'.*?\'\n            # Ajouter tous les JAR du répertoire dans le classpath\n            \1',
                content,
                flags=re.DOTALL
            )
            
            # Écrire le contenu modifié
            with open(fdep_path, 'w') as f:
                f.write(new_content)
            
            logger.info("✅ Indentation corrigée dans fdep.py")
        else:
            logger.info("✅ L'indentation semble correcte dans fdep.py")

def remove_corrupted_jars():
    """Supprimer les fichiers JAR corrompus"""
    for jar_file in CORRUPTED_JARS:
        jar_path = METANOME_BINS_DIR / jar_file
        if jar_path.exists():
            logger.info(f"Suppression du fichier JAR corrompu: {jar_path}")
            try:
                # Créer un répertoire de sauvegarde pour les JAR corrompus
                backup_dir = METANOME_BINS_DIR / "corrupted_backup"
                backup_dir.mkdir(exist_ok=True)
                
                # Déplacer le fichier au lieu de le supprimer
                shutil.move(str(jar_path), str(backup_dir / jar_file))
                logger.info(f"✅ JAR corrompu déplacé vers {backup_dir / jar_file}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la sauvegarde/suppression de {jar_path}: {e}")
        else:
            logger.info(f"Le fichier JAR {jar_path} n'existe pas")

def create_test_script():
    """Créer un script pour tester tous les algorithmes corrigés"""
    test_script_path = Path(__file__).parent / "test_algorithms_fixed.py"
    
    test_script_content = '''#!/usr/bin/env python3
# test_algorithms_fixed.py - Test des algorithmes de découverte de dépendances fonctionnelles corrigés

import os
import sys
import logging
from datetime import datetime
import pandas as pd
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules nécessaires
from MATILDA.src.database.database import Database
from MATILDA.src.algorithms.aidfd import AIDFD
from MATILDA.src.algorithms.dfd import DFD
from MATILDA.src.algorithms.fdep import FDEP
from MATILDA.src.algorithms.fastfds import FastFDs
from MATILDA.src.algorithms.pyro import Pyro
from MATILDA.src.algorithms.tane import Tane

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def create_test_data():
    """Créer un petit jeu de données de test"""'''
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Créer un petit CSV avec des données simples
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['Paris', 'Lyon', 'Paris', 'Marseille', 'Lyon'],
        'salary': [50000, 60000, 55000, 65000, 70000]
    }
    
    df = pd.DataFrame(data)
    csv_path = test_dir / "employees.csv"
    df.to_csv(csv_path, index=False)
    
    logger.info(f"Données de test créées: {csv_path}")
    return test_dir

def test_all_algorithms():
    """Tester tous les algorithmes de découverte de dépendances fonctionnelles"""
    # Créer les données de test
    test_data_dir = create_test_data()
    
    # Créer une base de données avec les données de test
    db = Database(name="test_db", directory=str(test_data_dir))
    
    # Liste des algorithmes à tester
    algorithms = [
        ("AIDFD", AIDFD(db)),
        ("DFD", DFD(db)),
        ("FDEP", FDEP(db)),
        ("FastFDs", FastFDs(db)),
        ("Pyro", Pyro(db)),
        ("Tane", Tane(db))
    ]
    
    results = {}
    
    # Tester chaque algorithme
    for name, algo in algorithms:
        logger.info(f"Test de l'algorithme {name}")
        
        try:
            start_time = datetime.now()
            rules = algo.discover_rules()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            rule_count = len(rules) if rules else 0
            
            results[name] = {
                "status": "Success",
                "rules_count": rule_count,
                "duration": duration
            }
            
            logger.info(f"✅ {name}: {rule_count} règles trouvées en {duration:.2f} secondes")
        except Exception as e:
            logger.error(f"❌ {name}: Erreur - {str(e)}")
            results[name] = {
                "status": "Failed",
                "error": str(e)
            }
    
    # Afficher un résumé des résultats
    logger.info("\n--- RÉSUMÉ DES TESTS ---")
    for name, result in results.items():
        status = result["status"]
        if status == "Success":
            logger.info(f"{name}: ✅ {result['rules_count']} règles en {result['duration']:.2f}s")
        else:
            logger.info(f"{name}: ❌ Échec - {result['error']}")

if __name__ == "__main__":
    test_all_algorithms()
"""
    
    with open(test_script_path, 'w') as f:
        f.write(test_script_content)
    
    # Rendre le script exécutable
    os.chmod(test_script_path, 0o755)
    
    logger.info(f"✅ Script de test créé: {test_script_path}")

def main():
    """Fonction principale"""
    logger.info("Début des corrections des algorithmes Java...")
    
    # Étape 1: Corriger les chemins de classe
    logger.info("Étape 1: Correction des chemins de classe Java")
    fix_class_paths()
    
    # Étape 2: Corriger les problèmes d'indentation
    logger.info("Étape 2: Correction des problèmes d'indentation")
    fix_indentation_issues()
    
    # Étape 3: Supprimer les JAR corrompus
    logger.info("Étape 3: Suppression des fichiers JAR corrompus")
    remove_corrupted_jars()
    
    # Étape 4: Créer un script de test
    logger.info("Étape 4: Création d'un script de test")
    create_test_script()
    
    logger.info("Corrections terminées. Vous pouvez maintenant exécuter test_algorithms_fixed.py pour tester les algorithmes.")

if __name__ == "__main__":
    main()
