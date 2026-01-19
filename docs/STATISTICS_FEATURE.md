# Statistical Analysis Feature

## Vue d'ensemble

MATILDA inclut maintenant un module complet d'**analyse statistique** pour évaluer les performances des règles découvertes. Cette fonctionnalité calcule automatiquement :

- **Statistiques descriptives** : moyenne, écart-type, médiane, min/max, intervalles de confiance
- **Tests de significativité** : tests t, tests de Mann-Whitney U
- **Tailles d'effet** : Cohen's d, corrélation rank-biserial
- **Rapports comparatifs** : comparaisons entre algorithmes et datasets

## Fichiers Créés

### Nouveau Module

- **`src/utils/statistical_analysis.py`** - Module principal d'analyse statistique
  - Classes : `PerformanceStats`, `SignificanceTest`
  - Fonctions : `compute_statistics()`, `perform_t_test()`, `perform_mannwhitneyu_test()`
  - Analyses : `analyze_rules_performance()`, `compare_algorithms()`, `generate_statistical_report()`

### Scripts Utilitaires

- **`generate_statistics_report.py`** - Script pour générer des rapports statistiques complets
- **`test_statistics.py`** - Tests unitaires pour le module statistique

### Documentation

- **`STATISTICS_FEATURE.md`** - Ce fichier (documentation de la fonctionnalité)

## Configuration

### Dans `config.yaml`

```yaml
results:
  output_dir: "data/output"
  compute_statistics: true           # Calculer stats pour chaque exécution
  generate_statistical_report: true  # Générer rapport global
  statistical_report_name: "statistical_analysis_report.json"
```

### Options

- **`compute_statistics`** : Calcule les statistiques descriptives pour chaque fichier de résultats
- **`generate_statistical_report`** : Génère un rapport comparatif global après l'exécution
- **`statistical_report_name`** : Nom du fichier de rapport statistique

## Utilisation

### 1. Automatique (lors de l'exécution de MATILDA)

Lorsque `compute_statistics: true` dans `config.yaml` :

```bash
python src/main.py
```

**Résultats :**
- `ALGORITHM_DATASET_results.json` - Résultats des règles
- `ALGORITHM_DATASET_statistics.json` - Statistiques descriptives (nouveau)

**Exemple de sortie :**

```json
{
  "accuracy": {
    "metric": "accuracy",
    "mean": 0.8750,
    "std": 0.0645,
    "median": 0.8800,
    "min": 0.7500,
    "max": 0.9500,
    "count": 150,
    "ci_95_lower": 0.8645,
    "ci_95_upper": 0.8855
  },
  "confidence": {
    "metric": "confidence",
    "mean": 0.9100,
    "std": 0.0523,
    ...
  }
}
```

### 2. Génération de Rapports Complets

#### Via Script Autonome

```bash
# Rapport basique
python generate_statistics_report.py

# Avec rapport Markdown
python generate_statistics_report.py --markdown

# Verbose avec détails
python generate_statistics_report.py --markdown --verbose

# Répertoire personnalisé
python generate_statistics_report.py --results-dir custom/path --output my_report.json
```

#### Sortie

- **JSON** : `statistical_analysis_report.json`
- **Markdown** : `statistical_analysis_report.md` (si `--markdown`)

### 3. Utilisation Programmatique

```python
from utils.statistical_analysis import (
    compute_statistics,
    perform_t_test,
    analyze_rules_performance,
    compare_algorithms,
)

# Calculer statistiques sur une liste de valeurs
values = [0.8, 0.85, 0.9, 0.75, 0.88]
stats = compute_statistics(values, "accuracy")
print(f"Mean: {stats.mean:.4f}, Std: {stats.std:.4f}")

# Analyser un fichier de résultats
stats_dict = analyze_rules_performance(
    Path("data/output/MATILDA_Bupa_results.json")
)

# Comparer deux algorithmes
comparisons = compare_algorithms(
    Path("data/output/MATILDA_Bupa_results.json"),
    Path("data/output/SPIDER_Bupa_results.json"),
    "MATILDA", "SPIDER"
)

for metric, test in comparisons.items():
    print(f"{metric}: p-value = {test.p_value:.4f}")
    if test.is_significant:
        print(f"  Significant difference! Effect size: {test.effect_size:.4f}")
```

## Statistiques Calculées

### Statistiques Descriptives

| Statistique | Description |
|-------------|-------------|
| **Mean (μ)** | Moyenne arithmétique des valeurs |
| **Std (σ)** | Écart-type (échantillon, ddof=1) |
| **Median** | Valeur médiane |
| **Min** | Valeur minimale |
| **Max** | Valeur maximale |
| **Count** | Nombre d'observations |
| **95% CI** | Intervalle de confiance à 95% |

