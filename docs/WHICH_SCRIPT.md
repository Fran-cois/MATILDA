# 🤔 Quel Script Utiliser ?

## Arbre de Décision

```
Combien d'algorithmes voulez-vous benchmarker ?
│
├─ TOUS LES ALGORITHMES → Utilisez run_full_benchmark.py 🚀
│                          • Automatique : tous algos + tous datasets
│                          • N runs avec statistiques (moyenne ± std)
│                          • Génère table LaTeX automatiquement
│                          • One-click solution !
│
├─ UN SEUL ALGORITHME
│   │
│   ├─ Besoin de statistiques ? → Utilisez run_benchmark.py 📈
│   │                              • N runs d'un algorithme
│   │                              • Calcule moyenne ± écart-type
│   │
│   └─ Pas de statistiques → Utilisez generate_latex_table.py ⚡
│                            • Très rapide (< 1 seconde)
│                            • Résultats existants
│
└─ RÉSULTATS EXISTANTS → Utilisez generate_latex_table.py ⚡
                         • Pas de re-run
                         • Table immédiate
```

## 📊 Comparaison

| Critère | `generate_latex_table.py` | `run_benchmark.py` | `run_full_benchmark.py` |
|---------|---------------------------|-------------------|-------------------------|
| **Vitesse** | ⚡⚡⚡ Très rapide (< 1s) | 🐢 Lent (N × run time) | 🐢🐢 Très lent (M × N × run) |
| **Statistiques** | ✗ Non (valeurs uniques) | ✅ Oui (moyenne ± std) | ✅ Oui (moyenne ± std) |
| **Re-exécution** | ✗ Non | ✅ Oui (N fois 1 algo) | ✅ Oui (N fois M algos) |
| **Résultats existants** | ✅ Oui | ✗ Non | ✗ Non |
| **Algorithmes** | Tous (existants) | 1 seul | **TOUS automatique** |
| **Automatisation** | Manuelle | Partielle | **Complète** ⭐ |
| **Usage** | Résultats rapides | 1 algo avec stats | **Article complet** |

## 🎯 Cas d'Usage

### 1. Article Scientifique Complet (Recommandé) 🎓

```bash
python run_full_benchmark.py --runs 5
```

**Pourquoi :** Tout automatique - tous algorithmes + stats + table LaTeX

### 2. Présentation Rapide (Aujourd'hui)

```bash
python generate_latex_table.py --detailed
```

**Pourquoi :** Rapide, résultats existants suffisants

### 3. Test d'un Nouvel Algorithme

```bash
python run_benchmark.py --runs 5 --datasets Bupa BupaImperfect
```

**Pourquoi :** Focus sur 1 algo, avec statistiques

## ⚡ Recommandations

### Pour Présentation / Meeting
→ **`generate_latex_table.py`**
- Rapide
- Résultats actuels OK
- Pas besoin de re-run

### Pour Article Scientifique
→ **`run_benchmark.py` avec --runs 5+**
- Statistiques robustes
- Reviewers apprécient mean ± std
- Montrer variabilité

### Pour Documentation Interne
→ **`generate_latex_table.py`**
- Simple et rapide
- Mise à jour facile

### Pour Comparaison Algorithms
→ **Les deux !**
1. `generate_latex_table.py` pour aperçu rapide
2. `run_benchmark.py` pour validation statistique

## 🚀 Quick Commands

```bash
# ONE-CLICK : Benchmark COMPLET avec stats (RECOMMANDÉ) ⭐
python run_full_benchmark.py --runs 5

# Quick table (< 1 seconde)
python generate_latex_table.py --detailed

# Test 1 algorithme avec stats
python run_benchmark.py --runs 5 --algorithms MATILDA

# Test rapide (3 runs, 2 algos)
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER

# Vérifier tout
python test_latex_generation.py
```

## 💡 Tips

### Si vous avez déjà plusieurs résultats...
→ Utilisez `generate_latex_table.py`

### Si vous voulez publier...
→ Utilisez `run_benchmark.py --runs 5` minimum

### Si vous êtes pressé...
→ Utilisez `generate_latex_table.py`

### Si vous voulez des stats fiables...
→ Utilisez `run_benchmark.py --runs 10`

## 📈 Temps d'Exécution Estimé

| Command | Datasets | Runs | Temps Estimé |
|---------|----------|------|--------------|
| `generate_latex_table.py` | Tous | - | < 1 seconde |
| `run_benchmark.py --runs 3` | 1 | 3 | ~5 minutes |
| `run_benchmark.py --runs 5` | 1 | 5 | ~8 minutes |
| `run_benchmark.py --runs 5` | 3 | 15 | ~25 minutes |
| `run_benchmark.py --runs 10` | 2 | 20 | ~30 minutes |

## ✅ Checklist : Quel Script ?

- [ ] **Besoin de stats ?** → OUI = `run_benchmark.py`, NON = `generate_latex_table.py`
- [ ] **Temps disponible ?** → < 1 min = `generate_latex_table.py`, > 5 min = `run_benchmark.py`
- [ ] **Publication ?** → OUI = `run_benchmark.py`, NON = `generate_latex_table.py`
- [ ] **Résultats existants OK ?** → OUI = `generate_latex_table.py`, NON = `run_benchmark.py`

---

## 🎯 Décision Finale Simplifiée

### JE VEUX UNE TABLE MAINTENANT
```bash
python generate_latex_table.py --detailed
```

### JE VEUX UNE TABLE POUR PUBLICATION (UN ALGO)
```bash
python run_benchmark.py --runs 5 --algorithms MATILDA
```

### JE VEUX BENCHMARKER TOUT POUR MON ARTICLE ⭐
```bash
python run_full_benchmark.py --runs 5
```

**C'est aussi simple que ça !** 🎉

---

## 📚 Documentation Complète

- **`run_full_benchmark.py`** → [FULL_BENCHMARK_GUIDE.md](FULL_BENCHMARK_GUIDE.md)
- **`run_benchmark.py`** → [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md)
- **`generate_latex_table.py`** → [LATEX_README.md](LATEX_README.md)
- **Configuration** → [benchmark_config.yaml](benchmark_config.yaml)
