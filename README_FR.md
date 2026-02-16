# MATILDA

MATILDA est un système de découverte de règles logiques depuis des bases de données relationnelles.

## 🚀 Quick Start avec CLI

MATILDA dispose maintenant d'une **interface en ligne de commande unifiée** pour toutes les opérations:

```bash
# Aide générale
python cli.py --help

# Commandes principales
python cli.py validate --auto                    # Valider les métriques
python cli.py benchmark --algorithm spider       # Lancer benchmark
python cli.py metrics --all                      # Calculer métriques
python cli.py test --all                         # Lancer tests
python cli.py clean --cache                      # Nettoyer
python cli.py report --latex                     # Générer rapports
python cli.py info --scripts --results           # Informations projet
```

---

## 📦 Installation

### Installation

#### Télécharger les prérequis de base de données

**macOS:**

```bash
brew install mysql-client@8.4
```

**Linux:**

```bash
sudo apt-get install mysql-client-8.4
```

**Windows:**

```powershell
choco install mysql --version=8.4
```

#### Configurer l'environnement virtuel Python3

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Windows utilisez `venv\Scripts\activate`
pip3 install -r requirements.txt
```

### Lancer l'application

1. Activer l'environnement virtuel :

```bash
source venv/bin/activate  # Sur Windows utilisez `venv\Scripts\activate`
```

2. Démarrer l'application :

```bash
cd src 
python main.py
```

### Optionnel : Exécuter AnyBURL

Pour utiliser l'algorithme AnyBURL, téléchargez le fichier jar AnyBURL depuis la page officielle et :

- placez-le dans `src/algorithms/bins/anyburl/` (n'importe quel nom de fichier `*.jar`), ou
- définissez la variable d'environnement `ANYBURL_JAR` avec le chemin absolu du jar.

Ensuite, définissez `algorithm.name: "ANYBURL"` dans votre configuration et exécutez normalement.

---

## 📊 Benchmarking & Tableaux LaTeX (NOUVEAU!)

**Besoin de benchmarker MATILDA pour une publication ?**

### Solution en Un Clic ⭐

```bash
# Benchmark complet : tous algorithmes × tous datasets × N exécutions + tableau LaTeX
python run_full_benchmark.py --runs 5
```

**Ce qu'il fait :**

- ✅ Exécute MATILDA, SPIDER, ANYBURL, POPPER sur tous les datasets
- ✅ Répète N fois, calcule **moyenne ± écart-type**
- ✅ Génère un tableau LaTeX professionnel automatiquement
- ✅ Sauvegarde les résultats et statistiques en JSON

**Durée :** 1-2 heures (5 exécutions)
**Sortie :** `data/output/benchmark_table_*.tex`

### Trois Scripts Disponibles

| Script                      | Usage                               | Vitesse     | Statistiques |
| --------------------------- | ----------------------------------- | ----------- | ------------ |
| `run_full_benchmark.py`   | Benchmark complet (tous les algos)  | 🐢🐢 1-4h   | ✅ Oui       |
| `run_benchmark.py`        | Benchmark 1 algo avec stats         | 🐢 5-30 min | ✅ Oui       |
| `generate_latex_table.py` | Tableau depuis résultats existants | ⚡ < 1s     | ❌ Non       |

### Exemples

```bash
# Benchmark complet pour article (recommandé)
python run_full_benchmark.py --runs 5

# Benchmark rapide (test)
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER

# Tableau immédiat depuis résultats existants
python generate_latex_table.py --detailed

# Avec fichier de configuration
python run_full_benchmark.py --config benchmark_config.yaml
```
