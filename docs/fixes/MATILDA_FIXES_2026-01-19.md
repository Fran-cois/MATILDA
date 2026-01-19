# MATILDA Fixes - 2026-01-19

## Problèmes corrigés

### 1. ✅ Logging excessif des erreurs FK
**Fichier**: `src/database/alchemy_utility.py` (lignes 223-246)

**Avant**: La méthode `are_foreign_keys()` loggait des ERROR pour chaque colonne qui n'était PAS une FK.

**Après**: Messages maintenant en DEBUG au lieu d'ERROR.

---

### 2. ✅ Logique is_compatible() trop restrictive  
**Fichier**: `src/algorithms/MATILDA/constraint_graph.py` (lignes 23-84)

**Avant**: Retournait `True` UNIQUEMENT pour les foreign keys (ligne 52), ignorant complètement les value overlaps.

**Après**:
- FK check conservé comme bonus de compatibilité
- Value overlap via `has_common_elements_above_threshold()` réactivé  
- Logique complète restaurée (domain checking, numerical types, etc.)
- Threshold abaissé de 10 à 3 pour meilleure sensibilité

**Résultat**: **50 paires compatibles sur Bupa** (au lieu de 1 seule)

---

### 3. ✅ Méthode manquante
**Fichier**: `src/database/alchemy_utility.py` (lignes 218-243)

Ajout de `get_attribute_values()` nécessaire pour le value overlap checking.

---

### 4. ✅ Path pruning trop agressif
**Fichier**: `src/algorithms/MATILDA/tgd_discovery.py` (lignes 421-446)

**Avant**: `path_pruning()` appelait `prediction()` avec threshold=0, éliminant tous les chemins qui ne satisfaisaient pas immédiatement des tuples.

**Après**: Retourne simplement `True` pour permettre l'exploration complète. La validation finale se fait dans `split_pruning()`.

---

## État actuel

### ✅ Ce qui fonctionne:
- Génération d'attributs: 16 attributs sur Bupa
- Compatibilité: 50 paires compatibles trouvées
- JIA list: 468 entrées créées
- Constraint graph: 426 nœuds construits  
- Infrastructure scalabilité: Complète (monitoring, visualization, orchestration)

### ⚠️ Problème restant: 0 règles découvertes

**Observation**: Malgré un graphe de contraintes correctement construit avec 426 nœuds, MATILDA trouve toujours 0 règles en 0.30s.

**Hypothèses**:
1. Le traversal DFS/BFS/A* ne visite pas réellement les nœuds
2. Un check dans `next_node_test()` bloque tous les nœuds  
3. Le générateur Python ne yield rien
4. Problème de configuration (max_table, max_vars)

**Debug ajouté**: Logging dans `graph_traversal.py` pour tracer le nombre de nœuds passés/échoués.

---

## Recommandations

### Option A: Utiliser datasets réels existants
Pour les tests de scalabilité, utiliser les datasets Bupa, Company, etc. déjà validés plutôt que synthétiques.

### Option B: Debug approfondi du traversal  
Investiguer pourquoi `next_node_test()` rejette tous les nœuds initiaux ou pourquoi le générateur ne yield rien.

### Option C: Configuration plus permissive
Tester avec `max_table=10` et `max_vars=20` pour voir si les contraintes sont trop strictes.

---

## Tests de scalabilité

Une fois les règles découvertes, le pipeline complet est prêt :

```bash
# Générer datasets
python3 scripts/utils/generate_with_tgds.py data/large_scale/1M.db --target-tuples 1000000
python3 scripts/utils/generate_with_tgds.py data/large_scale/5M.db --target-tuples 5000000  
python3 scripts/utils/generate_with_tgds.py data/large_scale/10M.db --target-tuples 10000000

# Test unique
PYTHONPATH=$PWD python3 scripts/benchmarks/stress_test.py data/large_scale/1M.db \
  --algorithm astar --heuristic hybrid --timeout 3600

# Suite complète (5 runs)
python3 scripts/benchmarks/run_scalability_tests.py

# Génération visualisations
python3 scripts/utils/visualize_scalability.py results/scalability
python3 scripts/utils/generate_tikz_scalability.py results/scalability
```

---

## Fichiers modifiés

1. `src/database/alchemy_utility.py` - FK logging + get_attribute_values()
2. `src/algorithms/MATILDA/constraint_graph.py` - is_compatible() + threshold
3. `src/algorithms/MATILDA/tgd_discovery.py` - path_pruning()
4. `src/algorithms/MATILDA/graph_traversal.py` - debug logging
5. `scripts/utils/generate_with_tgds.py` - Générateur avec TGDs intégrés (NOUVEAU)
6. `scripts/utils/debug_matilda_init.py` - Script de debug compatibilité (NOUVEAU)
7. `scripts/utils/debug_matilda_full.py` - Script de debug complet (NOUVEAU)
