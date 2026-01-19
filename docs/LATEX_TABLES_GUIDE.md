# 📊 Génération de Tables LaTeX pour MATILDA

## Vue d'ensemble

Deux scripts sont disponibles pour générer des tables LaTeX professionnelles à partir des résultats MATILDA :

1. **`generate_latex_table.py`** - Génère rapidement des tables à partir des résultats existants ⚡
2. **`run_benchmark.py`** - Exécute plusieurs runs et calcule statistiques (moyenne ± écart-type) 📈

## 🚀 Utilisation Rapide

### Générer Table à partir de Résultats Existants

```bash
# Table simple
python generate_latex_table.py

# Table détaillée avec toutes les métriques
python generate_latex_table.py --detailed

# Spécifier répertoire et sortie
python generate_latex_table.py --results-dir data/output --output my_table.tex
```

### Exécuter Benchmark avec Statistiques

```bash
# 5 runs (par défaut)
python run_benchmark.py --runs 5

# 3 runs sur datasets spécifiques
python run_benchmark.py --runs 3 --datasets Bupa BupaImperfect

# Plusieurs algorithmes
python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER
```

## 📋 Scripts Disponibles

### 1. `generate_latex_table.py` ⚡

**Avantages :**
- ✅ Très rapide (pas de re-exécution)
- ✅ Utilise résultats existants
- ✅ 2 modes : simple et détaillé

**Options :**

```bash
python generate_latex_table.py [OPTIONS]

Options:
  --results-dir DIR          Répertoire des résultats (défaut: data/output)
  --output FILE              Fichier de sortie (défaut: auto-généré)
  --algorithms ALG1 ALG2 ... Liste des algorithmes (défaut: tous)
  --datasets DS1 DS2 ...     Liste des datasets (défaut: tous)
  --detailed                 Table détaillée avec tous les temps
```

**Exemples :**

```bash
# Table simple avec résultats existants
python generate_latex_table.py

# Table détaillée
python generate_latex_table.py --detailed

# Algorithmes spécifiques
python generate_latex_table.py --algorithms MATILDA SPIDER

# Sortie personnalisée
python generate_latex_table.py --output results_table.tex --detailed
```

**Sortie - Table Simple :**

| Algorithm | Dataset | #Rules | Accuracy | Confidence | Time (s) |
|-----------|---------|--------|----------|------------|----------|
| MATILDA   | Bupa    | 9      | 1.0000   | 1.0000     | 0.0387   |

**Sortie - Table Détaillée :**

| Algorithm | Dataset | #Rules | Acc. | Conf. | T_compat | T_index | T_CG   |
|-----------|---------|--------|------|-------|----------|---------|--------|
| MATILDA   | Bupa    | 9      | 1.000| 1.000 | 0.0378   | 0.0382  | 0.0387 |

### 2. `run_benchmark.py` 📈

**Avantages :**
- ✅ Calcule statistiques (moyenne ± écart-type)
- ✅ Exécutions multiples pour robustesse
- ✅ Table LaTeX avec statistiques

**Options :**

```bash
python run_benchmark.py [OPTIONS]

Options:
  --runs N                   Nombre d'exécutions (défaut: 5)
  --datasets DS1 DS2 ...     Liste des datasets
  --algorithms ALG1 ALG2 ... Liste des algorithmes
  --config FILE              Fichier config (défaut: config.yaml)
  --output-dir DIR           Répertoire sortie (défaut: data/output)
  --no-latex                 Skip génération LaTeX
```

**Exemples :**

```bash
# 5 runs sur tous les datasets
python run_benchmark.py --runs 5

# 3 runs, datasets spécifiques
python run_benchmark.py --runs 3 --datasets Bupa BupaImperfect

# Plusieurs algorithmes
python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER ANYBURL

# Sans générer LaTeX (JSON seulement)
python run_benchmark.py --runs 3 --no-latex
```

**Sortie :**

| Algorithm | Dataset | #Rules | Time (s) | Time Building CG (s) |
|-----------|---------|--------|----------|---------------------|
| MATILDA   | Bupa    | $9 \pm 0.0$ | $15.2 \pm 1.3$ | $0.0387 \pm 0.0001$ |

## 📊 Formats de Sortie

### Table Simple

