#!/usr/bin/env python3
# test_tane_java.py - Test de l'implémentation Java de TANE

import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Ajouter les répertoires nécessaires au path pour l'importation des modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Chemin des répertoires
test_data_dir = 'test_data'
os.makedirs(test_data_dir, exist_ok=True)

def create_test_csvs():
    """Crée des fichiers CSV de test simples"""
    logger.info("Création des fichiers CSV de test")
    
    # Premier fichier - données simples
    test_file1 = os.path.join(test_data_dir, 'test_fd.csv')
    with open(test_file1, 'w') as f:
        f.write('id,name,age,city,country\n')
        f.write('1,John,25,Paris,France\n')
        f.write('2,Emma,30,Lyon,France\n')
        f.write('3,Paul,28,Marseille,France\n')
    logger.info(f"Fichier CSV de test créé: {test_file1}")
    
    return test_file1

def test_tane_java():
    """Teste l'implémentation Java de TANE"""
    logger.info("\n==== Test de l'implémentation Java de TANE ====")
    
    script_dir = os.path.join(current_dir, 'src', 'algorithms')
    jar_path = os.path.join(script_dir, 'bins', 'metanome')
    
    # Obtenir la liste des fichiers JAR
    all_jars = [os.path.join(jar_path, jar_file) for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
    classpath = ":".join(all_jars)
    
    csv_file = os.path.join(current_dir, test_data_dir, 'test_fd.csv')
    
    current_time = datetime.now()
    file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_TANE'
    
    # Préparer le répertoire pour les résultats
    os.makedirs('results', exist_ok=True)
    
    # Construire la commande
    cmd_string = (
        f"""java -Xmx4g -cp {classpath} """
        f"""de.metanome.cli.App --algorithm de.metanome.algorithms.tane.TaneAlgorithm """
        f"""--files {csv_file} --file-key INPUT_FILES """
        f"""--separator "," --output file:{file_name} --header"""
    )
    
    logger.info(f"Exécution de la commande: {cmd_string}")
    
    # Exécuter la commande
    import subprocess
    process = subprocess.Popen(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    if process.returncode == 0:
        logger.info("✅ L'exécution de TANE a réussi")
        
        # Lire les résultats
        result_file_path = os.path.join("results", f"{file_name}_fds")
        
        try:
            with open(result_file_path, mode="r") as f:
                raw_rules = [line for line in f if line.strip()]
            
            logger.info(f"Nombre de règles découvertes: {len(raw_rules)}")
            logger.info("Exemples de règles:")
            for rule in raw_rules[:5]:
                logger.info(f"  - {rule}")
            
            # Nettoyer le fichier de résultats
            os.remove(result_file_path)
            
            return raw_rules
        except FileNotFoundError:
            logger.error(f"Fichier de résultats non trouvé: {result_file_path}")
            return []
    else:
        logger.error(f"❌ Échec de l'exécution de TANE avec le code de retour {process.returncode}")
        logger.error(f"Sortie standard:\n{stdout.decode('utf-8', errors='replace')}")
        logger.error(f"Erreur standard:\n{stderr.decode('utf-8', errors='replace')}")
        return []

def cleanup():
    """Nettoie les fichiers temporaires"""
    import shutil
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
        logger.info(f"Répertoire de test supprimé: {test_data_dir}")

if __name__ == "__main__":
    try:
        # Créer les données de test
        create_test_csvs()
        
        # Tester TANE
        tane_rules = test_tane_java()
        
        # Nettoyer
        cleanup()
        
        # Résumé
        logger.info("\n==== Résumé des tests ====")
        logger.info(f"TANE Java: {'Succès' if tane_rules else 'Échec'}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution des tests: {str(e)}")
