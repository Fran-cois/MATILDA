# Calcul des Métriques MATILDA - Guide Complet

## Vue d'ensemble

Ce projet fournit des outils pour calculer les métriques MATILDA (correctness, compatibility, support, confidence) sur les résultats de différents algorithmes de découverte de règles :

- **Spider** : Découverte d'inclusion dependencies (IND)
- **Popper/ILP** : Apprentissage inductif de logique (Horn rules, TGD rules)

## Scripts Disponibles

| Script | Description | Usage |
|--------|-------------|-------|
| **`compute_spider_metrics.py`** | Métriques MATILDA pour Spider | `python compute_spider_metrics.py [fichier]` |
| **`compute_popper_metrics.py`** | Métriques MATILDA pour Popper/ILP | `python compute_popper_metrics.py [fichier]` |
| **`compute_all_metrics.py`** | Script unifié (auto-détection) | `python compute_all_metrics.py [options]` |

## Quick Start

### 1. Calculer les métriques pour Spider

```bash
# Sur un fichier spécifique
python compute_spider_metrics.py data/output/spider_Bupa_results.json

# Sur tous les fichiers Spider trouvés
python compute_spider_metrics.py
```

### 2. Calculer les métriques pour Popper

```bash
# Sur un fichier spécifique
python compute_popper_metrics.py data/output/popper_Bupa_results.json

# Sur tous les fichiers Popper trouvés
python compute_popper_metrics.py
```

### 3. Calculer toutes les métriques (script unifié)

```bash
# Traiter tous les résultats trouvés (Spider + Popper)
python compute_all_metrics.py

# Traiter seulement Spider
python compute_all_metrics.py --algorithm spider

# Traiter seulement Popper
python compute_all_metrics.py --algorithm popper

# Traiter un fichier spécifique (auto-détection)
python compute_all_metrics.py results.json
```

## Métriques MATILDA

### 1. Correctness (Validité)
- **Type:** Booléen (True/False)
- **Description:** La règle est valide selon la sémantique des données
- **Spider:** Vérifie que les colonnes référencées existent et peuvent être jointes
- **Popper:** Vérifie que les tables référencées existent et ont des données

### 2. Compatibility (Compatibilité)
- **Type:** Booléen (True/False)
- **Description:** Les éléments de la règle sont compatibles entre eux
- **Spider:** Vérifie la compatibilité des types de colonnes
- **Popper:** Vérifie la compatibilité des prédicats

### 3. Support
- **Type:** Float (0.0 - 1.0)
- **Description:** Proportion de tuples satisfaisant la règle
- **Spider:** Calcul basé sur COUNT des tuples dans les tables
- **Popper:** Utilise l'accuracy fournie par Popper

### 4. Confidence
- **Type:** Float (0.0 - 1.0)
- **Description:** Précision de la règle
- **Spider:** Ratio entre tuples satisfaisant la règle et total
- **Popper:** Utilise la confidence fournie par Popper

## Format des Résultats

### Spider (InclusionDependency)

**Entrée:**
```json
[
  {
    "type": "InclusionDependency",
    "table_dependant": "bupa",
    "columns_dependant": ["arg1"],
    "table_referenced": "drinks",
    "columns_referenced": ["arg1"],
    "display": "bupa[arg1] ⊆ drinks[arg1]"
  }
]
```

**Sortie avec métriques:**
```json
[
  {
    "type": "InclusionDependency",
    "table_dependant": "bupa",
    "columns_dependant": ["arg1"],
    "table_referenced": "drinks",
    "columns_referenced": ["arg1"],
    "display": "bupa[arg1] ⊆ drinks[arg1]",
    "correct": true,
    "compatible": true,
    "support": 0.4506,
    "confidence": 0.9006
  }
]
```

### Popper (HornRule / TGDRule)

