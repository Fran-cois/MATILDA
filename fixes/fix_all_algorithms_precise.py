#!/usr/bin/env python3
# fix_all_algorithms_precise.py - Correction précise des algorithmes Java

import os
import sys
import re
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_aidfd():
    """Correction spécifique pour l'algorithme AIDFD"""
    file_path = os.path.join("src", "algorithms", "aidfd.py")
    logger.info(f"Correction de AIDFD: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger la commande Java
        new_content = re.sub(
            r'cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''cmd_string = (
            f"""java -Xmx4g -cp {classpath} """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_files} """
            f"""--file-key INPUT_FILES --separator "," --header """
            f"""--output file:{file_name} """
            f"""--algorithm-config min_support:{self.min_support},min_confidence:{self.min_confidence},max_lhs_size:{self.max_lhs_size}"""
        )''',
            content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ AIDFD corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de AIDFD: {str(e)}")
        return False

def fix_pyro():
    """Correction spécifique pour l'algorithme Pyro"""
    file_path = os.path.join("src", "algorithms", "pyro.py")
    logger.info(f"Correction de Pyro: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger le chemin de classe
        new_content = re.sub(
            r'classPath\s*=\s*".*?"',
            r'classPath = "de.hpi.isg.pyro.core.ProfilingAlgorithm"',
            content
        )
        
        # Corriger la commande Java
        new_content = re.sub(
            r'cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''cmd_string = (
            f"""java -Xmx4g -cp {classpath} """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_files} """
            f"""--file-key INPUT_FILES --separator "," --header """
            f"""--output file:{file_name}"""
        )''',
            new_content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ Pyro corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de Pyro: {str(e)}")
        return False

def fix_dfd():
    """Correction spécifique pour l'algorithme DFD"""
    file_path = os.path.join("src", "algorithms", "dfd.py")
    logger.info(f"Correction de DFD: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger la commande Java, en préservant le traitement individuel des fichiers
        new_content = re.sub(
            r'metanome_cli_jar\s*=\s*.*?\n.*?dfd_jar\s*=\s*.*?\n.*?if not os\.path\.exists\(metanome_cli_jar\):.*?continue.*?if not os\.path\.exists\(dfd_jar\):.*?continue.*?cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''# Ajouter tous les JAR du répertoire dans le classpath
                all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
                classpath = ":".join(all_jars)
                
                cmd_string = (
                    f"""java -Xmx4g -cp {classpath} """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --header """
                    f"""--output file:{file_name}"""
                )''',
            content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ DFD corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de DFD: {str(e)}")
        return False

def fix_fdep():
    """Correction spécifique pour l'algorithme FDep"""
    file_path = os.path.join("src", "algorithms", "fdep.py")
    logger.info(f"Correction de FDep: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger la commande Java
        new_content = re.sub(
            r'cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''cmd_string = (
            f"""java -Xmx4g -cp {classpath} """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_files} """
            f"""--file-key INPUT_FILES --separator "," --header """
            f"""--output file:{file_name}"""
        )''',
            content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ FDep corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de FDep: {str(e)}")
        return False

def fix_fastfds():
    """Correction spécifique pour l'algorithme FastFDs"""
    file_path = os.path.join("src", "algorithms", "fastfds.py")
    logger.info(f"Correction de FastFDs: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger le chemin de classe
        new_content = re.sub(
            r'classPath\s*=\s*".*?"',
            r'classPath = "de.metanome.algorithms.fastfds.FastFD"',
            content
        )
        
        # Corriger la commande Java, en préservant le traitement individuel des fichiers
        new_content = re.sub(
            r'metanome_cli_jar\s*=\s*.*?\n.*?fastfds_jar\s*=\s*.*?\n.*?if not os\.path\.exists\(metanome_cli_jar\):.*?continue.*?if not os\.path\.exists\(fastfds_jar\):.*?continue.*?cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''# Ajouter tous les JAR du répertoire dans le classpath
                all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
                classpath = ":".join(all_jars)
                
                cmd_string = (
                    f"""java -Xmx4g -cp {classpath} """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --header """
                    f"""--output file:{file_name}"""
                )''',
            new_content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ FastFDs corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de FastFDs: {str(e)}")
        return False

def fix_tane():
    """Correction spécifique pour l'algorithme TANE"""
    file_path = os.path.join("src", "algorithms", "tane.py")
    logger.info(f"Correction de TANE: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Corriger le chemin de classe
        new_content = re.sub(
            r'classPath\s*=\s*".*?"',
            r'classPath = "de.metanome.algorithms.tane.TaneAlgorithm"',
            content
        )
        
        # Corriger la commande Java, en préservant le traitement individuel des fichiers
        new_content = re.sub(
            r'metanome_cli_jar\s*=\s*.*?\n.*?tane_jar\s*=\s*.*?\n.*?if not os\.path\.exists\(metanome_cli_jar\):.*?continue.*?if not os\.path\.exists\(tane_jar\):.*?continue.*?cmd_string\s*=\s*\(.*?--output file:{file_name}.*?\)',
            r'''# Ajouter tous les JAR du répertoire dans le classpath
                all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
                classpath = ":".join(all_jars)
                
                cmd_string = (
                    f"""java -Xmx4g -cp {classpath} """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --header """
                    f"""--output file:{file_name}"""
                )''',
            new_content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        logger.info(f"✅ TANE corrigé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction de TANE: {str(e)}")
        return False

def main():
    """Fonction principale"""
    logger.info("Début de la correction précise des algorithmes Java")
    
    # AIDFD
    fix_aidfd()
    
    # Pyro
    fix_pyro()
    
    # DFD
    fix_dfd()
    
    # FDep
    fix_fdep()
    
    # FastFDs
    fix_fastfds()
    
    # TANE
    fix_tane()
    
    logger.info("Fin de la correction précise des algorithmes Java")

if __name__ == "__main__":
    main()
