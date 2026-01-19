# Algorithmes de Traversée de Graphe pour MATILDA

MATILDA supporte maintenant trois algorithmes différents pour explorer le graphe de contraintes :

## 1. DFS (Depth-First Search) - Par défaut

**Description :** Explore en profondeur avant de revenir en arrière.

**Avantages :**
- Trouve rapidement des règles profondes et complexes
- Utilise moins de mémoire que BFS
- Bon pour découvrir des dépendances en chaîne

**Inconvénients :**
- Peut manquer des règles courtes initialement
- Peut explorer des branches non prometteuses en profondeur

**Quand l'utiliser :**
- Lorsque vous cherchez des règles complexes avec plusieurs tables
- Lorsque la mémoire est limitée
- Comportement par défaut de MATILDA

## 2. BFS (Breadth-First Search)

**Description :** Explore tous les voisins au même niveau avant de passer au niveau suivant.

**Avantages :**
- Trouve les règles les plus courtes en premier
- Exploration systématique de l'espace de recherche
- Bon pour trouver toutes les règles simples

**Inconvénients :**
- Utilise plus de mémoire (stocke tous les nœuds d'un niveau)
- Peut être plus lent pour trouver des règles complexes

**Quand l'utiliser :**
- Lorsque vous voulez d'abord les règles simples
- Pour une exploration exhaustive niveau par niveau
- Lorsque vous avez suffisamment de mémoire

## 3. A-star (A*)

**Description :** Utilise une fonction heuristique pour prioriser les règles prometteuses.

**Avantages :**
- Trouve les règles de haute qualité plus rapidement
- Optimise l'exploration en fonction de métriques (support/confiance)
- Équilibre entre profondeur et largeur

**Inconvénients :**
- Légèrement plus coûteux en calcul (évaluation heuristique)
- Le choix de l'heuristique affecte les résultats

**Quand l'utiliser :**
- Lorsque vous cherchez des règles de haute qualité
- Pour optimiser le temps de découverte des meilleures règles
- Lorsque vous avez une bonne fonction heuristique

## Configuration

### Dans config.yaml :

```yaml
algorithm:
  name: "MATILDA"
  matilda:
    traversal_algorithm: "dfs"  # Options: "dfs", "bfs", "astar"
```

### Par programmation :

```python
from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Initialiser la base de données
db = AlchemyUtility("sqlite:///path/to/db.db")

# Utiliser MATILDA avec BFS
matilda = MATILDA(db)
rules = list(matilda.discover_rules(
    traversal_algorithm="bfs",
    max_table=3,
    max_vars=6
))

# Utiliser MATILDA avec A-star
rules = list(matilda.discover_rules(
    traversal_algorithm="astar",
    max_table=3,
    max_vars=6
))
```

## Comparaison des Performances

| Algorithme | Mémoire | Vitesse (règles simples) | Vitesse (règles complexes) | Complétude |
|-----------|---------|-------------------------|---------------------------|-----------|
| DFS       | Faible  | Moyenne                 | Rapide                    | Oui       |
| BFS       | Élevée  | Rapide                  | Lente                     | Oui       |
| A-star    | Moyenne | Très rapide (qualité)   | Rapide (qualité)          | Partielle* |

*A-star explore en priorité les chemins prometteurs, donc la complétude dépend de l'heuristique.

## Exemples d'Utilisation

### Exemple 1 : Règles simples avec BFS

```yaml
algorithm:
  name: "MATILDA"
  matilda:
    traversal_algorithm: "bfs"
```

```bash
python src/main.py
```

### Exemple 2 : Règles optimales avec A-star

```yaml
algorithm:
  name: "MATILDA"
  matilda:
    traversal_algorithm: "astar"
```

### Exemple 3 : Comportement par défaut (DFS)

```yaml
algorithm:
  name: "MATILDA"
  # traversal_algorithm non spécifié = DFS par défaut
```

## Architecture

Les algorithmes de traversée sont implémentés dans :
- **Module principal :** `src/algorithms/MATILDA/graph_traversal.py`
- **Intégration :** `src/algorithms/MATILDA/tgd_discovery.py`
- **Interface :** `src/algorithms/matilda.py`

Chaque algorithme suit la même interface et peut être facilement échangé sans modifier le reste du code.

## Fonction Heuristique pour A-star

La fonction heuristique par défaut pour A-star privilégie les règles plus courtes. Vous pouvez personnaliser l'heuristique en passant une fonction personnalisée :

```python
def custom_heuristic(candidate_rule, mapper, db_inspector):
    """
    Heuristique personnalisée basée sur la qualité estimée.
    Retourne un score (plus élevé = meilleur).
    """
    # Exemple : favoriser les règles avec moins de tables
    num_tables = len(set((attr.i, attr.j) for jia in candidate_rule for attr in jia))
    return -num_tables  # Négatif car A-star minimise le coût

# Utiliser l'heuristique personnalisée
from algorithms.MATILDA.tgd_discovery import astar, path_pruning

for rule in astar(
    constraint_graph, 
    None, 
    path_pruning,
    db_inspector, 
    mapper,
    heuristic_func=custom_heuristic
):
    # Traiter la règle
    pass
```

## Notes Importantes

1. **Compatibilité :** Le code existant utilisant `dfs()` continue de fonctionner sans modification.

2. **Performance :** Le choix de l'algorithme peut avoir un impact significatif sur les performances selon la taille et la structure de votre base de données.

3. **Résultats :** Les trois algorithmes trouvent les mêmes règles valides, mais dans un ordre différent. Seul A-star peut ne pas explorer toutes les branches si l'heuristique écarte des chemins.

4. **Debugging :** Pour comparer les résultats, exécutez MATILDA avec chaque algorithme sur la même base de données et comparez les règles découvertes.
