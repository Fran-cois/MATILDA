# Calcul des Métriques MATILDA - Quick Reference

## Fichiers Créés (2026-01-14)

### Scripts Python (3 fichiers)
- ✅ `compute_spider_metrics.py` (18K) - Métriques pour Spider (IND)
- ✅ `compute_popper_metrics.py` (19K) - Métriques pour Popper/ILP (Horn/TGD)  
- ✅ `compute_all_metrics.py` (9.2K) - Script unifié avec auto-détection

### Documentation (6 fichiers)
- ✅ `METRICS_COMPLETE_GUIDE.md` (11K) - Guide global
- ✅ `SPIDER_METRICS_GUIDE.md` (4.4K) - Guide Spider
- ✅ `SPIDER_METRICS_README.md` (6.5K) - README Spider
- ✅ `POPPER_METRICS_GUIDE.md` (8.8K) - Guide Popper
- ✅ `POPPER_METRICS_README.md` (4.5K) - README Popper
- ✅ `POPPER_METRICS_SUMMARY.md` (6.7K) - Résumé technique Popper
- ✅ `FINAL_SUMMARY.md` (9.0K) - Récapitulatif complet

### Tests (1 fichier)
- ✅ `popper_Bupa_example_results.json` (1.8K) - 5 règles test (3 TGD, 2 Horn)

## Usage Rapide

```bash
# Spider
python compute_spider_metrics.py [fichier.json]

# Popper
python compute_popper_metrics.py [fichier.json]

# Tous (auto-détection)
python compute_all_metrics.py [--algorithm spider|popper|all]
```

## Métriques Calculées

| Métrique | Type | Description |
|----------|------|-------------|
| **correctness** | bool | Validité de la règle |
| **compatibility** | bool | Compatibilité des éléments |
| **support** | float | Proportion de tuples (0.0-1.0) |
| **confidence** | float | Précision de la règle (0.0-1.0) |

## Tests Réussis

- ✅ Spider: 10 règles, 100% valides
- ✅ Popper: 5 règles, 100% valides, support moy. 0.81, confidence moy. 0.86

## Documentation

Voir [METRICS_COMPLETE_GUIDE.md](METRICS_COMPLETE_GUIDE.md) pour le guide complet.

---

**Statut:** ✅ Complet et fonctionnel | **Date:** 2026-01-14
