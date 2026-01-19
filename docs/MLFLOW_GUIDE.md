# 📊 MLflow-like Experiment Tracking Guide

## Vue d'ensemble

Le système de benchmarking MATILDA suit maintenant une architecture MLflow avec :

- **Expériences** : Regroupent plusieurs runs (exécutions)
- **Runs** : Exécutions individuelles avec params, métriques et artefacts
- **Métriques** : Valeurs numériques trackées (accuracy, time, etc.)
- **Paramètres** : Configuration (algorithm, dataset, timeout)
- **Artefacts** : Fichiers générés (tables LaTeX, règles JSON)

---

## 🚀 Quick Start

### Lancer un Benchmark

```bash
# Benchmark avec nom d'expérience personnalisé
python3 run_full_benchmark.py --runs 5 --experiment-name "comparison_all_algos"

# Benchmark avec configuration par défaut
python3 run_full_benchmark.py --runs 5
```

### Explorer les Résultats

```bash
# Lister toutes les expériences
python3 mlflow_explorer.py list

# Voir les détails d'une expérience
python3 mlflow_explorer.py show <experiment_id>

# Lister les runs d'une expérience
python3 mlflow_explorer.py runs <experiment_id>

# Comparer deux expériences
python3 mlflow_explorer.py compare <exp_id1> <exp_id2>
```

---

## 📁 Structure des Fichiers

### Organisation MLflow

```
data/output/mlruns/
├── <experiment_id>/                    # Un répertoire par expérience
│   ├── experiment_meta.json           # Métadonnées de l'expérience
│   ├── runs.json                      # Tous les runs de l'expérience
│   ├── summary.json                   # Statistiques agrégées
│   ├── benchmark_table_*.tex          # Table LaTeX générée
│   │
│   └── <run_id>/                      # Un répertoire par run
│       ├── run_info.json              # Info du run (status, times)
│       ├── params.json                # Paramètres du run
│       ├── metrics.json               # Métriques du run
│       └── rules.json                 # Règles découvertes
```

### Fichiers Principaux

#### `experiment_meta.json`
```json
{
  "experiment_id": "f1f769ba",
  "name": "comparison_all_algos",
  "artifact_location": "data/output/mlruns/f1f769ba",
  "lifecycle_stage": "active",
  "creation_time": "20260112_161312",
  "tags": {
    "num_algorithms": 4,
    "num_datasets": 4,
    "runs_per_combination": 5
  }
}
```

#### `run_info.json`
```json
{
  "run_id": "2c74edc2-a90f-49",
  "run_name": "MATILDA_Bupa_run1",
  "experiment_id": "f1f769ba",
  "status": "FINISHED",  // ou "FAILED", "RUNNING"
  "start_time": "2026-01-12T16:13:10.378613",
  "end_time": "2026-01-12T16:13:12.565551",
  "artifact_uri": "data/output/mlruns/f1f769ba/2c74edc2-a90f-49"
}
```

#### `params.json`
```json
{
  "algorithm": "MATILDA",
  "dataset": "Bupa",
  "run_number": 1,
  "timeout": 3600
}
```

#### `metrics.json`
```json
{
  "num_rules": 9,
  "accuracy": 1.0,
  "confidence": 1.0,
  "time_total": 0.124,
  "time_compat": 0.038,
  "time_index": 0.038,
  "time_cg": 0.048,
  "duration_seconds": 2.19
}
```

#### `summary.json`
```json
{
  "MATILDA_Bupa": {
    "algorithm": "MATILDA",
    "dataset": "Bupa",
    "runs": [
      { "run_id": "xxx", "metrics": {...} },
      ...
    ],
    "metrics": {
      "num_rules": {
        "mean": 9.0,
        "std": 0.0,
        "min": 9,
        "max": 9,
        "count": 5
      },
      "accuracy": { "mean": 1.0, "std": 0.0, ... },
      ...
    }
  }
}
```

---

## 🔍 Utilisation de l'Explorateur

### Commandes Disponibles

#### 1. Lister les Expériences

```bash
python3 mlflow_explorer.py list
```

**Output:**
```
================================================================================
ID           Name                           Created              Status    
================================================================================
f1f769ba     test_mlflow_integration        20260112_161312      active    
a3b5c789     comparison_all_algos           20260112_143020      active    
================================================================================
Total experiments: 2
```

