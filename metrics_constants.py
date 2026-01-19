#!/usr/bin/env python3
"""
Constants and configuration for metrics computation and reporting.
"""

# Confidence thresholds for rule evaluation
MIN_CONFIDENCE_THRESHOLD = 0.5
HIGH_CONFIDENCE_THRESHOLD = 0.8
EXCELLENT_CONFIDENCE_THRESHOLD = 0.9

# Support thresholds for rule coverage
MIN_SUPPORT_THRESHOLD = 0.1
GOOD_SUPPORT_THRESHOLD = 0.5
EXCELLENT_SUPPORT_THRESHOLD = 0.8

# Accuracy thresholds (when available)
MIN_ACCURACY_THRESHOLD = 0.6
GOOD_ACCURACY_THRESHOLD = 0.8
EXCELLENT_ACCURACY_THRESHOLD = 0.95

# Default values for missing metrics
DEFAULT_CONFIDENCE = 0.0
DEFAULT_SUPPORT = 0.0
DEFAULT_ACCURACY = None

# AnyBURL specific constants
ANYBURL_DEFAULT_CONFIDENCE_WEIGHT = 0.6
ANYBURL_DEFAULT_SUPPORT_WEIGHT = 0.4

# Report formatting
METRIC_DECIMAL_PLACES = 4
PERCENTAGE_DECIMAL_PLACES = 2

# File discovery patterns
EXAMPLE_RESULTS_PATTERN = "*_example_results.json"
WITH_METRICS_PATTERN = "*_with_metrics*.json"
RESULTS_PATTERN = "*_results.json"

# Output formats
DISPLAY_PRECISION = 4
TABLE_WIDTH = 100
COLUMN_WIDTH = 15
