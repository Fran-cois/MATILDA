# 🎨 TikZ Graphics Support for MATILDA

**Date**: 19 janvier 2026  
**Feature**: TikZ/LaTeX figure generation  
**Status**: ✅ **IMPLEMENTED**

---

## 📋 Overview

J'ai ajouté la génération automatique de figures TikZ/LaTeX pour intégration directe dans votre thèse !

### ✅ Nouveau Script: `generate_tikz_scalability.py` (587 lignes)

Génère du code TikZ/PGFPlots de qualité publication pour tous les graphiques de scalabilité.

---

## 🎯 Fichiers Générés

Quand vous exécutez `python cli.py scalability --full`, vous obtenez maintenant:

### PNG (pour présentations)
- `scalability_runtime.png`
- `scalability_memory.png`
- `scalability_rules.png`
- `scalability_throughput.png`
- `scalability_overview.png`

### TikZ/LaTeX (pour thèse)
- `tikz_runtime.tex` - Runtime vs size
- `tikz_rules.tex` - Rules discovered
- `tikz_throughput.tex` - Throughput analysis
- `tikz_memory.tex` - Memory usage
- `tikz_combined.tex` - Vue d'ensemble 2x2
- `scalability_report.tex` - Document LaTeX complet
- `TIKZ_USAGE.md` - Instructions d'utilisation

---

## 📝 Usage dans LaTeX

### 1. Inclure une figure individuelle

```latex
\documentclass{article}
\usepackage{pgfplots}
\usepackage{tikz}
\pgfplotsset{compat=1.18}

\begin{document}

\begin{figure}[htbp]
    \centering
    \input{tikz_runtime.tex}
    \caption{Runtime scalability of MATILDA TGD discovery.}
    \label{fig:scalability_runtime}
\end{figure}

\end{document}
```

### 2. Compiler le document complet

```bash
cd results/scalability/
pdflatex scalability_report.tex
```

Vous obtenez un PDF avec toutes les figures !

### 3. Intégration dans votre thèse

```latex
% Dans votre chapitre résultats
\section{Scalability Analysis}

Figure~\ref{fig:scalability_runtime} shows the runtime scaling...

\begin{figure}[htbp]
    \centering
    \input{results/scalability/tikz_runtime.tex}
    \caption{Runtime scalability of MATILDA. The system exhibits 
             near-linear scaling up to 10M tuples.}
    \label{fig:scalability_runtime}
\end{figure}
```

---

## 🎨 Personnalisation

Les fichiers .tex sont totalement modifiables :

```latex
% Changer les couleurs
\addplot[
    color=blue,        % → red, green, orange, etc.
    mark=*,           % → square*, triangle*, diamond*
    line width=1.5pt, % → 1pt, 2pt, etc.
]

% Modifier les titres
title={Your Custom Title},

% Ajuster les dimensions
width=0.8\textwidth,
height=0.5\textwidth,

% Style de grille
grid=major,  % → minor, both, none
```

---

## ✨ Avantages TikZ

### Pour la thèse:
✅ **Vectoriel** - Échelle parfaitement, pas de pixellisation  
✅ **Intégration native** - Même police que le document  
✅ **Qualité publication** - Accepté par toutes les revues  
✅ **Personnalisable** - Modifiable directement dans LaTeX  
✅ **Léger** - Pas de fichiers image volumineux

### vs PNG:
- PNG: Bitmap, 300 DPI, ~500 KB/figure
- TikZ: Vectoriel, infini DPI, ~5 KB/figure

---

## 📦 Packages LaTeX Requis

```bash
# TeX Live
tlmgr install pgfplots tikz

# MiKTeX
mpm --install pgfplots
```

Ou dans votre document:
```latex
\usepackage{pgfplots}
\usepackage{tikz}
\usetikzlibrary{positioning,calc}
\pgfplotsset{compat=1.18}
```

---

## 🚀 Utilisation Rapide

```bash
# Générer les résultats + PNG + TikZ
python cli.py scalability --full

# TikZ uniquement (si résultats existent)
python scripts/utils/generate_tikz_scalability.py \
  results/scalability/scalability_summary.json

# Compiler le rapport
cd results/scalability/
pdflatex scalability_report.tex
```

---

## 📊 Exemple de Code Généré

