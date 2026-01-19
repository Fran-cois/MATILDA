# 🚀 Full Benchmark Automation

## Vue d'ensemble

`run_full_benchmark.py` automatise **tout le processus** :
1. ✅ Exécute tous les algorithmes sur tous les datasets
2. ✅ Répète N fois chaque combinaison
3. ✅ Calcule automatiquement **moyenne ± écart-type**
4. ✅ Génère le tableau LaTeX avec statistiques
5. ✅ Sauvegarde résultats et statistiques en JSON

**C'est la solution one-click pour benchmarker MATILDA !**

---

## 🎯 Quick Start

### 1️⃣ Option Simple : Arguments CLI

```bash
# Benchmark complet : 5 runs × tous algorithmes × tous datasets
python run_full_benchmark.py --runs 5

# Seulement MATILDA et SPIDER
python run_full_benchmark.py --runs 5 --algorithms MATILDA SPIDER

# Datasets spécifiques
python run_full_benchmark.py --runs 5 --datasets Bupa BupaImperfect

# Table simple au lieu de détaillée
python run_full_benchmark.py --runs 3 --table-type simple
```

### 2️⃣ Option Avancée : Fichier de Configuration

```bash
# Utiliser benchmark_config.yaml
python run_full_benchmark.py --config benchmark_config.yaml

# Modifier benchmark_config.yaml selon vos besoins
nano benchmark_config.yaml
```

---

## 📋 Exemples d'Usage

### Benchmark Rapide (Test)

```bash
# 3 runs, 2 algorithmes, 1 dataset = ~10 minutes
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER --datasets Bupa
```

**Quand utiliser :** Test rapide, vérification avant publication

### Benchmark Standard (Article)

```bash
# 5 runs, tous algorithmes, tous datasets = ~1-2 heures
python run_full_benchmark.py --runs 5
```

**Quand utiliser :** Article scientifique standard, statistiques robustes

### Benchmark Publication (Haute Qualité)

```bash
# 10 runs, tous algorithmes = ~3-4 heures
python run_full_benchmark.py --runs 10
```

**Quand utiliser :** Publication prestigieuse, reviewers exigeants

### Benchmark Ciblé

```bash
# Comparer seulement MATILDA vs SPIDER sur datasets imperfects
python run_full_benchmark.py --runs 5 \
  --algorithms MATILDA SPIDER \
  --datasets BupaImperfect ImperfectTest
```

**Quand utiliser :** Comparaison spécifique, analyse ciblée

---

## 🔧 Configuration YAML

### Fichier `benchmark_config.yaml`

```yaml
# Nombre de runs
runs: 5

# Algorithmes (commentez pour exclure)
algorithms:
  - MATILDA
  - SPIDER
  - ANYBURL
  - POPPER

# Datasets (commentez pour exclure)
datasets:
  - Bupa
  - BupaImperfect
  - ComparisonDataset
  - ImperfectTest

# Options
output_dir: data/output
timeout: 3600
table_type: detailed  # ou 'simple'
verbose: true
```

### Utilisation

```bash
# Charger depuis config
python run_full_benchmark.py --config benchmark_config.yaml

# Overrider certains paramètres
python run_full_benchmark.py --config benchmark_config.yaml --runs 10
```

---

## 📊 Sorties Générées

### 1. Fichier JSON des Résultats Bruts

**Fichier:** `data/output/full_benchmark_results_20260112_143020.json`

```json
{
  "MATILDA": {
    "Bupa": [
      { "rules": [...], "accuracy": 1.0, "time_total": 0.123 },
      { "rules": [...], "accuracy": 1.0, "time_total": 0.125 },
      ...
    ]
  }
}
```

### 2. Fichier JSON des Statistiques

**Fichier:** `data/output/full_benchmark_statistics_20260112_143020.json`

