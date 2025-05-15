#!/usr/bin/env python3
# fix_metanome_ultimate.py - Solution finale pour la correction des algorithmes Java Metanome

import os
import sys
import shutil
import logging
import re
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chemin de base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALGORITHMS_DIR = os.path.join(BASE_DIR, "src", "algorithms")
JAR_DIR = os.path.join(ALGORITHMS_DIR, "bins", "metanome")

# Définition des classes Java correctes pour chaque algorithme
ALGORITHM_CLASSES = {
    "aidfd": "de.metanome.algorithms.aidfd.AIDFD",
    "pyro": "de.hpi.isg.pyro.algorithm.ProfilingAlgorithm",
    "dfd": "de.metanome.algorithms.dfd.DFD",
    "fdep": "de.metanome.algorithms.fdep.FdepAlgorithm",
    "fastfds": "de.metanome.algorithms.fastfds.FastFD",
    "tane": "de.metanome.algorithms.tane.TaneAlgorithm"
}

def check_jar_files():
    """Vérifie si les fichiers JAR nécessaires existent"""
    logger.info("Vérification des fichiers JAR...")
    
    if not os.path.exists(JAR_DIR):
        logger.error(f"Le répertoire des JAR n'existe pas: {JAR_DIR}")
        return False
    
    jar_files = [f for f in os.listdir(JAR_DIR) if f.endswith('.jar')]
    if not jar_files:
        logger.error("Aucun fichier JAR trouvé")
        return False
    
    logger.info(f"Trouvé {len(jar_files)} fichiers JAR")
    
    # Vérifier si le JAR de l'interface CLI de Metanome existe
    metanome_cli_jar = os.path.join(JAR_DIR, "metanome-cli-1.2-SNAPSHOT.jar")
    if not os.path.exists(metanome_cli_jar):
        logger.warning(f"JAR Metanome CLI non trouvé: {metanome_cli_jar}")
    
    return True

def fix_algorithm_files():
    """Corrige tous les fichiers d'algorithme FD"""
    algorithms = ["aidfd", "pyro", "dfd", "fdep", "fastfds", "tane"]
    
    for algo in algorithms:
        logger.info(f"Correction de l'algorithme {algo}...")
        
        algorithm_file = os.path.join(ALGORITHMS_DIR, f"{algo}.py")
        if not os.path.exists(algorithm_file):
            logger.error(f"Fichier d'algorithme non trouvé: {algorithm_file}")
            continue
        
        # Sauvegarder le fichier original
        backup_file = f"{algorithm_file}.bak"
        if not os.path.exists(backup_file):
            shutil.copy2(algorithm_file, backup_file)
        
        # Lire le contenu du fichier
        with open(algorithm_file, 'r') as f:
            content = f.read()
        
        # Corriger la classe Java
        new_content = fix_java_class(content, algo)
        
        # Corriger la commande cmd_string
        new_content = fix_cmd_string(new_content)
        
        # Corriger les importations et les problèmes de dépendances
        new_content = fix_dependencies(new_content)
        
        # Écrire le contenu corrigé
        with open(algorithm_file, 'w') as f:
            f.write(new_content)
        
        logger.info(f"✅ Algorithme {algo} corrigé")

def fix_java_class(content, algo):
    """Corrige la classe Java dans le fichier d'algorithme"""
    java_class = ALGORITHM_CLASSES.get(algo.lower())
    if not java_class:
        logger.error(f"Classe Java non définie pour l'algorithme {algo}")
        return content
    
    # Chercher et remplacer la ligne qui définit classPath
    pattern = r'(classPath\s*=\s*["\']).*?(["\'])'
    if re.search(pattern, content):
        new_content = re.sub(pattern, f'\\1{java_class}\\2', content)
        return new_content
    
    return content

def fix_cmd_string(content):
    """Corrige la commande cmd_string pour utiliser tous les JAR dans le répertoire"""
    # Chercher le bloc cmd_string
    start_idx = content.find("cmd_string = (")
    if start_idx >= 0:
        # Trouver la fin du bloc
        end_idx = content.find(")", start_idx)
        if end_idx >= 0:
            # Trouver la ligne après la fermeture de la parenthèse
            next_line_idx = content.find("\n", end_idx)
            if next_line_idx >= 0:
                # Calculer l'indentation
                line_before = content.rfind("\n", 0, start_idx)
                indent = ""
                if line_before >= 0:
                    indent = content[line_before + 1:start_idx]
                
                # Construire la nouvelle commande
                new_cmd = (
                    f"{indent}cmd_string = (\n"
                    f"{indent}    f\"\"\"java -Xmx4g -cp {{jar_path}}*.jar \"\"\"\n"
                    f"{indent}    f\"\"\"de.metanome.cli.App --algorithm {{classPath}} --files {{csv_file}} \"\"\"\n"
                    f"{indent}    f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n"
                    f"{indent}    f\"\"\"--output file:{{file_name}}\"\"\"\n"
                    f"{indent})"
                )
                
                # Remplacer le bloc cmd_string
                content = content[:start_idx] + new_cmd + content[next_line_idx:]
    
    return content

def fix_dependencies(content):
    """Corrige les problèmes de dépendances Java"""
    # Supprimer les références aux dépendances problématiques
    deps = ["mdms-tools", "mdms-metanome-client", "mdms-model"]
    for dep in deps:
        if dep in content:
            # Trouver les lignes contenant la dépendance
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if dep not in line:
                    new_lines.append(line)
            content = "\n".join(new_lines)
    
    return content

