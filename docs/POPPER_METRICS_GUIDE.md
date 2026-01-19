# Guide Complet: Calcul des Métriques MATILDA pour Popper/ILP

Ce guide explique comment utiliser `compute_popper_metrics.py` pour calculer les métriques MATILDA sur les résultats de Popper/ILP.

## Vue d'ensemble

Le script `compute_popper_metrics.py` permet de:
1. Charger les résultats de Popper/ILP (règles Horn et TGD)
2. Calculer les métriques de **correctness** (validité) des règles
3. Calculer les métriques de **compatibility** des règles
4. Calculer le **support** et la **confidence** pour chaque règle
5. Générer un rapport avec toutes les métriques

## Prérequis

- Python 3.11+
- SQLite base de données
- Résultats Popper/ILP au format JSON

## Installation

Aucune installation supplémentaire nécessaire si vous avez déjà l'environnement MATILDA configuré.

## Utilisation

### 1. Traiter un fichier spécifique

```bash
python compute_popper_metrics.py data/output/popper_Bupa_results.json
```

### 2. Traiter tous les fichiers Popper trouvés

```bash
python compute_popper_metrics.py
```

Le script cherchera automatiquement les fichiers de résultats Popper dans:
- `data/output/*popper*.json`
- `data/output/*ILP*.json`
- `data/results/*/popper/popper_*_results.json`

## Format des Résultats Popper

Les résultats Popper contiennent des règles Horn ou TGD au format:

```json
{
    "rules": [
        {
            "type": "TGDRule",
            "body": [
                {"variable1": "X", "relation": "bupa___sep___arg1", "variable2": "Y"},
                {"variable1": "Y", "relation": "drinks___sep___arg2", "variable2": "Z"}
            ],
            "head": [
                {"variable1": "X", "relation": "sgot___sep___arg1", "variable2": "W"}
            ],
            "display": "sgot(X,W) :- bupa(X,Y), drinks(Y,Z)",
            "accuracy": 0.85,
            "confidence": 0.90
        }
    ]
}
```

### Différences avec Spider

| Aspect | Spider | Popper/ILP |
|--------|--------|------------|
| Type de règle | InclusionDependency | HornRule / TGDRule |
| Structure | Tables et colonnes | Prédicats logiques |
| Format | `table1[col1] ⊆ table2[col2]` | `head :- body1, body2` |
| Métriques | Calculées par le script | Partiellement fournies (accuracy, confidence) |

## Métriques MATILDA Calculées

### 1. Correctness (Validité)

**Définition:** Une règle est valide si ses prédicats peuvent être satisfaits ensemble dans la base de données.

**Calcul:**
- Vérifier que toutes les tables référencées existent
- Vérifier que les tables ont des données
- Valider la structure logique de la règle

**Exemple:**
```
Règle: sgot(X,Y) :- bupa(X,Z), drinks(Z,W)
Validité: ✓ (toutes les tables existent et ont des données)
```

### 2. Compatibility

**Définition:** Les prédicats de la règle sont compatibles entre eux.

**Calcul:**
- Pour les règles Popper, on utilise la même valeur que la validité
- Les prédicats partagent des variables communes
- Les tables peuvent être jointes logiquement

### 3. Support

**Définition:** Proportion de tuples satisfaisant la règle dans la base de données.

**Calcul:**
- Utiliser `accuracy` fournie par Popper si disponible
- Sinon, calculer approximativement basé sur le nombre de tuples

**Valeurs:**
- 0.0 à 1.0 (0% à 100%)
- Plus élevé = règle plus fréquente dans les données

### 4. Confidence

**Définition:** Précision de la règle (probabilité que head soit vrai sachant que body est vrai).

**Calcul:**
- Utiliser `confidence` fournie par Popper si disponible
- Sinon, calculer approximativement

**Valeurs:**
- 0.0 à 1.0 (0% à 100%)
- Plus élevé = règle plus précise

## Sortie du Script

Le script génère deux fichiers:

### 1. Fichier JSON avec métriques

`popper_Bupa_results_with_metrics_2026-01-14_18-45-00.json`

Contient les règles enrichies avec toutes les métriques:

```json
{
    "rules": [
        {
            "type": "TGDRule",
            "body": [...],
            "head": [...],
            "display": "sgot(X,W) :- bupa(X,Y), drinks(Y,Z)",
            "accuracy": 0.85,
            "confidence": 0.90,
            "correct": true,
            "compatible": true
        }
    ]
}
```

### 2. Rapport Markdown

`popper_Bupa_results_with_metrics_2026-01-14_18-45-00.md`

Contient un résumé lisible:

```markdown
# Rapport de Métriques MATILDA pour Popper/ILP

**Base de données:** Bupa.db
**Date:** 2026-01-14 18:45:00

## Résumé

- Nombre total de règles: 15
- Règles valides: 14 (93.3%)
- Support moyen: 0.7823
- Confidence moyenne: 0.8456

## Règles avec Métriques

| # | Type | Règle | Valide | Support | Confidence |
|---|------|-------|--------|---------|------------|
| 1 | TGD  | sgot(X,W) :- bupa(X,Y), drinks(Y,Z) | ✓ | 0.8500 | 0.9000 |
| 2 | Horn | drinks(X,Y) :- bupa(X,Y) | ✓ | 0.7800 | 0.8200 |
...
```