```json
{
  "MATILDA": {
    "Bupa": {
      "num_rules": { "mean": 9.0, "std": 0.0 },
      "accuracy": { "mean": 1.0, "std": 0.0 },
      "time_total": { "mean": 0.124, "std": 0.002 },
      "n_runs": 5
    }
  }
}
```

### 3. Table LaTeX avec Statistiques

**Fichier:** `data/output/benchmark_table_20260112_143020.tex`

```latex
\begin{table}[htbp]
\centering
\caption{Detailed Rule Discovery Performance with Statistics (5 runs)}
\resizebox{\textwidth}{!}{
\begin{tabular}{llrrrrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Acc.} & ...
\midrule
MATILDA & Bupa & $9 \pm 0.0$ & $1.000 \pm 0.000$ & ...
\bottomrule
\end{tabular}
}
\end{table}
```

### 4. Résumé Console

```
BENCHMARK SUMMARY
============================================================

MATILDA:
  Bupa                :   9.0 ±  0.0 rules (0.124 ± 0.002s)
  BupaImperfect       :   9.0 ±  0.0 rules (0.115 ± 0.003s)
  ...

SPIDER:
  BupaImperfect       :  50.0 ±  0.0 rules (0.089 ± 0.001s)
  ...
```

---

## ⏱️ Temps d'Exécution Estimé

| Configuration | Runs | Algos | Datasets | Temps Total |
|---------------|------|-------|----------|-------------|
| Test rapide | 1 | 1 | 1 | ~2 min |
| Quick | 3 | 2 | 1 | ~10 min |
| Standard | 5 | 4 | 4 | ~1-2 heures |
| Publication | 10 | 4 | 4 | ~3-4 heures |

**Formule:** `Temps ≈ runs × algos × datasets × 1-3 minutes`

---

## 🎛️ Options Complètes

```bash
python run_full_benchmark.py [OPTIONS]

Options:
  --runs N              Nombre de runs (défaut: 5)
  --algorithms A1 A2    Algorithmes (MATILDA, SPIDER, ANYBURL, POPPER)
  --datasets D1 D2      Datasets à benchmarker
  --output-dir DIR      Répertoire de sortie (défaut: data/output)
  --timeout SECS        Timeout par run (défaut: 3600)
  --table-type TYPE     Type de table: simple ou detailed (défaut: detailed)
  --config FILE         Fichier de configuration YAML
  --quiet               Mode silencieux
  -h, --help            Afficher l'aide
```

---

## 💡 Workflow Recommandé

### Pour Article Scientifique

```bash
# 1. Test rapide (vérifier que tout marche)
python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa

# 2. Benchmark standard (résultats article)
python run_full_benchmark.py --runs 5

# 3. Copier la table LaTeX dans votre article
cp data/output/benchmark_table_*.tex paper/tables/
```

### Pour Présentation

```bash
# Benchmark rapide avec table simple
python run_full_benchmark.py --runs 3 --table-type simple \
  --algorithms MATILDA SPIDER
```

### Pour Expérimentation

```bash
# Tester nouvelle feature sur dataset spécifique
python run_full_benchmark.py --runs 5 \
  --algorithms MATILDA \
  --datasets ImperfectTest
```

---

## 🔍 Résolution de Problèmes

### Problème : Timeout sur certains algorithmes

**Solution :** Augmenter le timeout

```bash
python run_full_benchmark.py --runs 5 --timeout 7200  # 2 heures
```

### Problème : Trop long

**Solution :** Réduire runs ou exclure algorithmes lents

```bash
# Exclure POPPER qui est lent
python run_full_benchmark.py --runs 5 --algorithms MATILDA SPIDER ANYBURL
```

### Problème : Certains runs échouent

**Solution :** Le script continue même si certains runs échouent. Les statistiques sont calculées sur les runs réussis.

### Problème : Mémoire insuffisante

**Solution :** Exécuter par dataset

```bash
# Benchmark dataset par dataset
for dataset in Bupa BupaImperfect ComparisonDataset; do
  python run_full_benchmark.py --runs 5 --datasets $dataset
done
```

