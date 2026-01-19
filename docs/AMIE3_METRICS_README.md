# Calcul des Métriques MATILDA pour AMIE3

## Description

Script Python pour calculer les métriques MATILDA (correctness, compatibility, support, confidence) sur les résultats d'AMIE3.

AMIE3 (AMIE+ plus improvements) est un système d'apprentissage de règles pour graphes de connaissances.

## Fichiers

- **`compute_amie3_metrics.py`**: Script principal (550+ lignes)
- **`AMIE3_METRICS_README.md`**: Ce fichier

## Usage Rapide

```bash
# Traiter un fichier spécifique
python compute_amie3_metrics.py data/output/AMIE3_Bupa_results.json

# Traiter tous les fichiers AMIE3 trouvés
python compute_amie3_metrics.py

# Avec le script unifié
python compute_all_metrics.py amie3_Bupa_example_results.json
python compute_all_metrics.py --algorithm amie3
```

## Métriques Calculées

| Métrique | Type | Description |
|----------|------|-------------|
| **correctness** | bool | Validité de la règle logique |
| **compatibility** | bool | Compatibilité des prédicats |
| **support** | float | Proportion de tuples (0.0 - 1.0) |
| **confidence** | float | Précision de la règle (0.0 - 1.0) |

## Format d'Entrée

### Format JSON (TGDRule)

```json
[
  {
    "type": "TGDRule",
    "body": [
      "Predicate(variable1='X', relation='bupa', variable2='Y')",
      "Predicate(variable1='Y', relation='drinks', variable2='Z')"
    ],
    "head": [
      "Predicate(variable1='X', relation='sgot', variable2='W')"
    ],
    "display": "sgot(X,W) :- bupa(X,Y), drinks(Y,Z)",
    "accuracy": -1.0,
    "confidence": 0.8234
  }
]
```

### Format TSV (AMIE3 brut)

```
Loaded 100
?x bupa ?y drinks ?z => ?x sgot ?w	0.8234	34.5
?x sgot ?y => ?x alkphos ?y	0.7123	25.2
```

## Format de Sortie

### 1. JSON enrichi

`amie3_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.json`

Contient les règles avec métriques ajoutées:
- `correct`: bool (validité)
- `compatible`: bool (compatibilité)
- `support`: float (support approximé)
- `confidence`: float (précision AMIE3)

### 2. Rapport Markdown

`amie3_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.md`

Résumé des statistiques avec tableau détaillé.

## Caractéristiques Spéciales

### AMIE3 vs Popper vs AnyBURL

| Aspect | Popper | AnyBURL | AMIE3 |
|--------|--------|---------|-------|
| Type | ILP (Prolog) | Graph Learning | Graph Learning |
| Prédicats | `table___sep___col` | Relations simples | Relations simples |
| Accuracy | Pré-calculé | -1.0 | -1.0 |
| Confidence | confidence | confidence | confidence |
| Support | accuracy (%) | Approximé | Approximé |
| Sortie | JSON TGDRule | JSON TGDRule | JSON/TSV TGDRule |

### Spécificités AMIE3

- **Format flexible**: Support JSON (TGDRule) et TSV (brut)
- **Prédicat multi-hop**: `?x r1 ?y r2 ?z => ?x r3 ?w`
- **Confidence haute**: Souvent 0.7-0.9 (algorithme conservateur)
- **Détection d'or**: Peut détecter `Loaded N` pour normaliser support

## Classe AMIE3MetricsCalculator

