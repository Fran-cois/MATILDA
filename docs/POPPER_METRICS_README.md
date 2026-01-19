# Calcul des Métriques MATILDA pour Popper/ILP

## Description

Script Python pour calculer les métriques MATILDA (correctness, compatibility, support, confidence) sur les résultats de l'algorithme Popper/ILP.

## Fichiers

- **`compute_popper_metrics.py`**: Script principal
- **`POPPER_METRICS_GUIDE.md`**: Guide complet d'utilisation
- **`POPPER_METRICS_README.md`**: Ce fichier

## Usage Rapide

```bash
# Traiter un fichier spécifique
python compute_popper_metrics.py data/output/popper_Bupa_results.json

# Traiter tous les fichiers Popper trouvés
python compute_popper_metrics.py
```

## Métriques Calculées

| Métrique | Description | Valeurs |
|----------|-------------|---------|
| **Correctness** | Validité de la règle logique | ✓ / ✗ |
| **Compatibility** | Compatibilité des prédicats | ✓ / ✗ |
| **Support** | Proportion de tuples satisfaits | 0.0 - 1.0 |
| **Confidence** | Précision de la règle | 0.0 - 1.0 |

## Format d'Entrée

Fichier JSON avec règles Horn ou TGD:

```json
{
    "rules": [
        {
            "type": "TGDRule",
            "body": [...],
            "head": [...],
            "display": "head :- body1, body2",
            "accuracy": 0.85,
            "confidence": 0.90
        }
    ]
}
```

## Format de Sortie

### 1. JSON enrichi

`popper_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.json`

Contient les règles avec métriques ajoutées.

### 2. Rapport Markdown

`popper_Bupa_results_with_metrics_YYYY-MM-DD_HH-MM-SS.md`

Résumé des statistiques:
- Nombre total de règles
- Règles valides (%)
- Support moyen
- Confidence moyenne
- Tableau détaillé par règle

## Différences avec Spider

| Aspect | Spider | Popper/ILP |
|--------|--------|------------|
| Type de règle | InclusionDependency | HornRule / TGDRule |
| Structure | Tables/colonnes | Prédicats logiques |
| Format | `T1[C1] ⊆ T2[C2]` | `head :- body` |
| Script | `compute_spider_metrics.py` | `compute_popper_metrics.py` |

## Exemples

### Règle Horn (simple)

```
drinks(X,Y) :- bupa(X,Y)
```

- **Validité**: ✓ (tables existent)
- **Support**: 0.78
- **Confidence**: 0.82

### Règle TGD (complexe)

```
sgot(X,W) :- bupa(X,Y), drinks(Y,Z)
```

- **Validité**: ✓ (prédicats compatibles)
- **Support**: 0.85
- **Confidence**: 0.90

## Documentation Complète

Voir [`POPPER_METRICS_GUIDE.md`](POPPER_METRICS_GUIDE.md) pour:
- Guide d'installation
- Exemples détaillés
- Interprétation des résultats
- Dépannage
- Comparaison avec Spider

## Exécution de Popper

Pour générer des résultats Popper:

```bash
python src/main.py -c config_popper_bupa.yaml
```

Avec `config_popper_bupa.yaml`:

```yaml
database:
  name: Bupa.db
  path: data/db/

algorithm:
  name: POPPER
  max_rules: 20
  timeout: 300
```

## Classes Principales

### `PopperMetricsCalculator`

```python
calculator = PopperMetricsCalculator(
    database_path="data/db/",
    database_name="Bupa.db",
    output_dir="data/output"
)

# Charger résultats
rules = calculator.load_popper_results("popper_results.json")

# Calculer métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

## Méthodes Clés

- `load_popper_results()`: Charge règles depuis JSON
- `calculate_rule_validity()`: Vérifie validité d'une règle
- `calculate_support_confidence()`: Calcule support/confidence
- `calculate_metrics()`: Calcule toutes les métriques
- `save_results()`: Sauvegarde JSON + rapport MD
- `generate_report()`: Génère rapport récapitulatif

## Logs

Les logs sont sauvegardés dans `popper_metrics.log`:

```
2026-01-14 18:45:00 - INFO - Chargement des résultats Popper depuis ...
2026-01-14 18:45:01 - INFO - 15 règles chargées
2026-01-14 18:45:02 - INFO - Calcul des métriques MATILDA sur 15 règles...
2026-01-14 18:45:05 - INFO - Résultats sauvegardés avec succès
```

## Interprétation

### Règle de Haute Qualité

- **Correctness**: ✓
- **Compatibility**: ✓
- **Support**: > 0.5
- **Confidence**: > 0.7

→ Règle fréquente et précise, à conserver

### Règle à Améliorer

- **Correctness**: ✓
- **Compatibility**: ✓
- **Support**: < 0.3
- **Confidence**: < 0.5

→ Règle rare ou imprécise, à revoir

## Dépendances

- Python 3.11+
- SQLAlchemy
- Modules MATILDA:
  - `database.alchemy_utility`
  - `utils.rules` (HornRule, TGDRule, RuleIO)

## Auteur

Créé pour le projet MATILDA.

## Voir Aussi

- [`compute_spider_metrics.py`](compute_spider_metrics.py): Métriques pour Spider
- [`SPIDER_METRICS_GUIDE.md`](SPIDER_METRICS_GUIDE.md): Guide Spider
- [`README.md`](README.md): Documentation MATILDA principale
