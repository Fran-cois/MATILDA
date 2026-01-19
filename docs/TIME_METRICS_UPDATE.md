# 📊 Mise à Jour : Analyse des Métriques de Temps de Calcul

**Date :** 12 janvier 2026  
**Version :** 2.1  
**Fonctionnalité :** Ajout des métriques de temps de calcul à l'analyse statistique

---

## 🎯 Résumé

Le module d'analyse statistique de MATILDA inclut maintenant l'analyse et la comparaison des **métriques de temps de calcul** pour tous les algorithmes et datasets.

## ✨ Nouveautés

### 📈 Nouvelles Métriques Analysées

| Métrique | Description | Unité |
|----------|-------------|-------|
| `time_compute_compatible` | Temps pour calculer attributs compatibles | secondes |
| `time_to_compute_indexed` | Temps pour calculer attributs indexés | secondes |
| `time_building_cg` | Temps pour construire le graphe de contraintes | secondes |

### 🔧 Nouvelles Fonctions

#### 1. `analyze_time_metrics()`
Analyse les métriques de temps à partir des fichiers `init_time_metrics_*.json`.

```python
stats = analyze_time_metrics(Path("data/output/init_time_metrics_Bupa.json"))
# Retourne: Dict[str, PerformanceStats]
```

#### 2. `compare_time_metrics()`
Compare les temps de calcul entre deux algorithmes/datasets.

```python
comp = compare_time_metrics(
    time_file1, time_file2,
    "Algorithm1", "Algorithm2"
)
# Retourne: Dict avec différences absolues et en pourcentage
```

#### 3. `generate_statistical_report()` - Mise à jour
Inclut maintenant automatiquement l'analyse des temps.

```python
report = generate_statistical_report(
    results_dir,
    include_time_metrics=True  # Par défaut
)
# report["time_metrics"] et report["time_comparisons"]
```

## 📊 Résultats Générés

### Rapport JSON

```json
{
  "time_metrics": {
    "MATILDA": {
      "Bupa": {
        "time_building_cg": {
          "mean": 0.038717,
          "std": 0.0,
          ...
        }
      }
    }
  },
  "time_comparisons": {
    "MATILDA_vs_SPIDER_Bupa_time": {
      "time_building_cg": {
        "MATILDA_time": 0.038717,
        "SPIDER_time": 0.035925,
        "difference": 0.002792,
        "percent_difference": 7.77,
        "faster_algorithm": "SPIDER"
      }
    }
  }
}
```

### Rapport Markdown

**Nouvelles sections ajoutées :**

1. **Compute Time Metrics** - Tableau des temps par algorithme/dataset
2. **Compute Time Comparisons** - Comparaisons détaillées avec % de différence

## 🚀 Utilisation

### Script de Génération

```bash
# Générer rapport complet avec temps
python generate_statistics_report.py --markdown --verbose
```

**Output console :**
```
======================================================================
Compute Time Metrics
======================================================================

MATILDA:
  Bupa:
    time_compute_compatible: 0.037848s
    time_to_compute_indexed: 0.038163s
    time_building_cg: 0.038717s

======================================================================
Compute Time Comparisons
======================================================================

MATILDA_vs_SPIDER_Bupa_time:
  time_building_cg: SPIDER is faster by 0.002792s (7.77%)
```

### API Programmatique

```python
from utils.statistical_analysis import analyze_time_metrics, compare_time_metrics

# Analyser
stats = analyze_time_metrics(time_file)
print(f"Temps de construction CG: {stats['time_building_cg'].mean:.6f}s")

# Comparer
comp = compare_time_metrics(file1, file2, "Algo1", "Algo2")
print(f"Plus rapide: {comp['time_building_cg']['faster_algorithm']}")
print(f"Différence: {comp['time_building_cg']['percent_difference']:.2f}%")
```

## 🧪 Tests

### Script de Test
```bash
python test_time_metrics.py
```

**Résultat :**
```
======================================================================
Testing Time Metrics Analysis Module
======================================================================

Test 1: Analyze Time Metrics
✓ Successfully analyzed time metrics
  Metrics found: 3

Test 2: Compare Time Metrics  
✓ Successfully compared time metrics
  Metrics compared: 3

======================================================================
✓ All tests passed!
======================================================================
```

## 📁 Fichiers Modifiés/Créés

### Modifiés

| Fichier | Lignes Ajoutées | Description |
|---------|----------------|-------------|
| `src/utils/statistical_analysis.py` | ~150 | Nouvelles fonctions d'analyse temps |
| `generate_statistics_report.py` | ~100 | Sections temps dans rapport Markdown |

### Créés

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `test_time_metrics.py` | 155 | Tests unitaires pour analyse temps |
| `TIME_METRICS_ANALYSIS.md` | 400+ | Documentation complète |
| `TIME_METRICS_UPDATE.md` | Ce fichier | Résumé de la mise à jour |

