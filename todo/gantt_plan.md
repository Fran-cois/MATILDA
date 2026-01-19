# Plan de travail MATILDA - Structure de dépendances

## 📊 Vue d'ensemble temporelle (estimation)

```
Semaine 1-2: Phase 1 (Fondations)
Semaine 3-4: Phase 2 (Optimisations) 
Semaine 5-6: Phase 3 (Validation)
Semaine 7-8: Phase 4 (Finalisation)
```

---

## 🔵 PHASE 1: Fondations & Nettoyage (Semaine 1-2)
**Objectif**: Préparer le terrain, stabiliser la base de code

### T1.1 - Nettoyage & Organisation du Code [2 jours]
- **Dépendances**: Aucune
- **Priorité**: 🔴 Critique
- **Actions**:
  - Déplacer fichiers de test vers `tests/`
  - Déplacer fichiers de debug vers `debug/`
  - Consolider les README multiples
  - Nettoyer `__pycache__`
- **Livrables**: Structure propre du repo
- **Impact**: Facilite toutes les autres tâches

### T1.2 - Validation des Métriques Existantes [3 jours]
- **Dépendances**: T1.1
- **Priorité**: 🔴 Critique
- **Actions**:
  - Vérifier cohérence AMIE3/AnyBurl/Spider/Popper
  - Valider les formules de calcul
  - Créer tests unitaires pour les métriques
  - Documenter les métriques validées
- **Livrables**: 
  - `tests/test_metrics_validation.py`
  - Rapport de validation
- **Impact**: Assure la fiabilité de toutes les analyses futures

### T1.3 - Finaliser Precision/Recall [2 jours]
- **Dépendances**: T1.2
- **Priorité**: 🟠 Haute
- **Statut**: 🟡 Almost done
- **Actions**:
  - Compléter le ground truth
  - Calculer P/R sur tous les datasets
  - Ajouter aux benchmarks
- **Livrables**: 
  - Métriques P/R complètes
  - Intégration dans `compute_all_metrics.py`

---

## 🟢 PHASE 2: Optimisations & Nouveautés (Semaine 3-4)

### T2.1 - Implémentation des Heuristiques [5 jours]
- **Dépendances**: T1.1, T1.2
- **Priorité**: 🟠 Haute
- **Actions**:
  - Implémenter heuristiques de recherche de chemins
  - Documenter les algorithmes (référence thèse PhD)
  - Comparer performances naive vs heuristic
  - Ajouter paramètres de configuration
- **Livrables**: 
  - `src/heuristics/path_search.py`
  - Documentation dans `GRAPH_TRAVERSAL_ALGORITHMS.md`
  - Benchmarks comparatifs
- **Impact**: ⚡ Amélioration significative des performances

### T2.2 - Sensitivity Analysis (N) [4 jours]
- **Dépendances**: T2.1 (pour avoir baseline optimisée)
- **Priorité**: 🟠 Haute
- **Actions**:
  - Définir range de N à tester (ex: N=1 à N=10)
  - Créer script d'expérimentation
  - Mesurer runtime vs pattern coverage
  - Créer visualisations (courbes trade-off)
- **Livrables**:
  - `scripts/sensitivity_analysis_N.py`
  - Rapport avec graphiques
  - Recommandations sur N optimal
- **Impact**: Justification scientifique des choix de paramètres

---

## 🟡 PHASE 3: Validation à l'Échelle (Semaine 5-6)

### T3.1 - Préparation Dataset Large [2 jours]
- **Dépendances**: T2.1
- **Priorité**: 🟠 Haute
- **Actions**:
  - Identifier/créer dataset >1M tuples
  - Configurer environnement (mémoire, disque)
  - Créer scripts de monitoring
- **Livrables**: 
  - Dataset préparé dans `data/large_scale/`
  - Scripts de monitoring

### T3.2 - Scalability Stress Test [5 jours]
- **Dépendances**: T3.1, T2.1
- **Priorité**: 🔴 Critique
- **Actions**:
  - Exécuter MATILDA sur dataset large
  - Monitor: temps, mémoire, CPU
  - Comparer avec baselines (AnyBurl sur même dataset)
  - Identifier bottlenecks
  - Optimiser si nécessaire
- **Livrables**:
  - Résultats de stress test
  - Profiling report
  - Preuves de scalabilité
- **Impact**: 🎯 Valide le claim principal "at scale"

### T3.3 - Reproductibilité & Seeds [2 jours]
- **Dépendances**: T3.2
- **Priorité**: 🟡 Moyenne
- **Actions**:
  - Fixer seeds pour tous les algorithmes
  - Documenter procédure de reproduction
  - Créer `REPRODUCIBILITY.md`
- **Livrables**: Guide de reproduction complet

---

## 🟣 PHASE 4: Analyses Statistiques & Finalisation (Semaine 7-8)

