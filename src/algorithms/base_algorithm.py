"""
Classe de base pour tous les algorithmes de découverte de règles.
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional, Dict, Any

from utils.rules import Rule
from database.alchemy_utility import AlchemyUtility

class BaseAlgorithm(ABC):
    """
    Classe abstraite de base pour les algorithmes de découverte de règles.
    Tous les algorithmes spécifiques doivent hériter de cette classe.
    """
    
    def __init__(self, database: Any, settings: Optional[Dict[str, Any]] = None):
        """
        Initialise l'algorithme avec une base de données et des paramètres.
        
        :param database: L'objet de connexion à la base de données.
        :param settings: Paramètres optionnels pour l'algorithme.
        """
        self.database = database
        self.settings = settings or {}
    
    @abstractmethod
    def discover_rules(self, **kwargs) -> Generator[Rule, None, None]:
        """
        Méthode principale pour découvrir des règles dans la base de données.
        
        :param kwargs: Arguments optionnels spécifiques à l'implémentation de l'algorithme.
        :return: Un générateur produisant les règles découvertes.
        """
        pass
    
    def validate_settings(self) -> Dict[str, Any]:
        """
        Valide les paramètres actuels et retourne les erreurs ou avertissements.
        
        :return: Un dictionnaire contenant les résultats de la validation.
        """
        return {
            'valid': True,
            'errors': [],
            'warnings': []
        }
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        Retourne les paramètres par défaut recommandés pour cet algorithme.
        
        :return: Un dictionnaire des paramètres par défaut.
        """
        return {}
    
    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour les paramètres actuels avec de nouveaux paramètres.
        
        :param new_settings: Les nouveaux paramètres à appliquer.
        :return: Les paramètres mis à jour.
        """
        self.settings.update(new_settings)
        return self.settings
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """
        Retourne des informations sur l'algorithme actuel.
        
        :return: Un dictionnaire d'informations sur l'algorithme.
        """
        return {
            'name': self.__class__.__name__,
            'description': self.__doc__ or "No description available."
        }
