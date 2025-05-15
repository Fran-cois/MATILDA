import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from algorithms.aidfd import AIDFD
from algorithms.pyro import Pyro
from utils.rules_classes.functional_dependency import FunctionalDependency

@pytest.fixture
def mock_database():
    db = MagicMock()
    
    # Créer une table de test avec des dépendances fonctionnelles évidentes
    # Employee(id, name, department, manager_id)
    # FD1: id -> name
    # FD2: id -> department
    # FD3: department -> manager_id
    test_data = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'department': ['IT', 'HR', 'IT', 'Finance', 'HR'],
        'manager_id': [101, 102, 101, 103, 102]
    })
    
    db.get_table_names.return_value = ['employees']
    db.get_table_data.return_value = test_data
    
    return db

def test_aidfd_discovery(mock_database):
    """Test the AIDFD algorithm for functional dependency discovery."""
    # Initialiser l'algorithme
    aidfd = AIDFD(mock_database)
    
    # Configurer les paramètres pour le test
    discovered_fds = aidfd.discover_rules(min_support=0.5, min_confidence=0.9)
    
    # Vérifier que des FDs ont été découvertes
    assert len(discovered_fds) > 0
    
    # Vérifier que toutes les FDs sont du bon type
    for fd in discovered_fds:
        assert isinstance(fd, FunctionalDependency)
    
    # Vérifier que les FDs attendues sont présentes
    expected_fds = [
        ('employees', ['id'], 'name'),
        ('employees', ['id'], 'department'),
        ('employees', ['department'], 'manager_id')
    ]
    
    fd_tuples = [(fd.table, fd.lhs, fd.rhs) for fd in discovered_fds]
    
    for expected in expected_fds:
        found = False
        for actual in fd_tuples:
            if (expected[0] == actual[0] and 
                set(expected[1]) == set(actual[1]) and 
                expected[2] == actual[2]):
                found = True
                break
        assert found, f"Expected FD {expected} not found in {fd_tuples}"

def test_pyro_discovery(mock_database):
    """Test the Pyro algorithm for functional dependency discovery."""
    # Initialiser l'algorithme
    pyro = Pyro(mock_database)
    
    # Configurer les paramètres pour le test
    discovered_fds = pyro.discover_rules(min_support=0.5)
    
    # Vérifier que des FDs ont été découvertes
    assert len(discovered_fds) > 0
    
    # Vérifier que toutes les FDs sont du bon type
    for fd in discovered_fds:
        assert isinstance(fd, FunctionalDependency)
    
    # Vérifier que les FDs attendues sont présentes
    expected_fds = [
        ('employees', ['id'], 'name'),
        ('employees', ['id'], 'department'),
        ('employees', ['department'], 'manager_id')
    ]
    
    fd_tuples = [(fd.table, fd.lhs, fd.rhs) for fd in discovered_fds]
    
    for expected in expected_fds:
        found = False
        for actual in fd_tuples:
            if (expected[0] == actual[0] and 
                set(expected[1]) == set(actual[1]) and 
                expected[2] == actual[2]):
                found = True
                break
        assert found, f"Expected FD {expected} not found in {fd_tuples}"

def test_fd_comparison():
    """Test comparison between different FD algorithms."""
    # Créer des FDs identiques avec des métriques différentes
    fd1 = FunctionalDependency('table1', ['a', 'b'], 'c', support=0.8, confidence=0.9)
    fd2 = FunctionalDependency('table1', ['a', 'b'], 'c', support=0.7, confidence=0.8)
    fd3 = FunctionalDependency('table1', ['a'], 'c', support=0.6, confidence=0.7)
    
    # Vérifier l'égalité
    assert fd1 == fd2
    assert fd1 != fd3
    
    # Vérifier les représentations
    assert str(fd1) == "table1: a, b → c"
    assert "support=0.80" in repr(fd1)
