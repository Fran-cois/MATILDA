# 🏗️ MATILDA CLI - Plan d'Implémentation

## 📐 Architecture

### Structure générale

```
cli.py
├── Configuration (Colors, paths)
├── Utilitaires (print_*, run_*)
├── Commandes (cmd_*)
│   ├── validate
│   ├── benchmark
│   ├── metrics
│   ├── test
│   ├── clean
│   ├── report
│   └── info
└── Main (parser, dispatch)
```

### Flux d'exécution

```
1. cli.py lancé
   ↓
2. ArgumentParser construit les sous-commandes
   ↓
3. Arguments parsés
   ↓
4. Dispatch vers cmd_<command>(args)
   ↓
5. cmd_* exécute les scripts appropriés
   ↓
6. Retour code de sortie (0=succès, 1=erreur)
```

---

## 🔧 Comment ajouter une nouvelle commande

### Template de commande

```python
def cmd_nouvelle_commande(args):
    """Description de la nouvelle commande"""
    print_header("TITRE DE LA COMMANDE")
    
    # 1. Valider les arguments
    if not args.required_arg:
        print_error("Argument requis manquant")
        return 1
    
    # 2. Construire le chemin du script
    script = SCRIPTS_DIR / "categorie" / "mon_script.py"
    
    # 3. Préparer les arguments du script
    script_args = []
    if args.option1:
        script_args.append('--option1')
    if args.option2:
        script_args.extend(['--option2', args.option2])
    
    # 4. Exécuter le script
    print_info(f"Exécution de {script.name}...")
    if run_python_script(script, script_args):
        print_success("Commande réussie")
        return 0
    else:
        print_error("Commande échouée")
        return 1
```

### Enregistrer la commande dans le parser

```python
# Dans main()
parser_nouvelle = subparsers.add_parser('nouvelle', 
                                        help='Description courte')
parser_nouvelle.add_argument('--option1', action='store_true',
                            help='Description option 1')
parser_nouvelle.add_argument('--option2', type=str,
                            help='Description option 2')
parser_nouvelle.set_defaults(func=cmd_nouvelle_commande)
```

### Exemple complet: Ajouter commande `analyze`

```python
# ========== COMMANDE: analyze ==========

def cmd_analyze(args):
    """Analyser les résultats et générer insights"""
    print_header("ANALYSE DES RÉSULTATS")
    
    if args.deep:
        script = SCRIPTS_DIR / "analytics" / "deep_analysis.py"
        print_info("Analyse approfondie...")
    else:
        script = SCRIPTS_DIR / "analytics" / "quick_analysis.py"
        print_info("Analyse rapide...")
    
    script_args = []
    if args.dataset:
        script_args.extend(['--dataset', args.dataset])
    if args.algorithm:
        script_args.extend(['--algorithm', args.algorithm])
    
    if run_python_script(script, script_args):
        print_success("Analyse terminée")
        
        # Post-traitement optionnel
        if args.visualize:
            viz_script = SCRIPTS_DIR / "analytics" / "visualize.py"
            print_info("Génération des visualisations...")
            run_python_script(viz_script)
        
        return 0
    else:
        print_error("Analyse échouée")
        return 1

# Dans main()
parser_analyze = subparsers.add_parser('analyze', 
                                       help='Analyser les résultats')
parser_analyze.add_argument('--dataset', type=str,
                           help='Dataset à analyser')
parser_analyze.add_argument('--algorithm', choices=['spider', 'popper', 'anyburl'],
                           help='Algorithme spécifique')
parser_analyze.add_argument('--deep', action='store_true',
                           help='Analyse approfondie')
parser_analyze.add_argument('--visualize', action='store_true',
                           help='Générer visualisations')
parser_analyze.set_defaults(func=cmd_analyze)
```

---

## 📝 Conventions de code

### Nommage

```python
# Fonctions de commande
def cmd_<nom_commande>(args):
    pass

# Utilitaires d'affichage
def print_<type>(text):
    pass

# Utilitaires d'exécution
def run_<type>_script(path, args):
    pass
```

