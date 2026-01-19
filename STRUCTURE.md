# MATILDA - Structure du projet

## 📁 Organisation du repository

```
MATILDA/
├── config/                    # Fichiers de configuration
│   ├── benchmark_config.yaml
│   ├── config.yaml
│   └── config_spider_bupa.yaml
│
├── data/                      # Données et résultats
│   ├── results/              # Résultats d'expériences JSON
│   ├── db/                   # Bases de données
│   └── ...
│
├── docs/                      # Documentation complète
│   ├── benchmarks/           # Guides de benchmark
│   ├── metrics/              # Documentation des métriques
│   ├── guides/               # Guides d'utilisation
│   └── summaries/            # Résumés et rapports
│
├── logs/                      # Fichiers de log
│
├── scripts/                   # Scripts exécutables
│   ├── benchmarks/           # Scripts de benchmark
│   │   ├── run_benchmark.py
│   │   ├── run_bupa_experiments.py
│   │   ├── run_full_benchmark.py
│   │   └── run_spider_with_metrics.py
│   ├── metrics/              # Calcul et comparaison de métriques
│   │   ├── compute_all_metrics.py
│   │   ├── compute_*_metrics.py
│   │   └── compare_*.py
│   └── utils/                # Utilitaires divers
│       ├── generate_latex_table.py
│       ├── generate_statistics_report.py
│       └── ...
│
├── src/                       # Code source principal
│   ├── algorithms/           # Implémentations MATILDA, AMIE3, etc.
│   ├── database/             # Gestion base de données
│   ├── tests/                # Tests unitaires intégrés
│   └── utils/                # Utilitaires du code source
│
├── tests/                     # Tests de haut niveau
│   ├── test_coverage_simple.py
│   ├── test_latex_generation.py
│   ├── test_new_metrics.py
│   ├── test_statistics.py
│   └── ...
│
├── todo/                      # Planification et suivi
│   ├── main.md
│   └── gantt_plan.md
│
├── README.md                  # Documentation principale
├── requirements.txt           # Dépendances Python
└── run_complete_benchmark.sh  # Script principal de benchmark
```

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Exécuter un benchmark complet
```bash
./run_complete_benchmark.sh
```

### Calculer toutes les métriques
```bash
python scripts/metrics/compute_all_metrics.py
```

### Générer les tableaux LaTeX
```bash
python scripts/utils/generate_latex_table.py
```

## 📊 Documentation

- **Guides de benchmark** : `docs/BENCHMARK_README.md`, `docs/BENCHMARKING_QUICKSTART.md`
- **Documentation métriques** : `docs/METRICS_COMPLETE_GUIDE.md`
- **Résultats et analyses** : `docs/BENCHMARK_RESULTS_SUMMARY.md`
- **Quick reference** : `docs/QUICK_START.md`

## 🧪 Tests

Exécuter tous les tests :
```bash
pytest tests/
```

Tests unitaires du code source :
```bash
pytest src/tests/
```

## 📈 Structure des données

- **Configurations** : `config/*.yaml`
- **Résultats bruts** : `data/results/*.json`
- **Logs d'exécution** : `logs/*.log`
- **Résultats structurés** : `results/`

## 🔧 Maintenance

- **Nettoyage des caches** : `find . -name "__pycache__" -exec rm -rf {} +`
- **Structure à jour** : Janvier 2026
- **Version Python recommandée** : 3.8+

---

Pour plus de détails, consultez la documentation dans `docs/`.
