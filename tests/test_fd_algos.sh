#!/usr/bin/env python3
# Exécuter les tests pour vérifier notre solution de repli

# Testez d'abord TANE
python -c """
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Chemin du JAR Metanome dans notre dossier bins/metanome, créons-le s'il n'existe pas
os.makedirs('src/algorithms/bins/metanome', exist_ok=True)

class MockDatabase:
    def __init__(self):
        self.base_csv_dir = 'test_data'
        
# Créer un petit fichier CSV pour le test
os.makedirs('test_data', exist_ok=True)
with open('test_data/test_fd.csv', 'w') as f:
    f.write('id,name,age,city,country\\n')
    f.write('1,Alice,30,Paris,France\\n')
    f.write('2,Bob,25,Lyon,France\\n')
    f.write('3,Charlie,35,Paris,France\\n')
    f.write('4,David,40,Berlin,Germany\\n')
    f.write('5,Eve,28,Madrid,Spain\\n')

from src.algorithms.tane import Tane
print('\\n===== Test TANE =====')
tane = Tane(MockDatabase())
result = tane.discover_rules(use_fallback=True)
print(f'Résultat TANE: {result}')
"""

# Testez DFD
python -c """
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Chemin du JAR Metanome dans notre dossier bins/metanome, créons-le s'il n'existe pas
os.makedirs('src/algorithms/bins/metanome', exist_ok=True)

class MockDatabase:
    def __init__(self):
        self.base_csv_dir = 'test_data'
        
# Créer un petit fichier CSV pour le test s'il n'existe pas déjà
os.makedirs('test_data', exist_ok=True)
if not os.path.exists('test_data/test_fd.csv'):
    with open('test_data/test_fd.csv', 'w') as f:
        f.write('id,name,age,city,country\\n')
        f.write('1,Alice,30,Paris,France\\n')
        f.write('2,Bob,25,Lyon,France\\n')
        f.write('3,Charlie,35,Paris,France\\n')
        f.write('4,David,40,Berlin,Germany\\n')
        f.write('5,Eve,28,Madrid,Spain\\n')

from src.algorithms.dfd import DFD
print('\\n===== Test DFD =====')
dfd = DFD(MockDatabase())
result = dfd.discover_rules(use_fallback=True)
print(f'Résultat DFD: {result}')
"""

# Testez FastFDs
python -c """
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Chemin du JAR Metanome dans notre dossier bins/metanome, créons-le s'il n'existe pas
os.makedirs('src/algorithms/bins/metanome', exist_ok=True)

class MockDatabase:
    def __init__(self):
        self.base_csv_dir = 'test_data'
        
# Créer un petit fichier CSV pour le test s'il n'existe pas déjà
os.makedirs('test_data', exist_ok=True)
if not os.path.exists('test_data/test_fd.csv'):
    with open('test_data/test_fd.csv', 'w') as f:
        f.write('id,name,age,city,country\\n')
        f.write('1,Alice,30,Paris,France\\n')
        f.write('2,Bob,25,Lyon,France\\n')
        f.write('3,Charlie,35,Paris,France\\n')
        f.write('4,David,40,Berlin,Germany\\n')
        f.write('5,Eve,28,Madrid,Spain\\n')

from src.algorithms.fastfds import FastFDs
print('\\n===== Test FastFDs =====')
fastfds = FastFDs(MockDatabase())
result = fastfds.discover_rules(use_fallback=True)
print(f'Résultat FastFDs: {result}')
"""

# Testez FDep
python -c """
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Chemin du JAR Metanome dans notre dossier bins/metanome, créons-le s'il n'existe pas
os.makedirs('src/algorithms/bins/metanome', exist_ok=True)

class MockDatabase:
    def __init__(self):
        self.base_csv_dir = 'test_data'
        
# Créer un petit fichier CSV pour le test s'il n'existe pas déjà
os.makedirs('test_data', exist_ok=True)
if not os.path.exists('test_data/test_fd.csv'):
    with open('test_data/test_fd.csv', 'w') as f:
        f.write('id,name,age,city,country\\n')
        f.write('1,Alice,30,Paris,France\\n')
        f.write('2,Bob,25,Lyon,France\\n')
        f.write('3,Charlie,35,Paris,France\\n')
        f.write('4,David,40,Berlin,Germany\\n')
        f.write('5,Eve,28,Madrid,Spain\\n')

from src.algorithms.fdep import FDep
print('\\n===== Test FDep =====')
fdep = FDep(MockDatabase())
result = fdep.discover_rules()
print(f'Résultat FDep: {result}')
"""
