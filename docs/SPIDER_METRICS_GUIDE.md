# Guide: Exécuter Spider et Calculer les Métriques MATILDA

Ce guide explique comment exécuter Spider sur Bupa et calculer les métriques MATILDA sur les résultats.

## Option 1: Utiliser main.py avec une configuration

La méthode la plus simple est d'utiliser le script principal avec une configuration pour Spider.

### Étape 1: Créer/modifier le fichier de configuration

Éditez `src/config.yaml` ou créez `config_spider_bupa.yaml`:

```yaml
algorithm:
  name: SPIDER

database:
  name: Bupa.db
  path: data/db/

logging:
  log_dir: logs

results:
  output_dir: data/output
  compute_statistics: true

monitor:
  memory_threshold: 16106127360
  timeout: 3600
```

### Étape 2: Exécuter Spider

```bash
python src/main.py -c config_spider_bupa.yaml
```

Cela va:
- Exécuter Spider sur Bupa.db
- Sauvegarder les règles dans `data/output/SPIDER_Bupa_results.json`
- Générer un rapport

### Étape 3: Calculer les métriques MATILDA

Utilisez le script dédié pour enrichir les résultats:

```bash
python compute_spider_metrics.py data/output/SPIDER_Bupa_results.json
```

Ou pour traiter automatiquement tous les fichiers Spider trouvés:

```bash
python compute_spider_metrics.py
```

## Option 2: Sans Docker (nécessite Java 11)

Si Docker n'est pas disponible mais que vous avez Java 11 installé:

### Installer Java 11 (macOS)

```bash
brew install openjdk@11
```

Puis définir JAVA_HOME:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)
```

### Exécuter Spider manuellement

```bash
cd data/db/Bupa/csv
java -cp ../../../../src/algorithms/bins/metanome/metanome-cli-1.2-SNAPSHOT.jar:../../../../src/algorithms/bins/metanome/SPIDER-1.2-SNAPSHOT.jar \
  de.metanome.cli.App \
  --algorithm de.metanome.algorithms.spider.SPIDERFile \
  --files *.csv \
  --table-key INPUT_FILES \
  --separator "," \
  --output file:spider_bupa_results \
  --header
```

Les résultats seront dans `spider_bupa_results_inds`.

### Convertir et calculer les métriques

1. Déplacez le fichier de résultats:
```bash
mv spider_bupa_results_inds ../../../../results/
```

2. Convertissez-le au format JSON (si nécessaire) et calculez les métriques avec le script Python.

## Option 3: Utiliser des résultats existants

Si vous avez déjà des résultats Spider, utilisez directement:

```bash
python compute_spider_metrics.py <chemin_vers_spider_results.json>
```

## Résultats

Après l'exécution, vous trouverez:

- **Fichier JSON avec métriques**: `data/output/spider_Bupa_metrics_<timestamp>.json`
  - Contient toutes les règles avec:
    - `correct`: Validité de la règle
    - `compatible`: Compatibilité des attributs
    - `support`: Support de la règle
    - `confidence`: Confidence de la règle

- **Rapport Markdown**: `data/output/spider_Bupa_metrics_<timestamp>.md`
  - Résumé statistique
  - Tableau des règles avec métriques
  - Définitions des métriques

## Métriques MATILDA Calculées

### Correctness (Validité)
La règle est valide si elle respecte les contraintes sémantiques de la base de données.

### Compatibility
Les attributs sont compatibles si leur chevauchement dépasse un seuil (par défaut 0.5).

### Support
Proportion de tuples satisfaisant la règle: `|A ∩ B| / |Total tuples|`

### Confidence
Proportion de tuples de la table dépendante satisfaisant la règle: `|A ∩ B| / |A|`

## Dépannage

### Docker n'est pas disponible
- Utilisez Option 1 avec Java 11
- Ou utilisez Option 3 avec des résultats existants

### Java version incorrecte
```bash
# Vérifier la version
java -version

# Installer Java 11
brew install openjdk@11

# Changer temporairement la version
export JAVA_HOME=$(/usr/libexec/java_home -v 11)
```

### Pas de fichiers de résultats trouvés
```bash
# Vérifier les répertoires
ls -la data/output/
ls -la data/results/*/spider/

# Exécuter Spider d'abord
python src/main.py -c config_spider_bupa.yaml
```

## Exemple de Sortie

```
2026-01-14 18:30:00 - INFO - Calcul des métriques MATILDA sur 15 règles Spider...
2026-01-14 18:30:01 - INFO - Règle: bupa[selector] ⊆ sgot[selector] | Valid: True | Support: 0.4523 | Confidence: 0.9876
...
2026-01-14 18:30:05 - INFO - Résultats sauvegardés dans data/output/spider_Bupa_metrics_2026-01-14_18-30-05.json
```

## Pour aller plus loin

- Modifier le seuil de compatibilité dans `compute_spider_metrics.py` (variable `threshold`)
- Comparer les métriques Spider avec MATILDA
- Utiliser les scripts d'analyse existants dans `scripts/` pour des comparaisons détaillées