**Entrée:**
```json
[
  {
    "type": "TGDRule",
    "body": [
      "Predicate(variable1='X', relation='bupa___sep___arg1', variable2='Y')",
      "Predicate(variable1='Y', relation='drinks___sep___arg2', variable2='Z')"
    ],
    "head": [
      "Predicate(variable1='X', relation='sgot___sep___arg1', variable2='W')"
    ],
    "display": "sgot(X,W) :- bupa(X,Y), drinks(Y,Z)",
    "accuracy": 0.8523,
    "confidence": 0.9012
  }
]
```

**Sortie avec métriques:**
```json
[
  {
    "type": "TGDRule",
    "body": [...],
    "head": [...],
    "display": "sgot(X,W) :- bupa(X,Y), drinks(Y,Z)",
    "accuracy": 0.8523,
    "confidence": 0.9012,
    "correct": true,
    "compatible": true
  }
]
```

## Fichiers Générés

Pour chaque fichier de résultats traité, deux fichiers sont générés :

### 1. JSON enrichi
`{original_name}_with_metrics_YYYY-MM-DD_HH-MM-SS.json`

Contient les règles avec toutes les métriques ajoutées.

### 2. Rapport Markdown
`{original_name}_with_metrics_YYYY-MM-DD_HH-MM-SS.md`

Contient un résumé lisible :
- Statistiques globales (nombre de règles, règles valides, moyennes)
- Tableau détaillé avec toutes les règles et leurs métriques
- Définitions des métriques
- Informations sur le type de règles

## Documentation Détaillée

- **Spider:** [SPIDER_METRICS_GUIDE.md](SPIDER_METRICS_GUIDE.md)
- **Popper:** [POPPER_METRICS_GUIDE.md](POPPER_METRICS_GUIDE.md)
- **Résumé Popper:** [POPPER_METRICS_SUMMARY.md](POPPER_METRICS_SUMMARY.md)

## Exemples d'Utilisation

### Workflow Complet Spider

```bash
# 1. Générer les résultats Spider
python src/main.py -c config_spider_bupa.yaml

# 2. Calculer les métriques MATILDA
python compute_spider_metrics.py data/results/Bupa/spider/spider_Bupa_results.json

# 3. Consulter les résultats
cat data/output/spider_Bupa_results_with_metrics_*.md
```

### Workflow Complet Popper

```bash
# 1. Générer les résultats Popper
python src/main.py -c config_popper_bupa.yaml

# 2. Calculer les métriques MATILDA
python compute_popper_metrics.py data/results/Bupa/popper/popper_Bupa_results.json

# 3. Consulter les résultats
cat data/output/popper_Bupa_results_with_metrics_*.md
```

### Traitement de Tous les Résultats

```bash
# Calculer les métriques sur tous les résultats trouvés
python compute_all_metrics.py

# Résultats dans data/output/ avec horodatage
```

## Utilisation Programmatique

### Spider

```python
from compute_spider_metrics import SpiderMetricsCalculator

# Créer le calculateur
calculator = SpiderMetricsCalculator(
    database_path="data/db/",
    database_name="Bupa.db",
    output_dir="data/output"
)

# Charger les résultats
rules = calculator.load_spider_results("spider_results.json")

# Calculer les métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

### Popper

```python
from compute_popper_metrics import PopperMetricsCalculator

# Créer le calculateur
calculator = PopperMetricsCalculator(
    database_path="data/db/",
    database_name="Bupa.db",
    output_dir="data/output"
)

# Charger les résultats
rules = calculator.load_popper_results("popper_results.json")

# Calculer les métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

## Comparaison Spider vs Popper

| Aspect | Spider | Popper |
|--------|--------|--------|
| **Type de règle** | InclusionDependency | HornRule / TGDRule |
| **Structure** | Tables et colonnes | Prédicats logiques |
| **Format règle** | `T1[C1] ⊆ T2[C2]` | `head :- body1, body2` |
| **Calcul validité** | Vérification JOIN | Vérification prédicats |
| **Calcul support** | COUNT sur tables | accuracy de Popper |
| **Calcul confidence** | Ratio tuples | confidence de Popper |
| **Complexité** | Moyen | Élevé |

## Logs

