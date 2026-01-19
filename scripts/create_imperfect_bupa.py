"""
Create an imperfect version of Bupa by introducing violations and missing data.
"""

import sqlite3
import shutil
import os

# Paths
original_db = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/Bupa.db"
imperfect_db = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/BupaImperfect.db"

# Copy the original database
print(f"Copying {original_db} to {imperfect_db}...")
shutil.copy2(original_db, imperfect_db)

# Connect to the imperfect database
conn = sqlite3.connect(imperfect_db)
cursor = conn.cursor()

# Disable foreign key constraints temporarily
cursor.execute("PRAGMA foreign_keys = OFF")

print("\nIntroducing imperfections...")

# 1. Delete some entries from bupa_type to create referential integrity violations
cursor.execute("DELETE FROM bupa_type WHERE arg1 = '1'")
deleted_type = cursor.rowcount
print(f"✓ Deleted {deleted_type} entry from bupa_type (creating violations)")

# 2. Delete some entries from bupa_name to create more violations  
cursor.execute("DELETE FROM bupa_name WHERE arg1 IN (SELECT arg1 FROM bupa_name LIMIT 5)")
deleted_names = cursor.rowcount
print(f"✓ Deleted {deleted_names} entries from bupa_name (creating violations)")

# 3. Update some bupa entries to point to non-existent records
cursor.execute("UPDATE bupa SET arg2 = '9' WHERE ROWID % 5 = 0")
updated_type = cursor.rowcount
print(f"✓ Updated {updated_type} entries in bupa to point to non-existent type (creating violations)")

# Commit changes
conn.commit()

# Get statistics
cursor.execute("SELECT COUNT(*) FROM bupa")
total_bupa = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM bupa_name")
total_names = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM bupa_type")
total_types = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM bupa b
    LEFT JOIN bupa_name bn ON b.arg1 = bn.arg1
    WHERE bn.arg1 IS NULL
""")
invalid_name_refs = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM bupa b
    LEFT JOIN bupa_type bt ON b.arg2 = bt.arg1
    WHERE bt.arg1 IS NULL
""")
invalid_type_refs = cursor.fetchone()[0]

conn.close()

print(f"\n✅ Imperfect database created: {imperfect_db}")
print(f"\nStatistics:")
print(f"- Total bupa records: {total_bupa}")
print(f"- Total bupa_name records: {total_names}")
print(f"- Total bupa_type records: {total_types}")
print(f"- Invalid name references: {invalid_name_refs} ({invalid_name_refs/total_bupa*100:.1f}%)")
print(f"- Invalid type references: {invalid_type_refs} ({invalid_type_refs/total_bupa*100:.1f}%)")

print(f"\nExpected behavior:")
print(f"• Rules involving name should have confidence ≈ {(total_bupa-invalid_name_refs)/total_bupa*100:.1f}%")
print(f"• Rules involving type should have confidence ≈ {(total_bupa-invalid_type_refs)/total_bupa*100:.1f}%")
print("These should result in metrics < 1.0 ✓")
