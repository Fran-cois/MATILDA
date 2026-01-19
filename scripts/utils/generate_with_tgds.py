#!/usr/bin/env python3
"""
Generate synthetic datasets with embedded TGD patterns for scalability testing.

This generator creates databases with intentional tuple-generating dependencies
that MATILDA should discover, unlike purely random data.

Embedded TGDs:
1. Orders → Customers: order.customer_name → customers.name
2. Orders + Customers → Shipments: Multiple patterns
3. Products → Orders: Price consistency patterns
"""

import argparse
import random
import sqlite3
import time
from pathlib import Path
from typing import List, Tuple


class TGDDatasetGenerator:
    """Generate datasets with embedded TGD patterns."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Seed data for realistic patterns
        self.customer_names = [
            "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", 
            "Eve Davis", "Frank Miller", "Grace Wilson", "Henry Moore",
            "Ivy Taylor", "Jack Anderson", "Kate Thomas", "Leo Jackson",
            "Mary White", "Noah Harris", "Olivia Martin", "Paul Thompson"
        ]
        
        self.cities = [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
        ]
        
        self.product_names = [
            "Laptop", "Mouse", "Keyboard", "Monitor", "Headphones",
            "Webcam", "Speaker", "Microphone", "Cable", "Adapter"
        ]
        
        self.statuses = ["pending", "processing", "shipped", "delivered"]
        
    def create_schema(self):
        """Create database schema with FK relationships."""
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Customers table
        self.conn.execute("""
            CREATE TABLE Customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                city TEXT NOT NULL,
                registration_date TEXT NOT NULL
            )
        """)
        
        # Products table
        self.conn.execute("""
            CREATE TABLE Products (
                id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                base_price REAL NOT NULL
            )
        """)
        
        # Orders table - with FKs and TGD patterns
        self.conn.execute("""
            CREATE TABLE Orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES Customers(id),
                product_id INTEGER NOT NULL REFERENCES Products(id),
                customer_name TEXT NOT NULL,
                customer_city TEXT NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        
        # Shipments table - depends on Orders + Customers
        self.conn.execute("""
            CREATE TABLE Shipments (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES Orders(id),
                customer_id INTEGER NOT NULL REFERENCES Customers(id),
                tracking_number TEXT NOT NULL,
                ship_date TEXT NOT NULL,
                delivery_city TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        
        # Create indexes
        for table in ["Customers", "Products", "Orders", "Shipments"]:
            self.conn.execute(f"CREATE INDEX idx_{table}_id ON {table}(id)")
        
        self.conn.commit()
        
    def populate_customers(self, n: int) -> List[int]:
        """Insert customers and return their IDs."""
        customer_ids = []
        
        for i in range(n):
            name = random.choice(self.customer_names)
            email = f"{name.lower().replace(' ', '.')}@email.com"
            city = random.choice(self.cities)
            date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            
            self.cursor.execute(
                "INSERT INTO Customers (name, email, city, registration_date) VALUES (?, ?, ?, ?)",
                (name, email, city, date)
            )
            customer_ids.append(self.cursor.lastrowid)
        
        return customer_ids
    
    def populate_products(self, n: int) -> List[int]:
        """Insert products and return their IDs."""
        product_ids = []
        categories = ["Electronics", "Accessories", "Computing"]
        
        for i in range(n):
            name = random.choice(self.product_names)
            category = random.choice(categories)
            price = round(random.uniform(10, 500), 2)
            
            self.cursor.execute(
                "INSERT INTO Products (product_name, category, base_price) VALUES (?, ?, ?)",
                (name, category, price)
            )
            product_ids.append(self.cursor.lastrowid)
        
        return product_ids
    
    def populate_orders(self, n: int, customer_ids: List[int], product_ids: List[int]) -> List[int]:
        """
        Insert orders with TGD patterns embedded.
        
        TGD Pattern: Orders(customer_id, X, Y) ∧ Customers(customer_id, name, city, Z) 
                     → Orders(customer_id, name, city, Y)
        """
        order_ids = []
        
        for i in range(n):
            customer_id = random.choice(customer_ids)
            product_id = random.choice(product_ids)
            
            # Fetch customer data to embed TGD
            self.cursor.execute("SELECT name, city FROM Customers WHERE id = ?", (customer_id,))
            customer_name, customer_city = self.cursor.fetchone()
            
            # Fetch product data to embed TGD
            self.cursor.execute("SELECT product_name, base_price FROM Products WHERE id = ?", (product_id,))
            product_name, base_price = self.cursor.fetchone()
            
            # Price is base_price with slight variation (TGD pattern)
            price = round(base_price * random.uniform(0.95, 1.05), 2)
            quantity = random.randint(1, 10)
            order_date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            status = random.choice(self.statuses)
            
            self.cursor.execute(
                """INSERT INTO Orders 
                   (customer_id, product_id, customer_name, customer_city, 
                    product_name, price, quantity, order_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (customer_id, product_id, customer_name, customer_city, 
                 product_name, price, quantity, order_date, status)
            )
            order_ids.append(self.cursor.lastrowid)
        
        return order_ids
    
    def populate_shipments(self, n: int, order_ids: List[int], customer_ids: List[int]):
        """
        Insert shipments with TGD patterns.
        
        TGD Pattern: Shipments(order_id, X, Y) ∧ Orders(order_id, customer_id, city, Z)
                     → Shipments(order_id, customer_id, city, Y)
        """
        for i in range(n):
            order_id = random.choice(order_ids)
            
            # Fetch order data to embed TGD
            self.cursor.execute(
                "SELECT customer_id, customer_city FROM Orders WHERE id = ?", 
                (order_id,)
            )
            customer_id, customer_city = self.cursor.fetchone()
            
            tracking = f"TRK{random.randint(100000, 999999)}"
            ship_date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            status = random.choice(["in_transit", "delivered"])
            
            self.cursor.execute(
                """INSERT INTO Shipments 
                   (order_id, customer_id, tracking_number, ship_date, delivery_city, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (order_id, customer_id, tracking, ship_date, customer_city, status)
            )
    
    def generate(self, target_tuples: int):
        """Generate dataset with specified number of tuples."""
        print(f"\n{'='*70}")
        print(f"🔧 GENERATING DATASET WITH TGD PATTERNS")
        print(f"{'='*70}")
        print(f"Target: {target_tuples:,} tuples")
        print(f"Output: {self.db_path}")
        print(f"{'='*70}\n")
        
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Remove old database
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        start_time = time.time()
        
        # Create schema
        print("✓ Creating schema...")
        self.create_schema()
        
        # Distribute tuples across tables (40% orders, 30% customers, 20% products, 10% shipments)
        n_orders = int(target_tuples * 0.40)
        n_customers = int(target_tuples * 0.30)
        n_products = int(target_tuples * 0.20)
        n_shipments = int(target_tuples * 0.10)
        
        # Populate tables
        print(f"✓ Inserting {n_customers:,} customers...")
        customer_ids = self.populate_customers(n_customers)
        
        print(f"✓ Inserting {n_products:,} products...")
        product_ids = self.populate_products(n_products)
        
        print(f"✓ Inserting {n_orders:,} orders (with TGDs)...")
        order_ids = self.populate_orders(n_orders, customer_ids, product_ids)
        
        print(f"✓ Inserting {n_shipments:,} shipments (with TGDs)...")
        self.populate_shipments(n_shipments, order_ids, customer_ids)
        
        self.conn.commit()
        
        # Get statistics
        total_tuples = sum([
            self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ["Customers", "Products", "Orders", "Shipments"]
        ])
        
        elapsed = time.time() - start_time
        db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
        
        print(f"\n{'='*70}")
        print(f"✅ DATASET GENERATION COMPLETE!")
        print(f"{'='*70}")
        print(f"Total tuples:     {total_tuples:,}")
        print(f"Time:             {elapsed:.2f}s ({int(total_tuples/elapsed):,} tuples/s)")
        print(f"Database:         {self.db_path}")
        print(f"Size:             {db_size:.2f} MB")
        print(f"{'='*70}\n")
        
        print("📊 Table Statistics:")
        for table in ["Customers", "Products", "Orders", "Shipments"]:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   {table:15s}: {count:,} rows")
        
        print(f"\n{'='*70}")
        print("🎯 Embedded TGD Patterns:")
        print("   1. Orders.customer_name → Customers.name")
        print("   2. Orders.customer_city → Customers.city")
        print("   3. Orders.product_name → Products.product_name")
        print("   4. Orders.price ≈ Products.base_price (with variance)")
        print("   5. Shipments.customer_id → Orders.customer_id")
        print("   6. Shipments.delivery_city → Orders.customer_city")
        print(f"{'='*70}\n")
        
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic datasets with embedded TGD patterns"
    )
    parser.add_argument(
        "output",
        help="Output database path (e.g., data/large_scale/1M_with_tgds.db)"
    )
    parser.add_argument(
        "--target-tuples",
        type=int,
        default=1000000,
        help="Target number of total tuples (default: 1,000,000)"
    )
    
    args = parser.parse_args()
    
    generator = TGDDatasetGenerator(args.output)
    generator.generate(args.target_tuples)


if __name__ == "__main__":
    main()
