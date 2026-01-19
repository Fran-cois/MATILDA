"""
Create an imperfect dataset for testing MATILDA metrics.
This dataset will have incomplete dependencies and violations to test
that metrics are not always 1.0.
"""

import sqlite3
import os

# Create database path
db_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/ImperfectTest.db"
tsv_dir = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/ImperfectTest/tsv"

# Create directories
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(tsv_dir, exist_ok=True)

# Remove existing database
if os.path.exists(db_path):
    os.remove(db_path)

# Create connection
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Creating tables...")

# Create simple tables similar to Bupa format
# person(id, name_id, age_id) - with violations
# person_name(id, value) - 2 columns required
# person_age(id, value) - 2 columns required

cursor.execute("""
    CREATE TABLE person (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT,
        arg3 TEXT
    )
""")

cursor.execute("""
    CREATE TABLE person_name (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

cursor.execute("""
    CREATE TABLE person_age (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

print("Inserting data...")

# Insert 100 persons with INTENTIONAL VIOLATIONS
persons_data = []
names_set = set()
ages_set = set()

for i in range(1, 101):
    person_id = f"P{i:03d}"
    
    # Names: most people have names, but 10 don't
    if i <= 90:
        name_id = f"N{(i % 30) + 1:03d}"  # 30 unique names, shared by multiple people
        names_set.add(name_id)
    else:
        name_id = None  # 10 people without names (incompleteness)
    
    # Ages: with violations
    if i <= 60:
        # Normal case: each person has one age
        age_id = f"A{(i % 20) + 1:03d}"  # 20 unique ages
    elif i <= 80:
        # VIOLATION: Reference to non-existent ages
        age_id = f"A999"  # Invalid age reference
    else:
        # Missing age
        age_id = None
    
    if age_id:
        ages_set.add(age_id)
    
    persons_data.append((person_id, name_id, age_id))

cursor.executemany("INSERT INTO person VALUES (?, ?, ?)", persons_data)

# Insert valid names (with dummy second column)
for name in sorted(names_set):
    if name and name != "A999":  # Don't insert the invalid one
        cursor.execute("INSERT INTO person_name VALUES (?, ?)", (name, f"value_{name}"))

# Insert valid ages (only first 20, not A999, with dummy second column)
for age in sorted([a for a in ages_set if a and a != "A999"])[:20]:
    cursor.execute("INSERT INTO person_age VALUES (?, ?)", (age, f"value_{age}"))

print(f"Inserted {len(persons_data)} persons")
print(f"Inserted {len(names_set)} unique names")
print(f"Inserted 20 unique ages")

conn.commit()

# Create TSV files for triple format
print("\nCreating TSV files...")

with open(os.path.join(tsv_dir, "ImperfectTest.tsv"), "w") as f:
    for person_id, name_id, age_id in persons_data:
        if name_id:
            f.write(f"person\targ1\tperson_name\tperson\targ2\t\"{name_id}\"\n")
        if age_id:
            f.write(f"person\targ1\tperson_name\tperson\targ3\t\"{age_id}\"\n")
            f.write(f"person\targ3\tperson_age\tperson\targ3\t\"{age_id}\"\n")
    
    for name in sorted(names_set):
        if name and name != "A999":
            f.write(f"person_name\targ1\tperson_name\tperson_name\targ1\t\"{name}\"\n")
    
    for age in sorted([a for a in ages_set if a and a != "A999"])[:20]:
        f.write(f"person_age\targ1\tperson_age\tperson_age\targ1\t\"{age}\"\n")

conn.close()

print(f"\nDatabase created: {db_path}")
print(f"TSV files created in: {tsv_dir}")

# Print statistics about violations
valid_name_refs = sum(1 for _, n, _ in persons_data if n is not None and n in names_set and n != "A999")
invalid_name_refs = sum(1 for _, n, _ in persons_data if n is None or (n and n not in names_set and n != "A999"))

valid_age_refs = sum(1 for _, _, a in persons_data if a is not None and a != "A999")
invalid_age_refs = sum(1 for _, _, a in persons_data if a == "A999")
missing_age_refs = sum(1 for _, _, a in persons_data if a is None)

print("\nDataset Statistics:")
print(f"- Total persons: {len(persons_data)}")
print(f"  - With valid names: {valid_name_refs} (expected: 90)")
print(f"  - Without names: {invalid_name_refs} (expected: 10)")
print(f"- Name references:")
print(f"  - Valid: {valid_name_refs}/{len(persons_data)} = {valid_name_refs/len(persons_data):.2%}")
print(f"  - Missing: {invalid_name_refs}/{len(persons_data)} = {invalid_name_refs/len(persons_data):.2%}")
print(f"- Age references:")
print(f"  - Valid: {valid_age_refs}/{len(persons_data)} = {valid_age_refs/len(persons_data):.2%}")
print(f"  - Invalid (A999): {invalid_age_refs}/{len(persons_data)} = {invalid_age_refs/len(persons_data):.2%}")
print(f"  - Missing: {missing_age_refs}/{len(persons_data)} = {missing_age_refs/len(persons_data):.2%}")

print("\nExpected metrics:")
print("• person(arg2=x) => person_name(arg1=x): confidence ≈ 90%")
print("• person(arg3=x) => person_age(arg1=x): confidence ≈ 60%")
print("These should result in metrics < 1.0 ✓")

