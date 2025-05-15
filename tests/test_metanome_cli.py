#!/usr/bin/env python3
# test_metanome_cli.py - Test simple pour metanome-cli

import os
import sys
import logging
import subprocess
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def create_test_csv():
    """Crée un fichier CSV de test simple"""
    test_dir = os.path.join(current_dir, "test_data")
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = os.path.join(test_dir, "test_simple.csv")
    with open(test_file, 'w') as f:
        f.write('id,name,age\n')
        f.write('1,Alice,30\n')
        f.write('2,Bob,25\n')
        f.write('3,Charlie,40\n')
    
    logger.info(f"Fichier CSV de test créé: {test_file}")
    return test_file

def test_metanome_cli():
    """Teste la commande de base de metanome-cli"""
    test_file = create_test_csv()
    
    # Chemins des JAR
    jar_path = os.path.join(current_dir, 'src', 'algorithms', 'bins', 'metanome')
    metanome_cli_jar = os.path.join(jar_path, "metanome-cli-1.2-SNAPSHOT.jar")
    tane_jar = os.path.join(jar_path, "tane-0.0.2-SNAPSHOT.jar")
    
    # Options de base
    current_time = datetime.now()
    output_file = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_TEST'
    
    # Commande de test
    cmd = f"""java -cp {metanome_cli_jar}:{tane_jar} de.metanome.cli.App --algorithm de.metanome.algorithms.tane.TaneAlgorithm --files {test_file} --file-key INPUT_FILES --separator "," --header --output file:{output_file}"""
    
    logger.info(f"Exécution de la commande de test: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        logger.info(f"Code de retour: {result.returncode}")
        
        if result.stdout:
            logger.info(f"Sortie standard: {result.stdout}")
        
        if result.stderr:
            logger.error(f"Erreur standard: {result.stderr}")
        
        if result.returncode == 0:
            logger.info("✅ Test réussi")
            # Vérifier si des résultats ont été générés
            result_file = os.path.join(current_dir, "results", f"{output_file}_fds")
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    content = f.read()
                logger.info(f"Contenu du fichier de résultats: {content}")
            else:
                logger.warning(f"Aucun fichier de résultats trouvé: {result_file}")
        else:
            logger.error("❌ Test échoué")
        
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== TEST SIMPLE DE METANOME-CLI ===")
    
    if test_metanome_cli():
        logger.info("Test terminé avec succès")
    else:
        logger.error("Test échoué")
