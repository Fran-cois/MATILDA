#!/usr/bin/env python3
# fix_fdep.py - Corrige les problèmes d'initialisation dans FDep

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def fix_fdep_implementation():
    """Corrige l'implémentation Java de FDep"""
    
    # Chemin du fichier fdep.py
    fdep_file = os.path.join(current_dir, 'src', 'algorithms', 'fdep.py')
    
    # Vérifier si le fichier existe
    if not os.path.exists(fdep_file):
        logger.error(f"Le fichier {fdep_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier
    with open(fdep_file, 'r') as f:
        content = f.read()
    
    # Trouver la définition de la méthode _discover_rules_java
    if "_discover_rules_java" in content:
        # Rechercher la ligne actuelle
        if "de.metanome.cli.App" in content:
            # Récupérer la commande actuelle
            lines = content.split('\n')
            cmd_string_lines = []
            in_cmd_string = False
            
            for i, line in enumerate(lines):
                if 'cmd_string = (' in line:
                    in_cmd_string = True
                    cmd_string_start = i
                
                if in_cmd_string:
                    cmd_string_lines.append(line)
                    
                if in_cmd_string and ')' in line and not line.strip().endswith('\\'):
                    in_cmd_string = False
                    cmd_string_end = i
                    break
            
            # Construire la nouvelle commande
            # Ajouter le paramètre --header true pour s'assurer que l'en-tête est correctement interprété
            new_cmd = []
            for line in cmd_string_lines:
                if "--output file" in line and "--header" not in line:
                    line = line.replace('--output file', '--header true --output file')
                new_cmd.append(line)
            
            # Remplacer la commande dans le contenu
            old_cmd = '\n'.join(cmd_string_lines)
            new_cmd = '\n'.join(new_cmd)
            
            updated_content = content.replace(old_cmd, new_cmd)
            
            # Sauvegarder le fichier mis à jour
            with open(fdep_file, 'w') as f:
                f.write(updated_content)
                
            logger.info(f"✅ Correction appliquée à {fdep_file} (ajout du paramètre --header true)")
            return True
        else:
            logger.error(f"Commande metanome non trouvée dans {fdep_file}")
            return False
    else:
        logger.error(f"La méthode _discover_rules_java n'a pas été trouvée dans {fdep_file}")
        return False

if __name__ == "__main__":
    logger.info("Début de la correction de l'algorithme FDep")
    
    if fix_fdep_implementation():
        logger.info("La correction pour FDep a été appliquée avec succès")
    else:
        logger.error("La correction pour FDep a échoué")
