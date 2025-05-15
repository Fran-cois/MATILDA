#!/usr/bin/env python3
# fix_fd_all_algorithms.py - Correction de tous les algorithmes FD

import os
import sys
import logging
import subprocess
import time

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Répertoire courant
current_dir = os.path.dirname(os.path.abspath(__file__))

def run_test_script(script_name):
    """Exécute un script Python et retourne True si l'exécution est réussie"""
    logger.info(f"Exécution du script {script_name}...")
    
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logger.info(f"✅ Le script {script_name} a réussi")
        return True
    else:
        logger.error(f"❌ Le script {script_name} a échoué : {result.stderr}")
        return False

def fix_all_algorithms():
    """Corrige tous les algorithmes FD"""
    
    algorithms = ["tane", "aidfd", "pyro", "dfd", "fdep", "fastfds"]
    fixed_count = 0
    
    for algo in algorithms:
        logger.info(f"\n===== Correction de l'algorithme {algo.upper()} =====")
        
        # Chemin du fichier de l'algorithme
        algo_file = os.path.join(current_dir, 'src', 'algorithms', f"{algo}.py")
        
        # Vérifier si le fichier existe
        if not os.path.exists(algo_file):
            logger.error(f"Le fichier {algo_file} n'existe pas")
            continue
        
        # Lire le contenu du fichier
        with open(algo_file, 'r') as f:
            content = f.read()
        
        # Vérifier s'il faut faire la correction
        if "--has-header true" in content:
            # Remplacer --has-header true par --header
            updated_content = content.replace('--has-header true"', '--header"')
            updated_content = updated_content.replace("--has-header true'", "--header'")
            
            # Sauvegarder le fichier mis à jour
            with open(algo_file, 'w') as f:
                f.write(updated_content)
                
            logger.info(f"✅ Correction appliquée à {algo_file} (--has-header true -> --header)")
            fixed_count += 1
        elif "--has-header" in content and not "true" in content.split("--has-header")[1].split('"')[0]:
            # Remplacer --has-header par --header
            updated_content = content.replace('--has-header"', '--header"')
            updated_content = updated_content.replace("--has-header'", "--header'")
            
            # Sauvegarder le fichier mis à jour
            with open(algo_file, 'w') as f:
                f.write(updated_content)
                
            logger.info(f"✅ Correction appliquée à {algo_file} (--has-header -> --header)")
            fixed_count += 1
        else:
            logger.info(f"ℹ️ Aucune correction nécessaire pour {algo_file} (utilise déjà --header)")
    
    return fixed_count

def test_all_algorithms():
    """Teste tous les algorithmes après la correction"""
    logger.info("\n===== Test de tous les algorithmes =====")
    
    # Exécuter le script de test complet
    return run_test_script("test_all_fd_algos.py")

def main():
    logger.info("==== CORRECTION ET TEST DES ALGORITHMES FD ====")
    
    # Correction des algorithmes
    fixed_count = fix_all_algorithms()
    logger.info(f"\n{fixed_count} algorithmes ont été corrigés")
    
    # Attendre un peu pour s'assurer que les modifications sont enregistrées
    time.sleep(1)
    
    # Test des algorithmes
    if test_all_algorithms():
        logger.info("\n✅ Tous les algorithmes fonctionnent correctement après les corrections")
    else:
        logger.error("\n❌ Certains algorithmes présentent encore des problèmes après les corrections")
        logger.info("Consultez les logs pour plus de détails")
    
    logger.info("\n==== FIN DE LA CORRECTION ET DU TEST ====")

if __name__ == "__main__":
    main()
