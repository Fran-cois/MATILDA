import ast
import os
import logging
import subprocess
import shlex
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Test command execution function
def run_cmd(cmd_string):
    try:
        cmd_list = shlex.split(cmd_string)
        logging.info(f"Executing command: {cmd_string}")
        
        process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = process.communicate()
        
        if process.returncode == 0:
            logging.info(f"Command executed successfully: {cmd_string}")
            if output:
                logging.info(f"Output: {output.decode()}")
            return True
        else:
            logging.error(f"Command failed with return code {process.returncode}: {errors.decode()}")
            return False
    except Exception as e:
        logging.error(f"An error occurred while executing the command: {e}")
        return False

# Utiliser le CSV d'exemple déjà créé
csv_file = "test_data/sample.csv"
if not os.path.exists(csv_file):
    logging.error(f"Le fichier CSV d'exemple n'existe pas: {csv_file}")
    exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))
algorithm_name = "FASTFDS"
classPath = "de.metanome.algorithms.fastfds.FastFD"
rule_type = "fds"
params = " --table-key INPUT_FILES"

current_time = datetime.now()
jar_path = f"{script_dir}/src/algorithms/bins/metanome/"
file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}_sample'

# Exécuter la commande uniquement pour ce fichier
metanome_cli_jar = f"{jar_path}metanome-cli-1.2-SNAPSHOT.jar" 
fastfds_jar = f"{jar_path}fastfds_algorithm-0.0.2-SNAPSHOT.jar"

# Vérifier si les fichiers JAR existent
if not os.path.exists(metanome_cli_jar):
    logging.error(f"Fichier JAR manquant: {metanome_cli_jar}")
    exit(1)
    
if not os.path.exists(fastfds_jar):
    logging.error(f"Fichier JAR manquant: {fastfds_jar}")
    exit(1)

# Construction de la commande
cmd_string = (
    f"""java -cp {metanome_cli_jar}:{fastfds_jar} """
    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file}{params} """
    f"""--separator "," --output file:{file_name} --header"""
)

# Création du dossier results si nécessaire
os.makedirs("results", exist_ok=True)

# Exécution de la commande
logging.info(f"Exécution de la commande: {cmd_string}")
success = run_cmd(cmd_string)

# Vérification des résultats
if success:
    result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
    try:
        with open(result_file_path, mode="r") as f:
            raw_rules = [line for line in f if line.strip()]
        logging.info(f"Nombre de règles découvertes: {len(raw_rules)}")
        for rule in raw_rules:
            logging.info(f"Règle: {rule}")
    except FileNotFoundError:
        logging.error(f"Fichier de résultats non trouvé: {result_file_path}")
else:
    logging.error("La commande a échoué. Vérifier les messages d'erreur ci-dessus.")