### Messages utilisateur

```python
# Toujours utiliser les fonctions stylisées
print_header("TITRE")    # Pour les en-têtes de section
print_success("OK")      # Pour les succès
print_error("Erreur")    # Pour les erreurs
print_warning("Attn")    # Pour les avertissements
print_info("Info")       # Pour les informations
```

### Gestion des erreurs

```python
def cmd_example(args):
    try:
        # Code principal
        if not check_precondition():
            print_error("Précondition non satisfaite")
            return 1
        
        result = execute_main_logic()
        
        if result:
            print_success("Succès")
            return 0
        else:
            print_error("Échec")
            return 1
            
    except FileNotFoundError as e:
        print_error(f"Fichier non trouvé: {e}")
        return 1
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
```

---

## 🎯 Fonctionnalités à implémenter

### Phase 1: Commandes de base ✅

- [x] `validate` - Validation des métriques
- [x] `benchmark` - Lancer benchmarks
- [x] `metrics` - Calculer métriques
- [x] `test` - Lancer tests
- [x] `clean` - Nettoyer projet
- [x] `report` - Générer rapports
- [x] `info` - Informations projet

### Phase 2: Commandes analytiques (À venir)

#### `analyze` - Analyse des résultats

```bash
python cli.py analyze --dataset Bupa --algorithm spider
python cli.py analyze --deep --visualize
python cli.py analyze --compare spider popper anyburl
```

**Implémentation**:
- Créer `scripts/analytics/analyze_results.py`
- Statistiques descriptives sur les règles
- Comparaison entre algorithmes
- Génération de graphiques

#### `coverage` - Analyse de couverture

```bash
python cli.py coverage --dataset Bupa
python cli.py coverage --algorithm spider --detailed
python cli.py coverage --all
```

**Implémentation**:
- Utiliser `compute_coverage_metrics.py` existant
- Ajouter visualisations de couverture
- Rapport détaillé par table

#### `profile` - Profiling de performance

```bash
python cli.py profile --benchmark full
python cli.py profile --memory
python cli.py profile --time --algorithm spider
```

**Implémentation**:
- Créer `scripts/profiling/profile_benchmark.py`
- Intégrer cProfile ou memory_profiler
- Générer flamegraphs

### Phase 3: Commandes avancées

#### `experiment` - Gestion d'expériences

```bash
python cli.py experiment create --name exp1 --config config.yaml
python cli.py experiment run exp1
python cli.py experiment list
python cli.py experiment compare exp1 exp2
```

**Implémentation**:
- Créer système de tracking d'expériences
- Intégration avec MLflow
- Gestion des configurations

#### `optimize` - Optimisation des hyperparamètres

```bash
python cli.py optimize --algorithm spider --metric confidence
python cli.py optimize --grid-search
python cli.py optimize --bayesian --trials 100
```

**Implémentation**:
- Créer `scripts/optimization/hyperparameter_tuning.py`
- Intégrer Optuna ou Hyperopt
- Grid search, Random search, Bayesian optimization

#### `deploy` - Déploiement et export

```bash
python cli.py deploy --export-rules --format json
python cli.py deploy --create-api
python cli.py deploy --docker
```

**Implémentation**:
- Export des règles dans différents formats
- Génération d'API REST
- Dockerization

### Phase 4: Intégrations

#### `mlflow` - Intégration MLflow

```bash
python cli.py mlflow start
python cli.py mlflow log-experiment exp1
python cli.py mlflow compare
python cli.py mlflow ui
```

**Implémentation**:
- Wrapper autour de `mlflow_explorer.py`
- Log automatique des métriques
- Interface simplifiée

#### `notebook` - Génération de notebooks

```bash
python cli.py notebook create --template analysis
python cli.py notebook run analysis.ipynb
python cli.py notebook export --format html
```

**Implémentation**:
- Templates Jupyter pré-configurés
- Génération automatique d'analyses
- Export en différents formats

---

## 🔌 Extension du CLI

### Ajouter un plugin système

