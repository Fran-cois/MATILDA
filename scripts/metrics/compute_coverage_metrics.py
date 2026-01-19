#!/usr/bin/env python3
"""
Compute MATILDA coverage metrics compared to other algorithms.

This script analyzes:
1. Rule Match Coverage: Rules from other algorithms that match MATILDA rules
2. Completeness: Rules that MATILDA should recover under joinability constraint
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set, Any
from dataclasses import dataclass


@dataclass
class CoverageMetrics:
    """Coverage metrics for an algorithm vs MATILDA."""
    algorithm: str
    dataset: str
    
    # Total rules
    matilda_total: int
    other_total: int
    
    # Segment 1: Rules that match
    rules_match_count: int
    rules_match_percentage: float
    
    # Segment 2: Completeness under joinability constraint
    joinable_rules_count: int
    matilda_recovered_count: int
    completeness_percentage: float
    
    # Detailed matches
    matched_pairs: List[Tuple[Dict, Dict]]
    unmatched_other: List[Dict]
    unmatched_matilda: List[Dict]


class RuleMatcher:
    """Matches rules between MATILDA and other algorithms."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def _log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(message)
    
    def normalize_table_name(self, name: str) -> str:
        """Normalize table names (remove _0 suffix, convert to lowercase)."""
        return name.replace('_0', '').lower().strip()
    
    def extract_tables_from_tgd(self, rule: Dict) -> Set[str]:
        """Extract table names from MATILDA TGD rule."""
        tables = set()
        
        # From body predicates
        for body_pred in rule.get('body', []):
            if 'relation=' in body_pred:
                import re
                match = re.search(r"relation='([^']+)'", body_pred)
                if match:
                    tables.add(self.normalize_table_name(match.group(1)))
        
        # From head predicates
        for head_pred in rule.get('head', []):
            if 'relation=' in head_pred:
                import re
                match = re.search(r"relation='([^']+)'", head_pred)
                if match:
                    tables.add(self.normalize_table_name(match.group(1)))
        
        return tables
    
    def extract_columns_from_tgd(self, rule: Dict) -> Dict[str, Set[str]]:
        """Extract table -> columns mapping from MATILDA TGD rule."""
        table_columns = {}
        
        for pred_str in rule.get('body', []) + rule.get('head', []):
            import re
            # Extract relation and variables
            relation_match = re.search(r"relation='([^']+)'", pred_str)
            var1_match = re.search(r"variable1='([^']+)'", pred_str)
            var2_match = re.search(r"variable2='([^']+)'", pred_str)
            
            if relation_match:
                table = self.normalize_table_name(relation_match.group(1))
                cols = set()
                if var1_match:
                    cols.add(var1_match.group(1))
                if var2_match:
                    # Columns are the variable names (like 'arg1', 'arg2')
                    pass
                
                if table not in table_columns:
                    table_columns[table] = set()
                table_columns[table].update(cols)
        
        return table_columns
    
    def tgd_matches_ind(self, tgd_rule: Dict, ind_rule: Dict) -> bool:
        """Check if a TGD rule matches an IND rule (SPIDER/IND format)."""
        # Extract IND components
        dep_table = self.normalize_table_name(ind_rule.get('table_dependant', ''))
        ref_table = self.normalize_table_name(ind_rule.get('table_referenced', ''))
        dep_cols = set(c.lower() for c in ind_rule.get('columns_dependant', []))
        ref_cols = set(c.lower() for c in ind_rule.get('columns_referenced', []))
        
        # Extract TGD tables
        tgd_tables = self.extract_tables_from_tgd(tgd_rule)
        
        # Check if TGD involves the same tables
        if dep_table in tgd_tables and ref_table in tgd_tables:
            # More sophisticated matching could check column correspondence
            return True
        
        return False
    
    def tgd_matches_horn(self, tgd1: Dict, tgd2: Dict) -> bool:
        """Check if two TGD/Horn rules match."""
        # Simple approach: compare tables involved
        tables1 = self.extract_tables_from_tgd(tgd1)
        tables2 = self.extract_tables_from_tgd(tgd2)
        
        # Rules match if they share most tables
        if not tables1 or not tables2:
            return False
        
        overlap = len(tables1 & tables2)
        min_size = min(len(tables1), len(tables2))
        
        # At least 80% table overlap
        return overlap / min_size >= 0.8 if min_size > 0 else False
    
    def is_joinable(self, rule: Dict, algorithm: str) -> bool:
        """Check if a rule satisfies joinability constraint.
        
        A rule is joinable if:
        - For INDs: dependent and referenced tables have overlapping attributes
        - For TGDs: body and head predicates share common variables/attributes
        """
        if algorithm.upper() in ['SPIDER', 'IND']:
            # For IND rules, check if tables have a join path
            # Simplified: assume all INDs are potentially joinable
            # In reality, you'd check the database schema
            return True
        
        elif rule.get('type') in ['TGDRule', 'HornRule']:
            # For TGD/Horn rules, check if body and head share variables
            body = rule.get('body', [])
            head = rule.get('head', [])
            
            # Extract variables from body and head
            import re
            body_vars = set()
            head_vars = set()
            
            for pred in body:
                vars_found = re.findall(r"variable[12]='([^']+)'", pred)
                body_vars.update(vars_found)
            
            for pred in head:
                vars_found = re.findall(r"variable[12]='([^']+)'", pred)
                head_vars.update(vars_found)
            
            # Rule is joinable if body and head share at least one variable
            return len(body_vars & head_vars) > 0
        
        # Default: assume joinable
        return True
    
    def compare_rule_sets(
        self,
        matilda_rules: List[Dict],
        other_rules: List[Dict],
        other_algorithm: str,
        dataset: str
    ) -> CoverageMetrics:
        """Compare MATILDA rules with another algorithm's rules."""
        
        self._log(f"\n{'='*80}")
        self._log(f"Comparing MATILDA vs {other_algorithm} on {dataset}")
        self._log(f"{'='*80}")
        
        matched_pairs = []
        matched_other_indices = set()
        
        # Segment 1: Find rules that match
        for matilda_rule in matilda_rules:
            for idx, other_rule in enumerate(other_rules):
                if idx in matched_other_indices:
                    continue
                
                # Check if rules match based on algorithm type
                is_match = False
                if other_rule.get('type') == 'InclusionDependency':
                    is_match = self.tgd_matches_ind(matilda_rule, other_rule)
                elif other_rule.get('type') in ['TGDRule', 'HornRule']:
                    is_match = self.tgd_matches_horn(matilda_rule, other_rule)
                
                if is_match:
                    matched_pairs.append((matilda_rule, other_rule))
                    matched_other_indices.add(idx)
                    break
        
        rules_match_count = len(matched_pairs)
        rules_match_percentage = (rules_match_count / len(other_rules) * 100) if other_rules else 0
        
        # Segment 2: Completeness under joinability constraint
        joinable_other_rules = [
            r for r in other_rules 
            if self.is_joinable(r, other_algorithm)
        ]
        
        matilda_recovered_count = 0
        for other_rule in joinable_other_rules:
            # Check if MATILDA recovered this joinable rule
            for matilda_rule in matilda_rules:
                if other_rule.get('type') == 'InclusionDependency':
                    is_match = self.tgd_matches_ind(matilda_rule, other_rule)
                else:
                    is_match = self.tgd_matches_horn(matilda_rule, other_rule)
                
                if is_match:
                    matilda_recovered_count += 1
                    break
        
        completeness_percentage = (
            (matilda_recovered_count / len(joinable_other_rules) * 100)
            if joinable_other_rules else 0
        )
        
        unmatched_other = [
            r for idx, r in enumerate(other_rules)
            if idx not in matched_other_indices
        ]
        
        unmatched_matilda = [
            m for m in matilda_rules
            if not any(m == pair[0] for pair in matched_pairs)
        ]
        
        self._log(f"\n📊 Results:")
        self._log(f"  MATILDA rules: {len(matilda_rules)}")
        self._log(f"  {other_algorithm} rules: {len(other_rules)}")
        self._log(f"\n  Segment 1 - Rules Match:")
        self._log(f"    Matched: {rules_match_count}/{len(other_rules)} ({rules_match_percentage:.1f}%)")
        self._log(f"\n  Segment 2 - Completeness (Joinability Constraint):")
        self._log(f"    Joinable rules in {other_algorithm}: {len(joinable_other_rules)}")
        self._log(f"    MATILDA recovered: {matilda_recovered_count}/{len(joinable_other_rules)} ({completeness_percentage:.1f}%)")
        
        return CoverageMetrics(
            algorithm=other_algorithm,
            dataset=dataset,
            matilda_total=len(matilda_rules),
            other_total=len(other_rules),
            rules_match_count=rules_match_count,
            rules_match_percentage=rules_match_percentage,
            joinable_rules_count=len(joinable_other_rules),
            matilda_recovered_count=matilda_recovered_count,
            completeness_percentage=completeness_percentage,
            matched_pairs=matched_pairs,
            unmatched_other=unmatched_other,
            unmatched_matilda=unmatched_matilda
        )


