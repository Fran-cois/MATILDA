#!/usr/bin/env python3
"""
Debug MATILDA full pipeline to identify why 0 rules are found.
"""

import sys
from pathlib import Path

# Add paths
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path / 'src'))
sys.path.insert(0, str(root_path))

from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.tgd_discovery import init


def debug_full_pipeline(db_path: str):
    """Debug complete MATILDA initialization and constraint graph."""
    
    print(f"\n{'='*70}")
    print("🔍 DEBUGGING MATILDA FULL PIPELINE")
    print(f"{'='*70}\n")
    
    # Connect to database
    print(f"Connecting to: {db_path}")
    db = AlchemyUtility(f"sqlite:///{db_path}")
    
    # Get tables
    tables = db.get_table_names()
    print(f"✓ Found {len(tables)} tables: {tables}")
    
    # Run initialization
    print("\n📋 Running MATILDA init()...")
    print("   This includes:")
    print("   - Generating attributes")
    print("   - Finding compatible attributes")
    print("   - Creating indexed attributes (JIA list)")
    print("   - Building constraint graph")
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            cg, mapper, jia_list = init(
                db,
                max_nb_occurrence=3,
                max_nb_occurrence_per_table_and_column={},
                results_path=tmpdir
            )
            
            print(f"\n✅ Initialization complete!")
            print(f"   Constraint graph: {cg is not None}")
            print(f"   Attribute mapper: {mapper is not None}")
            print(f"   JIA list size: {len(jia_list) if jia_list else 0}")
            
            # Check constraint graph nodes
            if cg:
                print(f"   Constraint graph nodes: {len(cg.nodes) if hasattr(cg, 'nodes') else 'N/A'}")
                if hasattr(cg, 'nodes') and cg.nodes:
                    print(f"   Sample nodes (first 3): {list(cg.nodes)[:3]}")
            
            if not jia_list or len(jia_list) == 0:
                print(f"\n❌ PROBLEM: JIA list is empty!")
                print("   This means no compatible indexed attributes were created.")
                print("   Without JIA list, the constraint graph has no edges to traverse.")
                print("   This explains why 0 rules are found.")
                
            if jia_list and len(jia_list) > 0:
                print(f"\n✅ JIA list has {len(jia_list)} entries")
                if hasattr(cg, 'nodes') and not cg.nodes:
                    print(f"   ❌ BUT constraint graph has 0 nodes!")
                    print("   This explains why traverse_graph finds nothing.")
                elif hasattr(cg, 'nodes') and cg.nodes:
                    print(f"   ✅ Constraint graph has {len(cg.nodes)} nodes - should work")
                print(f"   Sample JIA entries (first 5):")
                for jia in jia_list[:5]:
                    print(f"   - {jia}")
                    
        except Exception as e:
            print(f"\n❌ ERROR during initialization: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}\n")
    db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Path to database file")
    args = parser.parse_args()
    
    debug_full_pipeline(args.database)
