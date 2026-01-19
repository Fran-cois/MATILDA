# Analyse des Métriques de Temps de Calcul

## Vue d'ensemble

Le module d'analyse statistique de MATILDA inclut maintenant l'analyse des **métriques de temps de calcul** pour évaluer et comparer les performances temporelles des algorithmes.

## Métriques de Temps Analysées

### Métriques Disponibles

Les métriques de temps sont stockées dans les fichiers `init_time_metrics_*.json` et incluent :

| Métrique | Description |
|----------|-------------|
| **time_compute_compatible** | Temps pour calculer les attributs compatibles |
| **time_to_compute_indexed** | Temps pour calculer les attributs indexés |
| **time_building_cg** | Temps pour construire le graphe de contraintes |

### Exemple de Fichier

```json
{
    "time_compute_compatible": 0.037848,
    "time_to_compute_indexed": 0.038163,
    "time_building_cg": 0.038717
}
```

## Fonctions Ajoutées

### 1. `analyze_time_metrics()`

Analyse les métriques de temps à partir d'un fichier JSON.

```python
from utils.statistical_analysis import analyze_time_metrics
from pathlib import Path

# Analyser les métriques de temps
time_file = Path("data/output/init_time_metrics_Bupa.json")
stats = analyze_time_metrics(time_file)

for metric, stat in stats.items():
    print(f"{metric}: {stat.mean:.6f}s")
```

**Sortie :**
```
time_compute_compatible: 0.037848s
time_to_compute_indexed: 0.038163s
time_building_cg: 0.038717s
```

### 2. `compare_time_metrics()`

Compare les métriques de temps entre deux algorithmes.

```python
from utils.statistical_analysis import compare_time_metrics

# Comparer les temps entre deux datasets
comparisons = compare_time_metrics(
    Path("data/output/init_time_metrics_Bupa.json"),
    Path("data/output/init_time_metrics_BupaImperfect.json"),
    "Bupa", "BupaImperfect"
)

for metric, comp in comparisons.items():
    print(f"{metric}:")
    print(f"  Bupa: {comp['Bupa_time']:.6f}s")
    print(f"  BupaImperfect: {comp['BupaImperfect_time']:.6f}s")
    print(f"  Différence: {comp['difference']:.6f}s ({comp['percent_difference']:.2f}%)")
    print(f"  Plus rapide: {comp['faster_algorithm']}")
```

**Sortie :**
```
time_compute_compatible:
  Bupa: 0.037848s
  BupaImperfect: 0.033405s
  Différence: 0.004443s (13.30%)
  Plus rapide: BupaImperfect

time_to_compute_indexed:
  Bupa: 0.038163s
  BupaImperfect: 0.033727s
  Différence: 0.004436s (13.15%)
  Plus rapide: BupaImperfect

time_building_cg:
  Bupa: 0.038717s
  BupaImperfect: 0.034235s
  Différence: 0.004482s (13.09%)
  Plus rapide: BupaImperfect
```

### 3. `generate_statistical_report()` - Mise à jour

La fonction de génération de rapport inclut maintenant automatiquement les métriques de temps.

```python
from utils.statistical_analysis import generate_statistical_report

# Générer rapport complet avec métriques de temps
report = generate_statistical_report(
    Path("data/output"),
    include_time_metrics=True  # Activé par défaut
)

# Accéder aux métriques de temps
time_metrics = report["time_metrics"]
time_comparisons = report["time_comparisons"]
```

## Utilisation avec le Script

### Génération de Rapport

```bash
# Générer rapport avec métriques de temps
python generate_statistics_report.py --markdown --verbose
```

**Sortie console :**
```
======================================================================
Compute Time Metrics
======================================================================

MATILDA:
  ComparisonDataset:
    time_compute_compatible: 0.035372s
    time_to_compute_indexed: 0.035680s
    time_building_cg: 0.035925s
  Bupa:
    time_compute_compatible: 0.037848s
    time_to_compute_indexed: 0.038163s
    time_building_cg: 0.038717s

======================================================================
Compute Time Comparisons
======================================================================

MATILDA_vs_SPIDER_ComparisonDataset_time:
  time_compute_compatible: SPIDER is faster by 0.000000s (0.00%)
  time_to_compute_indexed: SPIDER is faster by 0.000000s (0.00%)
  time_building_cg: SPIDER is faster by 0.000000s (0.00%)
```

### Rapport Markdown

Le rapport Markdown généré inclut maintenant :

1. **Section "Compute Time Metrics"** - Temps de calcul par algorithme/dataset
2. **Section "Compute Time Comparisons"** - Comparaisons détaillées

#### Exemple de Tableau (Markdown)

**Compute Time Metrics:**

| Metric | Time (seconds) |
|--------|----------------|
| time_compute_compatible | 0.037848 |
| time_to_compute_indexed | 0.038163 |
| time_building_cg | 0.038717 |

**Compute Time Comparisons:**

| Metric | Time (s) | Faster Algorithm | Difference (s) | % Difference |
|--------|----------|------------------|----------------|-------------|
| time_compute_compatible | Bupa: 0.037848, BupaImperfect: 0.033405 | BupaImperfect | 0.004443 | 13.30% |

## Structure du Rapport JSON

Le rapport JSON généré contient maintenant :