---

## 📈 Analyse des Résultats

### 1. Comparer Statistiques

```python
import json

with open("data/output/full_benchmark_statistics_*.json") as f:
    stats = json.load(f)

# Meilleure précision
for algo in stats:
    for dataset in stats[algo]:
        acc = stats[algo][dataset]["accuracy"]
        print(f"{algo} on {dataset}: {acc['mean']:.3f} ± {acc['std']:.3f}")
```

### 2. Analyser Stabilité

```python
# Algorithmes avec faible écart-type = plus stables
for algo in stats:
    for dataset in stats[algo]:
        rules_std = stats[algo][dataset]["num_rules"]["std"]
        if rules_std > 1.0:
            print(f"⚠️  {algo} on {dataset} est instable (std={rules_std:.2f})")
```

### 3. Comparer Temps

```python
# Plus rapide
for algo in stats:
    total_time = sum(
        stats[algo][d]["time_total"]["mean"] 
        for d in stats[algo]
    )
    print(f"{algo}: {total_time:.3f}s total")
```

---

## 🎯 Cas d'Usage Typiques

### 1. "Je veux benchmarker MATILDA pour mon article"

```bash
python run_full_benchmark.py --runs 5
```

→ Exécute tout, génère table LaTeX prête pour publication

### 2. "Je veux comparer MATILDA vs SPIDER rapidement"

```bash
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER
```

→ Comparaison rapide (~15 minutes)

### 3. "Je teste une nouvelle feature de MATILDA"

```bash
python run_full_benchmark.py --runs 5 --algorithms MATILDA
```

→ Focus sur MATILDA uniquement

### 4. "Je veux des statistiques ultra-robustes"

```bash
python run_full_benchmark.py --runs 10
```

→ 10 runs = statistiques très fiables

---

## 🆚 Comparaison des Scripts

| Script | Usage | Vitesse | Statistiques |
|--------|-------|---------|--------------|
| `generate_latex_table.py` | Table depuis résultats existants | ⚡⚡⚡ < 1s | ✗ |
| `run_benchmark.py` | Benchmark 1 algo, N runs | 🐢 5-30 min | ✅ |
| `run_full_benchmark.py` | **Benchmark TOUT, N runs** | 🐢🐢 1-4h | ✅ |

**Recommandation :**
- Résultats rapides → `generate_latex_table.py`
- Test 1 algo → `run_benchmark.py`
- **Article complet** → `run_full_benchmark.py` ⭐

---

## ✅ Checklist Publication

- [ ] **Exécuter benchmark complet**
  ```bash
  python run_full_benchmark.py --runs 5
  ```

- [ ] **Vérifier les statistiques**
  - Écart-type raisonnable (< 10% de la moyenne) ?
  - Nombre de runs suffisant (N ≥ 5) ?

- [ ] **Générer table LaTeX**
  - Table générée automatiquement ✓
  - Format professionnel (booktabs) ✓

- [ ] **Intégrer dans article**
  ```bash
  cp data/output/benchmark_table_*.tex paper/tables/results.tex
  ```

- [ ] **Documenter méthodologie**
  - Nombre de runs : 5
  - Algorithmes testés : MATILDA, SPIDER, ANYBURL, POPPER
  - Datasets : Bupa, BupaImperfect, ComparisonDataset, ImperfectTest
  - Machine : [spécifier]
  - Timeout : 1h par run

---

## 🎓 Pour en savoir plus

- `WHICH_SCRIPT.md` - Guide pour choisir le bon script
- `LATEX_TABLES_GUIDE.md` - Guide complet LaTeX
- `benchmark_config.yaml` - Configuration exemple
- `README.md` - Documentation générale

---

**🎉 Avec `run_full_benchmark.py`, benchmarker tous les algorithmes et générer le tableau LaTeX est aussi simple qu'une seule commande !**
