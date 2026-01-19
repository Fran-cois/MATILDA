# 🔍 ÉVALUATION DU PLAN GANTT - 19 Janvier 2026

## ⚠️ SITUATION CRITIQUE IDENTIFIÉE

### 🚨 Problème bloquant majeur

**MATILDA trouve 0 règles** malgré :
- ✅ Graphe de contraintes construit (426 nœuds)
- ✅ JIA list créée (468 entrées)  
- ✅ Attributs compatibles (50 paires)
- ✅ Infrastructure complète

**Root cause**: Le traversal DFS/BFS/A* ne yield aucune règle. Temps d'exécution anormalement court (0.3s au lieu de plusieurs minutes attendues).

---

## 📊 ÉVALUATION PAR PHASE

### 🔵 PHASE 1: Fondations & Nettoyage
**Statut global**: ⚠️ **PARTIELLEMENT OBSOLÈTE**

#### T1.1 - Nettoyage & Organisation [2j]
- **Évaluation**: ✅ **PERTINENT** 
- **Statut actuel**: Partiellement fait
  - ✅ Scripts organisés dans `scripts/benchmarks/`, `scripts/utils/`
  - ✅ Packages créés (`__init__.py`)
  - ⚠️ Encore beaucoup de fichiers README/MD en doublon
  - ❌ Tests non déplacés vers `tests/`
  - ❌ Debug files non organisés
- **Recommandation**: **À FAIRE en premier** - facilitera le debugging
- **Effort réel**: 1 jour (vs 2j estimé)

#### T1.2 - Validation des Métriques Existantes [3j]
- **Évaluation**: ⚠️ **PRÉMATURÉ**
- **Problème**: Les métriques de AMIE3/AnyBurl/Spider fonctionnent, mais **on ne peut pas calculer les métriques de MATILDA** si 0 règles sont découvertes
- **Dépendance critique**: Nécessite que T0.1 (FIX MATILDA) soit résolu
- **Recommandation**: **BLOQUER** jusqu'à résolution du bug
- **Effort réel**: 2 jours APRÈS fix

#### T1.3 - Finaliser Precision/Recall [2j]
- **Évaluation**: ⚠️ **BLOQUÉ**
- **Statut**: "Almost done" mais inutilisable
- **Problème**: P/R nécessite des règles découvertes par MATILDA
- **Recommandation**: **REPORTER** après T0.1
- **Effort réel**: 1 jour après fix

**📉 Impact sur Phase 1**: Plan compromis, nécessite ajout de **T0.1 critique**

---

### 🟢 PHASE 2: Optimisations & Nouveautés
**Statut global**: 🚫 **NON VIABLE**

#### T2.1 - Implémentation des Heuristiques [5j]
- **Évaluation**: ❌ **INUTILE ACTUELLEMENT**
- **Raison**: 
  - Les heuristiques A*/hybrid sont **déjà implémentées** dans `graph_traversal.py`
  - Le problème n'est pas l'absence d'heuristiques, mais le **traversal qui ne fonctionne pas du tout**
  - Optimiser un système qui retourne 0 règles n'a aucun sens
- **Statut code**:
  - ✅ `astar()` implémenté (lignes 143-192 de graph_traversal.py)
  - ✅ `bfs()` implémenté  
  - ✅ `dfs()` implémenté
  - ✅ Heuristic functions présentes
- **Recommandation**: **ANNULER** cette tâche - déjà fait
- **Remplacer par**: Documentation des heuristiques existantes (1j)

#### T2.2 - Sensitivity Analysis (N) [4j]
- **Évaluation**: ⚠️ **BLOQUÉ**
- **Problème**: Impossible de tester N si aucune règle n'est découverte
- **Recommandation**: **REPORTER** après T0.1
- **Effort réel**: 3 jours après fix (déjà des résultats partiels)

**📉 Impact sur Phase 2**: Phase compromise, T2.1 déjà fait, T2.2 bloqué

---

### 🟡 PHASE 3: Validation à l'Échelle
**Statut global**: ⚠️ **INFRASTRUCTURE PRÊTE, EXECUTION BLOQUÉE**

#### T3.1 - Préparation Dataset Large [2j]
- **Évaluation**: ✅ **FAIT À 90%**
- **Statut**:
  - ✅ `generate_large_dataset.py` créé (370 lignes)
  - ✅ `generate_with_tgds.py` créé avec patterns intégrés (312 lignes)
  - ✅ Datasets générables: 1M, 5M, 10M tuples en quelques minutes
  - ⚠️ Datasets existants: dataset_1M.db, dataset_10M.db (possiblement corrompus)
- **Recommandation**: **Valider/Régénérer** les datasets (0.5j)
- **Crédit**: Déjà fait