```python
from compute_amie3_metrics import AMIE3MetricsCalculator

calculator = AMIE3MetricsCalculator(
    database_path="data/db/",
    database_name="Bupa.db",
    output_dir="data/output"
)

# Charger résultats
rules = calculator.load_amie3_results("amie3_results.json")

# Calculer métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

## Méthodes Principales

| Méthode | Description |
|---------|-------------|
| `load_amie3_results(filepath)` | Charge JSON ou TSV |
| `_load_json(filepath)` | Parse fichier JSON TGDRule |
| `_load_tsv(filepath)` | Parse format TSV AMIE3 brut |
| `_parse_predicates(str)` | Parse format `?x r1 ?y` |
| `calculate_rule_validity(rule)` | Vérifie tables existantes |
| `calculate_support_confidence(rule)` | Calcule support/confidence |
| `calculate_metrics(rules)` | Enrichit toutes les règles |
| `save_results(rules, filename)` | JSON + rapport Markdown |
| `generate_report(rules, path)` | Génère résumé Markdown |
| `find_amie3_results()` | Auto-découvre fichiers |

## Exemple de Résultats

### Résumé

```
Nombre total de règles: 5
Règles valides: 3 (60.0%)
Support moyen: 0.3450
Confidence moyenne: 0.7723
```

### Tableau

| # | Règle | Valide | Support | Confidence |
|---|-------|--------|---------|------------|
| 1 | sgot(X,W) :- bupa(X,Y), drinks(Y,Z) | ✓ | 0.3450 | 0.8234 |
| 2 | alkphos(X,Y) :- sgot(X,Y) | ✗ | 0.5000 | 0.7123 |

## Dépendances

```
Python 3.11+
SQLAlchemy
src.database.alchemy_utility
src.utils.rules (TGDRule, RuleIO)
```

## Logs

Fichier: `amie3_metrics.log`

```
2026-01-14 22:58:02 - INFO - Loading AMIE3 results from amie3_Bupa_example_results.json
2026-01-14 22:58:02 - INFO - 5 règles chargées
2026-01-14 22:58:02 - INFO - Calcul des métriques MATILDA sur 5 règles AMIE3...
2026-01-14 22:58:02 - INFO - Traitement de la règle: sgot(X,W) :- bupa(X,Y), drinks(Y,Z)
2026-01-14 22:58:02 - INFO -   → Valid: False | Support: 0.5000 | Confidence: 0.8234
2026-01-14 22:58:02 - INFO - Résultats sauvegardés avec succès
2026-01-14 22:58:02 - INFO - Rapport généré avec succès
2026-01-14 22:58:02 - INFO - Traitement terminé avec succès!
```

## Intégration avec compute_all_metrics.py

Le script unifié détecte automatiquement AMIE3:

```bash
# Auto-détection
python compute_all_metrics.py amie3_Bupa_results.json
# → Algorithme détecté: amie3

# Avec filtre
python compute_all_metrics.py --algorithm amie3
# → Traite tous les fichiers AMIE3 trouvés
```

## Interprétation des Résultats

### Règle de Haute Qualité

- **Correctness**: ✓ (tables valides)
- **Compatibility**: ✓ (prédicats compatibles)
- **Support**: > 0.5
- **Confidence**: > 0.7

→ Règle fréquente et précise, de confiance élevée

### Règle Rare

- **Support**: < 0.3
- **Confidence**: < 0.5

→ Règle peu fréquente, à revoir

## Comparaison avec Autres Calculateurs

| Script | Règles | Format | Focus |
|--------|--------|--------|-------|
| `compute_spider_metrics.py` | InclusionDependency | JSON | Dépendances inclusions |
| `compute_popper_metrics.py` | HornRule/TGDRule | JSON | Règles logiques ILP |
| `compute_anyburl_metrics.py` | TGDRule | JSON | Règles graphe |
| `compute_amie3_metrics.py` | TGDRule | JSON/TSV | **Règles graphe AMIE3** |

## Troubleshooting

### Erreur: "Cannot import RuleIO"

Vérifier que PYTHONPATH inclut `src/`:

```bash
export PYTHONPATH=/path/to/MATILDA/src:$PYTHONPATH
python compute_amie3_metrics.py
```

### Erreur: "Database not found"

AMIE3 peut fonctionner sans base de données (metrics = False pour toutes les règles).

### Fichier TSV vide

Les fichiers TSV AMIE3 peuvent être vides si l'algorithme n'a découvert aucune règle.

## Voir Aussi

- [compute_spider_metrics.py](compute_spider_metrics.py)
- [compute_popper_metrics.py](compute_popper_metrics.py)
- [compute_anyburl_metrics.py](compute_anyburl_metrics.py)
- [compute_all_metrics.py](compute_all_metrics.py)
- [METRICS_COMPLETE_GUIDE.md](METRICS_COMPLETE_GUIDE.md)
- [src/algorithms/amie3.py](src/algorithms/amie3.py)