## Exemples d'Utilisation

### Exemple 1: Analyser les résultats d'une exécution Popper

```bash
# 1. Exécuter Popper sur Bupa
python src/main.py -c config_popper_bupa.yaml

# 2. Calculer les métriques MATILDA
python compute_popper_metrics.py data/results/Bupa/popper/popper_Bupa_results.json
```

### Exemple 2: Comparer plusieurs exécutions

```bash
# Traiter tous les fichiers Popper
python compute_popper_metrics.py

# Les résultats seront dans data/output/ avec horodatage
```

### Exemple 3: Analyse programmmatique

```python
from compute_popper_metrics import PopperMetricsCalculator

# Créer le calculateur
calculator = PopperMetricsCalculator("data/db/", "Bupa.db", "data/output")

# Charger les résultats
rules = calculator.load_popper_results("data/output/popper_Bupa_results.json")

# Calculer les métriques
enriched_rules = calculator.calculate_metrics(rules)

# Sauvegarder
calculator.save_results(enriched_rules)
```

## Interprétation des Résultats

### Règles de Haute Qualité

Une règle de haute qualité devrait avoir:
- ✓ **Correctness:** True (valide)
- ✓ **Compatibility:** True (compatible)
- ✓ **Support:** > 0.5 (au moins 50% des tuples)
- ✓ **Confidence:** > 0.7 (au moins 70% de précision)

### Exemple de Bonne Règle

```
Règle: sgot(X,W) :- bupa(X,Y), drinks(Y,Z)
├─ Validité: ✓ (toutes les tables existent)
├─ Compatibilité: ✓ (variables partagées correctement)
├─ Support: 0.85 (85% des tuples satisfont la règle)
└─ Confidence: 0.90 (90% de précision)

Interprétation: Excellente règle, très fréquente et précise
```

### Exemple de Règle à Améliorer

```
Règle: alkphos(X,Y) :- mcv(X,Z)
├─ Validité: ✓
├─ Compatibilité: ✓
├─ Support: 0.25 (seulement 25% des tuples)
└─ Confidence: 0.45 (45% de précision)

Interprétation: Règle trop spécifique ou peu fiable
```

## Types de Règles Popper

### 1. Horn Rules

Règle avec un seul prédicat en tête:

```
head(X) :- body1(X,Y), body2(Y,Z)
```

**Caractéristiques:**
- Un seul prédicat en conséquence (head)
- Peut avoir plusieurs prédicats en condition (body)
- Plus simple à interpréter

### 2. TGD Rules (Tuple-Generating Dependencies)

Règle avec potentiellement plusieurs prédicats en tête:

```
head1(X,W), head2(W,V) :- body1(X,Y), body2(Y,Z)
```

**Caractéristiques:**
- Peut avoir plusieurs prédicats en conséquence
- Génère de nouveaux tuples
- Plus expressif mais plus complexe

## Dépannage

### Erreur: "Aucun fichier de résultats Popper trouvé"

**Solution:**
1. Vérifier que Popper a été exécuté avec succès
2. Vérifier le chemin des résultats
3. Créer un fichier exemple manuellement

### Erreur: "Table non trouvée"

**Solution:**
1. Vérifier que la base de données existe dans `data/db/`
2. Vérifier le nom de la base de données dans le fichier JSON
3. S'assurer que les tables référencées existent

### Métriques à 0.0

**Cause:** Popper n'a pas fourni accuracy/confidence

**Solution:**
- Le script calcule des valeurs approximatives
- Ré-exécuter Popper avec les bons paramètres
- Vérifier les logs pour les erreurs

## Comparaison avec Spider

| Aspect | Spider | Popper/ILP |
|--------|--------|------------|
| Script | `compute_spider_metrics.py` | `compute_popper_metrics.py` |
| Type de règle | Inclusion de tables | Règles logiques |
| Calcul validité | Vérification JOIN | Vérification prédicats |
| Calcul support | COUNT sur tables | Accuracy de Popper |
| Calcul confidence | Ratio tuples | Confidence de Popper |
| Complexité | Moyen | Élevé |

## Fichiers de Configuration

Pour exécuter Popper et générer des résultats:

```yaml
# config_popper_bupa.yaml
database:
  name: Bupa.db
  path: data/db/

algorithm:
  name: POPPER
  max_rules: 20
  timeout: 300

output:
  directory: data/results/
  format: json
```

## Références

- [Popper Documentation](https://github.com/logic-and-learning-lab/Popper)
- [ILP Basics](https://en.wikipedia.org/wiki/Inductive_logic_programming)
- [MATILDA Metrics](README.md)

## Support

Pour toute question ou problème:
1. Vérifier les logs dans `popper_metrics.log`
2. Consulter ce guide
3. Comparer avec `compute_spider_metrics.py` pour Spider
