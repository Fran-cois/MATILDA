#!/usr/bin/env python3
"""
Debug script to check why MATILDA finds 0 rules.
Tests the initialization phase and constraint graph building.
"""

import sys
from pathlib import Path

# Add both src and root to path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path / 'src'))
sys.path.insert(0, str(root_path))

from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.constraint_graph import Attribute
from tqdm import tqdm


def debug_initialization(db_path: str):
    """Debug MATILDA initialization phase."""
    
    print(f"\n{'='*70}")
    print("🔍 DEBUGGING MATILDA INITIALIZATION")
    print(f"{'='*70}\n")
    
    # Connect to database
    print(f"Connecting to: {db_path}")
    db = AlchemyUtility(f"sqlite:///{db_path}")
    
    # Get tables
    tables = db.get_table_names()
    print(f"✓ Found {len(tables)} tables: {tables}")
    
    # Generate attributes
    print("\n📋 Generating attributes...")
    attributes = Attribute.generate_attributes(db)
    print(f"✓ Generated {len(attributes)} attributes:")
    for attr in attributes[:10]:  # Show first 10
        print(f"   - {attr.table}.{attr.name}")
    if len(attributes) > 10:
        print(f"   ... and {len(attributes) - 10} more")
    
    # Find compatible attributes
    print(f"\n🔗 Finding compatible attributes...")
    compatible_count = 0
    
    for i, attr1 in enumerate(tqdm(attributes, desc="Checking compatibility")):
        for attr2 in attributes[i:]:
            if attr1.is_compatible(attr2, db_inspector=db):
                compatible_count += 1
                if compatible_count <= 5:  # Show first 5
                    print(f"   ✓ {attr1.table}.{attr1.name} ↔ {attr2.table}.{attr2.name}")
    
    print(f"\n✅ Total compatible pairs found: {compatible_count}")
    
    if compatible_count == 0:
        print("\n❌ PROBLEM: No compatible attributes found!")
        print("   This explains why MATILDA finds 0 rules.")
    else:
        print(f"\n✅ Found {compatible_count} compatible pairs - sufficient for TGD discovery")
        print("   Problem is likely in constraint graph construction or traversal phase")
    
    print(f"\n{'='*70}\n")
    db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Path to database file")
    args = parser.parse_args()
    
    debug_initialization(args.database)