## 📈 Exemple de Sortie

### Statistiques Descriptives

```
MATILDA - Bupa:
  time_compute_compatible: 0.037848s
  time_to_compute_indexed: 0.038163s  
  time_building_cg: 0.038717s
```

### Comparaisons

```
Bupa vs BupaImperfect:
  time_building_cg:
    Bupa: 0.038717s
    BupaImperfect: 0.034235s
    Différence: 0.004482s (13.09%)
    Plus rapide: BupaImperfect
```

## 🎓 Cas d'Usage

### 1. Identification des Goulots d'Étranglement

```python
# Trouver l'opération la plus lente
stats = analyze_time_metrics(time_file)
slowest = max(stats.items(), key=lambda x: x[1].mean)
print(f"Opération la plus lente: {slowest[0]} ({slowest[1].mean:.6f}s)")
```

### 2. Comparaison d'Algorithmes

```python
# Identifier l'algorithme le plus rapide
comp = compare_time_metrics(algo1_file, algo2_file, "MATILDA", "SPIDER")
for metric, data in comp.items():
    if data['faster_algorithm'] == 'MATILDA':
        print(f"MATILDA plus rapide pour {metric}")
```

### 3. Rapport pour Publication

```bash
# Générer rapport complet Markdown
python generate_statistics_report.py --markdown

# Utiliser les tableaux dans l'article scientifique
cat data/output/statistical_analysis_report.md
```

## ⚡ Performance

- **Overhead minimal** : Analyse en O(n) sur les fichiers temps
- **Intégration transparente** : Activée par défaut
- **Rapide** : < 1s pour analyser tous les fichiers

## 🔍 Limitations et Solutions

### Limitation : Valeurs Uniques

Les métriques de temps sont des valeurs uniques par run (pas de distribution).

**Impact :**
- ✓ Comparaisons absolues disponibles
- ✓ Pourcentages de différence calculés
- ✗ Tests de significativité impossibles (nécessitent N runs)

**Solution pour tests statistiques :**

```python
# Exécuter N fois pour obtenir distribution
times_list = []
for i in range(30):
    times_list.append(run_and_measure())

# Puis appliquer tests standards
t_test_result = perform_t_test(times_algo1, times_algo2, "time_building_cg")
```

## 🔄 Compatibilité

- ✅ **Rétrocompatible** : Anciens scripts fonctionnent sans modification
- ✅ **Optionnel** : Peut être désactivé avec `include_time_metrics=False`
- ✅ **Automatique** : Détection automatique des fichiers `init_time_metrics_*.json`

## 📝 Configuration

### Par Défaut (Aucune Config Nécessaire)

Les métriques de temps sont automatiquement analysées si les fichiers existent.

### Désactivation (si besoin)

```python
report = generate_statistical_report(
    results_dir,
    include_time_metrics=False  # Désactive analyse temps
)
```

## ✅ Checklist d'Implémentation

- [x] Fonction `analyze_time_metrics()` créée
- [x] Fonction `compare_time_metrics()` créée  
- [x] `generate_statistical_report()` mise à jour
- [x] Section temps dans rapport Markdown
- [x] Affichage verbeux dans console
- [x] Tests unitaires créés et validés
- [x] Documentation complète rédigée
- [x] Exemples d'utilisation fournis

## 🎉 Résultat Final

### Avant
```json
{
  "statistics": {...},
  "comparisons": {...},
  "summary": {...}
}
```

### Après
```json
{
  "statistics": {...},
  "comparisons": {...},
  "time_metrics": {...},          // ← NOUVEAU
  "time_comparisons": {...},      // ← NOUVEAU
  "summary": {
    "total_time_comparisons": 8   // ← NOUVEAU
  }
}
```

---

## 📚 Documentation

- **Guide complet** : [TIME_METRICS_ANALYSIS.md](TIME_METRICS_ANALYSIS.md)
- **Documentation générale** : [STATISTICS_FEATURE.md](STATISTICS_FEATURE.md)
- **Tests** : `python test_time_metrics.py`

## 🆘 Support

Pour toute question sur l'analyse des temps :

```bash
# Voir les temps en mode verbeux
python generate_statistics_report.py --verbose

# Tester les fonctions
python test_time_metrics.py

# Lire la documentation
cat TIME_METRICS_ANALYSIS.md
```

---

**✓ L'analyse des métriques de temps de calcul est maintenant pleinement opérationnelle !**

Les statistiques incluent désormais :
- 📈 Statistiques de performance (accuracy, confidence)
- ⏱️ Métriques de temps de calcul
- 🔬 Tests de significativité
- 📊 Rapports JSON et Markdown complets
