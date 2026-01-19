#!/usr/bin/env python3
"""
Documentation of Constants and Configuration for Metrics Computation.

This module defines all the constants used in MATILDA metrics computation
to ensure consistency and maintainability across the codebase.
"""

# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================
# Used to classify rules based on their confidence (applicability)

MIN_CONFIDENCE_THRESHOLD = 0.5
"""Minimum confidence level for a rule to be considered acceptable."""

HIGH_CONFIDENCE_THRESHOLD = 0.8
"""Confidence level for a rule to be considered high quality."""

EXCELLENT_CONFIDENCE_THRESHOLD = 0.9
"""Confidence level for a rule to be considered excellent."""


# ============================================================================
# SUPPORT THRESHOLDS
# ============================================================================
# Used to classify rules based on their support (coverage)

MIN_SUPPORT_THRESHOLD = 0.1
"""Minimum support level for a rule to cover sufficient data."""

GOOD_SUPPORT_THRESHOLD = 0.5
"""Support level for a rule to be considered good coverage."""

EXCELLENT_SUPPORT_THRESHOLD = 0.8
"""Support level for a rule to be considered excellent coverage."""


# ============================================================================
# ACCURACY THRESHOLDS
# ============================================================================
# Used to classify rules based on their accuracy (validity)
# Note: Only computed by POPPER and MATILDA validators

MIN_ACCURACY_THRESHOLD = 0.6
"""Minimum accuracy level for a rule to be considered valid."""

GOOD_ACCURACY_THRESHOLD = 0.8
"""Accuracy level for a rule to be considered high quality."""

EXCELLENT_ACCURACY_THRESHOLD = 0.95
"""Accuracy level for a rule to be considered excellent."""


# ============================================================================
# DEFAULT VALUES
# ============================================================================
# Used when metrics are not available or not computed

DEFAULT_CONFIDENCE = 0.0
"""Default confidence value when not provided."""

DEFAULT_SUPPORT = 0.0
"""Default support value when not provided."""

DEFAULT_ACCURACY = None
"""Default accuracy value (None) when not computed."""


# ============================================================================
# ALGORITHM-SPECIFIC CONSTANTS
# ============================================================================
# Constants specific to particular rule discovery algorithms

ANYBURL_DEFAULT_CONFIDENCE_WEIGHT = 0.6
"""Weight for confidence in AnyBURL metric weighting."""

ANYBURL_DEFAULT_SUPPORT_WEIGHT = 0.4
"""Weight for support in AnyBURL metric weighting."""


# ============================================================================
# REPORTING CONSTANTS
# ============================================================================
# Constants for output formatting and display

METRIC_DECIMAL_PLACES = 4
"""Number of decimal places for metric display."""

PERCENTAGE_DECIMAL_PLACES = 2
"""Number of decimal places for percentage display."""

TABLE_WIDTH = 100
"""Width of output tables in characters."""

COLUMN_WIDTH = 15
"""Standard column width in characters."""

DISPLAY_PRECISION = 4
"""Precision for displaying floating-point metrics."""


# ============================================================================
# FILE DISCOVERY PATTERNS
# ============================================================================
# Patterns used to find result files in the filesystem

EXAMPLE_RESULTS_PATTERN = "*_example_results.json"
"""Pattern for original algorithm results files."""

WITH_METRICS_PATTERN = "*_with_metrics*.json"
"""Pattern for MATILDA-computed metrics files."""

RESULTS_PATTERN = "*_results.json"
"""Pattern for general results files."""


# ============================================================================
# CONFIGURATION GUIDE
# ============================================================================
"""
To use these constants in your code:

1. Import the needed constants:
   from metrics_constants import (
       MIN_CONFIDENCE_THRESHOLD,
       GOOD_SUPPORT_THRESHOLD,
       ANYBURL_DEFAULT_CONFIDENCE_WEIGHT
   )

2. Use them in your code:
   if rule_confidence >= HIGH_CONFIDENCE_THRESHOLD:
       print("Rule has high confidence")
   
   weighted_score = (
       confidence * ANYBURL_DEFAULT_CONFIDENCE_WEIGHT +
       support * ANYBURL_DEFAULT_SUPPORT_WEIGHT
   )

3. When adding new algorithms:
   - Define algorithm-specific weights/thresholds as separate constants
   - Follow the naming pattern: ALGORITHM_PARAMETER_NAME
   - Add comments explaining what the constant controls

4. File patterns are used in MetricsAnalyzer.find_metrics_file():
   - First searches for EXAMPLE_RESULTS_PATTERN (original outputs)
   - Then searches for WITH_METRICS_PATTERN (MATILDA-computed)
   - This ensures we find actual data before searching for metrics
"""

# ============================================================================
# METRICS NAMING CONVENTION
# ============================================================================
"""
Metric types in the system:

1. ORIGINAL METRICS: Metrics computed by the algorithm itself
   - Stored in files matching EXAMPLE_RESULTS_PATTERN
   - Examples: anyburl_Bupa_example_results.json
   - Contains: confidence, support, accuracy (when available)

2. MATILDA METRICS: Metrics computed by MATILDA validators
   - Stored in files matching WITH_METRICS_PATTERN
   - Examples: anyburl_Bupa_example_results_with_metrics_2026-01-15_10-52-54.json
   - Contains: confidence, support, accuracy (computed from database)
   - Note: SPIDER metrics are INDs (different validation rules)

3. METRIC FIELDS:
   - accuracy: Correctness/validity of the rule (0.0-1.0)
   - confidence: Applicability/precision of the rule (0.0-1.0)
   - support: Coverage of the rule over the dataset (0.0-1.0)
   - correct: Boolean flag for rule validity
   - compatible: Boolean flag for rule compatibility
"""

if __name__ == "__main__":
    print(__doc__)
    print("\n✓ Constants module loaded successfully!")
    print(f"  • MIN_CONFIDENCE_THRESHOLD = {MIN_CONFIDENCE_THRESHOLD}")
    print(f"  • HIGH_CONFIDENCE_THRESHOLD = {HIGH_CONFIDENCE_THRESHOLD}")
    print(f"  • MIN_SUPPORT_THRESHOLD = {MIN_SUPPORT_THRESHOLD}")
    print(f"  • MIN_ACCURACY_THRESHOLD = {MIN_ACCURACY_THRESHOLD}")