def load_results(algorithm: str, dataset: str, output_dir: Path) -> List[Dict]:
    """Load results for an algorithm on a dataset."""
    filename = f"{algorithm}_{dataset}_results.json"
    filepath = output_dir / filename
    
    if not filepath.exists():
        print(f"⚠️  Results file not found: {filepath}")
        return []
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'rules' in data:
                return data['rules']
            else:
                print(f"⚠️  Unexpected format in {filepath}")
                return []
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return []


def save_coverage_metrics(metrics_list: List[CoverageMetrics], output_dir: Path):
    """Save coverage metrics to JSON file."""
    output_file = output_dir / "coverage_metrics.json"
    
    data = []
    for metrics in metrics_list:
        data.append({
            'algorithm': metrics.algorithm,
            'dataset': metrics.dataset,
            'matilda_total': metrics.matilda_total,
            'other_total': metrics.other_total,
            'rules_match_count': metrics.rules_match_count,
            'rules_match_percentage': metrics.rules_match_percentage,
            'joinable_rules_count': metrics.joinable_rules_count,
            'matilda_recovered_count': metrics.matilda_recovered_count,
            'completeness_percentage': metrics.completeness_percentage,
        })
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Coverage metrics saved to: {output_file}")


def generate_latex_coverage_table(metrics_list: List[CoverageMetrics], output_dir: Path):
    """Generate LaTeX table with coverage comparison."""
    
    # Group by dataset
    by_dataset = {}
    for m in metrics_list:
        if m.dataset not in by_dataset:
            by_dataset[m.dataset] = []
        by_dataset[m.dataset].append(m)
    
    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{MATILDA Coverage Comparison}")
    lines.append(r"\label{tab:matilda_coverage}")
    lines.append(r"\begin{tabular}{l|l|rr|rr}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Dataset} & \textbf{Algorithm} & \multicolumn{2}{c|}{\textbf{Rules Match}} & \multicolumn{2}{c}{\textbf{Completeness}} \\")
    lines.append(r" & & \textbf{Count} & \textbf{\%} & \textbf{Count} & \textbf{\%} \\")
    lines.append(r"\hline")
    
    for dataset, metrics in sorted(by_dataset.items()):
        for i, m in enumerate(metrics):
            if i == 0:
                dataset_cell = f"\\multirow{{{len(metrics)}}}{{*}}{{{dataset}}}"
            else:
                dataset_cell = ""
            
            lines.append(
                f"{dataset_cell} & {m.algorithm} & "
                f"{m.rules_match_count}/{m.other_total} & {m.rules_match_percentage:.1f}\\% & "
                f"{m.matilda_recovered_count}/{m.joinable_rules_count} & {m.completeness_percentage:.1f}\\% \\\\"
            )
        
        lines.append(r"\hline")
    
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    
    latex_content = "\n".join(lines)
    output_file = output_dir / "coverage_table.tex"
    
    with open(output_file, 'w') as f:
        f.write(latex_content)
    
    print(f"✅ LaTeX table saved to: {output_file}")
    
    return latex_content