### T4.1 - Re-run Global avec 5 Seeds [7 jours]
- **Dépendances**: T3.3, T2.1, T1.3
- **Priorité**: 🔴 Critique
- **Actions**:
  - Exécuter tous les benchmarks 5 fois (seeds différents)
  - Calculer mean, std, confidence intervals
  - Appliquer tests statistiques (t-test, Wilcoxon)
  - Vérifier significance (p-values)
- **Livrables**:
  - `results/statistical_analysis/`
  - Tableaux avec mean±std
  - Tests de significativité
- **Impact**: 🎯 Robustesse scientifique des résultats

### T4.2 - Génération Tableaux Finaux [2 jours]
- **Dépendances**: T4.1
- **Priorité**: 🟠 Haute
- **Actions**:
  - Mettre à jour tous les tableaux LaTeX
  - Inclure statistiques complètes
  - Générer visualisations finales
- **Livrables**: 
  - Tableaux LaTeX publication-ready
  - Figures haute résolution

### T4.3 - Documentation Finale [3 jours]
- **Dépendances**: T4.2, toutes les autres
- **Priorité**: 🟡 Moyenne
- **Actions**:
  - Mettre à jour README principal
  - Consolider la documentation
  - Créer guide d'installation complet
  - Ajouter exemples d'utilisation
- **Livrables**: Documentation complète et cohérente

---

## 📈 Graphe de dépendances

```
T1.1 (Nettoyage)
  ↓
T1.2 (Validation Métriques)
  ↓
T1.3 (P/R) ──────┐
  ↓              ↓
T2.1 (Heuristics) ← (peut bénéficier de P/R)
  ↓              ↓
T2.2 (Sensitivity N)
  ↓              ↓
T3.1 (Prep Dataset) ← (parallèle possible)
  ↓              ↓
T3.2 (Stress Test)
  ↓              ↓
T3.3 (Reproductibilité)
  ↓              ↓
T4.1 (Re-run x5) ← (collecte tout)
  ↓
T4.2 (Tableaux)
  ↓
T4.3 (Doc Finale)
```

---

## 🎯 Chemin Critique (Critical Path)

**T1.1 → T1.2 → T2.1 → T3.1 → T3.2 → T4.1 → T4.2 → T4.3**

Durée totale estimée: **7-8 semaines**

---

## 🔀 Tâches Parallélisables

### En Phase 1-2:
- T1.3 (P/R) peut commencer dès que T1.2 est stable
- T2.2 (Sensitivity) peut commencer en parallèle de T2.1 si on accepte baseline naive

### En Phase 3:
- T3.1 (Prep Dataset) peut commencer en parallèle de T2.2

---

## 📊 Effort Estimé Total

| Phase | Tâches | Jours | Jours-Homme |
|-------|--------|-------|-------------|
| Phase 1 | 3 | 7 | 7 |
| Phase 2 | 2 | 9 | 9 |
| Phase 3 | 3 | 9 | 9 |
| Phase 4 | 3 | 12 | 12 |
| **TOTAL** | **11** | **37** | **37 jours** (~7-8 semaines) |

---

## 🚦 Recommandations de Prioritisation

### Sprint 1 (2 semaines):
1. T1.1 - Nettoyage (URGENT)
2. T1.2 - Validation métriques (URGENT)
3. T1.3 - Finaliser P/R

### Sprint 2 (2 semaines):
4. T2.1 - Heuristiques (HIGH VALUE)
5. T3.1 - Prep dataset (en parallèle)

### Sprint 3 (2 semaines):
6. T2.2 - Sensitivity Analysis
7. T3.2 - Stress Test (HIGH IMPACT)

### Sprint 4 (2 semaines):
8. T3.3 - Reproductibilité
9. T4.1 - Re-run statistique (LONG)

### Sprint 5 (1 semaine):
10. T4.2 - Tableaux finaux
11. T4.3 - Documentation

---

## ⚠️ Risques Identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Stress test révèle des bugs majeurs | 🔴 Élevé | Faire T3.2 tôt, prévoir buffer |
| Re-run x5 prend >7 jours | 🟠 Moyen | Paralléliser sur plusieurs machines |
| Heuristiques ne donnent pas d'amélioration | 🟡 Faible | Documenter résultats négatifs |
| Dataset large non disponible | 🟠 Moyen | Préparer plusieurs options |

---

## 🎓 Conseils pour la Thèse

Les tâches marquées 🎯 sont **critiques** pour la défense:
- T3.2 (Scalability) - Valide le claim principal
- T4.1 (Statistical) - Robustesse scientifique
- T1.3 (P/R) - Validation qualitative

Les tâches 🟡 peuvent être dépriorisées si manque de temps:
- T3.3 (Reproductibilité) - Nice to have
- T2.2 (Sensitivity) si résultats déjà convaincants