```json
{
  "statistics": { ... },
  "comparisons": { ... },
  "time_metrics": {
    "MATILDA": {
      "Bupa": {
        "time_compute_compatible": {
          "metric": "time_compute_compatible",
          "mean": 0.037848,
          "std": 0.0,
          "median": 0.037848,
          "min": 0.037848,
          "max": 0.037848,
          "count": 1,
          "ci_95_lower": 0.037848,
          "ci_95_upper": 0.037848
        }
      }
    }
  },
  "time_comparisons": {
    "MATILDA_vs_SPIDER_Bupa_time": {
      "time_compute_compatible": {
        "metric": "time_compute_compatible",
        "MATILDA_time": 0.037848,
        "SPIDER_time": 0.037848,
        "difference": 0.0,
        "percent_difference": 0.0,
        "faster_algorithm": "SPIDER"
      }
    }
  },
  "summary": {
    "total_algorithms": 4,
    "total_datasets": 4,
    "total_comparisons": 8,
    "total_time_comparisons": 8
  }
}
```

## Test

Un script de test dédié est fourni :

```bash
python test_time_metrics.py
```

**Résultat :**
```
======================================================================
Testing Time Metrics Analysis Module
======================================================================

Test 1: Analyze Time Metrics
✓ Successfully analyzed time metrics from init_time_metrics_Bupa.json
  Metrics found: 3

Test 2: Compare Time Metrics
✓ Successfully compared time metrics
  Metrics compared: 3

======================================================================
✓ All tests passed!
======================================================================
```

## Cas d'Usage

### 1. Identifier les Goulots d'Étranglement

```python
# Analyser quel algorithme a les temps les plus longs
stats = analyze_time_metrics(time_file)

for metric, stat in sorted(stats.items(), key=lambda x: x[1].mean, reverse=True):
    print(f"{metric}: {stat.mean:.6f}s")
```

### 2. Comparer Performance Temporelle

```python
# Comparer les temps entre algorithmes
comparisons = compare_time_metrics(
    algo1_time_file,
    algo2_time_file,
    "Algorithm1", "Algorithm2"
)

for metric, comp in comparisons.items():
    if abs(comp['percent_difference']) > 10:
        print(f"⚠️ {metric}: différence de {comp['percent_difference']:.2f}%")
```

### 3. Rapport pour Publication

```bash
# Générer rapport complet pour article scientifique
python generate_statistics_report.py --markdown --verbose

# Utiliser les tableaux de temps dans l'article
```

## Limites Actuelles

### Valeurs Uniques

Les métriques de temps sont des **valeurs uniques par exécution**, pas des distributions. Par conséquent :

- ✓ Comparaisons de valeurs absolues disponibles
- ✓ Différences en pourcentage calculées
- ✗ Tests de significativité statistique (nécessitent plusieurs runs)

### Solution pour Tests Statistiques

Pour obtenir des tests de significativité sur les temps :

```python
# Exécuter l'algorithme N fois et stocker les temps
times = []
for i in range(30):
    start = time.time()
    run_algorithm()
    times.append(time.time() - start)

# Ensuite appliquer compute_statistics() et perform_t_test()
```

## Options de Configuration

Aucune configuration supplémentaire nécessaire ! Les métriques de temps sont :

- ✅ Automatiquement détectées dans `data/output/init_time_metrics_*.json`
- ✅ Incluses par défaut dans `generate_statistical_report()`
- ✅ Affichées dans le mode `--verbose`

Pour désactiver (si besoin) :

```python
report = generate_statistical_report(
    results_dir,
    include_time_metrics=False  # Désactive l'analyse des temps
)
```

## Fichiers Modifiés

| Fichier | Modifications |
|---------|--------------|
| **src/utils/statistical_analysis.py** | Ajout de `analyze_time_metrics()`, `compare_time_metrics()`, mise à jour de `generate_statistical_report()` |
| **generate_statistics_report.py** | Mise à jour de `create_markdown_report()` pour inclure sections temps |
| **test_time_metrics.py** | **Nouveau** - Tests pour analyse des temps |

## Résumé des Fonctionnalités

✅ **Analyse automatique** des métriques de temps  
✅ **Comparaisons détaillées** entre algorithmes/datasets  
✅ **Calcul de différences** absolues et en pourcentage  
✅ **Identification automatique** de l'algorithme le plus rapide  
✅ **Intégration complète** dans les rapports JSON et Markdown  
✅ **Affichage verbeux** dans la console  
✅ **Tests unitaires** complets  

## Exemple Complet

```python
#!/usr/bin/env python3
from pathlib import Path
from utils.statistical_analysis import (
    analyze_time_metrics,
    compare_time_metrics,
    generate_statistical_report
)

# 1. Analyser temps pour un dataset
stats = analyze_time_metrics(Path("data/output/init_time_metrics_Bupa.json"))
print(f"Time to build CG: {stats['time_building_cg'].mean:.6f}s")

# 2. Comparer deux datasets
comp = compare_time_metrics(
    Path("data/output/init_time_metrics_Bupa.json"),
    Path("data/output/init_time_metrics_BupaImperfect.json"),
    "Bupa", "BupaImperfect"
)
print(f"Faster dataset: {comp['time_building_cg']['faster_algorithm']}")

# 3. Générer rapport complet
report = generate_statistical_report(
    Path("data/output"),
    Path("time_analysis_report.json"),
    include_time_metrics=True
)
print(f"Time comparisons: {report['summary']['total_time_comparisons']}")
```

---

## 🎉 Résultat

MATILDA dispose maintenant d'une **analyse complète des temps de calcul** :

✅ Analyse des temps par opération  
✅ Comparaisons entre algorithmes/datasets  
✅ Identification automatique des goulots d'étranglement  
✅ Intégration dans les rapports statistiques  
✅ Tests unitaires validés  

**Les métriques de temps sont maintenant pleinement intégrées dans l'analyse statistique !** ✓
