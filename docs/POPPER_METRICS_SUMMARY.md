# Résumé: Métriques MATILDA pour Popper/ILP

## Fichiers créés

✅ **compute_popper_metrics.py** (503 lignes)
- Script principal pour calculer les métriques MATILDA sur les résultats Popper/ILP
- Classe `PopperMetricsCalculator` avec toutes les fonctionnalités
- Gestion des règles Horn et TGD
- Calcul de correctness, compatibility, support, confidence
- Génération de rapports JSON et Markdown

✅ **POPPER_METRICS_GUIDE.md**
- Guide complet d'utilisation du script
- Explications détaillées des métriques MATILDA pour Popper
- Exemples d'utilisation
- Section de dépannage
- Comparaison avec Spider

✅ **POPPER_METRICS_README.md**
- Documentation récapitulative
- Usage rapide
- Format d'entrée/sortie
- Tableau comparatif Spider vs Popper

✅ **popper_Bupa_example_results.json**
- Fichier de test avec 5 règles (3 TGD, 2 Horn)
- Format correct compatible avec RuleIO
- Utilisé pour tester le script

## Fonctionnalités Implémentées

### 1. Chargement des Résultats
- Utilise `RuleIO.load_rules_from_json()` pour charger les règles
- Compatible avec HornRule et TGDRule
- Gestion des erreurs de parsing

### 2. Calcul de Validité (Correctness)
- Vérification de l'existence des tables
- Validation de la structure logique
- Extraction des tables depuis les prédicats

### 3. Calcul Support/Confidence
- Utilise les valeurs `accuracy` et `confidence` fournies par Popper
- Calcul approximatif si valeurs non disponibles
- Basé sur le nombre de tuples dans les tables

### 4. Sauvegarde des Résultats
- JSON avec règles enrichies (métriques ajoutées)
- Rapport Markdown avec statistiques et tableau
- Horodatage automatique des fichiers

## Test Réussi

```bash
python compute_popper_metrics.py popper_Bupa_example_results.json
```

**Résultats:**
- 5 règles traitées
- 100% de règles valides
- Support moyen: 0.8053
- Confidence moyenne: 0.8567
- Fichiers générés:
  - `popper_Bupa_example_results_with_metrics_2026-01-14_18-41-17.json`
  - `popper_Bupa_example_results_with_metrics_2026-01-14_18-41-17.md`

## Différences avec Spider

| Aspect | compute_spider_metrics.py | compute_popper_metrics.py |
|--------|--------------------------|---------------------------|
| **Type de règle** | InclusionDependency | HornRule / TGDRule |
| **Structure** | Tables et colonnes | Prédicats logiques |
| **Validité** | Vérifie JOINs entre tables | Vérifie existence des tables |
| **Support** | COUNT sur tables | accuracy de Popper |
| **Confidence** | Ratio tuples | confidence de Popper |
| **Format prédicats** | N/A | `Predicate(variable1='...', relation='...', variable2='...')` |

## Utilisation

### Mode 1: Fichier spécifique
```bash
python compute_popper_metrics.py data/output/popper_Bupa_results.json
```

### Mode 2: Auto-découverte
```bash
python compute_popper_metrics.py
```
Cherche automatiquement dans:
- `data/output/*popper*.json`
- `data/output/*ILP*.json`
- `data/results/*/popper/popper_*_results.json`

### Mode 3: Programmmatique
```python
from compute_popper_metrics import PopperMetricsCalculator

calculator = PopperMetricsCalculator("data/db/", "Bupa.db")
rules = calculator.load_popper_results("popper_results.json")
enriched_rules = calculator.calculate_metrics(rules)
calculator.save_results(enriched_rules)
```

## Format des Règles Popper

### TGDRule (Tuple-Generating Dependencies)
```json
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
  "confidence": 0.9012,
  "correct": true,
  "compatible": true
}
```

### HornRule
```json
{
  "type": "HornRule",
  "body": [
    "Predicate(variable1='X', relation='bupa___sep___arg1', variable2='Y')"
  ],
  "head": "Predicate(variable1='X', relation='drinks___sep___arg1', variable2='Y')",
  "display": "drinks(X,Y) :- bupa(X,Y)",
  "accuracy": 0.7845,
  "confidence": 0.8234,
  "correct": true,
  "compatible": true
}
```

## Métriques Calculées

### 1. Correctness (correct)
- **Type:** Booléen (True/False)
- **Calcul:** Vérifie que toutes les tables référencées existent dans la BD
- **Utilisation:** Filtrer les règles invalides

### 2. Compatibility (compatible)
- **Type:** Booléen (True/False)
- **Calcul:** Même valeur que correctness pour Popper
- **Utilisation:** Vérifier la compatibilité des prédicats

### 3. Support (accuracy pour TGD)
- **Type:** Float (0.0 - 1.0)
- **Calcul:** Utilise `accuracy` de Popper ou calcul approximatif
- **Utilisation:** Mesurer la fréquence de la règle

### 4. Confidence
- **Type:** Float (0.0 - 1.0)
- **Calcul:** Utilise `confidence` de Popper ou calcul approximatif
- **Utilisation:** Mesurer la précision de la règle

## Logs

Le script génère des logs dans `popper_metrics.log`:

```
2026-01-14 18:41:17 - INFO - Chargement des résultats Popper depuis popper_Bupa_example_results.json...
2026-01-14 18:41:17 - INFO - 5 règles chargées
2026-01-14 18:41:17 - INFO - Calcul des métriques MATILDA sur 5 règles Popper...
2026-01-14 18:41:17 - INFO - Traitement de la règle TGDRule: sgot(X,W) :- bupa(X,Y), drinks(Y,Z)...
2026-01-14 18:41:17 - INFO -   → Valid: True | Support: 0.8523 | Confidence: 0.9012
...
2026-01-14 18:41:17 - INFO - Résultats sauvegardés avec succès
2026-01-14 18:41:17 - INFO - Traitement terminé avec succès!
```

## Prochaines Étapes

Pour utiliser ce script dans votre workflow:

1. **Exécuter Popper sur votre base de données:**
   ```bash
   python src/main.py -c config_popper.yaml
   ```

2. **Calculer les métriques MATILDA:**
   ```bash
   python compute_popper_metrics.py data/results/Bupa/popper/popper_Bupa_results.json
   ```

3. **Analyser les résultats:**
   - Consulter le rapport Markdown pour un résumé
   - Consulter le JSON pour les détails complets
   - Filtrer les règles selon vos critères de qualité

## Documentation

- **Guide complet:** [POPPER_METRICS_GUIDE.md](POPPER_METRICS_GUIDE.md)
- **README:** [POPPER_METRICS_README.md](POPPER_METRICS_README.md)
- **Comparaison Spider:** [SPIDER_METRICS_GUIDE.md](SPIDER_METRICS_GUIDE.md)

## Conclusion

Le script `compute_popper_metrics.py` fournit une solution complète pour calculer les métriques MATILDA sur les résultats de Popper/ILP, similaire à ce qui a été fait pour Spider avec `compute_spider_metrics.py`. 

**Avantages:**
- ✅ Compatible avec HornRule et TGDRule
- ✅ Réutilise les métriques de Popper (accuracy, confidence)
- ✅ Génère des rapports clairs et structurés
- ✅ Facile à intégrer dans un workflow existant
- ✅ Logs détaillés pour le débogage

**Testé avec succès sur 5 règles Popper avec 100% de réussite!**
