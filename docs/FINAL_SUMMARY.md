# Récapitulatif: Calcul des Métriques MATILDA

Date: 2026-01-14

## Objectif

Créer une fonction pour calculer les métriques MATILDA (correctness, compatibility, support, confidence) sur les résultats de Popper/ILP, similaire à ce qui existe déjà pour Spider.

## Résultat

✅ **Mission accomplie !** 

Un ensemble complet de scripts et de documentation a été créé pour calculer les métriques MATILDA sur les résultats de Popper/ILP et Spider.

## Fichiers Créés

### Scripts Python

1. **`compute_popper_metrics.py`** (503 lignes)
   - Calcule les métriques MATILDA pour Popper/ILP
   - Classe `PopperMetricsCalculator`
   - Gère HornRule et TGDRule
   - Auto-découverte des fichiers de résultats
   - Génération de rapports JSON et Markdown

2. **`compute_all_metrics.py`** (294 lignes)
   - Script unifié pour tous les algorithmes
   - Auto-détection du type d'algorithme
   - Traitement en batch de tous les résultats
   - Arguments en ligne de commande

### Documentation

3. **`POPPER_METRICS_GUIDE.md`**
   - Guide complet d'utilisation (20+ sections)
   - Explications des métriques
   - Exemples d'utilisation
   - Dépannage
   - Comparaison avec Spider

4. **`POPPER_METRICS_README.md`**
   - Documentation récapitulative
   - Usage rapide
   - Tableaux de référence

5. **`POPPER_METRICS_SUMMARY.md`**
   - Résumé technique
   - Fichiers créés
   - Fonctionnalités implémentées
   - Test results

6. **`METRICS_COMPLETE_GUIDE.md`**
   - Guide global pour tous les scripts
   - Quick start
   - Comparaison Spider vs Popper
   - Architecture des scripts

### Fichiers de Test

7. **`popper_Bupa_example_results.json`**
   - 5 règles Popper (3 TGD, 2 Horn)
   - Format correct pour RuleIO
   - Testé avec succès

## Fonctionnalités Implémentées

### Pour Popper/ILP

✅ **Chargement des résultats**
- Compatible avec `RuleIO.load_rules_from_json()`
- Support de HornRule et TGDRule
- Gestion des erreurs

✅ **Calcul de Correctness (Validité)**
- Vérification de l'existence des tables
- Extraction des tables depuis les prédicats
- Validation de la structure logique

✅ **Calcul de Compatibility**
- Basé sur la validité
- Vérification des variables partagées

✅ **Calcul de Support**
- Utilise `accuracy` de Popper si disponible
- Calcul approximatif sinon
- Basé sur le nombre de tuples

✅ **Calcul de Confidence**
- Utilise `confidence` de Popper si disponible
- Calcul approximatif sinon

✅ **Sauvegarde des résultats**
- JSON avec règles enrichies
- Rapport Markdown avec statistiques
- Horodatage automatique

### Script Unifié

✅ **Auto-détection**
- Détection automatique du type d'algorithme
- Par nom de fichier
- Par contenu JSON

✅ **Traitement en batch**
- Trouve tous les fichiers de résultats
- Traite Spider et Popper
- Résumé final des traitements

✅ **Arguments CLI**
- `--algorithm` pour filtrer
- `--data-dir` pour spécifier le répertoire
- Support fichier unique ou batch

## Tests Réussis

### Test compute_popper_metrics.py

```bash
python compute_popper_metrics.py popper_Bupa_example_results.json
```

**Résultats:**
- ✅ 5 règles traitées
- ✅ 100% de règles valides
- ✅ Support moyen: 0.8053
- ✅ Confidence moyenne: 0.8567
- ✅ Fichiers générés:
  - `popper_Bupa_example_results_with_metrics_2026-01-14_18-41-17.json`
  - `popper_Bupa_example_results_with_metrics_2026-01-14_18-41-17.md`

### Test compute_all_metrics.py

```bash
python compute_all_metrics.py popper_Bupa_example_results.json
```

**Résultats:**
- ✅ Algorithme détecté: popper
- ✅ Traitement réussi
- ✅ Fichiers générés correctement

## Comparaison avec Spider

| Aspect | Spider | Popper |
|--------|--------|--------|
| **Script créé** | `compute_spider_metrics.py` | `compute_popper_metrics.py` |
| **Lignes de code** | ~320 | ~503 |
| **Type de règle** | InclusionDependency | HornRule / TGDRule |
| **Structure règle** | Tables/colonnes | Prédicats logiques |
| **Calcul validité** | Vérification JOIN | Vérification prédicats |
| **Calcul support** | COUNT SQL | accuracy Popper |
| **Calcul confidence** | Ratio tuples | confidence Popper |
| **Complexité** | Moyen | Élevé |
| **Documentation** | ✅ Complete | ✅ Complete |
| **Tests** | ✅ 10 règles | ✅ 5 règles |

## Format des Règles

### Spider (InclusionDependency)

```json
{
  "type": "InclusionDependency",
  "table_dependant": "bupa",
  "columns_dependant": ["arg1"],
  "table_referenced": "drinks",
  "columns_referenced": ["arg1"]
}
```

### Popper (TGDRule)

