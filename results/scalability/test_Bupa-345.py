
import sys
import time
import os

# Add src to path using absolute path
project_root = r'/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA'
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Use absolute path for database
db_abs_path = os.path.join(project_root, '/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/input/Bupa.db')

start = time.time()
db = AlchemyUtility(f'sqlite:///{db_abs_path}')
m = MATILDA(db, {'nb_occurrence': 3, 'max_table': 3, 'max_vars': 4})
rules = list(m.discover_rules(traversal_algorithm='dfs', max_table=3, max_vars=4))
runtime = time.time() - start

print(f'RULES:{len(rules)}')
print(f'RUNTIME:{runtime:.2f}')
