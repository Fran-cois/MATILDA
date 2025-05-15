#!/usr/bin/env python3
# fix_tane.py - Corrige le problème d'initialisation des colonnes dans TANE

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def fix_tane_implementation():
    """Corrige l'implémentation Java de TANE"""
    
    # Chemin du fichier tane.py
    tane_file = os.path.join(current_dir, 'src', 'algorithms', 'tane.py')
    
    # Vérifier si le fichier existe
    if not os.path.exists(tane_file):
        logger.error(f"Le fichier {tane_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier
    with open(tane_file, 'r') as f:
        content = f.read()
    
    # Trouver la définition de la méthode _discover_rules_java
    if "_discover_rules_java" in content:
        # Modifier la commande Java pour initialiser correctement les noms de colonnes
        # Problème: this.columnNames est null, il faut s'assurer que les colonnes sont correctement initialisées
        old_cmd_string = """cmd_string = (
                    f"""java -cp {metanome_cli_jar}:{tane_jar} """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --output file:{file_name} --has-header"""
                )"""
                
        new_cmd_string = """cmd_string = (
                    f"""java -cp {metanome_cli_jar}:{tane_jar} """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --output file:{file_name} --has-header true"""
                )"""
                
        # Remplacer la commande
        updated_content = content.replace(old_cmd_string, new_cmd_string)
        
        # Sauvegarder le fichier mis à jour
        with open(tane_file, 'w') as f:
            f.write(updated_content)
            
        logger.info(f"✅ Correction appliquée à {tane_file} (ajout du paramètre --has-header true)")
        return True
    else:
        logger.error(f"La méthode _discover_rules_java n'a pas été trouvée dans {tane_file}")
        return False

if __name__ == "__main__":
    logger.info("Début de la correction de l'algorithme TANE")
    
    if fix_tane_implementation():
        logger.info("La correction pour TANE a été appliquée avec succès")
    else:
        logger.error("La correction pour TANE a échoué")
