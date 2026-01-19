# ✅ MATILDA Benchmark Automation - COMPLET

## 🎉 Résumé

Vous avez maintenant **3 scripts** pour générer des tableaux LaTeX avec vos résultats MATILDA :

### 1. `run_full_benchmark.py` ⭐ NOUVEAU !

**Le script ONE-CLICK pour tout automatiser**

```bash
python run_full_benchmark.py --runs 5
```

**Ce qu'il fait :**
- ✅ Exécute **TOUS** les algorithmes (MATILDA, SPIDER, ANYBURL, POPPER)
- ✅ Sur **TOUS** les datasets (Bupa, BupaImperfect, ComparisonDataset, ImperfectTest)
- ✅ **N fois** chaque combinaison
- ✅ Calcule **moyenne ± écart-type** automatiquement
- ✅ Génère **table LaTeX professionnelle** avec stats
- ✅ Sauvegarde tout en JSON

**Temps :** 1-4h selon N runs  
**Usage :** Article scientifique complet

---

### 2. `run_benchmark.py`

**Pour tester un algorithme spécifique avec stats**

```bash
python run_benchmark.py --runs 5 --algorithms MATILDA
```

**Ce qu'il fait :**
- ✅ Exécute **UN** algorithme N fois
- ✅ Calcule statistiques
- ✅ Génère table LaTeX

**Temps :** 5-30 min  
**Usage :** Test d'un algorithme

---

### 3. `generate_latex_table.py`

**Pour générer une table depuis résultats existants**

```bash
python generate_latex_table.py --detailed
```

**Ce qu'il fait :**
- ✅ Table LaTeX depuis fichiers JSON existants
- ❌ Pas de re-exécution
- ❌ Pas de statistiques

**Temps :** < 1 seconde  
**Usage :** Table rapide

---

## 📋 Fichiers Créés

### Scripts Python
- ✅ `run_full_benchmark.py` (nouveau, ~400 lignes)
- ✅ `run_benchmark.py` (~300 lignes)
- ✅ `generate_latex_table.py` (~350 lignes)
- ✅ `test_latex_generation.py` (~150 lignes)

### Configuration
- ✅ `benchmark_config.yaml` - Config pour benchmark complet

### Documentation
- ✅ `BENCHMARKING_QUICKSTART.md` - Guide rapide ⭐
- ✅ `FULL_BENCHMARK_GUIDE.md` - Guide `run_full_benchmark.py`
- ✅ `LATEX_TABLES_GUIDE.md` - Guide `run_benchmark.py`
- ✅ `LATEX_README.md` - Guide `generate_latex_table.py`
- ✅ `WHICH_SCRIPT.md` - Arbre de décision (mis à jour)
- ✅ `LATEX_SUMMARY.md` - Référence ultra-concise

### Exemples
- ✅ `data/output/example_document.tex`
- ✅ `data/output/example_stats_table.tex`

---

## 🚀 Pour Commencer

### Cas 1 : Article Scientifique (Recommandé)

```bash
# Une seule commande !
python run_full_benchmark.py --runs 5

# Copier la table dans votre article
cp data/output/benchmark_table_*.tex paper/tables/
```

Durée : 1-2 heures  
Résultat : Table professionnelle avec statistiques

---

### Cas 2 : Test Rapide

```bash
# Vérifier que tout marche (< 5 min)
python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa
```

---

### Cas 3 : Présentation Urgente

```bash
# Table immédiate depuis résultats existants (< 1s)
python generate_latex_table.py --detailed
```

---

## 📊 Formats de Sortie

### Table Simple (6 colonnes)

| Algorithm | Dataset | #Rules | Accuracy | Confidence | Time (s) |
|-----------|---------|--------|----------|------------|----------|

### Table Détaillée (8 colonnes)

| Algorithm | Dataset | #Rules | Acc. | Conf. | T_compat | T_index | T_CG |
|-----------|---------|--------|------|-------|----------|---------|------|

### Avec Statistiques (N runs)

Format : `$9 \pm 0.0$` (moyenne ± écart-type)

```latex
MATILDA & Bupa & $9 \pm 0.0$ & $1.000 \pm 0.000$ & ...
```

---

## 🎯 Options Principales

### `run_full_benchmark.py`

```bash
# Nombre de runs
--runs 5

# Algorithmes spécifiques
--algorithms MATILDA SPIDER

# Datasets spécifiques
--datasets Bupa BupaImperfect

# Type de table
--table-type detailed  # ou simple

# Fichier de config
--config benchmark_config.yaml

# Mode silencieux
--quiet
```

### Exemples

```bash
# Benchmark complet (défaut)
python run_full_benchmark.py --runs 5

# Rapide (3 runs, 2 algos)
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER

# Avec config
python run_full_benchmark.py --config benchmark_config.yaml

# Table simple
python run_full_benchmark.py --runs 5 --table-type simple
```

---

## 📁 Fichiers de Sortie

### Exécution du `run_full_benchmark.py`

```
data/output/
├── full_benchmark_results_20260112_143020.json      # Résultats bruts
├── full_benchmark_statistics_20260112_143020.json   # Statistiques
└── benchmark_table_20260112_143020.tex              # Table LaTeX
```

### Contenu JSON Statistiques

