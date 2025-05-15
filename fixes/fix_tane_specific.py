#!/usr/bin/env python3
# fix_tane_specific.py - Corriger le problème TANE spécifique

import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))
tane_file = os.path.join(current_dir, 'src', 'algorithms', 'tane.py')

# Lire le contenu du fichier TANE
with open(tane_file, 'r') as f:
    content = f.read()

# Chercher et remplacer la ligne de commande TANE
old_cmd = """                    cmd_string = (
                        f\"\"\"java -cp {metanome_cli_jar}:{tane_jar} \"\"\"
                        f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"
                        f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                        f\"\"\"--output file:{file_name}\"\"\"
                    )"""

new_cmd = """                    # Précharger et analyser le fichier CSV pour s'assurer que les noms de colonnes sont corrects
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
                        
                    cmd_string = (
                        f\"\"\"java -cp {metanome_cli_jar}:{tane_jar} \"\"\"
                        f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file_to_use} \"\"\"
                        f\"\"\"--file-key INPUT_FILES --separator "," --header \"\"\"
                        f\"\"\"--output file:{file_name} --verbose true\"\"\"
                    )"""

# Remplacer la commande
updated_content = content.replace(old_cmd, new_cmd)

# Sauvegarder les modifications
with open(tane_file, 'w') as f:
    f.write(updated_content)

# Vérifier que le remplacement a bien été effectué
if old_cmd in updated_content:
    logger.error("Le remplacement n'a pas fonctionné")
else:
    logger.info("Le fichier TANE a été mis à jour avec succès")
    
# Ajouter également le nettoyage du fichier temporaire
old_cleanup = """                if os.path.exists(result_file_path):
                    os.remove(result_file_path)"""
                    
new_cleanup = """                if os.path.exists(result_file_path):
                    os.remove(result_file_path)
                    
                # Nettoyer le fichier temporaire si créé
                if 'tmp_csv_file' in locals() and os.path.exists(tmp_csv_file):
                    os.remove(tmp_csv_file)
                    logging.info(f"Fichier temporaire supprimé: {tmp_csv_file}")"""

updated_content = updated_content.replace(old_cleanup, new_cleanup)

# Sauvegarder à nouveau
with open(tane_file, 'w') as f:
    f.write(updated_content)

logger.info("Corrections TANE appliquées")