#### 2. Détails d'une Expérience

```bash
python3 mlflow_explorer.py show f1f769ba
```

**Output:**
```
EXPERIMENT: test_mlflow_integration
ID:           f1f769ba
Location:     data/output/mlruns/f1f769ba
Status:       active

CONFIGURATION
  num_algorithms: 1
  num_datasets: 1
  runs_per_combination: 5

RUNS (5 total)
  ✓ Finished: 5
  ✗ Failed:   0

SUMMARY STATISTICS
MATILDA on Bupa:
  Runs: 5
  Rules:      9.0 ± 0.0 (min=9, max=9)
  Accuracy:   1.000 ± 0.000
  Duration:   2.19s ± 0.12s
```

#### 3. Lister les Runs

```bash
# Tous les runs
python3 mlflow_explorer.py runs f1f769ba

# Seulement les runs terminés
python3 mlflow_explorer.py runs f1f769ba --status FINISHED

# Seulement les runs échoués
python3 mlflow_explorer.py runs f1f769ba --status FAILED
```

#### 4. Détails d'un Run Spécifique

```bash
python3 mlflow_explorer.py run f1f769ba 2c74edc2
```

#### 5. Comparer Deux Expériences

```bash
python3 mlflow_explorer.py compare f1f769ba a3b5c789
```

**Output:**
```
COMPARISON: f1f769ba vs a3b5c789

MATILDA on Bupa:
Metric               Exp1                      Exp2                      Diff           
-----------------------------------------------------------------------------------
num_rules            9.000 ± 0.000             9.000 ± 0.000             +0.000 (+0.0%) 
accuracy             1.000 ± 0.000             0.998 ± 0.002             -0.002 (-0.2%) 
duration_seconds     2.190 ± 0.120             2.345 ± 0.098             +0.155 (+7.1%) 
```

---

## 📊 Workflows Typiques

### 1. Benchmark et Analyse

```bash
# 1. Lancer benchmark
python3 run_full_benchmark.py --runs 5 --experiment-name "baseline_v1"

# 2. Noter l'experiment_id (affiché dans l'output)
# Exemple: f1f769ba

# 3. Explorer les résultats
python3 mlflow_explorer.py show f1f769ba

# 4. Vérifier les runs
python3 mlflow_explorer.py runs f1f769ba
```

### 2. Comparer Deux Versions

```bash
# 1. Benchmark version 1
python3 run_full_benchmark.py --runs 5 --experiment-name "v1_baseline"
# -> experiment_id: abc123

# 2. Modifier l'algorithme, puis benchmark version 2
python3 run_full_benchmark.py --runs 5 --experiment-name "v2_improved"
# -> experiment_id: def456

# 3. Comparer
python3 mlflow_explorer.py compare abc123 def456
```

### 3. Analyser des Échecs

```bash
# 1. Lister les runs échoués
python3 mlflow_explorer.py runs f1f769ba --status FAILED

# 2. Examiner un run échoué
python3 mlflow_explorer.py run f1f769ba <failed_run_id>

# 3. Vérifier les logs ou artifacts
cat data/output/mlruns/f1f769ba/<run_id>/run_info.json
```

---

## 🎯 Cas d'Usage

### Article Scientifique

```bash
# Benchmark pour publication
python3 run_full_benchmark.py --runs 10 --experiment-name "paper_final_results"

# Vérifier statistiques
python3 mlflow_explorer.py show <exp_id>

# Table LaTeX générée automatiquement dans:
# data/output/mlruns/<exp_id>/benchmark_table_*.tex
```

### Tests de Régression

```bash
# Benchmark avant modification
python3 run_full_benchmark.py --runs 5 --experiment-name "before_refactor"

# Faire les modifications du code...

# Benchmark après modification
python3 run_full_benchmark.py --runs 5 --experiment-name "after_refactor"

# Comparer
python3 mlflow_explorer.py compare <before_id> <after_id>
```

### Optimisation de Paramètres

```bash
# Test avec DFS
# (modifier config: traversal_algorithm: dfs)
python3 run_full_benchmark.py --runs 5 --experiment-name "matilda_dfs"

# Test avec BFS
# (modifier config: traversal_algorithm: bfs)
python3 run_full_benchmark.py --runs 5 --experiment-name "matilda_bfs"

# Test avec A*
# (modifier config: traversal_algorithm: astar)
python3 run_full_benchmark.py --runs 5 --experiment-name "matilda_astar"

# Comparer tous
python3 mlflow_explorer.py compare <dfs_id> <bfs_id>
python3 mlflow_explorer.py compare <bfs_id> <astar_id>
```