```latex
\begin{tikzpicture}
\begin{axis}[
    width=0.8\textwidth,
    height=0.5\textwidth,
    xlabel={Dataset Size (Million Tuples)},
    ylabel={Runtime (seconds)},
    title={Scalability: Runtime vs Dataset Size},
    grid=major,
    legend pos=north west,
]

% MATILDA data
\addplot[
    color=blue,
    mark=*,
    line width=1.5pt,
] coordinates {
    (1.0,320.45)
    (5.0,1287.23)
    (10.0,2501.89)
};
\addlegendentry{MATILDA (A* + Hybrid)}

% Linear reference
\addplot[
    color=gray,
    dashed,
    line width=1pt,
] coordinates {
    (1.0,250.19)
    (5.0,1250.95)
    (10.0,2501.89)
};
\addlegendentry{Linear reference}

\end{axis}
\end{tikzpicture}
```

---

## 🎓 Intégration Thèse

### Structure Recommandée

```
thesis/
├── main.tex
├── chapters/
│   ├── introduction.tex
│   ├── related_work.tex
│   ├── methodology.tex
│   ├── results.tex          ← Inclure les figures ici
│   └── conclusion.tex
└── figures/
    └── scalability/          ← Copier les .tex ici
        ├── tikz_runtime.tex
        ├── tikz_rules.tex
        ├── tikz_throughput.tex
        └── tikz_combined.tex
```

### Dans results.tex

```latex
\chapter{Experimental Results}

\section{Scalability Analysis}

We evaluate MATILDA's scalability on datasets ranging from 
1 million to 10 million tuples...

\subsection{Runtime Scaling}

Figure~\ref{fig:scalability_runtime} presents the runtime 
scaling characteristics. The results demonstrate near-linear 
scaling with a factor of 1.12, indicating excellent scalability 
for large-scale knowledge base discovery.

\begin{figure}[htbp]
    \centering
    \input{figures/scalability/tikz_runtime.tex}
    \caption{Runtime scalability of MATILDA. Tests performed 
             with optimal configuration (A* + Hybrid heuristic, 
             N=3). Each data point represents the mean of 5 runs.}
    \label{fig:scalability_runtime}
\end{figure}

\subsection{Comparative Analysis}

Table~\ref{tab:comparison} compares MATILDA with state-of-the-art 
baselines...
```

---

## 💡 Tips & Tricks

### 1. Subplot avec 4 graphiques
Utilisez `tikz_combined.tex` pour une vue d'ensemble compacte.

### 2. Légende personnalisée
```latex
\addlegendentry{MATILDA (Proposed)}
\addlegendentry{AMIE3 (Baseline)}
\addlegendentry{AnyBURL (Baseline)}
```

### 3. Annotations
```latex
\node[pin=30:{Optimal}] at (axis cs:3,1200) {};
```

### 4. Erreur bars (pour statistiques)
```latex
\addplot[error bars/.cd, y dir=both, y explicit]
coordinates {
    (1.0,320.45) +- (0,15.2)
    (5.0,1287.23) +- (0,45.8)
};
```

---

## 🔧 Troubleshooting

### Erreur: "Package pgfplots not found"
```bash
tlmgr install pgfplots
```

### Erreur: "Dimension too large"
Réduire width/height dans le fichier .tex

### Erreur: "Undefined control sequence"
Vérifier que `\pgfplotsset{compat=1.18}` est présent

### Graphique trop petit
Augmenter `width=` et `height=` dans le .tex

---

## 📚 Ressources

- **PGFPlots Manual**: http://pgfplots.sourceforge.net/
- **TikZ Gallery**: http://www.texample.net/tikz/
- **Overleaf Guides**: https://www.overleaf.com/learn/latex/Pgfplots_package

---

## ✅ Résumé

✅ **587 lignes de code** pour génération TikZ  
✅ **6 fichiers .tex** générés automatiquement  
✅ **1 document LaTeX complet** (scalability_report.tex)  
✅ **Instructions complètes** (TIKZ_USAGE.md)  
✅ **Intégration** dans `python cli.py scalability --full`

---

**Maintenant vous avez des graphiques publication-ready en vectoriel pour votre thèse ! 🎓**

*Dernière mise à jour: 19 janvier 2026*