### Tests de Significativité

#### Test t Indépendant

- **Quand :** Comparer deux groupes (données paramétriques)
- **Hypothèse nulle (H₀)** : Les moyennes sont égales
- **Sortie** :
  - t-statistic
  - p-value
  - Cohen's d (taille d'effet)

**Interprétation Cohen's d :**
- Petit : d = 0.2
- Moyen : d = 0.5
- Grand : d = 0.8

#### Test de Mann-Whitney U

- **Quand :** Comparer deux groupes (non-paramétrique, alternative au t-test)
- **Hypothèse nulle (H₀)** : Les distributions sont identiques
- **Sortie** :
  - U-statistic
  - p-value
  - Corrélation rank-biserial (taille d'effet)

### Niveau de Significativité

- **α = 0.05** (par défaut)
- **p < 0.05** : Différence statistiquement significative ✓
- **p ≥ 0.05** : Pas de différence significative ✗

## Structure du Rapport

### Rapport JSON

```json
{
  "timestamp": "2026-01-12T15:30:45.123456",
  "statistics": {
    "MATILDA": {
      "Bupa": {
        "accuracy": { "mean": 0.95, "std": 0.03, ... },
        "confidence": { "mean": 0.92, "std": 0.05, ... }
      },
      "BupaImperfect": { ... }
    },
    "SPIDER": { ... }
  },
  "comparisons": {
    "MATILDA_vs_SPIDER_Bupa": {
      "accuracy": {
        "test": "Independent t-test",
        "statistic": 3.45,
        "p_value": 0.001,
        "is_significant": true,
        "effect_size": 0.65
      }
    }
  },
  "summary": {
    "total_algorithms": 4,
    "total_datasets": 3,
    "total_comparisons": 12
  }
}
```

### Rapport Markdown

```markdown
# Statistical Analysis Report

## Summary
- **Total Algorithms:** 4
- **Total Datasets:** 3
- **Total Comparisons:** 12

## Descriptive Statistics

### MATILDA
#### Dataset: Bupa
| Metric | Mean | Std Dev | Median | Min | Max | 95% CI |
|--------|------|---------|--------|-----|-----|--------|
| accuracy | 0.9500 | 0.0300 | 0.9600 | 0.8500 | 1.0000 | (0.9380, 0.9620) |

## Significance Tests
| Metric | Comparison | Test | Statistic | p-value | Significant | Effect Size |
|--------|------------|------|-----------|---------|-------------|-------------|
| accuracy | MATILDA vs SPIDER | t-test | 3.4500 | 0.0010 | ✓ | 0.6500 |

## Interpretation Guide
...
```

## Exemples d'Utilisation

### Exemple 1 : Évaluer la Performance d'un Algorithme

```python
from pathlib import Path
from utils.statistical_analysis import analyze_rules_performance

# Analyser les résultats de MATILDA
stats = analyze_rules_performance(
    Path("data/output/MATILDA_Bupa_results.json")
)

# Afficher les statistiques
for metric, stat in stats.items():
    print(f"{metric}:")
    print(f"  Mean: {stat.mean:.4f} ± {stat.std:.4f}")
    print(f"  95% CI: ({stat.confidence_interval_95[0]:.4f}, {stat.confidence_interval_95[1]:.4f})")
    print(f"  Range: [{stat.min:.4f}, {stat.max:.4f}]")
    print(f"  N = {stat.count}")
```

### Exemple 2 : Comparer Deux Algorithmes

```python
from utils.statistical_analysis import compare_algorithms

# Comparer MATILDA et SPIDER
comparisons = compare_algorithms(
    Path("data/output/MATILDA_Bupa_results.json"),
    Path("data/output/SPIDER_Bupa_results.json"),
    "MATILDA", "SPIDER",
    use_parametric=True  # Utiliser t-test
)

# Vérifier les différences significatives
for metric, test in comparisons.items():
    print(f"\n{metric}:")
    print(f"  Test: {test.test_name}")
    print(f"  p-value: {test.p_value:.4f}")
    
    if test.is_significant:
        print(f"  ✓ Différence significative!")
        print(f"  Effect size: {test.effect_size:.4f}")
        
        if test.effect_size > 0.8:
            print(f"  → Grande taille d'effet")
        elif test.effect_size > 0.5:
            print(f"  → Taille d'effet moyenne")
        else:
            print(f"  → Petite taille d'effet")
    else:
        print(f"  ✗ Pas de différence significative")
```

### Exemple 3 : Rapport Global

```python
from utils.statistical_analysis import generate_statistical_report

# Générer rapport complet
report = generate_statistical_report(
    Path("data/output"),
    Path("data/output/full_report.json")
)

# Résumé
print(f"Algorithmes analysés: {report['summary']['total_algorithms']}")
print(f"Datasets analysés: {report['summary']['total_datasets']}")
print(f"Comparaisons: {report['summary']['total_comparisons']}")

# Trouver les différences significatives
for comp_name, metrics in report["comparisons"].items():
    for metric, test in metrics.items():
        if test["is_significant"]:
            print(f"\n{comp_name} - {metric}:")
            print(f"  p = {test['p_value']:.4f}, d = {test['effect_size']:.4f}")
```

## Tests

### Exécuter les Tests

```bash
# Tests unitaires
python test_statistics.py
```

**Sortie attendue :**

```
======================================================================
Testing Statistical Analysis Module
======================================================================

Testing compute_statistics...
  Mean: 0.8400
  Std: 0.0645
  ✓ Passed!

Testing t-test...
  t-statistic: -7.0046
  p-value: 0.0001
  Significant: True
  ✓ Passed!

...

======================================================================
✓ All tests passed!
======================================================================
```

## Intégration dans le Workflow

### Workflow Complet

1. **Configuration** : Activer `compute_statistics: true` dans `config.yaml`

2. **Exécution** : Lancer MATILDA
   ```bash
   python src/main.py
   ```

3. **Résultats** :
   - Règles découvertes : `MATILDA_Dataset_results.json`
   - Statistiques : `MATILDA_Dataset_statistics.json`

4. **Rapport Global** (si `generate_statistical_report: true`)
   - Rapport JSON : `statistical_analysis_report.json`
   - Logs de comparaison dans la sortie

5. **Analyse Approfondie** (optionnel)
   ```bash
   python generate_statistics_report.py --markdown --verbose
   ```

## Bonnes Pratiques

### Choix du Test

- **Test t** : Données normalement distribuées, échantillons suffisants (n ≥ 30)
- **Mann-Whitney U** : Données non-normales, petits échantillons, données ordinales

### Interprétation

1. **Vérifier la significativité** : p < 0.05
2. **Examiner la taille d'effet** : Importance pratique
3. **Considérer le contexte** : Taille d'échantillon, domaine d'application

### Limitations

- **Petits échantillons** : Intervalles de confiance larges
- **Tests multiples** : Risque d'inflation du taux d'erreur (correction de Bonferroni si nécessaire)
- **Données non-IID** : Suppositions des tests paramétriques

## API Reference

### Classes

#### `PerformanceStats`

```python
@dataclass
class PerformanceStats:
    metric_name: str
    mean: float
    std: float
    median: float
    min: float
    max: float
    count: int
    confidence_interval_95: Tuple[float, float]
    
    def to_dict(self) -> Dict
```

#### `SignificanceTest`

```python
@dataclass
class SignificanceTest:
    test_name: str
    metric: str
    group1_name: str
    group2_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size: Optional[float] = None
    
    def to_dict(self) -> Dict
```

### Fonctions Principales

#### `compute_statistics()`

```python
def compute_statistics(
    values: List[float],
    metric_name: str = "metric"
) -> PerformanceStats
```

Calcule les statistiques descriptives.

#### `perform_t_test()`

```python
def perform_t_test(
    group1: List[float],
    group2: List[float],
    metric_name: str,
    group1_name: str = "Group 1",
    group2_name: str = "Group 2",
    alpha: float = 0.05
) -> SignificanceTest
```

Effectue un test t indépendant.

#### `analyze_rules_performance()`

```python
def analyze_rules_performance(
    rules_file: Path,
    metrics: Optional[List[str]] = None
) -> Dict[str, PerformanceStats]
```

Analyse les métriques de performance d'un fichier de règles.

#### `generate_statistical_report()`

```python
def generate_statistical_report(
    results_dir: Path,
    output_file: Optional[Path] = None,
    algorithms: Optional[List[str]] = None,
    datasets: Optional[List[str]] = None
) -> Dict[str, Any]
```

Génère un rapport statistique complet.

## Dépendances

- **numpy** : Calculs numériques
- **scipy** : Tests statistiques
- **json** : Sérialisation des résultats

## Références

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences
- Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other
- Student (1908). The Probable Error of a Mean

---

**Documentation complète et testée** ✓
