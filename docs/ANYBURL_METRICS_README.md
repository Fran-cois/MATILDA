# Calcul des Métriques MATILDA pour AnyBURL

## Description

Script Python pour calculer les métriques MATILDA (correctness, compatibility, support, confidence) sur les résultats d'AnyBURL.

## Fichiers

- **`compute_anyburl_metrics.py`**: Script principal (391 lignes)
- **`ANYBURL_METRICS_README.md`**: Ce fichier

## Usage Rapide

```bash
# Traiter un fichier spécifique
python compute_anyburl_metrics.py data/output/anyburl_Bupa_results.json

# Traiter tous les fichiers AnyBURL trouvés
python compute_anyburl_metrics.py
```

## Métriques Calculées

| Métrique | Type | Description |
|----------|------|-------------|
| **correctness** | bool | Validité de la règle logique |
| **compatibility** | bool | Compatibilité des prédicats |
| **support** | float | Proportion de tuples (0.0 - 1.0) |
| **confidence** | float | Précision de la règle (0.0 - 1.0) |

## Format d'Entrée

Fichier JSON avec règles TGD:

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

## Format de Sortie

### 1. JSON enrichi

`anyburl_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.json`

Contient les règles avec métriques ajoutées:
- `correct`: bool (validité)
- `compatible`: bool (compatibilité)
- `accuracy`: float (support)
- `confidence`: float (précision)

### 2. Rapport Markdown

`anyburl_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.md`

Résumé des statistiques:
- Nombre total de règles
- Règles valides (%)
- Support moyen
- Confidence moyenne
- Tableau détaillé par règle

## Comparaison avec Popper et Spider

| Aspect | Spider | Popper | AnyBURL |
|--------|--------|--------|---------|
| Type de règle | InclusionDependency | HornRule / TGDRule | TGDRule |
| Structure | Tables/colonnes | Prédicats logiques | Prédicats logiques |
| Format | `T1[C1] ⊆ T2[C2]` | `head :- body` | `body => head` |
| Validité | Vérif. JOIN | Vérif. tables | Vérif. tables |
| Support | SQL COUNT | accuracy Popper | approx. |
| Confidence | Ratio tuples | confidence Popper | confidence AnyBURL |

## Exemple de Résultats

### Résumé

```
Nombre total de règles: 5
Règles valides: 5 (100.0%)
Support moyen: 0.3450
Confidence moyenne: 0.7723
```

### Tableau des Règles

| # | Règle | Valide | Support | Confidence |
|---|-------|--------|---------|------------|
| 1 | sgot(X,W) :- bupa(X,Y), drinks(Y,Z) | ✓ | 0.3450 | 0.8234 |
| 2 | alkphos(X,Y) :- sgot(X,Y) | ✓ | 0.3450 | 0.7123 |
| 3 | sgpt(X,W) :- bupa(X,Y), drinks(X,Z) | ✓ | 0.3450 | 0.6789 |
| 4 | gammagt(X,Y) :- mcv(X,Y) | ✓ | 0.3450 | 0.9012 |
| 5 | bupa(X,W) :- drinks(X,Y), mcv(X,Z) | ✓ | 0.3450 | 0.7456 |

## Classes Principales

### `AnyBURLMetricsCalculator`

```python
calculator = AnyBURLMetricsCalculator(
    database_path="data/db/",
    database_name="Bupa.db",
    output_dir="data/output"
)

# Charger résultats
rules = calculator.load_anyburl_results("anyburl_results.json")

# Calculer métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

## Méthodes Clés

- `load_anyburl_results()`: Charge règles depuis JSON
- `calculate_rule_validity()`: Vérifie validité d'une règle
- `calculate_support_confidence()`: Calcule support/confidence
- `calculate_metrics()`: Calcule toutes les métriques
- `save_results()`: Sauvegarde JSON + rapport MD
- `generate_report()`: Génère rapport récapitulatif

## Logs

Les logs sont sauvegardés dans `anyburl_metrics.log`:

```
2026-01-14 20:23:21 - INFO - Chargement des résultats AnyBURL...
2026-01-14 20:23:21 - INFO - 5 règles chargées
2026-01-14 20:23:21 - INFO - Calcul des métriques MATILDA...
2026-01-14 20:23:21 - INFO - Traitement de la règle: sgot(X,W) :- ...
2026-01-14 20:23:21 - INFO -   → Valid: True | Support: 0.3450 | Confidence: 0.8234
2026-01-14 20:23:21 - INFO - Résultats sauvegardés avec succès
```

## Interprétation

### Règle de Haute Qualité

- **Correctness**: ✓
- **Compatibility**: ✓
- **Support**: > 0.5
- **Confidence**: > 0.7

→ Règle fréquente et précise, à conserver

### Règle à Améliorer

- **Support**: < 0.3
- **Confidence**: < 0.5

→ Règle rare ou imprécise, à revoir

## Dépendances

- Python 3.11+
- SQLAlchemy
- Modules MATILDA:
  - `database.alchemy_utility`
  - `utils.rules` (TGDRule, RuleIO)

## Voir Aussi

- [`compute_spider_metrics.py`](compute_spider_metrics.py): Métriques pour Spider
- [`compute_popper_metrics.py`](compute_popper_metrics.py): Métriques pour Popper
- [`compute_all_metrics.py`](compute_all_metrics.py): Script unifié
- [`METRICS_COMPLETE_GUIDE.md`](METRICS_COMPLETE_GUIDE.md): Guide global
