#!/usr/bin/env python3
"""
Large-scale dataset generator for MATILDA stress testing.

Generates synthetic databases with configurable size (rows, tables, complexity)
for scalability testing. Supports multiple generation strategies with proper
foreign key relationships.
"""

import argparse
import sqlite3
import random
import string
import time
from pathlib import Path
from typing import List, Tuple
import sys


class LargeDatasetGenerator:
    """Generate large-scale synthetic datasets for TGD discovery testing."""
    
    def __init__(self, db_path: str, seed: int = 42):
        """
        Initialize generator.
        
        :param db_path: Path to output SQLite database.
        :param seed: Random seed for reproducibility.
        """
        self.db_path = db_path
        self.seed = seed
        random.seed(seed)
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print(f"✓ Database saved: {self.db_path}")
    
    def generate_synthetic_schema(self, num_tables: int = 5, 
                                  cols_per_table: int = 5,
                                  with_relationships: bool = True) -> List[Tuple[str, List[str]]]:
        """
        Generate synthetic schema (tables and columns) with proper foreign keys.
        
        :param num_tables: Number of tables to create.
        :param cols_per_table: Number of columns per table (including id).
        :param with_relationships: Add foreign key constraints in schema.
        :return: List of (table_name, [column_definitions]) tuples.
        """
        schema = []
        for i in range(num_tables):
            table_name = f"Table{i+1}"
            columns = [f"id INTEGER PRIMARY KEY"]
            
            # Calculate regular columns vs FK columns
            num_fk_cols = 0
            if with_relationships and i > 0:
                # Reference 1-2 previous tables
                num_fk_cols = min(2, i)
            
            num_regular_cols = cols_per_table - 1 - num_fk_cols
            
            # Add regular data columns
            for j in range(num_regular_cols):
                col_name = f"col{j+1}"
                col_type = random.choice(["INTEGER", "TEXT", "REAL"])
                columns.append(f"{col_name} {col_type}")
            
            # Add foreign key columns (reference previous tables)
            if with_relationships and i > 0:
                for ref_idx in range(num_fk_cols):
                    ref_table = f"Table{ref_idx+1}"
                    fk_col_name = f"{ref_table.lower()}_id"
                    columns.append(f"{fk_col_name} INTEGER REFERENCES {ref_table}(id)")
            
            schema.append((table_name, columns))
        
        return schema
    
    def create_tables(self, schema: List[Tuple[str, List[str]]]):
        """
        Create tables in database.
        
        :param schema: List of (table_name, [columns]) tuples.
        """
        for table_name, columns in schema:
            columns_str = ", ".join(columns)
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
            self.cursor.execute(create_sql)
            print(f"  Created table: {table_name}")
        self.conn.commit()
    
    def populate_table(self, table_name: str, column_defs: List[str], num_rows: int,
                      foreign_keys: List[Tuple[str, int]] = None):
        """
        Populate table with synthetic data matching column types.
        
        :param table_name: Name of table to populate.
        :param column_defs: List of column definitions from schema.
        :param num_rows: Number of rows to insert.
        :param foreign_keys: List of (ref_table, max_id) for foreign key relationships.
        """
        print(f"  Populating {table_name} with {num_rows:,} rows...")
        
        # Parse column definitions (skip id column which is first)
        col_info = []
        for col_def in column_defs[1:]:
            parts = col_def.split()
            col_name = parts[0]
            col_type = parts[1].upper()
            is_fk = "REFERENCES" in col_def
            col_info.append((col_name, col_type, is_fk))
        
        # Batch insert for performance
        batch_size = 10000
        for batch_start in range(0, num_rows, batch_size):
            batch_end = min(batch_start + batch_size, num_rows)
            batch_data = []
            
            for row_id in range(batch_start + 1, batch_end + 1):
                values = [row_id]  # id column
                
                fk_idx = 0
                for col_name, col_type, is_fk in col_info:
                    if is_fk and foreign_keys and fk_idx < len(foreign_keys):
                        # Foreign key reference - must be valid
                        ref_table, max_id = foreign_keys[fk_idx]
                        # Ensure FK value exists in referenced table
                        values.append(random.randint(1, max_id))
                        fk_idx += 1
                    elif col_type == "INTEGER":
                        values.append(random.randint(1, 1000))
                    elif col_type == "TEXT":
                        values.append(self._random_string(5, 15))
                    elif col_type == "REAL":
                        values.append(round(random.uniform(0, 1000), 2))
                    else:
                        values.append(random.randint(1, 1000))  # Default fallback
                
                batch_data.append(values)
            
            # Insert batch
            placeholders = ", ".join(["?"] * len(values))
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            self.cursor.executemany(insert_sql, batch_data)
            
            if batch_end % 50000 == 0:
                print(f"    Progress: {batch_end:,}/{num_rows:,} rows")
                self.conn.commit()
        
        self.conn.commit()
        print(f"  ✓ Completed {table_name}: {num_rows:,} rows")
    
    def _random_string(self, min_len: int, max_len: int) -> str:
        """Generate random string."""
        length = random.randint(min_len, max_len)
        return ''.join(random.choices(string.ascii_letters, k=length))
    
    def generate_dataset(self, target_tuples: int = 1000000,
                        num_tables: int = 5,
                        cols_per_table: int = 5,
                        with_relationships: bool = True):
        """
        Generate complete large-scale dataset with proper foreign keys.
        
        :param target_tuples: Target total number of tuples (rows across all tables).
        :param num_tables: Number of tables.
        :param cols_per_table: Columns per table (including id).
        :param with_relationships: Create foreign key relationships between tables.
        """
        print(f"\n{'='*70}")
        print(f"🏗️  LARGE DATASET GENERATION")
        print(f"{'='*70}")
        print(f"Target tuples: {target_tuples:,}")
        print(f"Tables: {num_tables}")
        print(f"Columns per table: {cols_per_table}")
        print(f"Relationships: {with_relationships}")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        # Connect
        self.connect()
        
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        # Generate schema
        print("Step 1: Generating schema...")
        schema = self.generate_synthetic_schema(num_tables, cols_per_table, with_relationships)
        
        # Create tables
        print("\nStep 2: Creating tables...")
        self.create_tables(schema)
        
        # Distribute rows across tables
        rows_per_table = target_tuples // num_tables
        
        # Populate tables
        print(f"\nStep 3: Populating tables ({rows_per_table:,} rows each)...")
        table_max_ids = {}
        
        for idx, (table_name, column_defs) in enumerate(schema):
            # Build foreign keys from previous tables
            foreign_keys = None
            if with_relationships and idx > 0:
                # Reference 1-2 previous tables
                num_refs = min(2, idx)
                foreign_keys = []
                for ref_idx in range(num_refs):
                    ref_table = f"Table{ref_idx+1}"
                    ref_max_id = table_max_ids[ref_table]
                    foreign_keys.append((ref_table, ref_max_id))
            
            self.populate_table(
                table_name=table_name,
                column_defs=column_defs,
                num_rows=rows_per_table,
                foreign_keys=foreign_keys
            )
            
            table_max_ids[table_name] = rows_per_table
        
        # Close
        self.close()
        
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"✅ Dataset generation complete!")
        print(f"   Total tuples: {target_tuples:,}")
        print(f"   Time: {elapsed:.2f}s ({target_tuples/elapsed:.0f} tuples/s)")
        print(f"   Database: {self.db_path}")
        print(f"{'='*70}")
    
    def get_statistics(self):
        """Print database statistics."""
        self.connect()
        
        print(f"\n{'='*70}")
        print("📊 DATABASE STATISTICS")
        print(f"{'='*70}")
        
        # Get tables
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.cursor.fetchall()]
        
        total_rows = 0
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            total_rows += count
            print(f"  {table:<20} {count:>15,} rows")
        
        # Get database size
        import os
        db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        
        print(f"{'='*70}")
        print(f"  Total Tables:        {len(tables)}")
        print(f"  Total Tuples:        {total_rows:,}")
        print(f"  Database Size:       {db_size_mb:.2f} MB")
        print(f"{'='*70}")
        
        self.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate large-scale synthetic dataset for MATILDA stress testing.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1M tuple dataset (default)
  python scripts/utils/generate_large_dataset.py data/large_scale/dataset_1M.db
  
  # Generate 5M tuple dataset
  python scripts/utils/generate_large_dataset.py data/large_scale/dataset_5M.db --target-tuples 5000000
  
  # Generate 10M tuples, 10 tables, 8 columns each
  python scripts/utils/generate_large_dataset.py data/large_scale/dataset_10M.db \
    --target-tuples 10000000 --num-tables 10 --cols-per-table 8
  
  # Show statistics of existing database
  python scripts/utils/generate_large_dataset.py data/large_scale/dataset_1M.db --stats-only
        """
    )
    
    parser.add_argument('output', help='Output SQLite database path')
    parser.add_argument('--target-tuples', '-t', type=int, default=1000000,
                       help='Target number of tuples (default: 1,000,000)')
    parser.add_argument('--num-tables', '-T', type=int, default=5,
                       help='Number of tables (default: 5)')
    parser.add_argument('--cols-per-table', '-c', type=int, default=5,
                       help='Columns per table (default: 5)')
    parser.add_argument('--no-relationships', action='store_true',
                       help='Do not create foreign key relationships')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics of existing database')
    
    args = parser.parse_args()
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    generator = LargeDatasetGenerator(str(output_path), seed=args.seed)
    
    if args.stats_only:
        generator.get_statistics()
    else:
        generator.generate_dataset(
            target_tuples=args.target_tuples,
            num_tables=args.num_tables,
            cols_per_table=args.cols_per_table,
            with_relationships=not args.no_relationships
        )
        generator.get_statistics()


if __name__ == '__main__':
    main()