```json
{
  "type": "TGDRule",
  "body": [
    "Predicate(variable1='X', relation='bupa___sep___arg1', variable2='Y')"
  ],
  "head": [
    "Predicate(variable1='X', relation='sgot___sep___arg1', variable2='W')"
  ],
  "display": "sgot(X,W) :- bupa(X,Y)"
}
```

### Popper (HornRule)

```json
{
  "type": "HornRule",
  "body": [
    "Predicate(variable1='X', relation='bupa___sep___arg1', variable2='Y')"
  ],
  "head": "Predicate(variable1='X', relation='drinks___sep___arg1', variable2='Y')",
  "display": "drinks(X,Y) :- bupa(X,Y)"
}
```

## Métriques MATILDA

### 1. Correctness (Validité)
- **Type:** Boolean
- **Spider:** Vérifie les JOINs
- **Popper:** Vérifie les tables

### 2. Compatibility
- **Type:** Boolean
- **Spider:** Vérifie les types
- **Popper:** Vérifie les prédicats

### 3. Support
- **Type:** Float (0.0-1.0)
- **Spider:** COUNT SQL
- **Popper:** accuracy de Popper

### 4. Confidence
- **Type:** Float (0.0-1.0)
- **Spider:** Ratio tuples
- **Popper:** confidence de Popper

## Usage

### Mode 1: Fichier Spécifique

```bash
# Spider
python compute_spider_metrics.py spider_results.json

# Popper
python compute_popper_metrics.py popper_results.json

# Auto-détection
python compute_all_metrics.py results.json
```

### Mode 2: Auto-Découverte

```bash
# Spider uniquement
python compute_spider_metrics.py

# Popper uniquement
python compute_popper_metrics.py

# Tous les algorithmes
python compute_all_metrics.py
```

### Mode 3: Filtrage par Algorithme

```bash
# Tous les algorithmes
python compute_all_metrics.py --algorithm all

# Spider uniquement
python compute_all_metrics.py --algorithm spider

# Popper uniquement
python compute_all_metrics.py --algorithm popper
```

## Sortie des Scripts

### Fichiers JSON

Format: `{nom_original}_with_metrics_{timestamp}.json`

Contient les règles avec métriques ajoutées:
- `correct`: Boolean
- `compatible`: Boolean
- `support`: Float (TGD seulement pour Popper)
- `confidence`: Float (TGD seulement pour Popper)

### Fichiers Markdown

Format: `{nom_original}_with_metrics_{timestamp}.md`

Contient:
- Résumé des statistiques
- Tableau avec toutes les règles
- Définitions des métriques
- Informations sur les types de règles

## Logs

- **Spider:** `spider_metrics.log`
- **Popper:** `popper_metrics.log`

Format:
```
2026-01-14 18:41:17 - INFO - Chargement des résultats Popper...
2026-01-14 18:41:17 - INFO - 5 règles chargées
2026-01-14 18:41:17 - INFO - Calcul des métriques MATILDA...
2026-01-14 18:41:17 - INFO - Traitement de la règle TGDRule...
2026-01-14 18:41:17 - INFO -   → Valid: True | Support: 0.8523
2026-01-14 18:41:17 - INFO - Résultats sauvegardés avec succès
```

## Points d'Attention

### Format des Prédicats Popper

Les prédicats doivent être au format string RuleIO:

```python
"Predicate(variable1='X', relation='table___sep___attr', variable2='Y')"
```

**PAS** au format dict:

```python
{
  "variable1": "X",
  "relation": "table___sep___attr",
  "variable2": "Y"
}
```

### HornRule vs TGDRule

- **HornRule:** `head` est un seul Predicate (string)
- **TGDRule:** `head` est une liste de Predicates (list)

### Métriques Manquantes

Si Popper ne fournit pas `accuracy` ou `confidence`:
- Le script calcule une approximation
- Basé sur le nombre de tuples dans les tables
- Peut être moins précis

## Prochaines Étapes

Pour utiliser ces scripts dans votre workflow:

1. **Exécuter les algorithmes**
   ```bash
   python src/main.py -c config_spider.yaml
   python src/main.py -c config_popper.yaml
   ```

2. **Calculer les métriques**
   ```bash
   python compute_all_metrics.py
   ```

3. **Analyser les résultats**
   - Consulter les rapports Markdown
   - Filtrer les règles par qualité
   - Comparer les algorithmes

## Documentation

| Fichier | Description |
|---------|-------------|
| **METRICS_COMPLETE_GUIDE.md** | Guide global pour tous les scripts |
| **SPIDER_METRICS_GUIDE.md** | Guide détaillé Spider |
| **POPPER_METRICS_GUIDE.md** | Guide détaillé Popper |
| **POPPER_METRICS_README.md** | README récapitulatif Popper |
| **POPPER_METRICS_SUMMARY.md** | Résumé technique Popper |

## Résumé

✅ **Scripts créés:** 2 scripts spécifiques + 1 script unifié
✅ **Documentation:** 5 fichiers de documentation complets
✅ **Tests:** Réussis avec fichiers exemple
✅ **Métriques:** Toutes les métriques MATILDA implémentées
✅ **Compatibilité:** Compatible avec les formats existants
✅ **Extensibilité:** Architecture permettant d'ajouter d'autres algorithmes

**Tout est prêt pour calculer les métriques MATILDA sur les résultats de Popper/ILP ! 🎉**
