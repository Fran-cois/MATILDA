#!/usr/bin/env python3
"""
Robust multi-algorithm comparator for MATILDA rule discovery metrics.

Supports extensible comparator architecture for different algorithm types
with comprehensive error handling and validation. Shows both original metrics
and MATILDA-computed metrics for comprehensive comparison.
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import statistics
from dataclasses import dataclass, field

# Import constants for metric configuration
from metrics_constants import (
    MIN_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    EXCELLENT_CONFIDENCE_THRESHOLD,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MetricStats:
    """Container for algorithm metrics (both original and MATILDA-computed)."""
    rules_count: int = 0
    
    # Original metrics (from algorithm output)
    original_accuracy: Optional[float] = None
    original_confidence: float = 0.0
    original_support: float = 0.0
    
    # MATILDA-computed metrics
    matilda_accuracy: Optional[float] = None
    matilda_confidence: float = 0.0
    matilda_support: float = 0.0
    
    filename: str = ""
    matilda_filename: str = ""
    error: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if metrics are valid."""
        return self.rules_count > 0 or self.error is None
    
    def has_matilda_metrics(self) -> bool:
        """Check if MATILDA metrics are available."""
        return self.matilda_filename != "" or (
            self.matilda_accuracy is not None or 
            self.matilda_confidence > 0.0 or 
            self.matilda_support > 0.0
        )


class BaseComparator(ABC):
    """Abstract base class for algorithm comparators."""
    
    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{algorithm_name}]")
    
    @abstractmethod
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from rules. Must be implemented by subclasses."""
        pass
    
    def load_and_analyze(self, filepath: Path) -> Optional[MetricStats]:
        """Load file and extract metrics with error handling."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                self.logger.warning(f"Expected list but got {type(data).__name__}")
                return None
            
            if not data:
                self.logger.debug(f"File is empty: {filepath.name}")
                return None
            
            stats = self.extract_metrics(data)
            stats.filename = filepath.name
            self.logger.info(f"✓ Loaded {stats.rules_count} rules from {filepath.name}")
            return stats
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading {filepath.name}: {e}")
            return None


