import ast
import os
import logging
import subprocess
import shlex
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

# Test with one specific CSV file
csv_file = "/Users/famat/PycharmProjects/MATILDA_ALL/MATILDA/data/db/Bupa2/csv/bupa.csv"
script_dir = os.path.dirname(os.path.abspath(__file__))
algorithm_name = "tane"
classPath = "de.metanome.algorithms.tane.TaneAlgorithm"
rule_type = "fds"

# Generate filename for output
current_time = datetime.now()
jar_path = f"{script_dir}/src/algorithms/bins/metanome/"
file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}_bupa'

# Verify JAR files
metanome_cli_jar = f"{jar_path}metanome-cli-1.2-SNAPSHOT.jar" 
tane_jar = f"{jar_path}tane-0.0.2-SNAPSHOT.jar"

# Construct and run the command with different parameters (removing --table-key)
cmd_string = (
    f"""java -cp {metanome_cli_jar}:{tane_jar} """
    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
    f"""--separator "," --output file:{file_name} --header"""
)

# Create results directory if it doesn't exist
os.makedirs("results", exist_ok=True)

# Run the command
success = run_cmd(cmd_string)

# Check results
if success:
    result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
    if os.path.exists(result_file_path):
        logging.info(f"Result file found: {result_file_path}")
        with open(result_file_path, mode="r") as f:
            raw_rules = [line for line in f if line.strip()]
        logging.info(f"Number of rules discovered: {len(raw_rules)}")
        if raw_rules:
            logging.info(f"First rule: {raw_rules[0]}")
    else:
        logging.error(f"Result file not found: {result_file_path}")
