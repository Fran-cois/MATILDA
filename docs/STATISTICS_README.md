# Nouvelle Fonctionnalité : Analyse Statistique des Performances

## Résumé

MATILDA intègre maintenant un **module d'analyse statistique complet** qui calcule automatiquement :

✅ **Statistiques descriptives** : moyenne, écart-type, médiane, min/max, intervalles de confiance  
✅ **Tests de significativité** : tests t, tests de Mann-Whitney U  
✅ **Tailles d'effet** : Cohen's d, corrélation rank-biserial  
✅ **Rapports comparatifs** : comparaisons automatiques entre algorithmes

## Fichiers Créés

### Module Principal
- **`src/utils/statistical_analysis.py`** - Module complet d'analyse statistique (374 lignes)

### Scripts
- **`generate_statistics_report.py`** - Générateur de rapports statistiques
- **`test_statistics.py`** - Tests unitaires (✓ tous passent)

### Documentation
- **`STATISTICS_FEATURE.md`** - Documentation complète de la fonctionnalité
- **`STATISTICS_README.md`** - Ce fichier

## Fichiers Modifiés

### Configuration
- **`src/config.yaml`** - Ajout des options statistiques
  ```yaml
  results:
    compute_statistics: true
    generate_statistical_report: true
    statistical_report_name: "statistical_analysis_report.json"
  ```

### Code Principal
- **`src/main.py`** - Intégration de l'analyse statistique dans le pipeline

## 🚀 Utilisation Rapide

### 1. Configuration (config.yaml)

```yaml
results:
  compute_statistics: true           # Active les statistiques
  generate_statistical_report: true  # Génère rapport global
```

### 2. Exécution Automatique

```bash
python src/main.py
```

**Résultats générés :**
- `ALGORITHM_DATASET_results.json` - Résultats des règles
- `ALGORITHM_DATASET_statistics.json` - **Nouveau** : Statistiques descriptives
- `statistical_analysis_report.json` - **Nouveau** : Rapport comparatif global

### 3. Génération de Rapports Avancés

```bash
# Rapport complet avec Markdown
python generate_statistics_report.py --markdown --verbose

# Résultats :
# - statistical_analysis_report.json
# - statistical_analysis_report.md
```

## 📊 Exemples de Sortie

### Statistiques Descriptives (JSON)

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
  }
}
```

### Rapport Comparatif

```
======================================================================
Summary
======================================================================
Algorithms analyzed: 4
Datasets analyzed: 4
Comparisons performed: 8

======================================================================
Significant Differences Found (3)
======================================================================
  MATILDA vs SPIDER (accuracy)
    p-value: 0.0012, effect size: 0.7523
  MATILDA vs ANYBURL (confidence)
    p-value: 0.0000, effect size: 2.1456
```

## 💡 Utilisation Programmatique

### Analyser un Fichier de Résultats

```python
from utils.statistical_analysis import analyze_rules_performance

stats = analyze_rules_performance(
    Path("data/output/MATILDA_Bupa_results.json")
)

for metric, stat in stats.items():
    print(f"{metric}: μ={stat.mean:.4f}, σ={stat.std:.4f}")
```

### Comparer Deux Algorithmes

```python
from utils.statistical_analysis import compare_algorithms

comparisons = compare_algorithms(
    Path("data/output/MATILDA_Bupa_results.json"),
    Path("data/output/SPIDER_Bupa_results.json"),
    "MATILDA", "SPIDER"
)

for metric, test in comparisons.items():
    if test.is_significant:
        print(f"{metric}: Différence significative (p={test.p_value:.4f})")
```

### Générer Rapport Global

```python
from utils.statistical_analysis import generate_statistical_report

report = generate_statistical_report(
    Path("data/output"),
    Path("report.json")
)

print(f"Comparaisons: {report['summary']['total_comparisons']}")
```

## 📈 Statistiques Disponibles

### Descriptives

| Statistique | Description |
|-------------|-------------|
| Mean (μ) | Moyenne |
| Std (σ) | Écart-type |
| Median | Médiane |
| Min/Max | Valeurs extrêmes |
| 95% CI | Intervalle de confiance |

### Tests de Significativité

| Test | Usage | Sortie |
|------|-------|--------|
| **t-test** | Comparer moyennes (paramétrique) | t-statistic, p-value, Cohen's d |
| **Mann-Whitney U** | Comparer distributions (non-paramétrique) | U-statistic, p-value, rank-biserial |

### Interprétation

- **p < 0.05** : Différence statistiquement significative ✓
- **p ≥ 0.05** : Pas de différence significative ✗

**Taille d'effet (Cohen's d) :**
- Petit : 0.2
- Moyen : 0.5
- Grand : 0.8

## 🧪 Tests

```bash
# Exécuter les tests
python test_statistics.py
```

**Résultat :**

```
======================================================================
Testing Statistical Analysis Module
======================================================================

