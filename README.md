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

**📚 Documentation complète**: Voir [CLI_GUIDE.md](CLI_GUIDE.md)

---

## 📦 Installation

### Installation

#### Download database requirements
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

#### Set up Python3 virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip3 install -r requirements.txt
```

### Run the application
1. Activate the virtual environment:
```bash
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
2. Start the application:
```bash
cd src 
python main.py
```

### Optional: Run AnyBURL

To use the AnyBURL algorithm, download the AnyBURL jar from the official page and either:

- place it under `src/algorithms/bins/anyburl/` (any `*.jar` filename), or
- set the environment variable `ANYBURL_JAR` to the absolute path of the jar.

Then set `algorithm.name: "ANYBURL"` in your config and run as usual.

---

## 📊 Benchmarking & LaTeX Tables (NEW!)

**Besoin de benchmarker MATILDA pour une publication ?**

### One-Click Solution ⭐

```bash
# Benchmark complet : tous algorithmes × tous datasets × N runs + table LaTeX
python run_full_benchmark.py --runs 5
```

**Ce qu'il fait :**
- ✅ Exécute MATILDA, SPIDER, ANYBURL, POPPER sur tous datasets
- ✅ Répète N fois, calcule **moyenne ± écart-type**
- ✅ Génère table LaTeX professionnelle automatiquement
- ✅ Sauvegarde résultats et statistiques en JSON

**Durée :** 1-2 heures (5 runs)  
**Output :** `data/output/benchmark_table_*.tex`

### Trois Scripts Disponibles

| Script | Usage | Vitesse | Statistiques |
|--------|-------|---------|--------------|
| `run_full_benchmark.py` | Benchmark complet (tous algos) | 🐢🐢 1-4h | ✅ Oui |
| `run_benchmark.py` | Benchmark 1 algo avec stats | 🐢 5-30 min | ✅ Oui |
| `generate_latex_table.py` | Table depuis résultats existants | ⚡ < 1s | ❌ Non |

### Exemples

```bash
# Benchmark complet pour article (recommandé)
python run_full_benchmark.py --runs 5

# Benchmark rapide (test)
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER

# Table immédiate depuis résultats existants
python generate_latex_table.py --detailed

# Avec fichier de configuration
python run_full_benchmark.py --config benchmark_config.yaml
```

### Documentation Complète

- **[BENCHMARKING_QUICKSTART.md](BENCHMARKING_QUICKSTART.md)** - Guide de démarrage rapide ⭐
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Résumé de l'implémentation
- [WHICH_SCRIPT.md](WHICH_SCRIPT.md) - Arbre de décision : quel script choisir ?
- [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md) - Guide `run_full_benchmark.py`
- [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md) - Guide `run_benchmark.py`
- [LATEX_README.md](LATEX_README.md) - Guide `generate_latex_table.py`
- [benchmark_config.yaml](benchmark_config.yaml) - Exemple de configuration

---