```latex
\begin{table}[htbp]
\centering
\caption{Rule Discovery Results}
\label{tab:results}
\begin{tabular}{llrrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Accuracy} & \textbf{Confidence} & \textbf{Time (s)} \\
\midrule
MATILDA & Bupa & 9 & 1.0000 & 1.0000 & 0.0387 \\
 & BupaImperfect & 9 & 1.0000 & 0.9775 & 0.0342 \\
\midrule
SPIDER & BupaImperfect & 50 & 0.0000 & 0.0000 & 0.0342 \\
\bottomrule
\end{tabular}
\end{table}
```

### Table Détaillée

```latex
\begin{table}[htbp]
\centering
\caption{Detailed Rule Discovery Performance}
\label{tab:detailed_results}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llrrrrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Acc.} & \textbf{Conf.} & \textbf{T\textsubscript{compat}} & \textbf{T\textsubscript{index}} & \textbf{T\textsubscript{CG}} \\
\midrule
MATILDA & Bupa & 9 & 1.000 & 1.000 & 0.0378 & 0.0382 & 0.0387 \\
\bottomrule
\end{tabular}}
\end{table}

% Legend:
% Acc. = Average Accuracy
% Conf. = Average Confidence
% T_compat = Time to compute compatible attributes (seconds)
% T_index = Time to compute indexed attributes (seconds)
% T_CG = Time to build constraint graph (seconds)
```

### Table avec Statistiques

```latex
\begin{table}[htbp]
\centering
\caption{Performance Comparison: Number of Rules and Execution Time}
\label{tab:benchmark_results}
\begin{tabular}{llrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Time (s)} & \textbf{Time Building CG (s)} \\
\midrule
MATILDA & Bupa & $9 \pm 0.0$ & $15.23 \pm 1.34$ & $0.0387 \pm 0.0001$ \\
\bottomrule
\end{tabular}
\end{table}
```

## 📝 Utilisation dans LaTeX

### 1. Ajouter Packages

```latex
\usepackage{booktabs}     % Pour les tables professionnelles
\usepackage{graphicx}     % Pour resizebox (table détaillée)
```

### 2. Inclure la Table

```latex
% Dans votre document
\input{latex_table_simple_20260112_132649.tex}

% Ou directement copier-coller le contenu
```

### 3. Personnaliser

```latex
% Changer le caption
\caption{My Custom Title}

% Changer le label
\label{tab:my_results}

% Changer la position
\begin{table}[h!]  % Force here
\begin{table}[t]   % Top of page
```

## 🎯 Cas d'Usage

### 1. Table Rapide pour Présentation

```bash
# Générer table simple rapidement
python generate_latex_table.py

# Copier dans slides.tex
```

### 2. Table Détaillée pour Article

```bash
# Générer table avec tous les détails
python generate_latex_table.py --detailed --output paper_table.tex

# Inclure dans article.tex
\input{paper_table.tex}
```

### 3. Benchmark Statistique Robuste

```bash
# 10 runs pour statistiques solides
python run_benchmark.py --runs 10 --datasets Bupa BupaImperfect

# Table avec moyenne ± écart-type générée automatiquement
```

### 4. Comparaison Multi-Algorithmes

```bash
# Comparer plusieurs algorithmes
python generate_latex_table.py --algorithms MATILDA SPIDER ANYBURL --detailed

# Ou avec benchmark
python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER ANYBURL
```

## 📈 Workflow Complet

### Pour Article Scientifique

```bash
# 1. Exécuter benchmarks (5+ runs)
python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER ANYBURL

# 2. Générer table LaTeX avec statistiques
# (Automatique dans run_benchmark.py)

# 3. Inclure dans article
\input{benchmark_table_20260112_132649.tex}

# 4. Compiler LaTeX
pdflatex article.tex
```

### Pour Présentation Rapide

```bash
# 1. Utiliser résultats existants
python generate_latex_table.py

# 2. Copier table dans slides

# 3. Compiler présentation
```

## 🔧 Fichiers Générés

| Script | Fichiers Générés |
|--------|------------------|
| `generate_latex_table.py` | `latex_table_simple_TIMESTAMP.tex` ou `latex_table_detailed_TIMESTAMP.tex` |
| `run_benchmark.py` | `benchmark_results_TIMESTAMP.json` + `benchmark_table_TIMESTAMP.tex` |

## ⚙️ Configuration

### Modifier Colonnes Table Simple

Dans `generate_latex_table.py` ligne ~100 :