```python
# plugins/__init__.py
class CLIPlugin:
    """Classe de base pour plugins CLI"""
    
    @property
    def name(self):
        """Nom du plugin"""
        raise NotImplementedError
    
    def register_parser(self, subparsers):
        """Enregistrer le parser du plugin"""
        raise NotImplementedError
    
    def execute(self, args):
        """Exécuter le plugin"""
        raise NotImplementedError

# plugins/my_plugin.py
from plugins import CLIPlugin

class MyPlugin(CLIPlugin):
    @property
    def name(self):
        return "myplugin"
    
    def register_parser(self, subparsers):
        parser = subparsers.add_parser(self.name, help='Mon plugin')
        parser.add_argument('--option', help='Option')
        parser.set_defaults(func=self.execute)
    
    def execute(self, args):
        print(f"Plugin exécuté avec {args.option}")
        return 0

# Dans cli.py main()
# Charger les plugins
from plugins import discover_plugins
plugins = discover_plugins()
for plugin in plugins:
    plugin.register_parser(subparsers)
```

### Configuration externe

```yaml
# cli_config.yaml
commands:
  validate:
    default_algorithm: spider
    auto_save: true
  
  benchmark:
    default_runs: 5
    timeout: 3600
  
  test:
    default_coverage: true
    pytest_args: "-v --tb=short"

paths:
  scripts: ./scripts
  results: ./results
  logs: ./logs

logging:
  level: INFO
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

```python
# Dans cli.py
import yaml

def load_config():
    config_file = ROOT_DIR / "cli_config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f)
    return {}

CONFIG = load_config()

# Utiliser dans les commandes
def cmd_validate(args):
    default_algo = CONFIG.get('commands', {}).get('validate', {}).get('default_algorithm')
    algorithm = args.algorithm or default_algo
    # ...
```

---

## 🧪 Tests du CLI

### Structure des tests

```
tests/
├── test_cli.py              # Tests du CLI principal
├── test_cli_commands.py     # Tests des commandes
└── test_cli_utils.py        # Tests des utilitaires
```

### Template de test

```python
# tests/test_cli_commands.py
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Importer le CLI
sys.path.insert(0, str(Path(__file__).parent.parent))
from cli import cmd_validate, cmd_test, run_python_script

class TestCLICommands(unittest.TestCase):
    
    @patch('cli.run_python_script')
    def test_validate_auto(self, mock_run):
        """Test commande validate --auto"""
        mock_run.return_value = True
        
        args = MagicMock()
        args.auto = True
        args.interactive = False
        args.report = False
        args.algorithm = None
        args.output = None
        
        result = cmd_validate(args)
        
        self.assertEqual(result, 0)
        mock_run.assert_called_once()
    
    @patch('cli.run_python_script')
    def test_validate_algorithm_specific(self, mock_run):
        """Test validation algorithme spécifique"""
        mock_run.return_value = True
        
        args = MagicMock()
        args.auto = False
        args.interactive = False
        args.report = False
        args.algorithm = 'spider'
        args.output = None
        
        result = cmd_validate(args)
        
        self.assertEqual(result, 0)
        call_args = mock_run.call_args[0]
        self.assertIn('--algorithm', call_args[1])
        self.assertIn('spider', call_args[1])

if __name__ == '__main__':
    unittest.main()
```

### Tests d'intégration

```python
# tests/test_cli_integration.py
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CLI = ROOT / "cli.py"

