#!/usr/bin/env python3
# fix_pyro.py - Corrige le problème de dépendance manquante dans PYRO

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def fix_pyro_implementation():
    """Corrige l'implémentation Java de PYRO"""
    
    # Chemin du fichier pyro.py
    pyro_file = os.path.join(current_dir, 'src', 'algorithms', 'pyro.py')
    
    # Vérifier si le fichier existe
    if not os.path.exists(pyro_file):
        logger.error(f"Le fichier {pyro_file} n'existe pas")
        return False
    
    # Lire le contenu du fichier
    with open(pyro_file, 'r') as f:
        content = f.read()
    
    # Trouver la définition de la méthode _discover_rules_java
    if "_discover_rules_java" in content:
        # Modifier la commande Java pour éviter le problème de dépendance manquante MetacrateClient
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
            # Remplacer le classpath et s'assurer que les bons JAR sont utilisés
            new_cmd = []
            for line in cmd_string_lines:
                if "java -" in line:
                    # Ajouter une option pour contourner le problème de MetacrateClient
                    line = line.replace("java -", "java -Dde.metanome.algorithm.pyro.skip-metacrate=true -")
                new_cmd.append(line)
            
            # Remplacer la commande dans le contenu
            old_cmd = '\n'.join(cmd_string_lines)
            new_cmd = '\n'.join(new_cmd)
            
            updated_content = content.replace(old_cmd, new_cmd)
            
            # Sauvegarder le fichier mis à jour
            with open(pyro_file, 'w') as f:
                f.write(updated_content)
                
            logger.info(f"✅ Correction appliquée à {pyro_file} (ajout du paramètre pour contourner MetacrateClient)")
            return True
        else:
            logger.error(f"Commande metanome non trouvée dans {pyro_file}")
            return False
    else:
        logger.error(f"La méthode _discover_rules_java n'a pas été trouvée dans {pyro_file}")
        return False

if __name__ == "__main__":
    logger.info("Début de la correction de l'algorithme PYRO")
    
    if fix_pyro_implementation():
        logger.info("La correction pour PYRO a été appliquée avec succès")
    else:
        logger.error("La correction pour PYRO a échoué")