```json
{
  "MATILDA": {
    "Bupa": {
      "num_rules": {"mean": 9.0, "std": 0.0},
      "accuracy": {"mean": 1.0, "std": 0.0},
      "time_total": {"mean": 0.124, "std": 0.002},
      "n_runs": 5
    }
  }
}
```

---

## ⏱️ Temps d'Exécution

| Commande | Temps | Usage |
|----------|-------|-------|
| `generate_latex_table.py` | < 1s | Table rapide |
| `run_benchmark.py --runs 5` | 5-15 min | Test 1 algo |
| `run_full_benchmark.py --runs 3` | 30-60 min | Benchmark rapide |
| `run_full_benchmark.py --runs 5` | 1-2h | Article standard |
| `run_full_benchmark.py --runs 10` | 3-4h | Publication prestige |

---

## 🧪 Tester

```bash
# Vérifier installation
python test_latex_generation.py

# Test ultra-rapide (< 1 min)
python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[BENCHMARKING_QUICKSTART.md](BENCHMARKING_QUICKSTART.md)** | **Guide rapide complet** ⭐ |
| [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md) | Guide détaillé `run_full_benchmark.py` |
| [WHICH_SCRIPT.md](WHICH_SCRIPT.md) | Arbre de décision : quel script choisir ? |
| [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md) | Guide `run_benchmark.py` |
| [LATEX_README.md](LATEX_README.md) | Guide `generate_latex_table.py` |
| [LATEX_SUMMARY.md](LATEX_SUMMARY.md) | Référence ultra-concise |
| [benchmark_config.yaml](benchmark_config.yaml) | Configuration exemple |

---

## 💡 Conseils

### Pour Gagner du Temps

```bash
# Moins de runs
python run_full_benchmark.py --runs 3

# Exclure algorithmes lents
python run_full_benchmark.py --runs 5 --algorithms MATILDA SPIDER
```

### Pour Publication

```bash
# 5+ runs recommandés
python run_full_benchmark.py --runs 5

# 10 runs pour reviewers exigeants
python run_full_benchmark.py --runs 10
```

### Exécuter en Arrière-Plan

```bash
# Lancer et continuer à travailler
nohup python run_full_benchmark.py --runs 5 > benchmark.log 2>&1 &

# Suivre progression
tail -f benchmark.log
```

---

## 🆘 Résolution de Problèmes

### "Timeout expired"

```bash
# Augmenter timeout (2h)
python run_full_benchmark.py --runs 5 --timeout 7200
```

### "Certains runs échouent"

Le script continue même si certains runs échouent. Les statistiques sont calculées sur les runs réussis uniquement.

### "Trop lent"

```bash
# Exécuter par morceaux
python run_full_benchmark.py --runs 5 --algorithms MATILDA
python run_full_benchmark.py --runs 5 --algorithms SPIDER
# etc.
```

---

## ✅ Checklist Article

- [ ] **Exécuter benchmark**
  ```bash
  python run_full_benchmark.py --runs 5
  ```

- [ ] **Vérifier résultats**
  - Fichiers JSON créés ? ✓
  - Table LaTeX générée ? ✓
  - Statistiques raisonnables (std < 10% mean) ? ✓

- [ ] **Intégrer dans article**
  ```bash
  cp data/output/benchmark_table_*.tex paper/tables/results.tex
  ```

- [ ] **Compiler article**
  ```bash
  cd paper && pdflatex main.tex
  ```

- [ ] **Documenter méthodologie**
  - Nombre de runs : 5
  - Algorithmes : MATILDA, SPIDER, ANYBURL, POPPER
  - Datasets : Bupa, BupaImperfect, ComparisonDataset, ImperfectTest
  - Timeout : 1h par run
  - Machine : [spécifier CPU/RAM]

- [ ] **Sauvegarder données**
  - `full_benchmark_results_*.json`
  - `full_benchmark_statistics_*.json`
  - Logs si nécessaire

---

## 🎓 Récapitulatif

### Vous avez maintenant :

✅ **3 scripts Python** pour tous vos besoins de benchmarking  
✅ **Configuration YAML** flexible  
✅ **Tests automatisés** pour vérifier que tout marche  
✅ **7 fichiers de documentation** complets  
✅ **Exemples LaTeX** prêts à l'emploi  

### Le plus simple :

```bash
# Pour article scientifique
python run_full_benchmark.py --runs 5

# Pour table rapide
python generate_latex_table.py --detailed
```

---

## 🎯 Prochaines Étapes

1. **Tester le système**
   ```bash
   python test_latex_generation.py
   ```

2. **Lancer un benchmark test**
   ```bash
   python run_full_benchmark.py --runs 1 --algorithms MATILDA --datasets Bupa
   ```

3. **Benchmark complet pour article**
   ```bash
   python run_full_benchmark.py --runs 5
   ```

4. **Intégrer dans votre article**
   ```bash
   cp data/output/benchmark_table_*.tex paper/tables/
   ```

---

**🎉 Système complet et prêt à l'emploi !**

**Question ? Consultez [BENCHMARKING_QUICKSTART.md](BENCHMARKING_QUICKSTART.md) ou [WHICH_SCRIPT.md](WHICH_SCRIPT.md)**
