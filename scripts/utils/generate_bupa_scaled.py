#!/usr/bin/env python3
"""
Generate scaled Bupa-like datasets (100K, 500K, 1M tuples).

Maintains the same schema as original Bupa but with synthetic data.
Reduced complexity: only 3 tables with simple relationships.
"""

import argparse
import sqlite3
import random
import time
from pathlib import Path


class BupaScaledGenerator:
    """Generate Bupa-like datasets at scale."""
    
    # Bupa schema (simplified to 3 main tables for lower complexity)
    SCHEMA = {
        'patient': ['id INTEGER PRIMARY KEY', 'name TEXT'],
        'liver_test': ['id INTEGER PRIMARY KEY', 'patient_id INTEGER', 'mcv REAL', 'alkphos REAL', 'sgpt REAL', 'sgot REAL', 'gammagt REAL'],
        'diagnosis': ['id INTEGER PRIMARY KEY', 'patient_id INTEGER', 'drinks REAL', 'selector INTEGER']
    }
    
    def __init__(self, db_path: str, num_patients: int, seed: int = 42):
        """
        Initialize generator.
        
        :param db_path: Output database path
        :param num_patients: Number of patient records (scales all tables)
        :param seed: Random seed
        """
        self.db_path = db_path
        self.num_patients = num_patients
        self.seed = seed
        random.seed(seed)
        
    def generate(self):
        """Generate the complete database."""
        print(f"\n🔧 Generating Bupa-scaled dataset: {self.num_patients:,} patients")
        print(f"📁 Output: {self.db_path}")
        
        start_time = time.time()
        
        # Connect
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        print("\n📋 Creating tables...")
        for table_name, columns in self.SCHEMA.items():
            columns_str = ", ".join(columns)
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            cursor.execute(f"CREATE TABLE {table_name} ({columns_str})")
            print(f"  ✓ {table_name}")
        
        # Populate patients
        print(f"\n👥 Inserting {self.num_patients:,} patients...")
        patient_batch = []
        for i in range(1, self.num_patients + 1):
            name = f"Patient_{i:08d}"
            patient_batch.append((i, name))
            
            if len(patient_batch) >= 10000:
                cursor.executemany("INSERT INTO patient VALUES (?, ?)", patient_batch)
                patient_batch = []
                if i % 100000 == 0:
                    print(f"  Progress: {i:,}/{self.num_patients:,}")
        
        if patient_batch:
            cursor.executemany("INSERT INTO patient VALUES (?, ?)", patient_batch)
        conn.commit()
        
        # Populate liver tests (1 per patient)
        print(f"\n🧪 Inserting {self.num_patients:,} liver tests...")
        test_batch = []
        for i in range(1, self.num_patients + 1):
            test_batch.append((
                i,  # id
                i,  # patient_id (1:1 relationship)
                round(random.uniform(70, 110), 2),  # mcv
                round(random.uniform(20, 150), 2),  # alkphos
                round(random.uniform(5, 80), 2),    # sgpt
                round(random.uniform(10, 120), 2),  # sgot
                round(random.uniform(10, 200), 2)   # gammagt
            ))
            
            if len(test_batch) >= 10000:
                cursor.executemany(
                    "INSERT INTO liver_test VALUES (?, ?, ?, ?, ?, ?, ?)", 
                    test_batch
                )
                test_batch = []
                if i % 100000 == 0:
                    print(f"  Progress: {i:,}/{self.num_patients:,}")
        
        if test_batch:
            cursor.executemany(
                "INSERT INTO liver_test VALUES (?, ?, ?, ?, ?, ?, ?)", 
                test_batch
            )
        conn.commit()
        
        # Populate diagnoses (1 per patient)
        print(f"\n📊 Inserting {self.num_patients:,} diagnoses...")
        diag_batch = []
        for i in range(1, self.num_patients + 1):
            diag_batch.append((
                i,  # id
                i,  # patient_id (1:1 relationship)
                round(random.uniform(0, 10), 2),  # drinks
                random.randint(1, 2)  # selector
            ))
            
            if len(diag_batch) >= 10000:
                cursor.executemany(
                    "INSERT INTO diagnosis VALUES (?, ?, ?, ?)", 
                    diag_batch
                )
                diag_batch = []
                if i % 100000 == 0:
                    print(f"  Progress: {i:,}/{self.num_patients:,}")
        
        if diag_batch:
            cursor.executemany(
                "INSERT INTO diagnosis VALUES (?, ?, ?, ?)", 
                diag_batch
            )
        conn.commit()
        
        # Statistics
        print("\n📈 Database Statistics:")
        for table_name in self.SCHEMA.keys():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count:,} rows")
        
        # Close
        conn.close()
        
        # File size
        file_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Generation complete!")
        print(f"📦 Size: {file_size_mb:.1f} MB")
        print(f"⏱️  Time: {elapsed:.1f}s")
        print(f"⚡ Rate: {self.num_patients/elapsed:,.0f} patients/sec")


def main():
    parser = argparse.ArgumentParser(
        description="Generate scaled Bupa-like datasets"
    )
    parser.add_argument(
        '--size',
        type=str,
        choices=['1k', '5k', '10k', '50k', '100k'],
        required=True,
        help="Dataset size (1k, 5k, 10k, 50k, or 100k patients)"
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/large_scale',
        help="Output directory"
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help="Random seed"
    )
    
    args = parser.parse_args()
    
    # Parse size
    size_map = {
        '1k': 1000,
        '5k': 5000,
        '10k': 10000,
        '50k': 50000,
        '100k': 100000
    }
    num_patients = size_map[args.size]
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate
    db_path = output_dir / f"Bupa_{args.size}.db"
    generator = BupaScaledGenerator(str(db_path), num_patients, args.seed)
    generator.generate()


if __name__ == "__main__":
    main()