---

## 💾 Compatibilité

### Format Legacy

Pour compatibilité avec les anciens scripts, les résultats sont aussi sauvegardés dans le format legacy :

```
data/output/
├── full_benchmark_results_*.json      # Format ancien
├── full_benchmark_statistics_*.json   # Format ancien
└── benchmark_table_*.tex              # Table LaTeX (copie)
```

Ces fichiers peuvent être utilisés avec les anciens scripts comme `generate_latex_table.py`.

---

## 🔧 Intégration avec MLflow Officiel

Si vous voulez utiliser le vrai MLflow UI :

### 1. Installer MLflow

```bash
pip install mlflow
```

### 2. Convertir les Données

Les données sont déjà dans un format compatible. Vous pouvez :

```bash
# Lancer l'UI MLflow
cd data/output
mlflow ui --backend-store-uri mlruns/
```

### 3. Voir dans le Navigateur

Ouvrez http://localhost:5000 pour explorer visuellement vos expériences.

---

## 📈 Métriques Trackées

| Métrique | Description | Unité |
|----------|-------------|-------|
| `num_rules` | Nombre de règles découvertes | count |
| `accuracy` | Précision des règles | 0-1 |
| `confidence` | Confiance des règles | 0-1 |
| `time_total` | Temps total | seconds |
| `time_compat` | Temps compatibility graph | seconds |
| `time_index` | Temps indexation | seconds |
| `time_cg` | Temps construction CG | seconds |
| `duration_seconds` | Durée complète du run | seconds |

---

## 🎓 Best Practices

### 1. Nommage des Expériences

```bash
# ✅ Bon : Descriptif et daté
--experiment-name "comparison_algos_2026_01_12"
--experiment-name "matilda_bfs_optimization_v2"

# ❌ Mauvais : Trop vague
--experiment-name "test"
--experiment-name "exp1"
```

### 2. Nombre de Runs

- **Test rapide** : 1-3 runs
- **Développement** : 3-5 runs
- **Publication** : 5-10 runs
- **Haute précision** : 10+ runs

### 3. Organisation

```bash
# Garder les expériences organisées par projet
--experiment-name "project_task_version"

# Exemples:
--experiment-name "paper_baseline_v1"
--experiment-name "paper_optimized_v2"
--experiment-name "paper_final_v3"
```

### 4. Archivage

```bash
# Archiver les anciennes expériences
mkdir data/output/mlruns_archive
mv data/output/mlruns/<old_exp_id> data/output/mlruns_archive/
```

---

## 🆘 Troubleshooting

### Expérience introuvable

```bash
# Lister toutes les expériences disponibles
python3 mlflow_explorer.py list

# Vérifier le répertoire
ls -la data/output/mlruns/
```

### Runs échoués

```bash
# Identifier les runs échoués
python3 mlflow_explorer.py runs <exp_id> --status FAILED

# Examiner les détails
cat data/output/mlruns/<exp_id>/<run_id>/run_info.json
```

### Comparer des expériences incompatibles

Les expériences doivent avoir des algorithmes/datasets en commun pour être comparables.

---

## 📚 Résumé

**Commandes essentielles :**

```bash
# Lancer benchmark
python3 run_full_benchmark.py --runs 5 --experiment-name "my_experiment"

# Explorer résultats
python3 mlflow_explorer.py list
python3 mlflow_explorer.py show <exp_id>
python3 mlflow_explorer.py compare <exp1> <exp2>
```

**Structure :**
- `data/output/mlruns/<exp_id>/` : Tous les artefacts d'une expérience
- `experiment_meta.json` : Métadonnées
- `runs.json` : Tous les runs
- `summary.json` : Statistiques agrégées
- `<run_id>/` : Artefacts de chaque run

**Avantages MLflow :**
- ✅ Traçabilité complète
- ✅ Comparaison facile
- ✅ Statistiques automatiques
- ✅ Organisation claire
- ✅ Compatible avec MLflow UI

---

**🎉 Système de tracking complet pour vos benchmarks MATILDA !**
