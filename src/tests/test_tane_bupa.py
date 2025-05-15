"""
Script de test pour l'algorithme Tane sur la base de données Bupa.
Exécute Tane et affiche les dépendances fonctionnelles découvertes.
"""

import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin Python pour les imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from algorithms.tane import Tane
from database.alchemy_utility import AlchemyUtility

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tane_on_bupa():
    """
    Teste l'algorithme Tane sur la base de données Bupa.
    """
    # Chemin vers la base de données Bupa
    db_path = Path(parent_dir).parent / "data" / "db" / "Bupa.db"
    
    # Vérifier si la base de données existe
    if not db_path.exists():
        logger.error(f"Base de données introuvable: {db_path}")
        return
    
    logger.info(f"Utilisation de la base de données: {db_path}")
    
    # Connexion à la base de données
    db_uri = f"sqlite:///{db_path}"
    
    try:
        with AlchemyUtility(db_uri, database_path=str(db_path.parent), create_index=False) as db_util:
            # Créer une instance de Tane
            tane = Tane(db_util)
            
            # Exécuter l'algorithme
            logger.info("Lancement de l'algorithme Tane sur Bupa.db...")
            rules = tane.discover_rules()
            
            # Afficher les résultats
            logger.info(f"Nombre total de dépendances fonctionnelles découvertes: {len(rules)}")
            
            # Afficher les règles découvertes
            for i, (rule, (support, confidence)) in enumerate(rules.items(), 1):
                logger.info(f"Règle {i}: {rule} (support: {support}, confiance: {confidence})")
            
            logger.info("Test terminé.")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de Tane: {e}")

if __name__ == "__main__":
    test_tane_on_bupa()
