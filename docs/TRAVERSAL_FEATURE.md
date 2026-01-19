# Nouvelle Fonctionnalité : Algorithmes de Traversée de Graphe

## Résumé des Modifications

MATILDA supporte maintenant **trois algorithmes de traversée de graphe** pour explorer l'espace des règles candidates :

1. **DFS (Depth-First Search)** - Par défaut, comportement original
2. **BFS (Breadth-First Search)** - Nouveau, exploration niveau par niveau
3. **A-star (A*)** - Nouveau, recherche guidée par heuristique

## Fichiers Modifiés

### Nouveaux Fichiers

- **`src/algorithms/MATILDA/graph_traversal.py`** - Module contenant les trois algorithmes de traversée
- **`GRAPH_TRAVERSAL_ALGORITHMS.md`** - Documentation détaillée des algorithmes
- **`test_traversal.py`** - Tests unitaires pour les algorithmes
- **`demo_traversal.py`** - Script de démonstration comparant les algorithmes

### Fichiers Modifiés

- **`src/algorithms/MATILDA/tgd_discovery.py`**
  - Import du nouveau module `graph_traversal`
  - Refactoring de `dfs()` pour déléguer au nouveau module
  - Ajout de fonctions `bfs()`, `astar()`, et `traverse_graph()`
  - Compatibilité arrière maintenue pour le code existant

- **`src/algorithms/matilda.py`**
  - Ajout du support pour le paramètre `traversal_algorithm`
  - Extraction de l'algorithme depuis la configuration
  - Logs pour indiquer l'algorithme utilisé

- **`src/main.py`**
  - Ajout du paramètre `config` à `DatabaseProcessor`
  - Transmission du paramètre `traversal_algorithm` à MATILDA
  - Support de la configuration par fichier YAML

- **`src/config.yaml`**
  - Nouvelle section `algorithm.matilda` avec `traversal_algorithm`
  - Documentation des options disponibles

## Utilisation

### Option 1 : Via Configuration (Recommandé)

Modifier `src/config.yaml` :

```yaml
algorithm:
  name: "MATILDA"
  matilda:
    traversal_algorithm: "dfs"  # Options: "dfs", "bfs", "astar"
```

Puis exécuter :

```bash
python src/main.py
```

### Option 2 : Par Programmation

```python
from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

db = AlchemyUtility("sqlite:///data/db/Bupa.db")
matilda = MATILDA(db)

# Utiliser BFS
rules = matilda.discover_rules(
    traversal_algorithm="bfs",
    max_table=3,
    max_vars=6
)
```

### Option 3 : Utilisation Directe

```python
from algorithms.MATILDA.tgd_discovery import init, traverse_graph, path_pruning

cg, mapper, jia_list = init(db_inspector, max_nb_occurrence=3)

# Utiliser A-star
for candidate_rule in traverse_graph(
    cg, None, path_pruning, db_inspector, mapper,
    max_table=3, max_vars=6, algorithm="astar"
):
    # Traiter la règle
    pass
```

## Tests

### Tests Unitaires

```bash
python test_traversal.py
```

Ce script vérifie :
- Les imports fonctionnent correctement
- La sélection d'algorithme fonctionne
- La configuration est valide

### Démonstration Comparative

```bash
python demo_traversal.py
```

Ce script compare les trois algorithmes sur une base de données de test.

## Comparaison des Algorithmes

| Caractéristique | DFS | BFS | A-star |
|----------------|-----|-----|--------|
| Mémoire | ✓ Faible | ✗ Élevée | ~ Moyenne |
| Règles simples d'abord | ✗ | ✓ | ~ |
| Règles complexes | ✓ Rapide | ✗ Lent | ✓ Rapide |
| Règles de qualité | ~ | ~ | ✓✓ |
| Complétude | ✓ | ✓ | ~ (dépend de l'heuristique) |

### Quand Utiliser Quel Algorithme ?

**DFS (par défaut)** :
- ✓ Comportement original de MATILDA
- ✓ Bon équilibre général
- ✓ Faible consommation mémoire
- ✓ Trouve les règles complexes rapidement

**BFS** :
- ✓ Vous voulez les règles simples en premier
- ✓ Exploration systématique
- ✓ Analyse complète requise
- ✗ Peut être lent sur de grandes bases

**A-star** :
- ✓ Optimisation pour trouver les meilleures règles
- ✓ Temps de découverte réduit pour les règles de qualité
- ✓ Bon compromis exploration/exploitation
- ~ L'heuristique par défaut favorise les règles courtes

## Architecture

```
src/algorithms/MATILDA/
├── graph_traversal.py          # Nouveau : Algorithmes de traversée
│   ├── dfs()                   # Implémentation DFS
│   ├── bfs()                   # Implémentation BFS
│   ├── astar()                 # Implémentation A-star
│   └── get_traversal_algorithm() # Factory function
│
├── tgd_discovery.py            # Modifié
│   ├── dfs()                   # Wrapper vers graph_traversal.dfs
│   ├── bfs()                   # Nouveau wrapper
│   ├── astar()                 # Nouveau wrapper
│   └── traverse_graph()        # Nouvelle fonction générique
│
└── constraint_graph.py         # Inchangé
```

## Compatibilité

✅ **Compatibilité arrière maintenue**

Le code existant utilisant `dfs()` directement continue de fonctionner sans modification. Les fonctions `bfs()` et `astar()` sont de nouvelles additions.

## Personnalisation A-star

Vous pouvez définir votre propre heuristique pour A-star :

```python
def custom_heuristic(candidate_rule, mapper, db_inspector):
    """
    Heuristique personnalisée.
    Retourne un score (plus élevé = meilleur).
    """
    # Exemple : favoriser les règles avec moins de tables
    num_tables = len(set((a.i, a.j) for jia in candidate_rule for a in jia))
    return 1.0 / num_tables  # Plus de tables = score plus bas

# Utiliser
from algorithms.MATILDA.tgd_discovery import astar

for rule in astar(cg, None, path_pruning, db, mapper, 
                  heuristic_func=custom_heuristic):
    # ...
```

## Performance

Les performances relatives dépendent de :
- Taille de la base de données
- Complexité du schéma
- Paramètres `max_table` et `max_vars`
- Type de règles recherchées

Il est recommandé de tester les trois algorithmes sur vos données spécifiques.

## Contribution

Cette implémentation est modulaire et extensible. Pour ajouter un nouvel algorithme de traversée :

1. Ajouter la fonction dans `graph_traversal.py`
2. Suivre la même signature que `dfs()`, `bfs()`, `astar()`
3. Ajouter l'entrée dans `get_traversal_algorithm()`
4. Créer un wrapper dans `tgd_discovery.py` si nécessaire

## Documentation Complète

Voir [GRAPH_TRAVERSAL_ALGORITHMS.md](GRAPH_TRAVERSAL_ALGORITHMS.md) pour une documentation détaillée incluant :
- Descriptions approfondies de chaque algorithme
- Exemples d'utilisation
- Guide de configuration
- Personnalisation des heuristiques
- Comparaisons de performance

## Questions / Support

Pour des questions sur cette fonctionnalité, consultez :
1. [GRAPH_TRAVERSAL_ALGORITHMS.md](GRAPH_TRAVERSAL_ALGORITHMS.md) - Documentation détaillée
2. `test_traversal.py` - Tests et exemples
3. `demo_traversal.py` - Démonstration comparative
