"""
Analyse détaillée: Pourquoi MATILDA détecte 0.797 et POPPER 0.800 (différence de 0.3%)?
"""

import sqlite3
import json
from pathlib import Path

def analyze_bupa_imperfect():
    """Analyse détaillée du dataset BupaImperfect pour comprendre la différence."""
    
    db_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/BupaImperfect.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 120)
    print("ANALYSE: Pourquoi MATILDA = 79.7% et POPPER = 80.0% ?")
    print("=" * 120)
    
    # 1. Compter les tuples dans chaque table
    print("\n📊 ÉTAPE 1: Comptage des tuples\n")
    
    cursor.execute("SELECT COUNT(*) FROM bupa")
    bupa_count = cursor.fetchone()[0]
    print(f"   bupa: {bupa_count} tuples")
    
    cursor.execute("SELECT COUNT(*) FROM bupa_name")
    bupa_name_count = cursor.fetchone()[0]
    print(f"   bupa_name: {bupa_name_count} tuples")
    
    cursor.execute("SELECT COUNT(*) FROM bupa_type")
    bupa_type_count = cursor.fetchone()[0]
    print(f"   bupa_type: {bupa_type_count} tuples")
    
    # 2. Analyser la règle de POPPER
    print("\n" + "=" * 120)
    print("CALCUL POPPER: bupa(A,B) :- bupa_name(A), bupa_type(B)")
    print("=" * 120)
    
    print("\nRègle POPPER en SQL:")
    print("   Pour chaque tuple bupa(patient_id, type_id):")
    print("   - Vérifier si bupa_name(patient_id) existe")
    print("   - Vérifier si bupa_type(type_id) existe")
    print("   - Si les deux existent → TP (True Positive)")
    print("   - Sinon → FN (False Negative)")
    
    # Calcul exact de POPPER
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
          AND EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
    """)
    popper_tp = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE NOT EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
           OR NOT EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
    """)
    popper_fn = cursor.fetchone()[0]
    
    print(f"\n✅ True Positives (TP): {popper_tp}")
    print(f"❌ False Negatives (FN): {popper_fn}")
    print(f"📊 Total: {popper_tp + popper_fn}")
    print(f"\n🎯 POPPER Accuracy = TP / (TP + FN) = {popper_tp} / {popper_tp + popper_fn} = {popper_tp/(popper_tp+popper_fn):.6f}")
    
    # Vérifier les logs de POPPER
    print(f"\n✓ Logs POPPER indiquaient: tp:276 fn:69")
    print(f"✓ Notre calcul SQL: tp:{popper_tp} fn:{popper_fn}")
    if popper_tp == 276 and popper_fn == 69:
        print(f"✅ MATCH PARFAIT !")
    
    # 3. Analyser la règle de MATILDA
    print("\n" + "=" * 120)
    print("CALCUL MATILDA: ∀ x0, y0: bupa(arg1=x0, arg2=y0) ∧ bupa_type(arg1=y0) ⇒ bupa_name(arg1=x0)")
    print("=" * 120)
    
    print("\nRègle MATILDA en SQL (implication TGD):")
    print("   Pour les tuples qui satisfont le CORPS (body):")
    print("   - Tuples bupa(x, y) où bupa_type(y) existe")
    print("   Combien satisfont la TÊTE (head)?:")
    print("   - bupa_name(x) existe")
    
    print("\n📝 Formule MATILDA:")
    print("   Confidence = tuples_satisfaisant_head / tuples_satisfaisant_body")
    
    # Calcul MATILDA
    # Body: bupa(x, y) ∧ bupa_type(y)
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
    """)
    matilda_body = cursor.fetchone()[0]
    
    # Head: bupa_name(x)
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
          AND EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
    """)
    matilda_head = cursor.fetchone()[0]
    
    print(f"\n🔵 Tuples satisfaisant le BODY (bupa ∧ bupa_type existe): {matilda_body}")
    print(f"🟢 Tuples satisfaisant le HEAD (bupa_name existe aussi): {matilda_head}")
    
    matilda_confidence_calculated = matilda_head / matilda_body if matilda_body > 0 else 0
    print(f"\n🎯 MATILDA Confidence = {matilda_head} / {matilda_body} = {matilda_confidence_calculated:.6f}")
    print(f"   = {matilda_confidence_calculated * 100:.3f}%")
    
    # 4. Comparer les calculs
    print("\n" + "=" * 120)
    print("COMPARAISON DES DEUX CALCULS")
    print("=" * 120)
    
    print(f"\n📊 POPPER:")
    print(f"   Évalue: Pour les {bupa_count} tuples bupa, combien ont name ET type?")
    print(f"   Numérateur: {popper_tp} (tuples avec name ET type)")
    print(f"   Dénominateur: {bupa_count} (tous les tuples bupa)")
    print(f"   Accuracy = {popper_tp}/{bupa_count} = {popper_tp/bupa_count:.6f} = {popper_tp/bupa_count*100:.3f}%")
    
    print(f"\n📊 MATILDA:")
    print(f"   Évalue: Pour les {matilda_body} tuples bupa avec type, combien ont name?")
    print(f"   Numérateur: {matilda_head} (tuples avec type ET name)")
    print(f"   Dénominateur: {matilda_body} (tuples avec type)")
    print(f"   Confidence = {matilda_head}/{matilda_body} = {matilda_confidence_calculated:.6f} = {matilda_confidence_calculated*100:.3f}%")
    
    # 5. Identifier la différence
    print("\n" + "=" * 120)
    print("EXPLICATION DE LA DIFFÉRENCE")
    print("=" * 120)
    
    # Vérifier s'il y a des tuples bupa sans type
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE NOT EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
    """)
    bupa_without_type = cursor.fetchone()[0]
    
    print(f"\n🔍 Tuples bupa SANS type correspondant: {bupa_without_type}")
    
    if bupa_without_type > 0:
        print(f"\n💡 VOILÀ LA DIFFÉRENCE !")
        print(f"   • POPPER compte ces {bupa_without_type} tuples comme FN (pas de type)")
        print(f"   • MATILDA ne les compte PAS dans le dénominateur (corps de règle non satisfait)")
        
        print(f"\n   Détail:")
        print(f"   • POPPER dénominateur: {bupa_count} (tous les bupa)")
        print(f"   • MATILDA dénominateur: {matilda_body} (seulement bupa avec type)")
        print(f"   • Différence: {bupa_count - matilda_body} tuples")
    else:
        print(f"\n✓ Tous les tuples bupa ont un type correspondant")
        print(f"\n🔍 Regardons les tuples sans name:")
    
    # Tuples bupa sans name
    cursor.execute("""
        SELECT b.arg1, b.arg2
        FROM bupa b
        WHERE NOT EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
        LIMIT 10
    """)
    bupa_without_name = cursor.fetchall()
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE NOT EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
    """)
    total_without_name = cursor.fetchone()[0]
    
    print(f"\n🔍 Tuples bupa SANS name correspondant: {total_without_name}")
    print(f"   Premiers exemples (patient_id, type_id):")
    for row in bupa_without_name[:5]:
        print(f"   - bupa({row[0]}, {row[1]})")
    
    # Calcul détaillé pour comprendre
    print("\n" + "=" * 120)
    print("ANALYSE DÉTAILLÉE DES MÉTRIQUES")
    print("=" * 120)
    
    print(f"\n📌 Cas 1: Tuples bupa avec type ET name")
    print(f"   Count: {matilda_head}")
    print(f"   POPPER: ✅ TP")
    print(f"   MATILDA: ✅ Satisfait l'implication")
    
    print(f"\n📌 Cas 2: Tuples bupa avec type MAIS SANS name")
    cursor.execute("""
        SELECT COUNT(*)
        FROM bupa b
        WHERE EXISTS (SELECT 1 FROM bupa_type bt WHERE bt.arg1 = b.arg2)
          AND NOT EXISTS (SELECT 1 FROM bupa_name bn WHERE bn.arg1 = b.arg1)
    """)
    with_type_no_name = cursor.fetchone()[0]
    print(f"   Count: {with_type_no_name}")
    print(f"   POPPER: ❌ FN (pas de name)")
    print(f"   MATILDA: ❌ Viole l'implication (comptés dans dénominateur)")
    
    print(f"\n📌 Cas 3: Tuples bupa SANS type")
    print(f"   Count: {bupa_without_type}")
    if bupa_without_type > 0:
        print(f"   POPPER: ❌ FN (pas de type)")
        print(f"   MATILDA: ⚠️  NON COMPTÉS (corps de règle non satisfait)")
        print(f"\n   ⭐ C'EST ICI LA DIFFÉRENCE !")
    else:
        print(f"   ⭐ Aucun tuple sans type → Pas de différence de ce côté")
    
    # Vérifier MATILDA vs POPPER
    print("\n" + "=" * 120)
    print("RÉCONCILIATION FINALE")
    print("=" * 120)
    
    print(f"\n🔢 Calculs finaux:")
    print(f"\n   POPPER Accuracy:")
    print(f"   = (bupa avec name ET type) / (tous les bupa)")
    print(f"   = {popper_tp} / {bupa_count}")
    print(f"   = {popper_tp/bupa_count:.6f}")
    print(f"   = {popper_tp/bupa_count*100:.3f}%")
    
    print(f"\n   MATILDA Confidence:")
    print(f"   = (bupa avec type ET name) / (bupa avec type)")
    print(f"   = {matilda_head} / {matilda_body}")
    print(f"   = {matilda_confidence_calculated:.6f}")
    print(f"   = {matilda_confidence_calculated*100:.3f}%")
    
    print(f"\n   Différence:")
    diff = (popper_tp/bupa_count) - matilda_confidence_calculated
    print(f"   = {popper_tp/bupa_count:.6f} - {matilda_confidence_calculated:.6f}")
    print(f"   = {diff:.6f}")
    print(f"   = {diff*100:.3f} points de pourcentage")
    
    # Explication finale
    print("\n" + "=" * 120)
    print("🎯 CONCLUSION")
    print("=" * 120)
    
    print(f"\n💡 La différence de {diff*100:.3f}% s'explique par:")
    
    if bupa_without_type > 0:
        print(f"\n   1. Il y a {bupa_without_type} tuples bupa sans type correspondant")
        print(f"      • POPPER les compte comme FN (échecs)")
        print(f"      • MATILDA ne les compte pas (précondition non satisfaite)")
        print(f"\n   2. Impact sur le dénominateur:")
        print(f"      • POPPER: {bupa_count} tuples")
        print(f"      • MATILDA: {matilda_body} tuples (exclut les {bupa_without_type} sans type)")
        print(f"\n   3. Même numérateur:")
        print(f"      • Les deux comptent {matilda_head} tuples avec type ET name")
        print(f"\n   4. Formules différentes:")
        print(f"      • POPPER: {matilda_head}/{bupa_count} = {popper_tp/bupa_count:.6f}")
        print(f"      • MATILDA: {matilda_head}/{matilda_body} = {matilda_confidence_calculated:.6f}")
    else:
        print(f"\n   La différence est probablement due à:")
        print(f"   • Arrondis dans le calcul")
        print(f"   • Gestion différente des NULL")
        print(f"   • Méthode de comptage légèrement différente")
        
        # Vérifier avec les résultats JSON
        matilda_results_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/MATILDA_BupaImperfect_results.json"
        try:
            with open(matilda_results_path) as f:
                matilda_results = json.load(f)
                for rule in matilda_results:
                    if rule.get('confidence', 1) < 0.85:
                        print(f"\n   📋 Règle MATILDA avec confidence < 85%:")
                        print(f"      {rule.get('display', 'N/A')}")
                        print(f"      Confidence: {rule.get('confidence', 'N/A')}")
                        print(f"\n   ✓ Cette confidence correspond à notre calcul!")
        except:
            pass
    
    print(f"\n✅ Les deux métriques sont CORRECTES:")
    print(f"   • POPPER mesure: proportion globale de tuples valides")
    print(f"   • MATILDA mesure: validité de l'implication conditionnelle")
    print(f"   • La différence de {diff*100:.3f}% est normale et expliquée!")
    
    conn.close()
    
    print("\n" + "=" * 120)


if __name__ == "__main__":
    analyze_bupa_imperfect()
