# 🚀 MATILDA CLI - Guide d'utilisation

## Installation

```bash
# Rendre le CLI exécutable
chmod +x cli.py

# Optionnel: créer un alias
alias matilda="python /path/to/MATILDA/cli.py"
```

## Commandes disponibles

### 📋 Aide générale

```bash
python cli.py --help
python cli.py <command> --help
```

---

## 🔍 validate - Validation des métriques

Valide la cohérence des métriques entre AMIE3, AnyBurl, Spider et Popper.

### Usage

```bash
# Validation automatique complète
python cli.py validate --auto

# Mode interactif
python cli.py validate --interactive

# Générer un rapport de validation
python cli.py validate --report

# Valider un algorithme spécifique
python cli.py validate --algorithm spider
python cli.py validate --algorithm popper
python cli.py validate --algorithm anyburl
python cli.py validate --algorithm amie3

# Spécifier fichier de sortie
python cli.py validate --report --output mon_rapport.json
```

### Exemple

```bash
$ python cli.py validate --auto

================================================================================
🚀 VALIDATION DES MÉTRIQUES
================================================================================

📊 Validation SPIDER (1 fichiers)
  Fichier: spider_Bupa_example_results.json
    ✅ Toutes les vérifications passées (6)

  Total vérifications : 21
  ✅ Réussies        : 21
  ❌ Échouées        : 0
  📊 Taux de succès  : 100.0%
```

---

## 🏃 benchmark - Lancer les benchmarks

Exécute les benchmarks MATILDA sur différents algorithmes.

### Usage

```bash
# Benchmark complet (tous algorithmes)
python cli.py benchmark --full

# Benchmark par algorithme
python cli.py benchmark --algorithm spider
python cli.py benchmark --algorithm bupa
python cli.py benchmark --algorithm all

# Benchmark par défaut
python cli.py benchmark
```

### Exemples

```bash
# Lancer benchmark Spider
python cli.py benchmark --algorithm spider

# Benchmark complet avec script shell
python cli.py benchmark --full
```

---

## 📊 metrics - Calculer les métriques

Calcule les métriques de performance pour les résultats d'algorithmes.

### Usage

```bash
# Calculer toutes les métriques
python cli.py metrics --all

# Métriques pour un algorithme spécifique
python cli.py metrics --algorithm spider
python cli.py metrics --algorithm popper
python cli.py metrics --algorithm anyburl
python cli.py metrics --algorithm amie3
python cli.py metrics --algorithm coverage

# Comparer les métriques entre algorithmes
python cli.py metrics --compare
```

### Exemples

```bash
# Calculer toutes les métriques
python cli.py metrics --all

# Comparer Spider vs Popper vs AnyBurl
python cli.py metrics --compare
```

---

## 🧪 test - Lancer les tests

Exécute les tests unitaires et d'intégration.

### Usage

```bash
# Tous les tests
python cli.py test --all

# Tests unitaires seulement
python cli.py test --unit

# Tests de validation des métriques
python cli.py test --validation

# Test d'un fichier spécifique
python cli.py test --file test_metrics_validation.py

# Avec couverture de code
python cli.py test --all --coverage
```

### Exemples

```bash
# Lancer tous les tests avec couverture
python cli.py test --all --coverage

# Tests de validation uniquement
python cli.py test --validation

# Test spécifique
python cli.py test --file test_latex_generation.py
```

---

## 🧹 clean - Nettoyer le projet

Supprime les fichiers temporaires et caches.

### Usage

```bash
# Nettoyer tout
python cli.py clean --all

# Caches Python uniquement
python cli.py clean --cache

# Fichiers log
python cli.py clean --logs

# Résultats (nécessite --force)
python cli.py clean --results --force

# Artefacts de build
python cli.py clean --build

# Forcer la suppression
python cli.py clean --all --force
```

### Exemples

```bash
# Nettoyage rapide (cache + build)
python cli.py clean --cache --build

# Nettoyage complet (ATTENTION: supprime tout)
python cli.py clean --all --force

# Nettoyer les logs avec confirmation
python cli.py clean --logs --force
```

---

## 📄 report - Générer rapports

Génère des rapports et tableaux pour publications.

### Usage

```bash
# Tous les rapports
python cli.py report --all

# Tableaux LaTeX
python cli.py report --latex

# Rapport statistique
python cli.py report --statistics

# Rapport de validation
python cli.py report --validation
```

### Exemples

