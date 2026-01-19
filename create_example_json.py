#!/usr/bin/env python3
"""Create example JSON for TikZ testing."""
import json

data = {
    "test_date": "2026-01-19 11:20:00",
    "configuration": {
        "algorithm": "astar",
        "heuristic": "hybrid",
        "max_table": 3,
        "max_vars": 6,
        "timeout": 3600
    },
    "datasets": {
        "1M": {
            "num_tuples": 1000000,
            "results": {
                "matilda": {
                    "success": True,
                    "runtime_seconds": 320.45,
                    "num_rules": 142,
                    "rules_per_second": 0.44,
                    "memory_peak_mb": 512.3,
                    "cpu_avg_percent": 67.8
                }
            }
        },
        "5M": {
            "num_tuples": 5000000,
            "results": {
                "matilda": {
                    "success": True,
                    "runtime_seconds": 1287.23,
                    "num_rules": 298,
                    "rules_per_second": 0.23,
                    "memory_peak_mb": 1845.7,
                    "cpu_avg_percent": 72.4
                }
            }
        },
        "10M": {
            "num_tuples": 10000000,
            "results": {
                "matilda": {
                    "success": True,
                    "runtime_seconds": 2501.89,
                    "num_rules": 467,
                    "rules_per_second": 0.19,
                    "memory_peak_mb": 3234.1,
                    "cpu_avg_percent": 75.2
                }
            }
        }
    },
    "scalability_metrics": {
        "sizes": ["1M", "5M", "10M"],
        "runtimes": [320.45, 1287.23, 2501.89],
        "tuple_counts": [1000000, 5000000, 10000000],
        "scaling_factors": [0.80, 0.97],
        "avg_scaling_factor": 0.89,
        "interpretation": "sub-linear"
    }
}

with open('results/scalability/example_scalability_summary.json', 'w') as f:
    json.dump(data, f, indent=2)

print("✓ JSON example créé : results/scalability/example_scalability_summary.json")