class SpiderComparator(BaseComparator):
    """Comparator for SPIDER IND algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from SPIDER rules (INDs without accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        
        for rule in rules:
            # SPIDER produces: confidence, support, correct, compatible
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.original_confidence = statistics.mean(confidences) if confidences else 0.0
        stats.original_support = statistics.mean(supports) if supports else 0.0
        stats.original_accuracy = None  # Spider doesn't compute accuracy
        
        return stats


class PopperComparator(BaseComparator):
    """Comparator for POPPER/ILP algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from POPPER rules (TGDs with accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        accuracies = []
        confidences = []
        supports = []
        
        for rule in rules:
            # POPPER produces: accuracy, confidence, support, correct, compatible
            acc = rule.get('accuracy')
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if acc is not None and isinstance(acc, (int, float)) and acc >= 0:
                accuracies.append(acc)
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.original_accuracy = statistics.mean(accuracies) if accuracies else None
        stats.original_confidence = statistics.mean(confidences) if confidences else 0.0
        stats.original_support = statistics.mean(supports) if supports else 0.0
        
        return stats


class Amie3Comparator(BaseComparator):
    """Comparator for AMIE3 algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from AMIE3 rules (Horn rules without accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        
        for rule in rules:
            # AMIE3 format: confidence, support but no accuracy
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.original_accuracy = None
        stats.original_confidence = statistics.mean(confidences) if confidences else 0.0
        stats.original_support = statistics.mean(supports) if supports else 0.0
        
        return stats


class AnyburlComparator(BaseComparator):
    """Comparator for AnyBURL MLN algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from AnyBURL rules (TGDs without accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        accuracies = []
        
        for rule in rules:
            # AnyBURL format: confidence field, accuracy field (may be -1.0 for invalid)
            conf = rule.get('confidence', 0)
            acc = rule.get('accuracy', -1.0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            
            # AnyBURL uses -1.0 for invalid, treat as valid support metric if >= 0
            if isinstance(acc, (int, float)) and acc >= 0:
                accuracies.append(acc)
                supports.append(acc)  # Use accuracy as support proxy
        
        stats.original_accuracy = None  # AnyBURL doesn't compute accuracy (uses -1.0)
        stats.original_confidence = statistics.mean(confidences) if confidences else 0.0
        stats.original_support = statistics.mean(supports) if supports else 0.0
        
        return stats


class ComparatorRegistry:
    """Registry for managing algorithm comparators."""
    
    _comparators = {
        'spider': SpiderComparator,
        'popper': PopperComparator,
        'amie3': Amie3Comparator,
        'anyburl': AnyburlComparator,
    }
    
    @classmethod
    def register(cls, algorithm: str, comparator_class: type) -> None:
        """Register a new comparator."""
        cls._comparators[algorithm.lower()] = comparator_class
        logger.info(f"Registered comparator: {algorithm}")
    
    @classmethod
    def get(cls, algorithm: str) -> Optional[BaseComparator]:
        """Get a comparator instance."""
        algo_lower = algorithm.lower()
        if algo_lower not in cls._comparators:
            logger.warning(f"No comparator found for {algorithm}")
            return None
        return cls._comparators[algo_lower](algorithm)
    
    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all registered algorithms."""
        return list(cls._comparators.keys())


class MetricsAnalyzer:
    """Main analyzer for algorithm metrics across databases."""
    
    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def find_metrics_file(self, algorithm: str, database: str, matilda: bool = False) -> Optional[Path]:
        """Find the most recent metrics file for an algorithm/database pair."""
        # Search in multiple locations
        search_dirs = [Path("."), self.output_dir]
        
        if matilda:
            # Look for MATILDA-computed metrics files
            patterns = [
                f"{algorithm}_{database}*_with_metrics*.json",
            ]
        else:
            # Look for original algorithm output (example_results files)
            patterns = [
                f"{algorithm}_{database}*_example_results.json",
                f"{algorithm}_{database}*_results.json",
            ]
        
        for pattern in patterns:
            for search_dir in search_dirs:
                files = list(search_dir.glob(pattern))
                if files:
                    # Filter out empty files
                    valid_files = [f for f in files if f.stat().st_size > 10]
                    if valid_files:
                        # Get the most recent file
                        return max(valid_files, key=lambda x: x.stat().st_mtime)
        
        return None
    
    def analyze_metrics(self, database_name: str = "Bupa") -> Optional[Dict[str, MetricStats]]:
        """Analyze both original and MATILDA metrics for all algorithms."""
        comparison = {}
        
        for algo in ComparatorRegistry.list_algorithms():
            # Find original metrics file
            original_file = self.find_metrics_file(algo, database_name, matilda=False)
            # Find MATILDA-computed metrics file
            matilda_file = self.find_metrics_file(algo, database_name, matilda=True)
            
            if not original_file and not matilda_file:
                self.logger.warning(f"No metrics files found for {algo} on {database_name}")
                comparison[algo] = MetricStats(error=f"No files found")
                continue
            
            # Get appropriate comparator
            comparator = ComparatorRegistry.get(algo)
            if not comparator:
                self.logger.error(f"No comparator for {algo}")
                comparison[algo] = MetricStats(error=f"No comparator")
                continue
            
            # Load original metrics
            stats = None
            if original_file:
                stats = comparator.load_and_analyze(original_file)
            
            if not stats:
                stats = MetricStats(error=f"Failed to load {original_file.name if original_file else 'original'}")
                comparison[algo] = stats
                continue
            
            # Load MATILDA metrics if available
            if matilda_file:
                try:
                    with open(matilda_file, 'r') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list) and len(data) > 0:
                        # Extract MATILDA-computed metrics
                        matilda_confidences = []
                        matilda_supports = []
                        matilda_accuracies = []
                        
                        for rule in data:
                            conf = rule.get('confidence', 0)
                            supp = rule.get('accuracy', 0)  # MATILDA uses accuracy field as support
                            acc = rule.get('accuracy')
                            
                            if isinstance(conf, (int, float)) and conf >= 0:
                                matilda_confidences.append(conf)
                            if isinstance(supp, (int, float)) and supp >= 0:
                                matilda_supports.append(supp)
                            if acc is not None and isinstance(acc, (int, float)) and acc >= 0:
                                matilda_accuracies.append(acc)
                        
                        stats.matilda_confidence = statistics.mean(matilda_confidences) if matilda_confidences else 0.0
                        stats.matilda_support = statistics.mean(matilda_supports) if matilda_supports else 0.0
                        stats.matilda_accuracy = statistics.mean(matilda_accuracies) if matilda_accuracies else None
                        stats.matilda_filename = matilda_file.name
                        self.logger.info(f"✓ Loaded MATILDA metrics from {matilda_file.name}")
                except Exception as e:
                    self.logger.warning(f"Could not load MATILDA metrics from {matilda_file.name}: {e}")
            
            comparison[algo] = stats
        
        if not any(v.rules_count > 0 for v in comparison.values()):
            self.logger.error(f"No valid metrics found for {database_name}")
            return None
        
        return comparison
    
    def print_original_metrics_table(self, comparison: Dict[str, MetricStats]) -> None:
        """Print original algorithm metrics table."""
        print(f"\n{'ORIGINAL ALGORITHM METRICS':100}")
        print("-" * 100)
        print(f"{'Algorithm':12} | {'Rules':7} | {'Accuracy':10} | {'Confidence':12} | {'Support':10}")
        print("-" * 100)
        
        for algo in sorted(comparison.keys()):
            stats = comparison[algo]
            
            if stats.error or stats.rules_count == 0:
                continue
            
            acc_str = f"{stats.original_accuracy:.4f}" if stats.original_accuracy is not None else "N/A"
            conf_str = f"{stats.original_confidence:.4f}"
            supp_str = f"{stats.original_support:.4f}"
            
            print(f"{algo.upper():12} | {stats.rules_count:7} | {acc_str:10} | {conf_str:12} | {supp_str:10}")
    
    def print_matilda_metrics_table(self, comparison: Dict[str, MetricStats]) -> None:
        """Print MATILDA-computed metrics table."""
        print(f"\n{'MATILDA-COMPUTED METRICS':100}")
        print("-" * 100)
        print(f"{'Algorithm':12} | {'Rules':7} | {'Accuracy':10} | {'Confidence':12} | {'Support':10} | {'Status':15}")
        print("-" * 100)
        
        for algo in sorted(comparison.keys()):
            stats = comparison[algo]
            
            if stats.rules_count == 0:
                status = "No Data"
                print(f"{algo.upper():12} | {'N/A':7} | {'N/A':10} | {'N/A':12} | {'N/A':10} | {status:15}")
                continue
            
            if not stats.has_matilda_metrics():
                status = "Not Available"
                print(f"{algo.upper():12} | {stats.rules_count:7} | {'N/A':10} | {'N/A':12} | {'N/A':10} | {status:15}")
                continue
            
            acc_str = f"{stats.matilda_accuracy:.4f}" if stats.matilda_accuracy is not None else "N/A"
            conf_str = f"{stats.matilda_confidence:.4f}"
            supp_str = f"{stats.matilda_support:.4f}"
            status = "✓ Computed"
            
            print(f"{algo.upper():12} | {stats.rules_count:7} | {acc_str:10} | {conf_str:12} | {supp_str:10} | {status:15}")
    
    def generate_comparison_insights(self, comparison: Dict[str, MetricStats]) -> None:
        """Generate insights comparing original vs MATILDA metrics."""
        print(f"\n{'='*100}")
        print("📊 COMPARATIVE INSIGHTS: Original vs MATILDA Metrics")
        print(f"{'='*100}\n")
        
        valid = {k: v for k, v in comparison.items() if not v.error and v.rules_count > 0}
        
        if not valid:
            self.logger.error("No valid data for analysis")
            return
        
        # For each algorithm, show differences
        for algo in sorted(valid.keys()):
            stats = valid[algo]
            print(f"\n🔹 {algo.upper()}")
            print("-" * 80)
            
            # Original metrics
            print(f"  Original Metrics:")
            print(f"    • Confidence: {stats.original_confidence:.4f}")
            print(f"    • Support:    {stats.original_support:.4f}")
            if stats.original_accuracy is not None:
                print(f"    • Accuracy:   {stats.original_accuracy:.4f}")
            else:
                print(f"    • Accuracy:   Not computed by algorithm")
            
            # MATILDA metrics
            if stats.has_matilda_metrics():
                print(f"  MATILDA-Computed Metrics:")
                print(f"    • Confidence: {stats.matilda_confidence:.4f}")
                print(f"    • Support:    {stats.matilda_support:.4f}")
                if stats.matilda_accuracy is not None:
                    print(f"    • Accuracy:   {stats.matilda_accuracy:.4f}")
                else:
                    print(f"    • Accuracy:   Not computed by MATILDA")
                
                # Show differences
                print(f"  Differences:")
                conf_diff = stats.matilda_confidence - stats.original_confidence
                print(f"    • Confidence: {conf_diff:+.4f} ({conf_diff/stats.original_confidence*100:+.1f}%)" if stats.original_confidence > 0 else f"    • Confidence: {conf_diff:+.4f}")
            else:
                print(f"  MATILDA-Computed Metrics: Not available")


def main():
    """Main execution."""
    database = "Bupa"
    
    print(f"\n{'='*100}")
    print(f"📊 COMPARATIVE ANALYSIS: {database} (Original vs MATILDA Metrics)")
    print(f"{'='*100}")
    
    analyzer = MetricsAnalyzer()
    comparison = analyzer.analyze_metrics(database)
    
    if not comparison:
        logger.error("Analysis failed")
        return 1
    
    analyzer.print_original_metrics_table(comparison)
    analyzer.print_matilda_metrics_table(comparison)
    analyzer.generate_comparison_insights(comparison)
    
    print(f"\n{'='*100}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())



class BaseComparator(ABC):
    """Abstract base class for algorithm comparators."""
    
    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{algorithm_name}]")
    
    @abstractmethod
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from rules. Must be implemented by subclasses."""
        pass
    
    def load_and_analyze(self, filepath: Path) -> Optional[MetricStats]:
        """Load file and extract metrics with error handling."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                self.logger.warning(f"Expected list but got {type(data).__name__}")
                return None
            
            if not data:
                self.logger.debug(f"File is empty: {filepath.name}")
                return None
            
            stats = self.extract_metrics(data)
            stats.filename = filepath.name
            self.logger.info(f"✓ Loaded {stats.rules_count} rules from {filepath.name}")
            return stats
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading {filepath.name}: {e}")
            return None


class SpiderComparator(BaseComparator):
    """Comparator for SPIDER IND algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from SPIDER rules (INDs without accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        
        for rule in rules:
            # SPIDER produces: confidence, support, correct, compatible
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.confidence = statistics.mean(confidences) if confidences else 0.0
        stats.support = statistics.mean(supports) if supports else 0.0
        stats.accuracy = None  # Spider doesn't compute accuracy
        
        return stats


class PopperComparator(BaseComparator):
    """Comparator for POPPER/ILP algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from POPPER rules (TGDs with accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        accuracies = []
        confidences = []
        supports = []
        
        for rule in rules:
            # POPPER produces: accuracy, confidence, support, correct, compatible
            acc = rule.get('accuracy')
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if acc is not None and isinstance(acc, (int, float)) and acc >= 0:
                accuracies.append(acc)
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.accuracy = statistics.mean(accuracies) if accuracies else None
        stats.accuracy_count = len(accuracies)
        stats.confidence = statistics.mean(confidences) if confidences else 0.0
        stats.support = statistics.mean(supports) if supports else 0.0
        
        return stats


class Amie3Comparator(BaseComparator):
    """Comparator for AMIE3 algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from AMIE3 rules (Horn rules without accuracy)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        
        for rule in rules:
            # AMIE3: confidence, support, correct, compatible
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.confidence = statistics.mean(confidences) if confidences else 0.0
        stats.support = statistics.mean(supports) if supports else 0.0
        stats.accuracy = None
        
        return stats


class AnyburlComparator(BaseComparator):
    """Comparator for AnyBURL algorithms."""
    
    def extract_metrics(self, rules: List[Dict]) -> MetricStats:
        """Extract metrics from AnyBURL rules (MLN-based)."""
        stats = MetricStats(rules_count=len(rules))
        
        confidences = []
        supports = []
        
        for rule in rules:
            # AnyBURL: confidence, support, correct, compatible
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            
            if isinstance(conf, (int, float)) and conf >= 0:
                confidences.append(conf)
            if isinstance(supp, (int, float)) and supp >= 0:
                supports.append(supp)
        
        stats.confidence = statistics.mean(confidences) if confidences else 0.0
        stats.support = statistics.mean(supports) if supports else 0.0
        stats.accuracy = None
        
        return stats


class ComparatorRegistry:
    """Registry for algorithm comparators."""
    
    _comparators: Dict[str, type] = {
        'spider': SpiderComparator,
        'popper': PopperComparator,
        'amie3': Amie3Comparator,
        'anyburl': AnyburlComparator,
    }
    
    @classmethod
    def register(cls, algorithm: str, comparator_class: type) -> None:
        """Register a new comparator."""
        cls._comparators[algorithm.lower()] = comparator_class
        logger.info(f"Registered comparator: {algorithm}")
    
    @classmethod
    def get(cls, algorithm: str) -> Optional[BaseComparator]:
        """Get a comparator instance."""
        algo_lower = algorithm.lower()
        if algo_lower not in cls._comparators:
            logger.warning(f"No comparator found for {algorithm}")
            return None
        return cls._comparators[algo_lower](algorithm)
    
    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all registered algorithms."""
        return list(cls._comparators.keys())


class MetricsAnalyzer:
    """Main analyzer for algorithm metrics across databases."""
    
    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def find_metrics_file(self, algorithm: str, database: str) -> Optional[Path]:
        """Find the most recent metrics file for an algorithm/database pair."""
        # Search in multiple locations
        search_dirs = [Path("."), self.output_dir]
        
        # Look for example_results files first (they have data), excluding _with_metrics
        patterns = [
            f"{algorithm}_{database}*_example_results.json",  # Exact example files
            f"{algorithm}_{database}*_results.json",  # Regular results files
            f"{algorithm}_{database}*_with_metrics*.json",  # Metrics files (may be empty)
        ]
        
        for pattern in patterns:
            for search_dir in search_dirs:
                files = list(search_dir.glob(pattern))
                if files:
                    # Filter out empty files
                    valid_files = [f for f in files if f.stat().st_size > 10]
                    if valid_files:
                        # Get the most recent file
                        return max(valid_files, key=lambda x: x.stat().st_mtime)
        
        return None
    
    def analyze_metrics(self, database_name: str = "Bupa") -> Optional[Dict[str, MetricStats]]:
        """Analyze metrics for all algorithms on a specific database."""
        comparison = {}
        
        for algo in ComparatorRegistry.list_algorithms():
            metrics_file = self.find_metrics_file(algo, database_name)
            
            if not metrics_file:
                self.logger.warning(f"No metrics file found for {algo} on {database_name}")
                comparison[algo] = MetricStats(error=f"No file found")
                continue
            
            # Get appropriate comparator
            comparator = ComparatorRegistry.get(algo)
            if not comparator:
                self.logger.error(f"No comparator for {algo}")
                comparison[algo] = MetricStats(error=f"No comparator")
                continue
            
            # Load and analyze
            stats = comparator.load_and_analyze(metrics_file)
            if stats:
                comparison[algo] = stats
            else:
                comparison[algo] = MetricStats(error=f"Failed to load {metrics_file.name}")
        
        if not any(v.rules_count > 0 for v in comparison.values()):
            self.logger.error(f"No valid metrics found for {database_name}")
            return None
        
        return comparison
    
    def print_comparison_table(self, comparison: Dict[str, MetricStats]) -> None:
        """Print formatted comparison table."""
        print(f"\n{'Algorithm':12} | {'Rules':7} | {'Accuracy':10} | {'Confidence':12} | {'Support':10}")
        print("-" * 75)
        
        for algo in sorted(comparison.keys()):
            stats = comparison[algo]
            
            if stats.error:
                print(f"{algo.upper():12} | {'ERROR':7} | {stats.error}")
                continue
            
            acc_str = f"{stats.accuracy:.4f}" if stats.accuracy is not None else "N/A"
            conf_str = f"{stats.confidence:.4f}"
            supp_str = f"{stats.support:.4f}"
            
            print(f"{algo.upper():12} | {stats.rules_count:7} | {acc_str:10} | {conf_str:12} | {supp_str:10}")
    
    def generate_insights(self, comparison: Dict[str, MetricStats]) -> None:
        """Generate and print analytical insights."""
        print(f"\n{'='*100}")
        print("📈 KEY INSIGHTS")
        print(f"{'='*100}\n")
        
        # Filter valid comparisons
        valid = {k: v for k, v in comparison.items() if not v.error and v.rules_count > 0}
        
        if not valid:
            self.logger.error("No valid data for analysis")
            return
        
        # Rules count comparison
        total_rules = sum(v.rules_count for v in valid.values())
        print(f"Total Rules Generated: {total_rules}")
        
        for algo in sorted(valid.keys()):
            count = valid[algo].rules_count
            pct = (count / total_rules * 100) if total_rules > 0 else 0
            print(f"  • {algo.upper():8}: {count:3} rules ({pct:5.1f}%)")
        
        # Accuracy analysis
        accs = {k: v.accuracy for k, v in valid.items() if v.accuracy is not None}
        if accs:
            print(f"\nAccuracy (when available):")
            for algo in sorted(accs.keys()):
                print(f"  • {algo.upper():8}: {accs[algo]:.4f}")
            best_algo = max(accs.keys(), key=lambda k: accs[k])
            print(f"\n✅ Best Accuracy: {best_algo.upper()} ({accs[best_algo]:.4f})")
        else:
            print(f"\n⚠️  No accuracy metrics available")
        
        # Confidence analysis
        confs = {k: v.confidence for k, v in valid.items()}
        print(f"\nConfidence (rule applicability):")
        for algo in sorted(confs.keys()):
            print(f"  • {algo.upper():8}: {confs[algo]:.4f}")
        best_conf = max(confs.keys(), key=lambda k: confs[k])
        print(f"\n✅ Best Confidence: {best_conf.upper()} ({confs[best_conf]:.4f})")
        
        # Support analysis
        supports = {k: v.support for k, v in valid.items()}
        print(f"\nSupport (rule coverage):")
        for algo in sorted(supports.keys()):
            print(f"  • {algo.upper():8}: {supports[algo]:.4f}")
        best_supp = max(supports.keys(), key=lambda k: supports[k])
        print(f"\n✅ Best Support: {best_supp.upper()} ({supports[best_supp]:.4f})")
        
        # Summary rankings
        print(f"\n{'='*100}")
        print("📋 SUMMARY")
        print(f"{'='*100}\n")
        
        print("Algorithm Performance Ranking:\n")
        
        print("1️⃣  BY CONFIDENCE (Rule Applicability):")
        for i, algo in enumerate(sorted(confs.keys(), key=lambda k: confs[k], reverse=True), 1):
            print(f"   {i}. {algo.upper():8} - {confs[algo]:.4f}")
        
        if accs:
            print("\n2️⃣  BY ACCURACY (Rule Validity):")
            for i, algo in enumerate(sorted(accs.keys(), key=lambda k: accs[k], reverse=True), 1):
                print(f"   {i}. {algo.upper():8} - {accs[algo]:.4f}")
        
        print("\n3️⃣  BY RULE COUNT (Coverage):")
        for i, algo in enumerate(sorted(valid.keys(), key=lambda k: valid[k].rules_count, reverse=True), 1):
            count = valid[algo].rules_count
            print(f"   {i}. {algo.upper():8} - {count} rules")


def main():
    """Main execution."""
    database = "Bupa"
    
    print(f"\n{'='*100}")
    print(f"📊 COMPARATIVE ANALYSIS: {database}")
    print(f"{'='*100}\n")
    
    analyzer = MetricsAnalyzer()
    comparison = analyzer.analyze_metrics(database)
    
    if not comparison:
        logger.error("Analysis failed")
        return 1
    
    analyzer.print_comparison_table(comparison)
    analyzer.generate_insights(comparison)
    
    print(f"\n{'='*100}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