#### T3.2 - Scalability Stress Test [5j]
- **Évaluation**: ⚠️ **INFRASTRUCTURE COMPLÈTE, TESTS IMPOSSIBLES**
- **Statut**:
  - ✅ `stress_test.py` créé (382 lignes) avec monitoring complet
  - ✅ `run_scalability_tests.py` créé (381 lignes) - orchestration 4 phases
  - ✅ `monitor_resources.py` créé (312 lignes) - CPU/RAM/Disk tracking
  - ✅ `visualize_scalability.py` créé (315 lignes) - 5 PNG graphs
  - ✅ `generate_tikz_scalability.py` créé (605 lignes) - LaTeX output
  - ❌ **IMPOSSIBLE À EXÉCUTER** - MATILDA retourne 0 règles
- **Total lignes**: 1,985 lignes d'infrastructure prête
- **Problème**: Le code est prêt mais inutilisable tant que T0.1 n'est pas résolu
- **Recommandation**: **EN ATTENTE** de T0.1
- **Effort réel après fix**: 2 jours de tests + analyse

#### T3.3 - Reproductibilité & Seeds [2j]
- **Évaluation**: 🟡 **NICE TO HAVE**
- **Statut**: Non commencé
- **Recommandation**: **BASSE PRIORITÉ** - faire après T0.1 et tests fonctionnels

**📊 Impact sur Phase 3**: Infrastructure excellente (1985 lignes), bloquée par bug critique

---

### 🟣 PHASE 4: Analyses Statistiques & Finalisation
**Statut global**: 🚫 **TOTALEMENT BLOQUÉ**

#### T4.1 - Re-run Global avec 5 Seeds [7j]
- **Évaluation**: ❌ **IMPOSSIBLE**
- **Problème**: Cannot run statistical analysis on 0 rules
- **Recommandation**: **ANNULER** jusqu'à résolution complète

#### T4.2 - Génération Tableaux Finaux [2j]
- **Évaluation**: ❌ **PRÉMATURÉ**
- **Recommandation**: **REPORTER** 

#### T4.3 - Documentation Finale [3j]
- **Évaluation**: ✅ **PARTIELLEMENT FAIT**
- **Statut**:
  - ✅ Documentation extensive créée (>30 fichiers MD)
  - ⚠️ Trop fragmentée, besoin consolidation
- **Recommandation**: **CONSOLIDATION** (1j) après résolution bugs

---

## 🚨 TÂCHE CRITIQUE MANQUANTE

### **T0.1 - FIX MATILDA CORE BUG** [3-7 jours] 🔥
**PRIORITÉ**: 🔴🔴🔴 **BLOQUANT ABSOLU**

**Problème identifié**:
```
Input: Bupa.db (345 tuples, 9 tables)
Initialization: ✅ 426 graph nodes, 468 JIA entries
Traversal DFS: ❌ 0 rules in 0.3s
Expected: ~50-200 rules in 30-120s
```

**Hypothèses**:
1. `next_node_test()` rejette tous les nœuds initiaux
2. Le générateur Python ne yield pas (problème de flow)
3. Checks de minimalité trop stricts
4. Bug dans `check_table_occurrences()` ou `check_minimal_candidate_rule()`

**Actions requises**:
1. **Debug intensif** du traversal (2j)
   - Ajouter logging détaillé dans graph_traversal.py
   - Tracer chaque étape: nœud testé → pourquoi rejeté
   - Identifier le filtre qui bloque tout
   
2. **Tests unitaires** sur next_node_test (1j)
   - Tester avec graphe simplifié (2-3 nœuds)
   - Valider chaque condition séparément
   
3. **Validation avec dataset connu** (1j)
   - Utiliser un dataset où MATILDA a déjà fonctionné
   - Comparer comportement avant/après modifications récentes
   
4. **Fix + validation** (1-2j)
   - Appliquer correctif
   - Tester sur Bupa, Company, autres datasets
   - Valider que les résultats ont du sens

**Livrables**:
- ✅ MATILDA découvre des règles (>0)
- ✅ Temps d'exécution cohérent (>10s pour petits datasets)
- ✅ Tests unitaires du traversal
- ✅ Documentation du bug + fix

**Risque**: Si non résolu → **TOUT LE PLAN ÉCHOUE**

---

## 📊 RÉVISION DU GRAPHE DE DÉPENDANCES

### Graphe RÉEL (avec T0.1):

```
T0.1 (FIX CORE BUG) ← 🔥 CRITIQUE
  ↓
T1.1 (Nettoyage) ← facilite debug
  ↓
T1.2 (Validation) ← maintenant possible
  ↓
T1.3 (P/R finalization)
  ↓
[T2.1 CANCELLED - déjà fait]
  ↓
T2.2 (Sensitivity N)
  ↓
T3.1 (DÉJÀ FAIT ✅) 
  ↓
T3.2 (Stress Tests) ← infrastructure prête
  ↓
T3.3 (Seeds - optionnel)
  ↓
T4.1 (Statistical re-runs)
  ↓
T4.2 (Tables)
  ↓
T4.3 (Doc consolidation)
```

