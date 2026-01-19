# 📊 Guide du Système de Coverage MATILDA

## Vue d'ensemble

Le système de coverage compare MATILDA avec d'autres algorithmes de découverte de règles selon deux dimensions :

### Segment 1 : **Rules Match** (Règles correspondantes)
Mesure combien de règles découvertes par l'autre algorithme correspondent à des règles MATILDA.

**Formule**: `Matched Rules / Total Other Rules × 100%`

### Segment 2 : **Completeness** (Complétude sous contrainte de joinabilité)
Mesure la capacité de MATILDA à découvrir les règles "joinables" des autres algorithmes.

**Formule**: `MATILDA Recovered / Joinable Rules × 100%`

---

## 🚀 Utilisation

### Méthode 1 : Calcul Manuel (Données Existantes)

Si vous avez déjà exécuté les benchmarks et avez les fichiers de résultats :

```bash
python3 compute_coverage_metrics.py
```

**Entrées requises** :
- `data/output/MATILDA_{dataset}_results.json`
- `data/output/{ALGORITHM}_{dataset}_results.json` (SPIDER, ANYBURL, POPPER)

**Sorties générées** :
- `data/output/coverage_metrics.json` - Métriques complètes
- `data/output/coverage_table.tex` - Table LaTeX

### Méthode 2 : Benchmark Automatique avec Coverage

Le script `run_full_benchmark.py` calcule automatiquement la coverage :

```bash
# Benchmark complet avec coverage
python3 run_full_benchmark.py --runs 5

# Spécifier algorithmes et datasets
python3 run_full_benchmark.py --runs 5 \
    --algorithms MATILDA SPIDER ANYBURL \
    --datasets BupaImperfect ComparisonDataset

# Désactiver le calcul de coverage
python3 run_full_benchmark.py --runs 5 --no-coverage
```

**Sorties MLflow** :
```
data/output/mlruns/<experiment_id>/
├── coverage_metrics.json
├── coverage_table.tex
├── experiment_meta.json
├── runs.json
└── summary.json
```

---

## 📐 Algorithme de Matching

### Pour SPIDER (Inclusion Dependencies)

```python
def match_spider_ind(tgd_rule, ind_rule):
    """
    Un TGD MATILDA match un IND SPIDER si :
    - Le TGD implique les mêmes tables (dependant et referenced)
    """
    tgd_tables = extract_tables(tgd_rule)
    ind_tables = {ind_rule['table_dependant'], ind_rule['table_referenced']}
    
    return ind_tables.issubset(tgd_tables)
```

**Exemple** :
- SPIDER IND: `bupa.arg1 ⊆ drinks.arg1`
- MATILDA TGD: `∀ x0: bupa_0(arg1=x0) ⇒ drinks_0(arg1=x0)`
- ✅ **Match** : Les deux impliquent tables `bupa` et `drinks`

### Pour ANYBURL/POPPER (TGD/Horn Rules)

```python
def match_tgd_tgd(tgd1, tgd2):
    """
    Deux TGDs matchent si :
    - Ils partagent au moins 80% des tables impliquées
    """
    tables1 = extract_tables(tgd1)
    tables2 = extract_tables(tgd2)
    
    overlap = len(tables1 & tables2)
    min_size = min(len(tables1), len(tables2))
    
    return (overlap / min_size) >= 0.8
```

---

## 🔍 Contrainte de Joinabilité

Une règle est considérée **joinable** si :

### Pour INDs (SPIDER)
- Les tables dependant et referenced peuvent être jointes
- **Simplifié** : Tous les INDs sont considérés joinables par défaut

### Pour TGDs (MATILDA, ANYBURL, POPPER)
- Le body et le head partagent au moins une variable commune
- **Formule** : `len(body_vars ∩ head_vars) > 0`

**Exemple joinable** :
```
∀ x0: bupa_0(arg1=x0) ⇒ drinks_0(arg1=x0)
```
✅ Variable `x0` partagée entre body et head

**Exemple non-joinable** :
```
∀ x0, x1: bupa_0(arg1=x0) ⇒ drinks_0(arg1=x1)
```
❌ Pas de variable commune (x0 ≠ x1)

---

## 📊 Format de Sortie

### Coverage Metrics JSON

