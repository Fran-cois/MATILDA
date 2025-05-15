#!/usr/bin/env python3
# fix_metanome_algorithms.py - Script de correction des problèmes d'intégration des algorithmes Java

import os
import logging
import sys
import shutil
import subprocess
from typing import List, Dict, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
algorithms_dir = os.path.join(src_dir, 'algorithms')
bins_dir = os.path.join(algorithms_dir, 'bins', 'metanome')

# Configurations correctes pour chaque algorithme
ALGORITHM_CONFIGS = {
    "aidfd": {
        "class_path": "de.metanome.algorithms.aidfd.AIDFD",
        "jar_name": "AIDFD-0.0.2-SNAPSHOT.jar",
        "algorithm_config_params": {
            "timeout [s]": "600",
            "neg-cover growth window size": "100",
            "use bloomfilter": "true",
            "until iteration k": "0",
            "neg-cover growth thresh [x/1000000]": "100000"
        }
    },
    "pyro": {
        "class_path": "de.hpi.isg.pyro.metanome.algorithms.PyroAkka",
        "jar_name": "pyro-distro-1.0-SNAPSHOT-distro.jar",
        "dependent_jars": ["mdms-metanome-client-0.0.3.jar", "mdms-model-0.0.3.jar", "mdms-tools-0.0.3.jar"],
        "algorithm_config_params": {
            "threshold": "0.7",
            "max_attributes_in_lhs": "4"
        }
    },
    "dfd": {
        "class_path": "de.metanome.algorithms.dfd.dfdMetanome.DFDMetanome",
        "jar_name": "dfd-0.0.2-SNAPSHOT.jar",
        "pre_read_file": True  # Flag indiquant que le fichier CSV doit être préchargé
    },
    "fdep": {
        "class_path": "de.metanome.algorithms.fdep.FdepAlgorithm",
        "jar_name": "fdep_algorithm-0.0.2-SNAPSHOT.jar",
        "input_generator_fix": True  # Flag pour corriger le problème de inputGenerator
    },
    "fastfds": {
        "class_path": "de.metanome.algorithms.fastfds.FastFDMagicMain",  # Changement de classe pour utiliser une classe avec un constructeur par défaut
        "jar_name": "fastfds_algorithm-0.0.2-SNAPSHOT.jar"
    },
    "tane": {
        "class_path": "de.metanome.algorithms.tane.TaneAlgorithm",
        "jar_name": "tane-0.0.2-SNAPSHOT.jar",
        "column_names_fix": True  # Flag pour corriger le problème de columnNames null
    }
}

def download_missing_jars() -> None:
    """Télécharge les JARs manquants nécessaires pour les algorithmes"""
    mdms_jars = [
        "mdms-metanome-client-0.0.3.jar",
        "mdms-model-0.0.3.jar",
        "mdms-tools-0.0.3.jar"
    ]
    
    # URL de base pour le téléchargement des JARs
    base_url = "https://mvnrepository.com/artifact/de.hpi.isg.mdms"
    
    for jar in mdms_jars:
        jar_path = os.path.join(bins_dir, jar)
        
        # Vérifier si le JAR existe déjà
        if os.path.exists(jar_path):
            logger.info(f"Le JAR {jar} existe déjà")
            continue
        
        logger.info(f"Téléchargement du JAR {jar}...")
        # Utilisation de curl pour télécharger le JAR
        try:
            # Créer le répertoire s'il n'existe pas
            os.makedirs(bins_dir, exist_ok=True)
            
            # Construire l'URL complet
            jar_name_without_ext = jar.split('.jar')[0]
            version = jar_name_without_ext.split('-')[-1]
            artifact_id = jar_name_without_ext.split('-')[0]
            
            url = f"{base_url}/{artifact_id}/{version}/{jar}"
            
            # Télécharger avec curl
            subprocess.run(
                ["curl", "-L", "-o", jar_path, url],
                check=True
            )
            
            logger.info(f"JAR {jar} téléchargé avec succès")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors du téléchargement du JAR {jar}: {str(e)}")

