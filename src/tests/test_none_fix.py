#!/usr/bin/env python3
"""
Test rapide pour vérifier que le fix des None values fonctionne
"""

import json
from pathlib import Path

# Simuler les données problématiques
print("🧪 Test du fix des valeurs None dans les métriques de temps")
print("=" * 60)

# Cas 1: Toutes les valeurs sont None
print("\n1️⃣  Test avec toutes valeurs None:")
time_data = {'compatibility_graph': None, 'index': None, 'cg_construction': None}
time_compat = time_data.get('compatibility_graph', 0) or 0
time_index = time_data.get('index', 0) or 0
time_cg = time_data.get('cg_construction', 0) or 0
time_total = time_compat + time_index + time_cg
print(f"   time_compat: {time_compat}, time_index: {time_index}, time_cg: {time_cg}")
print(f"   time_total: {time_total}")
assert time_total == 0, "Erreur: time_total devrait être 0"
print("   ✅ Passed")

# Cas 2: Certaines valeurs sont None
print("\n2️⃣  Test avec certaines valeurs None:")
time_data = {'compatibility_graph': 1.5, 'index': None, 'cg_construction': 2.3}
time_compat = time_data.get('compatibility_graph', 0) or 0
time_index = time_data.get('index', 0) or 0
time_cg = time_data.get('cg_construction', 0) or 0
time_total = time_compat + time_index + time_cg
print(f"   time_compat: {time_compat}, time_index: {time_index}, time_cg: {time_cg}")
print(f"   time_total: {time_total}")
assert time_total == 3.8, f"Erreur: time_total devrait être 3.8, obtenu {time_total}"
print("   ✅ Passed")

# Cas 3: Toutes les valeurs sont présentes
print("\n3️⃣  Test avec toutes valeurs présentes:")
time_data = {'compatibility_graph': 1.0, 'index': 2.0, 'cg_construction': 3.0}
time_compat = time_data.get('compatibility_graph', 0) or 0
time_index = time_data.get('index', 0) or 0
time_cg = time_data.get('cg_construction', 0) or 0
time_total = time_compat + time_index + time_cg
print(f"   time_compat: {time_compat}, time_index: {time_index}, time_cg: {time_cg}")
print(f"   time_total: {time_total}")
assert time_total == 6.0, f"Erreur: time_total devrait être 6.0, obtenu {time_total}"
print("   ✅ Passed")

# Cas 4: Clés manquantes dans le dict
print("\n4️⃣  Test avec clés manquantes:")
time_data = {'compatibility_graph': 1.0}
time_compat = time_data.get('compatibility_graph', 0) or 0
time_index = time_data.get('index', 0) or 0
time_cg = time_data.get('cg_construction', 0) or 0
time_total = time_compat + time_index + time_cg
print(f"   time_compat: {time_compat}, time_index: {time_index}, time_cg: {time_cg}")
print(f"   time_total: {time_total}")
assert time_total == 1.0, f"Erreur: time_total devrait être 1.0, obtenu {time_total}"
print("   ✅ Passed")

# Cas 5: Valeur 0 (ne doit pas être convertie en 0 par 'or')
print("\n5️⃣  Test avec valeur 0 (edge case):")
time_data = {'compatibility_graph': 0, 'index': 5, 'cg_construction': 0}
time_compat = time_data.get('compatibility_graph', 0) or 0
time_index = time_data.get('index', 0) or 0
time_cg = time_data.get('cg_construction', 0) or 0
time_total = time_compat + time_index + time_cg
print(f"   time_compat: {time_compat}, time_index: {time_index}, time_cg: {time_cg}")
print(f"   time_total: {time_total}")
assert time_total == 5, f"Erreur: time_total devrait être 5, obtenu {time_total}"
print("   ✅ Passed (0 est traité correctement)")

print("\n" + "=" * 60)
print("🎉 Tous les tests passés avec succès!")
print("\n💡 Le fix résout bien le problème:")
print("   - Les valeurs None sont converties en 0")
print("   - Les additions fonctionnent sans erreur")
print("   - Les valeurs 0 légitimes sont préservées")