### Chemin Critique RÉVISÉ:
**T0.1 (FIX) → T1.1 → T1.2 → T1.3 → T2.2 → T3.2 → T4.1 → T4.2**

---

## ⏱️ EFFORT ESTIMÉ RÉVISÉ

| Phase | Tâches | Estimation Originale | Estimation Réaliste |
|-------|--------|---------------------|---------------------|
| **T0.1 (NOUVEAU)** | Fix core bug | - | **3-7 jours** 🔥 |
| Phase 1 | 3 tâches | 7j | **4j** (après fix) |
| Phase 2 | 2 tâches | 9j | **3j** (T2.1 cancelled) |
| Phase 3 | 3 tâches | 9j | **3j** (infrastructure prête) |
| Phase 4 | 3 tâches | 12j | **10j** |
| **TOTAL** | **11+1** | **37j** | **27-31j** (avec fix) |

**Délai révisé**: 5-6 semaines (vs 7-8 semaines originales)

---

## 🎯 PLAN D'ACTION IMMÉDIAT

### Sprint 0 (URGENT - 3-7 jours)
1. ✅ **T0.1.1** - Debug traversal avec logging détaillé
2. ✅ **T0.1.2** - Identifier pourquoi 0 règles
3. ✅ **T0.1.3** - Fix + tests unitaires
4. ✅ **T0.1.4** - Validation sur 3 datasets

### Sprint 1 (Après fix - 1 semaine)
1. T1.1 - Nettoyage (1j)
2. T1.2 - Validation métriques (2j)
3. T1.3 - P/R finalization (1j)
4. Documentation heuristiques existantes (1j)

### Sprint 2 (2 semaines)
1. T2.2 - Sensitivity Analysis N (3j)
2. T3.2 - Stress tests 1M/5M/10M (4j)
3. Analyse résultats + optimisations (3j)

### Sprint 3 (2 semaines)
1. T4.1 - Re-run statistical (7j)
2. T4.2 - Tables finaux (2j)
3. T4.3 - Doc consolidation (1j)

---

## ⚠️ RISQUES CRITIQUES

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **T0.1 prend >7 jours** | 🟠 40% | 🔴 FATAL | Envisager rollback code, chercher version stable |
| **Bug non fixable** | 🟡 20% | 🔴 FATAL | Utiliser datasets où MATILDA fonctionnait avant |
| Stress test révèle nouveaux bugs | 🟢 60% | 🟠 Moyen | Prévoir buffer 3-5j |
| Re-run x5 >7 jours | 🟢 30% | 🟡 Faible | Paralléliser |

---

## ✅ POINTS POSITIFS

1. **Infrastructure scalabilité**: COMPLÈTE (1985 lignes) ✅
2. **Heuristiques**: Déjà implémentées (A*, BFS, DFS) ✅
3. **Dataset generators**: Fonctionnels ✅
4. **Monitoring**: CPU/RAM/Disk tracking ready ✅
5. **Visualizations**: PNG + TikZ/LaTeX ready ✅
6. **Baselines**: AMIE3, AnyBurl, Spider, Popper intégrés ✅

**Le travail est fait à ~40% - il manque juste le cœur du système qui fonctionne!**

---

## 🎓 IMPACT THÈSE

### Critique pour défense:
- ❌ **T0.1 (Fix)** - BLOQUANT ABSOLU
- 🔴 **T3.2 (Scalability)** - Claim principal "at scale" 
- 🔴 **T4.1 (Statistical)** - Robustesse scientifique
- 🟠 **T1.3 (P/R)** - Validation qualitative

### Peut être sacrifié si temps:
- 🟡 T3.3 (Reproductibilité) - Nice to have
- 🟡 T2.2 (Sensitivity) - Si résultats déjà convaincants
- 🟡 Documentation exhaustive - Minimum viable suffit

---

## 🔮 RECOMMANDATION FINALE

### Option A: FIX RAPIDE (Recommandé)
**Si T0.1 résolu en 3-5j** → Plan viable, livrable en 5-6 semaines

### Option B: ROLLBACK
**Si T0.1 >7j** → Chercher version MATILDA stable antérieure, sacrifier récentes optimizations

### Option C: PIVOT
**Si T0.1 non fixable** → Documenter infrastructure, focus sur baselines, expliquer limitations

---

## 📈 PROBABILITÉ DE SUCCÈS

- **Avec fix rapide (3-5j)**: 🟢 **85%** de compléter le plan
- **Avec fix long (5-7j)**: 🟠 **60%** de compléter le plan
- **Sans fix**: 🔴 **10%** - plan compromise, pivot nécessaire

**Conclusion**: Le plan est excellent MAIS totalement dépendant de la résolution de T0.1 dans les 7 prochains jours.