def create_test_script():
    """Crée un script de test pour tous les algorithmes"""
    test_script = os.path.join(BASE_DIR, "test_unified_algorithms.py")
    
    content = '''#!/usr/bin/env python3
# test_unified_algorithms.py - Test unifié pour tous les algorithmes FD

import os
import sys
import logging
import shutil
from datetime import datetime

# Ajouter le répertoire courant au chemin
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "src"))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Répertoire de données de test
test_dir = os.path.join(current_dir, "test_data")
os.makedirs(test_dir, exist_ok=True)

def create_test_data():
    """Crée les données de test"""
    logger.info("Création des données de test...")
    
    # Fichier test 1 - données simples
    test_file1 = os.path.join(test_dir, "customers.csv")
    with open(test_file1, "w") as f:
        f.write("customer_id,first_name,last_name,email,city,country\\n")
        f.write("1,John,Smith,john.smith@example.com,Paris,France\\n")
        f.write("2,Emma,Johnson,emma.j@example.com,Lyon,France\\n")
        f.write("3,Paul,Williams,p.williams@example.com,Marseille,France\\n")
        f.write("4,Sophia,Brown,sophia.brown@example.com,Paris,France\\n")
        f.write("5,James,Davis,james.d@example.com,Nice,France\\n")
        f.write("6,Olivia,Miller,o.miller@example.com,Bordeaux,France\\n")
        f.write("7,Alexander,Wilson,alex.w@example.com,Lille,France\\n")
        f.write("8,Emily,Garcia,emily.g@example.com,Toulouse,France\\n")
        f.write("9,Daniel,Taylor,d.taylor@example.com,Paris,France\\n")
        f.write("10,Sophie,Thomas,s.thomas@example.com,Lyon,France\\n")
    logger.info(f"Fichier créé: {test_file1}")
    
    # Fichier test 2 - données d'employés
    test_file2 = os.path.join(test_dir, "employees.csv")
    with open(test_file2, "w") as f:
        f.write("emp_id,first_name,last_name,department,manager_id,salary\\n")
        f.write("101,Jean,Dupont,IT,201,55000\\n")
        f.write("102,Marie,Martin,HR,202,48000\\n")
        f.write("103,Pierre,Durand,IT,201,52000\\n")
        f.write("104,Sophie,Leroy,Finance,203,60000\\n")
        f.write("105,Thomas,Petit,IT,201,51000\\n")
        f.write("106,Claire,Moreau,HR,202,49000\\n")
        f.write("107,Antoine,Robert,Finance,203,58000\\n")
        f.write("108,Emilie,Simon,IT,201,53000\\n")
        f.write("109,Nicolas,Michel,Marketing,204,51000\\n")
        f.write("110,Julie,Dubois,Marketing,204,50000\\n")
    logger.info(f"Fichier créé: {test_file2}")
    
    return [test_file1, test_file2]

class MockDatabase:
    """Classe simulant une base de données pour les tests"""
    def __init__(self):
        self.base_csv_dir = test_dir

def test_algorithm(algo_class, algo_name):
    """Teste un algorithme spécifique"""
    logger.info(f"\\n==== Test de {algo_name} ====")
    db = MockDatabase()
    algorithm = algo_class(db)
    
    try:
        rules = algorithm._discover_rules_java()
        
        if rules:
            logger.info(f"✅ {algo_name} a découvert {len(rules)} dépendances fonctionnelles")
            logger.info("Exemples de dépendances:")
            for rule in list(rules.keys())[:5]:  # Afficher les 5 premières règles
                logger.info(f"  - {rule}")
            return True
        else:
            logger.error(f"❌ {algo_name} n'a pas découvert de dépendances")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution de {algo_name}: {str(e)}")
        return False

def cleanup():
    """Nettoie les fichiers temporaires"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        logger.info(f"Répertoire supprimé: {test_dir}")

def main():
    """Fonction principale"""
    try:
        # Créer les données de test
        create_test_data()
        
        # Importer les algorithmes
        from src.algorithms.aidfd import AIDFD
        from src.algorithms.pyro import Pyro
        from src.algorithms.dfd import DFD
        from src.algorithms.fdep import FDep
        from src.algorithms.fastfds import FastFDs
        from src.algorithms.tane import Tane
        
        # Algorithmes à tester
        algorithms = [
            (AIDFD, "AIDFD"),
            (Pyro, "Pyro"),
            (DFD, "DFD"),
            (FDep, "FDep"),
            (FastFDs, "FastFDs"),
            (Tane, "TANE")
        ]
        
        # Résultats
        results = {}
        
        # Tester chaque algorithme
        for algo_class, algo_name in algorithms:
            results[algo_name] = test_algorithm(algo_class, algo_name)
        
        # Nettoyage
        cleanup()
        
        # Afficher les résultats
        logger.info("\\n==== Résumé des tests ====")
        for algo_name, success in results.items():
            status = "✅ Succès" if success else "❌ Échec"
            logger.info(f"{algo_name}: {status}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()
'''
    
    # Écrire le script
    with open(test_script, 'w') as f:
        f.write(content)
    
    # Rendre le script exécutable
    os.chmod(test_script, 0o755)
    
    logger.info(f"Script de test créé: {test_script}")

def main():
    """Fonction principale"""
    # Vérifier les fichiers JAR
    if not check_jar_files():
        logger.warning("Problèmes avec les fichiers JAR, mais on continue...")
    
    # Corriger les fichiers d'algorithme
    fix_algorithm_files()
    
    # Créer le script de test
    create_test_script()
    
    logger.info("Correction des algorithmes terminée avec succès!")
    logger.info("Pour tester les algorithmes, exécutez: python test_unified_algorithms.py")

if __name__ == "__main__":
    main()