```bash
# Générer tableaux LaTeX pour publication
python cli.py report --latex

# Rapport statistique complet
python cli.py report --statistics

# Générer tous les rapports
python cli.py report --all
```

---

## ℹ️ info - Informations projet

Affiche les informations sur la structure du projet.

### Usage

```bash
# Informations de base
python cli.py info

# Avec liste des scripts
python cli.py info --scripts

# Avec liste des résultats
python cli.py info --results

# Avec liste de la documentation
python cli.py info --docs

# Mode verbeux (détails complets)
python cli.py info --scripts --results --docs --verbose
```

### Exemple

```bash
$ python cli.py info --scripts --results

================================================================================
🚀 INFORMATIONS MATILDA
================================================================================

Projet: MATILDA
Racine: /path/to/MATILDA

📁 Structure:
  ✅ Scripts         : scripts              (14 items)
  ✅ Tests           : tests                (9 items)
  ✅ Documentation   : docs                 (40 items)

📜 Scripts disponibles:
  Benchmarks:
    • run_benchmark.py
    • run_spider_with_metrics.py
  
  Métriques:
    • compute_all_metrics.py
    • compare_matilda_benchmark.py
```

---

## 🔄 Workflows typiques

### Workflow 1: Développement quotidien

```bash
# 1. Nettoyer les caches
python cli.py clean --cache

# 2. Lancer les tests
python cli.py test --all

# 3. Valider les métriques
python cli.py validate --auto
```

### Workflow 2: Nouveau benchmark

```bash
# 1. Lancer le benchmark
python cli.py benchmark --algorithm spider

# 2. Calculer les métriques
python cli.py metrics --algorithm spider

# 3. Générer rapport
python cli.py report --statistics
```

### Workflow 3: Publication

```bash
# 1. Validation complète
python cli.py validate --report

# 2. Tests avec couverture
python cli.py test --all --coverage

# 3. Générer tous les rapports
python cli.py report --all

# 4. Tableaux LaTeX
python cli.py report --latex
```

### Workflow 4: Nettoyage complet

```bash
# 1. Nettoyer caches et build
python cli.py clean --cache --build

# 2. Supprimer les logs anciens
python cli.py clean --logs --force

# 3. Vérifier l'état
python cli.py info --scripts --results
```

---

## 💡 Astuces

### Créer un alias

Pour simplifier l'utilisation, créez un alias dans votre shell:

```bash
# Dans ~/.zshrc ou ~/.bashrc
alias matilda="python /path/to/MATILDA/cli.py"

# Puis utilisez:
matilda validate --auto
matilda test --all
matilda info --scripts
```

### Chaîner les commandes

```bash
# Nettoyer, tester, valider
python cli.py clean --cache && \
python cli.py test --all && \
python cli.py validate --auto
```

### Script de routine quotidienne

Créez un script `daily_check.sh`:

```bash
#!/bin/bash
echo "🔍 Routine quotidienne MATILDA"

python cli.py clean --cache
python cli.py test --validation
python cli.py validate --auto
python cli.py info --results

echo "✅ Routine terminée"
```

---

## 🎓 Pour la thèse

### Workflow pré-soumission

```bash
# 1. Validation complète
python cli.py validate --report

# 2. Tests exhaustifs
python cli.py test --all --coverage

# 3. Benchmark complet
python cli.py benchmark --full

# 4. Calculer toutes les métriques
python cli.py metrics --all

# 5. Générer rapports LaTeX
python cli.py report --latex

# 6. Statistiques
python cli.py report --statistics
```

### Vérification quotidienne thèse

```bash
# Vérifier que tout fonctionne
python cli.py test --validation && \
python cli.py validate --auto && \
python cli.py info --results
```

---

## 🚨 Dépannage

### Erreur "script non trouvé"

```bash
# Vérifier la structure
python cli.py info --scripts

# Vérifier que vous êtes à la racine
pwd  # Doit être dans le dossier MATILDA
```

### Erreur d'import

```bash
# Vérifier l'environnement Python
which python
python --version

# Installer les dépendances
pip install -r requirements.txt
```

### Permission refusée

```bash
# Rendre exécutable
chmod +x cli.py

# Ou utiliser avec python explicitement
python cli.py <command>
```

---

## 📚 Voir aussi

- `README.md` - Documentation principale
- `STRUCTURE.md` - Structure du projet
- `docs/` - Documentation détaillée
- `todo/gantt_plan.md` - Plan de développement

---

**Version**: 1.0.0  
**Dernière mise à jour**: Janvier 2026  
**Auteur**: MATILDA Project
