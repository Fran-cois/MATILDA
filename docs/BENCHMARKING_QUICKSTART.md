# 🚀 MATILDA Benchmarking - Quick Start

## 🎯 Pour les Pressés

**Vous voulez benchmarker MATILDA pour une publication ?**

```bash
# ONE COMMAND = Tout automatique ⭐
python run_full_benchmark.py --runs 5
```

✅ Exécute tous les algorithmes  
✅ Calcule statistiques (moyenne ± std)  
✅ Génère table LaTeX professionnelle  
✅ Sauvegarde résultats JSON  

**Durée estimée :** 1-2 heures  
**Output :** `data/output/benchmark_table_*.tex`

---

## 📊 Trois Scripts, Trois Usages

### 1️⃣ `run_full_benchmark.py` - Benchmark Complet 🎓

**Quand :** Article scientifique, comparaison complète

```bash
# Benchmark TOUT : tous algorithmes × tous datasets × N runs
python run_full_benchmark.py --runs 5

# Ciblé : 2 algorithmes spécifiques
python run_full_benchmark.py --runs 5 --algorithms MATILDA SPIDER

# Avec config
python run_full_benchmark.py --config benchmark_config.yaml
```

**Output :**
- ✅ Résultats JSON avec toutes les exécutions
- ✅ Statistiques JSON (mean, std, n_runs)
- ✅ Table LaTeX avec format `$9 \pm 0.0$`
- ✅ Résumé console

**Temps :** 1-4h selon nombre de runs  
**Doc :** [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md)

---

### 2️⃣ `run_benchmark.py` - Benchmark Ciblé 📈

**Quand :** Test d'un algorithme spécifique avec stats

```bash
# Benchmarker MATILDA seulement (5 runs)
python run_benchmark.py --runs 5 --algorithms MATILDA

# Sur datasets spécifiques
python run_benchmark.py --runs 5 --datasets Bupa BupaImperfect
```

**Output :**
- ✅ Résultats JSON d'un algorithme
- ✅ Statistiques pour cet algorithme
- ✅ Table LaTeX partielle

**Temps :** 5-30 min selon algorithme  
**Doc :** [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md)

---

### 3️⃣ `generate_latex_table.py` - Table Rapide ⚡

**Quand :** Résultats déjà calculés, besoin d'une table vite

```bash
# Table détaillée depuis résultats existants (< 1 seconde)
python generate_latex_table.py --detailed

# Table simple (6 colonnes)
python generate_latex_table.py

# Algorithmes spécifiques
python generate_latex_table.py --algorithms MATILDA SPIDER
```

**Output :**
- ✅ Table LaTeX depuis fichiers `*_results.json` existants
- ❌ Pas de statistiques (valeurs uniques)

**Temps :** < 1 seconde  
**Doc :** [LATEX_README.md](LATEX_README.md)

---

## 🤔 Quel Script Choisir ?

| Besoin | Script | Commande |
|--------|--------|----------|
| 📄 **Article complet** | `run_full_benchmark.py` | `python run_full_benchmark.py --runs 5` |
| 🧪 **Tester 1 algo** | `run_benchmark.py` | `python run_benchmark.py --runs 5 --algorithms MATILDA` |
| ⚡ **Table immédiate** | `generate_latex_table.py` | `python generate_latex_table.py --detailed` |

**Guide détaillé :** [WHICH_SCRIPT.md](WHICH_SCRIPT.md)

---

## 📁 Fichiers de Configuration

### `benchmark_config.yaml`

```yaml
# Nombre de runs par combinaison algo/dataset
runs: 5

# Algorithmes à benchmarker
algorithms:
  - MATILDA
  - SPIDER
  - ANYBURL
  - POPPER

# Datasets
datasets:
  - Bupa
  - BupaImperfect
  - ComparisonDataset
  - ImperfectTest

# Options
table_type: detailed  # ou 'simple'
timeout: 3600         # 1 heure par run
```

**Usage :**
```bash
python run_full_benchmark.py --config benchmark_config.yaml
```

---

## 📊 Formats de Sortie