Les scripts génèrent des logs détaillés :

- **Spider:** `spider_metrics.log`
- **Popper:** `popper_metrics.log`

Format des logs :
```
2026-01-14 18:30:00 - INFO - Chargement des résultats depuis ...
2026-01-14 18:30:01 - INFO - 10 règles chargées
2026-01-14 18:30:02 - INFO - Calcul des métriques MATILDA...
2026-01-14 18:30:05 - INFO - Résultats sauvegardés avec succès
```

## Dépannage

### Erreur: "Aucun fichier de résultats trouvé"

**Solution:**
1. Vérifier que l'algorithme a été exécuté avec succès
2. Vérifier les chemins de recherche
3. Créer un fichier exemple manuellement (voir exemples fournis)

### Erreur: "Table non trouvée"

**Solution:**
1. Vérifier que la base de données existe dans `data/db/`
2. Vérifier le nom de la base de données dans le fichier JSON
3. S'assurer que les tables référencées existent

### Métriques incorrectes

**Solution:**
1. Vérifier les logs pour les warnings
2. Vérifier le format des données d'entrée
3. Consulter la documentation spécifique à l'algorithme

## Tests

Des fichiers de test sont fournis :

- **`spider_Bupa_example_results.json`** : 10 règles IND
- **`popper_Bupa_example_results.json`** : 5 règles (3 TGD, 2 Horn)

Pour tester les scripts :

```bash
# Test Spider
python compute_spider_metrics.py spider_Bupa_example_results.json

# Test Popper
python compute_popper_metrics.py popper_Bupa_example_results.json

# Test script unifié
python compute_all_metrics.py --algorithm all
```

## Interprétation des Résultats

### Règle de Haute Qualité

Une règle de haute qualité devrait avoir :
- ✓ **Correctness:** True (valide)
- ✓ **Compatibility:** True (compatible)
- ✓ **Support:** > 0.5 (au moins 50%)
- ✓ **Confidence:** > 0.7 (au moins 70%)

### Règle à Améliorer

Critères pour identifier les règles à améliorer :
- ✗ **Correctness:** False (invalide) → Ignorer ou corriger
- ✗ **Support:** < 0.3 → Règle trop rare
- ✗ **Confidence:** < 0.5 → Règle imprécise

## Architecture des Scripts

### compute_spider_metrics.py
- Classe: `SpiderMetricsCalculator`
- Méthodes principales:
  - `load_spider_results()`: Charge les IND
  - `calculate_validity()`: Vérifie la validité
  - `calculate_support_confidence()`: Calcule support/confidence
  - `save_results()`: Sauvegarde JSON + MD

### compute_popper_metrics.py
- Classe: `PopperMetricsCalculator`
- Méthodes principales:
  - `load_popper_results()`: Charge les règles Horn/TGD
  - `calculate_rule_validity()`: Vérifie la validité
  - `calculate_support_confidence()`: Calcule support/confidence
  - `save_results()`: Sauvegarde JSON + MD

### compute_all_metrics.py
- Script unifié avec auto-détection
- Fonctions:
  - `detect_algorithm()`: Détecte le type de résultats
  - `process_file()`: Traite un fichier
  - `find_all_results()`: Trouve tous les résultats

## Dépendances

- Python 3.11+
- SQLAlchemy
- Modules MATILDA:
  - `database.alchemy_utility`
  - `utils.rules` (InclusionDependency, HornRule, TGDRule, RuleIO)

## Contributions

Pour ajouter un nouveau type d'algorithme :

1. Créer `compute_{algorithm}_metrics.py`
2. Implémenter la classe `{Algorithm}MetricsCalculator`
3. Ajouter la logique de détection dans `compute_all_metrics.py`
4. Créer la documentation `{ALGORITHM}_METRICS_GUIDE.md`

## Licence

Projet MATILDA - 2026

## Contact

Pour toute question ou problème, consulter :
1. Les logs générés par les scripts
2. La documentation spécifique à l'algorithme
3. Les fichiers exemple fournis