```python
latex_lines.append("\\textbf{Algorithm} & \\textbf{Dataset} & \\textbf{\\#Rules} & ...")
```

### Modifier Colonnes Table Détaillée

Dans `generate_latex_table.py` ligne ~160 :

```python
latex_lines.append("\\textbf{Algorithm} & \\textbf{Dataset} & ... ")
```

### Ajouter Métriques

Modifier dans `collect_results()` :

```python
data[algorithm][dataset] = {
    'num_rules': num_rules,
    'custom_metric': ...,  # Ajouter ici
}
```

## 📊 Métriques Disponibles

| Métrique | Description | Source |
|----------|-------------|--------|
| `num_rules` | Nombre de règles découvertes | `*_results.json` |
| `avg_accuracy` | Accuracy moyenne des règles | `*_results.json` |
| `avg_confidence` | Confidence moyenne des règles | `*_results.json` |
| `time_compute_compatible` | Temps calcul attributs compatibles | `init_time_metrics_*.json` |
| `time_to_compute_indexed` | Temps calcul attributs indexés | `init_time_metrics_*.json` |
| `time_building_cg` | Temps construction graphe contraintes | `init_time_metrics_*.json` |

## 🎨 Personnalisation Avancée

### Table avec Couleurs

```latex
\usepackage{xcolor}
\usepackage{colortbl}

% Dans la table
\rowcolor{lightgray} MATILDA & Bupa & 9 & ... \\
```

### Table Multi-Pages

```latex
\usepackage{longtable}

\begin{longtable}{llrrrr}
\caption{Long Results Table} \\
\toprule
... headers ...
\endfirsthead
... répéter headers ...
\endhead
... data ...
\end{longtable}
```

### Table Rotée

```latex
\usepackage{rotating}

\begin{sidewaystable}
  ... table content ...
\end{sidewaystable}
```

## ✅ Checklist Publication

- [ ] Exécuter benchmark avec ≥5 runs
- [ ] Générer table LaTeX avec statistiques
- [ ] Vérifier packages LaTeX (booktabs, graphicx)
- [ ] Personnaliser caption et label
- [ ] Vérifier formatage nombres (précision)
- [ ] Ajouter légende si nécessaire
- [ ] Compiler et vérifier rendu PDF
- [ ] Citer MATILDA dans le texte

## 🆘 Dépannage

### Erreur : "No results found"

```bash
# Vérifier répertoire
ls data/output/*_results.json

# Spécifier répertoire explicitement
python generate_latex_table.py --results-dir path/to/results
```

### Table Trop Large

```latex
% Utiliser resizebox
\resizebox{\textwidth}{!}{%
  ... table ...
}

% Ou réduire police
\small
\begin{tabular}{...}
```

### Caractères Spéciaux LaTeX

Les underscores sont échappés automatiquement dans les scripts.
Si besoin manuel : `\_` au lieu de `_`

## 📚 Exemples Complets

### Exemple 1 : Table Simple

```bash
python generate_latex_table.py --algorithms MATILDA --datasets Bupa
```

**Sortie :**
```latex
\begin{table}[htbp]
\centering
\caption{Rule Discovery Results}
\begin{tabular}{llrrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Accuracy} & \textbf{Confidence} & \textbf{Time (s)} \\
\midrule
MATILDA & Bupa & 9 & 1.0000 & 1.0000 & 0.0387 \\
\bottomrule
\end{tabular}
\end{table}
```

### Exemple 2 : Benchmark avec Stats

```bash
python run_benchmark.py --runs 5 --datasets Bupa BupaImperfect
```

**Sortie :**
```latex
MATILDA & Bupa & $9 \pm 0.0$ & $15.23 \pm 1.34$ & $0.0387 \pm 0.0001$ \\
MATILDA & BupaImperfect & $9 \pm 0.0$ & $14.87 \pm 1.12$ & $0.0342 \pm 0.0002$ \\
```

---

## 🎉 Résultat

Vous disposez maintenant de **2 scripts complets** pour générer des tables LaTeX professionnelles :

✅ **Génération rapide** - À partir de résultats existants  
✅ **Benchmark statistique** - Avec moyenne ± écart-type  
✅ **Tables détaillées** - Toutes les métriques de temps  
✅ **Personnalisables** - Format et contenu adaptables  
✅ **Prêts pour publication** - Format professionnel booktabs  

**Idéal pour articles scientifiques, présentations et rapports !** 📊✨