def fix_aidfd() -> None:
    """Corrige les problèmes spécifiques à l'algorithme AIDFD"""
    file_path = os.path.join(algorithms_dir, "aidfd.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger la commande pour passer les bons paramètres de configuration
    # Problème: no configuration requirement present for key min_support
    old_cmd_string = """cmd_string = (
            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"
            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"
            f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
            f\"\"\"--output file:{file_name} \"\"\"
            f\"\"\"--algorithm-config min_support:{self.min_support},min_confidence:{self.min_confidence},max_lhs_size:{self.max_lhs_size}\"\"\"
        )"""
    
    new_cmd_string = """cmd_string = (
            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"
            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"
            f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
            f\"\"\"--output file:{file_name} \"\"\"
            f\"\"\"--algorithm-config timeout [s]:600,neg-cover growth window size:100,use bloomfilter:true,until iteration k:0,neg-cover growth thresh [x/1000000]:100000\"\"\"
        )"""
    
    updated_content = content.replace(old_cmd_string, new_cmd_string)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def fix_pyro() -> None:
    """Corrige les problèmes spécifiques à l'algorithme Pyro"""
    file_path = os.path.join(algorithms_dir, "pyro.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Télécharger les JARs manquants pour la dépendance MetacrateClient
    download_missing_jars()
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger la commande pour inclure les JARs supplémentaires
    # Problème: java.lang.NoClassDefFoundError: de/hpi/isg/mdms/clients/MetacrateClient
    old_cmd_string = """# Ajouter tous les JAR du répertoire dans le classpath
        all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
        classpath = ":".join(all_jars)"""
    
    new_cmd_string = """# Ajouter tous les JAR du répertoire dans le classpath
        all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
        # S'assurer que les jars de MDMS sont inclus pour Pyro
        mdms_jars = [
            f"{jar_path}mdms-metanome-client-0.0.3.jar",
            f"{jar_path}mdms-model-0.0.3.jar",
            f"{jar_path}mdms-tools-0.0.3.jar"
        ]
        for mdms_jar in mdms_jars:
            if os.path.exists(mdms_jar) and mdms_jar not in all_jars:
                all_jars.append(mdms_jar)
        classpath = ":".join(all_jars)"""
    
    updated_content = content.replace(old_cmd_string, new_cmd_string)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def fix_dfd() -> None:
    """Corrige les problèmes spécifiques à l'algorithme DFD"""
    file_path = os.path.join(algorithms_dir, "dfd.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger le problème NullPointerException
    # Nous devons ajouter une étape pour précharger le fichier CSV avant de l'utiliser
    # Cela aidera à éviter le problème de "local1 is null"
    
    old_cmd_string = """cmd_string = (
                    f\"\"\"java -Xmx4g -cp {metanome_cli_jar}:{dfd_jar} \"\"\"
                    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"
                    f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                    f\"\"\"--output file:{file_name}\"\"\"
                )"""
    
    new_cmd_string = """# Précharger le fichier CSV pour éviter le NullPointerException
                    try:
                        # Vérifier le contenu du fichier CSV
                        import pandas as pd
                        df = pd.read_csv(csv_file)
                        logging.info(f"Fichier CSV préchargé avec succès. Colonnes: {list(df.columns)}")
                        
                        if len(df) == 0:
                            logging.error(f"Le fichier CSV {csv_file} est vide")
                            continue
                    except Exception as e:
                        logging.error(f"Erreur lors du préchargement du fichier CSV {csv_file}: {str(e)}")
                        continue
                        
                    cmd_string = (
                        f\"\"\"java -Xmx4g -cp {metanome_cli_jar}:{dfd_jar} \"\"\"
                        f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"
                        f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                        f\"\"\"--output file:{file_name} --verbose true\"\"\"
                    )"""
    
    updated_content = content.replace(old_cmd_string, new_cmd_string)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def fix_fdep() -> None:
    """Corrige les problèmes spécifiques à l'algorithme FDEP"""
    file_path = os.path.join(algorithms_dir, "fdep.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger le problème "No input Generator set"
    # Nous devons nous assurer que le générateur d'entrée est correctement initialisé
    old_cmd_string = """cmd_string = (
            f\"\"\"java -cp {classpath} \"\"\"
            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"
            f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
            f\"\"\"--output file:{file_name}\"\"\"
        )"""
    
    new_cmd_string = """# Traiter les fichiers un par un au lieu de tous ensemble pour éviter les problèmes
        results = []
        for csv_file in csv_files.split():
            file_name_single = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}_{os.path.basename(csv_file).replace(".csv", "")}'
            
            cmd_string_single = (
                f\"\"\"java -cp {classpath} \"\"\"
                f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"
                f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                f\"\"\"--output file:{file_name_single} --verbose true\"\"\"
            )
            
            logger.info(f"Exécution de la commande: {cmd_string_single}")
            
            if run_cmd(cmd_string_single):
                result_file_path = os.path.join("results", f"{file_name_single}_{rule_type}")
                
                try:
                    with open(result_file_path, mode="r") as f:
                        file_rules = [line for line in f if line.strip()]
                        if file_rules:
                            logger.info(f"Découvert {len(file_rules)} règles depuis {csv_file}")
                            raw_rules.extend(file_rules)
                        else:
                            logger.warning(f"Aucune règle découverte depuis {csv_file}")
                    
                    if os.path.exists(result_file_path):
                        os.remove(result_file_path)
                        
                except FileNotFoundError:
                    logger.error(f"Fichier de résultats non trouvé: {result_file_path}")
            else:
                logger.error(f"Échec de l'exécution de {algorithm_name} pour {csv_file}")
        
        # Ne pas exécuter la commande globale
        cmd_string = None"""
    
    updated_content = content.replace(old_cmd_string, new_cmd_string)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def fix_fastfds() -> None:
    """Corrige les problèmes spécifiques à l'algorithme FastFDs"""
    file_path = os.path.join(algorithms_dir, "fastfds.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger le problème InstantiationException: de.metanome.algorithms.fastfds.FastFD
    # Nous devons changer la classe utilisée pour une qui a un constructeur par défaut
    old_class_path = "classPath = \"de.metanome.algorithms.fastfds.FastFD\""
    new_class_path = "classPath = \"de.metanome.algorithms.fastfds.FastFDMagicMain\"  # Utiliser la classe avec constructeur par défaut"
    
    updated_content = content.replace(old_class_path, new_class_path)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def fix_tane() -> None:
    """Corrige les problèmes spécifiques à l'algorithme TANE"""
    file_path = os.path.join(algorithms_dir, "tane.py")
    
    if not os.path.exists(file_path):
        logger.error(f"Le fichier {file_path} n'existe pas")
        return
    
    # Lire le contenu du fichier
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger le problème NullPointerException: Cannot invoke "java.util.List.size()" because "this.columnNames" is null
    old_cmd_string = """cmd_string = (
                    f\"\"\"java -cp {metanome_cli_jar}:{tane_jar} \"\"\"
                    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"
                    f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                    f\"\"\"--output file:{file_name}\"\"\"
                )"""
    
    new_cmd_string = """# Précharger et analyser le fichier CSV pour s'assurer que les noms de colonnes sont corrects
                    try:
                        # Vérifier le contenu du fichier CSV
                        import pandas as pd
                        df = pd.read_csv(csv_file)
                        logging.info(f"Fichier CSV préchargé avec succès. Colonnes: {list(df.columns)}")
                        
                        if len(df) == 0:
                            logging.error(f"Le fichier CSV {csv_file} est vide")
                            continue
                            
                        # Créer un fichier temporaire avec entêtes explicites si nécessaire
                        tmp_csv_file = f"{csv_file}.tmp"
                        df.to_csv(tmp_csv_file, index=False)
                        csv_file_to_use = tmp_csv_file
                    except Exception as e:
                        logging.error(f"Erreur lors du préchargement du fichier CSV {csv_file}: {str(e)}")
                        csv_file_to_use = csv_file
                        
                    # Ajouter l'option --input-row-limit pour limiter le nombre de lignes si nécessaire
                    cmd_string = (
                        f\"\"\"java -cp {metanome_cli_jar}:{tane_jar} \"\"\"
                        f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file_to_use} \"\"\"
                        f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                        f\"\"\"--output file:{file_name} --verbose true\"\"\"
                    )"""
    
    updated_content = content.replace(old_cmd_string, new_cmd_string)
    
    # Corriger également la gestion du fichier temporaire pour le nettoyer après usage
    old_cleanup = """if os.path.exists(result_file_path):
                    os.remove(result_file_path)"""
                    
    new_cleanup = """if os.path.exists(result_file_path):
                    os.remove(result_file_path)
                    
                # Nettoyer le fichier temporaire si créé
                if 'tmp_csv_file' in locals() and os.path.exists(tmp_csv_file):
                    os.remove(tmp_csv_file)
                    logging.info(f"Fichier temporaire supprimé: {tmp_csv_file}")"""
    
    updated_content = updated_content.replace(old_cleanup, new_cleanup)
    
    # Sauvegarder le fichier
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Correction appliquée à {file_path}")

def run_tests() -> None:
    """Exécute le script de test pour vérifier les corrections"""
    test_script = os.path.join(current_dir, "test_all_corrected_algos.py")
    
    if not os.path.exists(test_script):
        logger.error(f"Le script de test {test_script} n'existe pas")
        return
    
    logger.info(f"Exécution du script de test {test_script}...")
    
    result = subprocess.run(
        [sys.executable, test_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Le script de test a réussi")
        logger.info(result.stdout)
    else:
        logger.error(f"❌ Le script de test a échoué")
        logger.error(result.stderr)
        
    return result.returncode == 0

def main() -> None:
    """Fonction principale"""
    logger.info("=== Début de la correction des algorithmes Java de découverte de dépendances fonctionnelles ===")
    
    # Vérifier l'existence du répertoire des bins
    if not os.path.exists(bins_dir):
        logger.error(f"Le répertoire {bins_dir} n'existe pas")
        sys.exit(1)
    
    # Corriger chaque algorithme
    fix_aidfd()
    fix_pyro()
    fix_dfd()
    fix_fdep()
    fix_fastfds()
    fix_tane()
    
    logger.info("=== Fin de la correction des algorithmes ===")
    
    # Exécuter les tests
    success = run_tests()
    
    if success:
        logger.info("=== Tous les algorithmes ont été corrigés avec succès ===")
    else:
        logger.warning("=== Certains problèmes persistent, vérifier les résultats des tests ===")
    
if __name__ == "__main__":
    main()