def test_cli_help():
    """Test que --help fonctionne"""
    result = subprocess.run(
        [sys.executable, str(CLI), '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'MATILDA CLI' in result.stdout

def test_info_command():
    """Test commande info"""
    result = subprocess.run(
        [sys.executable, str(CLI), 'info'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'MATILDA' in result.stdout

def test_validate_auto():
    """Test validation automatique"""
    result = subprocess.run(
        [sys.executable, str(CLI), 'validate', '--auto'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

---

## 📊 Monitoring et Logging

### Ajout de logging détaillé

```python
import logging
from pathlib import Path
from datetime import datetime

# Configuration logging
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"cli_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('matilda.cli')

def cmd_validate(args):
    logger.info(f"Commande validate lancée avec args: {args}")
    # ...
    logger.info("Validation terminée avec succès")
```

### Métriques d'utilisation

```python
import json
from datetime import datetime

METRICS_FILE = ROOT_DIR / "cli_metrics.json"

def log_command_usage(command, args, duration, success):
    """Log l'utilisation des commandes"""
    metrics = []
    if METRICS_FILE.exists():
        with open(METRICS_FILE) as f:
            metrics = json.load(f)
    
    metrics.append({
        'timestamp': datetime.now().isoformat(),
        'command': command,
        'args': vars(args),
        'duration': duration,
        'success': success
    })
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

# Utiliser dans main()
import time
start = time.time()
result = args.func(args)
duration = time.time() - start
log_command_usage(args.command, args, duration, result == 0)
```

---

## 🔒 Sécurité et Validation

### Validation des entrées

```python
def validate_path(path_str):
    """Valide qu'un chemin est sûr"""
    path = Path(path_str).resolve()
    
    # Vérifier que le chemin est dans le projet
    if not str(path).startswith(str(ROOT_DIR)):
        raise ValueError(f"Chemin invalide: {path}")
    
    return path

def validate_algorithm(algo):
    """Valide le nom d'algorithme"""
    valid = ['spider', 'popper', 'anyburl', 'amie3']
    if algo not in valid:
        raise ValueError(f"Algorithme invalide: {algo}. Valides: {valid}")
    return algo
```

### Gestion des permissions

```python
def check_write_permission(directory):
    """Vérifie les permissions d'écriture"""
    if not os.access(directory, os.W_OK):
        print_error(f"Pas de permission d'écriture: {directory}")
        return False
    return True

def cmd_clean(args):
    if args.results:
        results_dir = ROOT_DIR / "results"
        if not check_write_permission(results_dir):
            return 1
        # ...
```

---

## 🚀 Déploiement et Distribution

### Créer un package installable

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='matilda-cli',
    version='1.0.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'matilda=cli:main',
        ],
    },
    install_requires=[
        # dépendances
    ],
)

# Installation
pip install -e .

# Utilisation
matilda validate --auto
matilda info --scripts
```

### Docker container avec CLI

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]

# Usage
docker build -t matilda-cli .
docker run matilda-cli validate --auto
docker run matilda-cli info
```

---

## 📈 Roadmap

### Version 1.0 (Actuelle) ✅
- Commandes de base (validate, benchmark, metrics, test, clean, report, info)
- Documentation complète
- Tests de base

### Version 1.1 (Prochain sprint)
- [ ] Commande `analyze`
- [ ] Commande `coverage` améliorée
- [ ] Intégration MLflow
- [ ] Tests d'intégration complets

### Version 1.2
- [ ] Système de plugins
- [ ] Configuration externe (YAML)
- [ ] Commande `experiment`
- [ ] Profiling avancé

### Version 2.0
- [ ] API REST
- [ ] Interface web
- [ ] Support multi-base de données
- [ ] Optimisation automatique

---

## 🤝 Contribution

### Checklist pour nouvelle commande

- [ ] Créer la fonction `cmd_<nom>(args)`
- [ ] Ajouter le parser dans `main()`
- [ ] Documenter dans `CLI_GUIDE.md`
- [ ] Créer tests unitaires
- [ ] Créer tests d'intégration
- [ ] Mettre à jour ce fichier (IMPLEMENTATION.md)
- [ ] Ajouter exemples d'utilisation

### Style de code

```python
# Suivre PEP 8
# Docstrings pour toutes les fonctions
# Type hints quand possible
# Commentaires explicatifs

def cmd_example(args) -> int:
    """
    Description courte de la commande.
    
    Args:
        args: Arguments parsés par argparse
        
    Returns:
        0 si succès, 1 si erreur
        
    Example:
        >>> cmd_example(args)
        0
    """
    pass
```

---

**Version**: 1.0.0  
**Dernière mise à jour**: Janvier 2026  
**Mainteneur**: MATILDA Project