```json
{
  "algorithm": "SPIDER",
  "dataset": "BupaImperfect",
  "matilda_total": 9,
  "other_total": 50,
  "rules_match_count": 3,
  "rules_match_percentage": 6.0,
  "joinable_rules_count": 50,
  "matilda_recovered_count": 3,
  "completeness_percentage": 6.0
}
```

### Coverage Table LaTeX

```latex
\begin{table}[htbp]
\centering
\caption{MATILDA Coverage Comparison}
\begin{tabular}{llrrrrrr}
\textbf{Dataset} & \textbf{Algorithm} & 
\textbf{\#MATILDA} & \textbf{\#Other} & 
\multicolumn{2}{c}{\textbf{Rules Match}} & 
\multicolumn{2}{c}{\textbf{Completeness}} \\
 & & & & \textbf{Count} & \textbf{\%} & \textbf{Count} & \textbf{\%} \\
\hline
BupaImperfect & SPIDER & 9 & 50 & 3 & 6.0\% & 3 & 6.0\% \\
\end{tabular}
\end{table}
```

---

## 📈 Interprétation des Résultats

### Exemple de Résultats

```
Dataset: BupaImperfect
Algorithm: SPIDER

MATILDA rules: 9
SPIDER rules: 50

Segment 1 - Rules Match:
  Matched: 3/50 (6.0%)
  
Segment 2 - Completeness:
  Joinable rules: 50
  MATILDA recovered: 3/50 (6.0%)
```

### Analyse

1. **Rules Match: 6.0%**
   - 3 des 50 règles SPIDER ont une correspondance dans MATILDA
   - **Interprétation** : MATILDA découvre un sous-ensemble des règles SPIDER
   - **Cause possible** : MATILDA est plus sélectif (filtre sur accuracy/confidence)

2. **Completeness: 6.0%**
   - Toutes les 50 règles SPIDER sont joinables
   - MATILDA a récupéré 3 de ces règles joinables
   - **Interprétation** : MATILDA a une coverage de 6% pour les règles joinables
   - **Cause possible** : Différences dans les critères de découverte

---

## 🎯 Cas d'Usage

### 1. Validation de l'Approche MATILDA

**Question** : MATILDA découvre-t-il les mêmes types de dépendances que SPIDER ?

**Méthode** :
```bash
python3 compute_coverage_metrics.py
```

**Analyse** :
- Rules Match élevé (>50%) → Bonne convergence
- Rules Match faible (<20%) → Approches différentes
- Completeness élevé → MATILDA capture l'essentiel
- Completeness faible → MATILDA manque des dépendances

### 2. Comparaison Multi-Algorithmes

**Question** : Quel algorithme a la meilleure couverture par rapport à MATILDA ?

**Méthode** :
```bash
python3 run_full_benchmark.py --runs 5 \
    --algorithms MATILDA SPIDER ANYBURL POPPER \
    --datasets BupaImperfect ComparisonDataset
```

**Analyse** :
Comparer les pourcentages de coverage pour identifier :
- L'algorithme le plus proche de MATILDA
- Les types de règles manquées par MATILDA
- Les avantages/inconvénients de chaque approche

### 3. Amélioration de MATILDA

**Question** : Quelles règles MATILDA ne découvre-t-il pas ?

**Méthode** :
1. Exécuter `compute_coverage_metrics.py` avec `verbose=True`
2. Examiner les règles non-matchées dans les logs
3. Analyser pourquoi MATILDA les a manquées

**Actions** :
- Ajuster les seuils de confidence/accuracy
- Modifier l'algorithme de traversal (DFS → BFS → A*)
- Étendre les patterns de règles recherchés

---

## 🔧 Paramètres de Configuration

### Dans run_full_benchmark.py

```python
runner = FullBenchmarkRunner(
    runs=5,                              # Nombre de runs par combinaison
    algorithms=['MATILDA', 'SPIDER'],    # Algorithmes à comparer
    datasets=['BupaImperfect'],          # Datasets à tester
    compute_coverage=True,               # Activer coverage (défaut: True)
    verbose=True                         # Logs détaillés
)
```

### Dans compute_coverage_metrics.py