Testing compute_statistics...
  ✓ Passed!

Testing t-test...
  ✓ Passed!

Testing Mann-Whitney U test...
  ✓ Passed!

Testing JSON serialization...
  ✓ Passed!

Testing analyze_rules_performance...
  ✓ Passed!

======================================================================
✓ All tests passed!
======================================================================
```

## 🎯 Cas d'Usage

### 1. Évaluer la Stabilité d'un Algorithme

```python
# Calculer écart-type pour évaluer la variabilité
stats = analyze_rules_performance(rules_file)
print(f"Accuracy: {stats['accuracy'].mean:.4f} ± {stats['accuracy'].std:.4f}")

# Faible std → algorithme stable
# Élevé std → résultats variables
```

### 2. Comparer Algorithmes

```python
# Tester si MATILDA est significativement meilleur que SPIDER
comparison = compare_algorithms(matilda_file, spider_file, "MATILDA", "SPIDER")

if comparison['accuracy'].is_significant:
    print("MATILDA est significativement différent de SPIDER")
    print(f"Taille d'effet: {comparison['accuracy'].effect_size:.4f}")
```

### 3. Rapport de Publication

```bash
# Générer rapport complet pour article scientifique
python generate_statistics_report.py --markdown --verbose

# Inclure :
# - statistical_analysis_report.md dans le paper
# - Tableaux de statistiques descriptives
# - Résultats des tests de significativité
```

## 📁 Structure des Fichiers Générés

```
data/output/
├── MATILDA_Bupa_results.json              # Règles découvertes
├── MATILDA_Bupa_statistics.json           # ← NOUVEAU : Stats descriptives
├── SPIDER_Bupa_results.json
├── SPIDER_Bupa_statistics.json            # ← NOUVEAU
├── statistical_analysis_report.json       # ← NOUVEAU : Rapport global
└── statistical_analysis_report.md         # ← NOUVEAU : Version Markdown
```

## ⚙️ Options de Configuration

| Option | Description | Défaut |
|--------|-------------|--------|
| `compute_statistics` | Calculer stats par fichier | `false` |
| `generate_statistical_report` | Générer rapport global | `false` |
| `statistical_report_name` | Nom du fichier rapport | `statistical_analysis_report.json` |

## 🔧 API Complète

### Fonctions Principales

```python
# Statistiques descriptives
compute_statistics(values, metric_name) -> PerformanceStats

# Tests de significativité
perform_t_test(group1, group2, ...) -> SignificanceTest
perform_mannwhitneyu_test(group1, group2, ...) -> SignificanceTest

# Analyse de fichiers
analyze_rules_performance(rules_file) -> Dict[str, PerformanceStats]
compare_algorithms(file1, file2, ...) -> Dict[str, SignificanceTest]

# Rapports
generate_statistical_report(results_dir) -> Dict
```

### Classes

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

@dataclass
class SignificanceTest:
    test_name: str
    metric: str
    group1_name: str
    group2_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size: Optional[float]
```

## 📚 Documentation

- **`STATISTICS_FEATURE.md`** - Documentation complète
  - Exemples détaillés
  - API reference
  - Bonnes pratiques
  - Interprétation des résultats

## ✅ Avantages

1. **Automatique** - Intégré dans le workflow MATILDA
2. **Complet** - Statistiques + tests de significativité
3. **Flexible** - Utilisation autonome ou intégrée
4. **Scientifique** - Tests statistiques standards
5. **Exportable** - Formats JSON et Markdown

## 🎓 Références Scientifiques

- Cohen, J. (1988). Statistical Power Analysis
- Mann & Whitney (1947). Test of Stochastic Ordering
- Student (1908). The Probable Error of a Mean

## 🔗 Workflow Complet

1. **Configuration** : `config.yaml` → activer `compute_statistics`
2. **Exécution** : `python src/main.py`
3. **Résultats** : Statistiques automatiquement calculées
4. **Rapport** : `python generate_statistics_report.py --markdown`
5. **Analyse** : Consulter les rapports JSON/Markdown

---

## 🎉 Résultat

MATILDA offre maintenant une **analyse statistique complète et automatique** des performances :

✅ **Scientifiquement rigoureux** - Tests statistiques standards  
✅ **Facilement interprétable** - Rapports clairs et détaillés  
✅ **Totalement automatisé** - Intégré dans le pipeline  
✅ **Exportable** - Formats multiples (JSON, Markdown)  
✅ **Testé** - Suite de tests complète  

**Implémentation complète et prête à l'emploi** ✓
