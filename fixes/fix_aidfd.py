#!/usr/bin/env python3
# fix_aidfd.py - Corrige le problème d'inputGenerator dans AIDFD

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def fix_aidfd_implementation():
    """Corrige l'implémentation Java de AIDFD"""
    
    # Chemin du fichier aidfd.py
    aidfd_file = os.path.join(current_dir, 'src', 'algorithms', 'aidfd.py')
    
    # Vérifier si le fichier existe
    if not os.path.exists(aidfd_file):
        logger.error(f"Le fichier {aidfd_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier
    with open(aidfd_file, 'r') as f:
        content = f.read()
    
    # Trouver la définition de la méthode _discover_rules_java
    if "_discover_rules_java" in content:
        # Modifier la commande Java pour initialiser correctement inputGenerator
        # Problème: inputGenerator est null, il faut s'assurer qu'il est correctement initialisé
        old_cmd_string = """cmd_string = (
            f"""java -Xmx4g -cp {classpath} """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_files} """
            f"""--file-key INPUT_FILES --separator "," --output file:{file_name} --header"""
        )"""
                
        new_cmd_string = """cmd_string = (
            f"""java -Xmx4g -cp {classpath} """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_files} """
            f"""--file-key INPUT_FILES --separator "," --output file:{file_name} --header true """
            f"""--algorithm-config min_support:{self.min_support},min_confidence:{self.min_confidence},max_lhs_size:{self.max_lhs_size}"""
        )"""
                
        # Remplacer la commande
        updated_content = content.replace(old_cmd_string, new_cmd_string)
        
        # Sauvegarder le fichier mis à jour
        with open(aidfd_file, 'w') as f:
            f.write(updated_content)
            
        logger.info(f"✅ Correction appliquée à {aidfd_file} (ajout des paramètres pour initialiser inputGenerator)")
        return True
    else:
        logger.error(f"La méthode _discover_rules_java n'a pas été trouvée dans {aidfd_file}")
        return False

if __name__ == "__main__":
    logger.info("Début de la correction de l'algorithme AIDFD")
    
    if fix_aidfd_implementation():
        logger.info("La correction pour AIDFD a été appliquée avec succès")
    else:
        logger.error("La correction pour AIDFD a échoué")
