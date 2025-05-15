#!/usr/bin/env python3
# check_jars.py - Vérifie les JAR disponibles pour les algorithmes Metanome

import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_jars():
    '''Vérifie les JAR disponibles pour les algorithmes Metanome'''
    
    # Répertoire des JAR
    jar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "algorithms", "bins", "metanome")
    
    if not os.path.exists(jar_dir):
        logger.error(f"❌ Répertoire de JAR non trouvé: {jar_dir}")
        return False
    
    # Liste des fichiers JAR
    jar_files = [f for f in os.listdir(jar_dir) if f.endswith('.jar')]
    
    if not jar_files:
        logger.error("❌ Aucun fichier JAR trouvé dans le répertoire")
        return False
    
    logger.info(f"✅ {len(jar_files)} fichiers JAR trouvés:")
    for jar_file in jar_files:
        file_size = os.path.getsize(os.path.join(jar_dir, jar_file))
        logger.info(f"  - {jar_file} ({file_size} octets)")
    
    # Vérifier si les fichiers JAR essentiels sont présents
    essential_jars = [
        "metanome-cli-1.2-SNAPSHOT.jar"
    ]
    
    for jar in essential_jars:
        if jar not in jar_files:
            logger.warning(f"⚠️ JAR essentiel manquant: {jar}")
        else:
            logger.info(f"✅ JAR essentiel présent: {jar}")
    
    # Si les fichiers JAR sont présents mais vides, les télécharger
    for jar_file in jar_files:
        file_path = os.path.join(jar_dir, jar_file)
        if os.path.getsize(file_path) < 1000:  # Moins de 1 Ko, probablement un fichier vide
            logger.warning(f"⚠️ Le fichier JAR {jar_file} semble vide ou invalide")
    
    return True

if __name__ == "__main__":
    check_jars()