### Table Simple (6 colonnes)

```latex
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & 
\textbf{Accuracy} & \textbf{Confidence} & \textbf{Time (s)}
```

### Table Détaillée (8 colonnes)

```latex
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & 
\textbf{Acc.} & \textbf{Conf.} & \textbf{T_compat} & 
\textbf{T_index} & \textbf{T_CG}
```

### Format Statistiques

Avec N runs :
```latex
MATILDA & Bupa & $9 \pm 0.0$ & $1.000 \pm 0.000$ & ...
```

---

## 🧪 Tester

```bash
# Vérifier que tout fonctionne
python test_latex_generation.py

# Test rapide (1 run, 1 algo)
python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa
```

---

## ⏱️ Temps d'Exécution

| Configuration | Temps Estimé |
|---------------|--------------|
| `generate_latex_table.py` | < 1 seconde |
| `run_benchmark.py --runs 5` (1 algo) | 5-15 minutes |
| `run_full_benchmark.py --runs 3` | 30-60 minutes |
| `run_full_benchmark.py --runs 5` | 1-2 heures |
| `run_full_benchmark.py --runs 10` | 3-4 heures |

---

## 📚 Documentation Complète

| Document | Contenu |
|----------|---------|
| [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md) | Guide `run_full_benchmark.py` |
| [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md) | Guide `run_benchmark.py` |
| [LATEX_README.md](LATEX_README.md) | Guide `generate_latex_table.py` |
| [WHICH_SCRIPT.md](WHICH_SCRIPT.md) | Arbre de décision |
| [LATEX_SUMMARY.md](LATEX_SUMMARY.md) | Référence ultra-concise |
| [benchmark_config.yaml](benchmark_config.yaml) | Config exemple |

---

## 🎯 Workflow Recommandé

### Pour Article Scientifique

```bash
# 1. Test rapide (vérifier)
python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa

# 2. Benchmark complet (1-2h)
python run_full_benchmark.py --runs 5

# 3. Copier table dans article
cp data/output/benchmark_table_*.tex paper/tables/

# 4. Compiler LaTeX
pdflatex paper/main.tex
```

### Pour Présentation

```bash
# Table rapide depuis résultats existants
python generate_latex_table.py --detailed

# Ou benchmark rapide si nouveaux résultats
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER
```

---

## 💡 Tips

### Réduire le Temps d'Exécution

```bash
# Moins de runs
python run_full_benchmark.py --runs 3

# Moins d'algorithmes
python run_full_benchmark.py --runs 5 --algorithms MATILDA SPIDER

# Moins de datasets
python run_full_benchmark.py --runs 5 --datasets Bupa BupaImperfect
```

### Gérer les Timeouts

```bash
# Augmenter timeout (2 heures)
python run_full_benchmark.py --runs 5 --timeout 7200
```

### Exécuter en Arrière-Plan

```bash
# Lancer et continuer à travailler
nohup python run_full_benchmark.py --runs 5 > benchmark.log 2>&1 &

# Suivre progression
tail -f benchmark.log
```

---

## 🆘 Aide

```bash
# Aide générale
python run_full_benchmark.py --help
python run_benchmark.py --help
python generate_latex_table.py --help

# Tests
python test_latex_generation.py
```

---

## ✅ Checklist Article

- [ ] Exécuter `python run_full_benchmark.py --runs 5`
- [ ] Vérifier `data/output/benchmark_table_*.tex`
- [ ] Vérifier statistiques : écart-type < 10% de moyenne
- [ ] Copier table dans `paper/tables/`
- [ ] Compiler LaTeX et vérifier rendu
- [ ] Documenter méthodologie (5 runs, timeout 1h, etc.)
- [ ] Sauvegarder `full_benchmark_results_*.json` et `*_statistics_*.json`

---

## 🎉 C'est Tout !

**Pour la plupart des cas :**
```bash
python run_full_benchmark.py --runs 5
```

**Besoin d'aide ?** Consultez [WHICH_SCRIPT.md](WHICH_SCRIPT.md) ou [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md)