def main():
    """Main execution."""
    # Configuration
    output_dir = Path("data/output")
    datasets = ["Bupa", "BupaImperfect", "ComparisonDataset", "ImperfectTest"]
    other_algorithms = ["SPIDER", "ANYBURL", "POPPER"]
    
    print("🚀 Computing MATILDA Coverage Metrics")
    print("=" * 80)
    
    matcher = RuleMatcher(verbose=True)
    all_metrics = []
    
    for dataset in datasets:
        # Load MATILDA rules
        matilda_rules = load_results("MATILDA", dataset, output_dir)
        if not matilda_rules:
            print(f"⚠️  Skipping {dataset}: No MATILDA results")
            continue
        
        print(f"\n\n{'#'*80}")
        print(f"# Dataset: {dataset}")
        print(f"# MATILDA rules: {len(matilda_rules)}")
        print(f"{'#'*80}")
        
        for algorithm in other_algorithms:
            other_rules = load_results(algorithm, dataset, output_dir)
            if not other_rules:
                print(f"  ⚠️  Skipping {algorithm}: No results")
                continue
            
            # Compare
            metrics = matcher.compare_rule_sets(
                matilda_rules=matilda_rules,
                other_rules=other_rules,
                other_algorithm=algorithm,
                dataset=dataset
            )
            
            all_metrics.append(metrics)
    
    # Save results
    if all_metrics:
        print("\n\n" + "="*80)
        print("💾 Saving Results")
        print("="*80)
        save_coverage_metrics(all_metrics, output_dir)
        generate_latex_coverage_table(all_metrics, output_dir)
        
        print("\n\n" + "="*80)
        print("📊 Summary")
        print("="*80)
        for m in all_metrics:
            print(f"{m.dataset:20s} vs {m.algorithm:10s}: "
                  f"Match={m.rules_match_percentage:5.1f}%  "
                  f"Completeness={m.completeness_percentage:5.1f}%")
    else:
        print("\n⚠️  No metrics computed. Check that result files exist.")


if __name__ == "__main__":
    main()