```python
matcher = RuleMatcher(verbose=True)  # Logs détaillés du matching

# Ajuster les seuils
def tgd_matches_tgd(self, tgd1, tgd2):
    overlap_threshold = 0.8  # 80% de tables communes (réglable)
    return (overlap / min_size) >= overlap_threshold
```

---

## 📚 Structure des Règles

### MATILDA TGD Rule

```json
{
  "type": "TGDRule",
  "body": [
    "Predicate(variable1='arg1', relation='bupa_0', variable2='x0')"
  ],
  "head": [
    "Predicate(variable1='arg1', relation='drinks_0', variable2='x0')"
  ],
  "display": "∀ x0: bupa_0(arg1=x0) ⇒ drinks_0(arg1=x0)",
  "accuracy": 1.0,
  "confidence": 1.0
}
```

### SPIDER IND Rule

```json
{
  "type": "InclusionDependency",
  "table_dependant": "bupa",
  "columns_dependant": ["arg1"],
  "table_referenced": "drinks",
  "columns_referenced": ["arg1"]
}
```

### ANYBURL/POPPER TGD Rule

```json
{
  "type": "TGDRule",
  "body": [...],
  "head": [...],
  "display": "bupa(A,B) :- drinks(A), sgot(B)",
  "accuracy": 0.85,
  "confidence": 0.92
}
```

---

## 🛠️ Troubleshooting

### Problème 1 : Aucune correspondance trouvée (0%)

**Causes possibles** :
1. Les règles sont dans des formats incompatibles
2. Les noms de tables ne correspondent pas (casse, préfixes)
3. Les algorithmes découvrent des types de règles très différents

**Solutions** :
1. Vérifier la normalisation des noms de tables
2. Affiner les critères de matching
3. Examiner manuellement quelques règles des deux côtés

### Problème 2 : Coverage très élevée (>90%)

**Causes possibles** :
1. Critères de matching trop permissifs
2. Les algorithmes sont très similaires
3. Dataset simple avec peu de variabilité

**Actions** :
1. Augmenter le seuil de matching (0.8 → 0.9)
2. Ajouter des critères supplémentaires (colonnes, variables)
3. Tester sur des datasets plus complexes

### Problème 3 : Fichiers de résultats manquants

**Erreur** : `⚠️ Results file not found`

**Solutions** :
```bash
# 1. Vérifier les fichiers existants
ls -lh data/output/*_results.json

# 2. Réexécuter les benchmarks manquants
cd src && python3 main.py --algorithm SPIDER --database BupaImperfect

# 3. Ou utiliser les résultats MLflow
python3 mlflow_explorer.py list
python3 mlflow_explorer.py show <experiment_id>
```

---

## 📖 Références

### Scripts Principaux

1. **`compute_coverage_metrics.py`** (~400 lignes)
   - Calcul standalone de coverage
   - Lecture des résultats existants
   - Génération de table LaTeX

2. **`run_full_benchmark.py`** (~1000 lignes)
   - Benchmark complet automatisé
   - Intégration MLflow
   - Coverage automatique

3. **`mlflow_explorer.py`** (~450 lignes)
   - Exploration des expériences
   - Visualisation des métriques
   - Comparaison d'expériences

### Méthodes Clés

- `compute_coverage_metrics()` - Calcul principal
- `tgd_matches_ind()` - Matching TGD ↔ IND
- `tgd_matches_tgd()` - Matching TGD ↔ TGD
- `is_joinable()` - Vérification joinabilité
- `generate_coverage_table()` - Génération LaTeX

---

## ✅ Checklist d'Utilisation

Avant d'exécuter l'analyse de coverage :

- [ ] Fichiers de résultats MATILDA présents
- [ ] Fichiers de résultats autres algorithmes présents
- [ ] Formats JSON valides (vérifier avec `jq .` ou `python -m json.tool`)
- [ ] Noms de datasets cohérents
- [ ] Suffisamment de règles découvertes (>0)

Après exécution :

- [ ] `coverage_metrics.json` généré
- [ ] `coverage_table.tex` généré
- [ ] Logs examninés pour warnings
- [ ] Résultats cohérents (0-100%)
- [ ] Table LaTeX compilable

---

**🎉 Système de Coverage MATILDA opérationnel !**

Pour questions ou améliorations, voir la documentation complète ou les exemples dans `data/output/`.
