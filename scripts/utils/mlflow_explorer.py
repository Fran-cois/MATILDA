#!/usr/bin/env python3
"""
MLflow Experiment Explorer

Utility to explore and analyze MLflow-like benchmark experiments.

Usage:
    python mlflow_explorer.py list
    python mlflow_explorer.py show <experiment_id>
    python mlflow_explorer.py compare <exp_id1> <exp_id2>
    python mlflow_explorer.py runs <experiment_id>
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys


class MLflowExplorer:
    """Explorer for MLflow-like experiment tracking."""
    
    def __init__(self, mlruns_dir: Path = Path("data/output/mlruns")):
        self.mlruns_dir = mlruns_dir
    
    def list_experiments(self):
        """List all experiments."""
        if not self.mlruns_dir.exists():
            print("No experiments found.")
            return
        
        experiments = []
        for exp_dir in self.mlruns_dir.iterdir():
            if exp_dir.is_dir():
                meta_file = exp_dir / "experiment_meta.json"
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)
                        experiments.append(meta)
        
        if not experiments:
            print("No experiments found.")
            return
        
        print(f"\n{'='*80}")
        print(f"{'ID':<12} {'Name':<30} {'Created':<20} {'Status':<10}")
        print(f"{'='*80}")
        
        for exp in sorted(experiments, key=lambda x: x.get('creation_time', ''), reverse=True):
            exp_id = exp['experiment_id']
            name = exp['name'][:28] + ".." if len(exp['name']) > 30 else exp['name']
            created = exp.get('creation_time', 'N/A')
            status = exp.get('lifecycle_stage', 'N/A')
            print(f"{exp_id:<12} {name:<30} {created:<20} {status:<10}")
        
        print(f"{'='*80}\n")
        print(f"Total experiments: {len(experiments)}")
        print(f"Location: {self.mlruns_dir.absolute()}\n")
    
    def show_experiment(self, experiment_id: str):
        """Show detailed information about an experiment."""
        exp_dir = self.mlruns_dir / experiment_id
        
        if not exp_dir.exists():
            print(f"❌ Experiment {experiment_id} not found.")
            return
        
        # Load metadata
        meta_file = exp_dir / "experiment_meta.json"
        with open(meta_file) as f:
            meta = json.load(f)
        
        # Load runs
        runs_file = exp_dir / "runs.json"
        runs = []
        if runs_file.exists():
            with open(runs_file) as f:
                runs = json.load(f)
        
        # Load summary
        summary_file = exp_dir / "summary.json"
        summary = {}
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)
        
        # Display
        print(f"\n{'='*80}")
        print(f"EXPERIMENT: {meta['name']}")
        print(f"{'='*80}")
        print(f"ID:           {meta['experiment_id']}")
        print(f"Location:     {meta['artifact_location']}")
        print(f"Status:       {meta.get('lifecycle_stage', 'N/A')}")
        print(f"Created:      {meta.get('creation_time', 'N/A')}")
        print(f"Last Update:  {meta.get('last_update_time', 'N/A')}")
        
        print(f"\n{'='*80}")
        print("CONFIGURATION")
        print(f"{'='*80}")
        for key, value in meta.get('tags', {}).items():
            print(f"  {key}: {value}")
        
        print(f"\n{'='*80}")
        print(f"RUNS ({len(runs)} total)")
        print(f"{'='*80}")
        
        finished = sum(1 for r in runs if r['info']['status'] == 'FINISHED')
        failed = sum(1 for r in runs if r['info']['status'] == 'FAILED')
        running = sum(1 for r in runs if r['info']['status'] == 'RUNNING')
        
        print(f"  ✓ Finished: {finished}")
        print(f"  ✗ Failed:   {failed}")
        print(f"  ⏳ Running:  {running}")
        
        if summary:
            print(f"\n{'='*80}")
            print("SUMMARY STATISTICS")
            print(f"{'='*80}")
            
            for key, data in summary.items():
                algo = data['algorithm']
                dataset = data['dataset']
                metrics = data.get('metrics', {})
                
                print(f"\n{algo} on {dataset}:")
                print(f"  Runs: {len(data['runs'])}")
                
                if 'num_rules' in metrics:
                    nr = metrics['num_rules']
                    print(f"  Rules:      {nr['mean']:.1f} ± {nr['std']:.1f} (min={nr['min']}, max={nr['max']})")
                
                if 'accuracy' in metrics:
                    acc = metrics['accuracy']
                    print(f"  Accuracy:   {acc['mean']:.3f} ± {acc['std']:.3f}")
                
                if 'confidence' in metrics:
                    conf = metrics['confidence']
                    print(f"  Confidence: {conf['mean']:.3f} ± {conf['std']:.3f}")
                
                if 'duration_seconds' in metrics:
                    dur = metrics['duration_seconds']
                    print(f"  Duration:   {dur['mean']:.2f}s ± {dur['std']:.2f}s")
        
        print(f"\n{'='*80}\n")
    
    def list_runs(self, experiment_id: str, status: str = None):
        """List all runs in an experiment."""
        exp_dir = self.mlruns_dir / experiment_id
        
        if not exp_dir.exists():
            print(f"❌ Experiment {experiment_id} not found.")
            return
        
        runs_file = exp_dir / "runs.json"
        if not runs_file.exists():
            print("No runs found.")
            return
        
        with open(runs_file) as f:
            runs = json.load(f)
        
        if status:
            runs = [r for r in runs if r['info']['status'] == status.upper()]
        
        print(f"\n{'='*80}")
        print(f"RUNS for experiment {experiment_id}")
        print(f"{'='*80}")
        print(f"{'Run ID':<20} {'Name':<35} {'Status':<10} {'Duration':<10}")
        print(f"{'='*80}")
        
        for run in runs:
            run_id = run['info']['run_id']
            name = run['info']['run_name'][:33] + ".." if len(run['info']['run_name']) > 35 else run['info']['run_name']
            status = run['info']['status']
            
            duration = "N/A"
            if 'duration_seconds' in run.get('metrics', {}):
                duration = f"{run['metrics']['duration_seconds']:.2f}s"
            
            print(f"{run_id:<20} {name:<35} {status:<10} {duration:<10}")
        
        print(f"{'='*80}")
        print(f"Total runs: {len(runs)}\n")
    
    def show_run(self, experiment_id: str, run_id: str):
        """Show detailed information about a specific run."""
        exp_dir = self.mlruns_dir / experiment_id
        run_dir = exp_dir / run_id
        
        if not run_dir.exists():
            # Try to find run in runs.json
            runs_file = exp_dir / "runs.json"
            if runs_file.exists():
                with open(runs_file) as f:
                    runs = json.load(f)
                    run = next((r for r in runs if r['info']['run_id'].startswith(run_id)), None)
                    
                    if run:
                        print(f"\n{'='*80}")
                        print(f"RUN: {run['info']['run_name']}")
                        print(f"{'='*80}")
                        print(f"Run ID:    {run['info']['run_id']}")
                        print(f"Status:    {run['info']['status']}")
                        print(f"Started:   {run['info']['start_time']}")
                        print(f"Finished:  {run['info']['end_time']}")
                        
                        print(f"\n{'='*80}")
                        print("PARAMETERS")
                        print(f"{'='*80}")
                        for key, value in run.get('params', {}).items():
                            print(f"  {key}: {value}")
                        
                        print(f"\n{'='*80}")
                        print("METRICS")
                        print(f"{'='*80}")
                        for key, value in run.get('metrics', {}).items():
                            print(f"  {key}: {value}")
                        
                        print(f"\n{'='*80}\n")
                        return
            
            print(f"❌ Run {run_id} not found in experiment {experiment_id}.")
            return
    
    def compare_experiments(self, exp_id1: str, exp_id2: str):
        """Compare two experiments."""
        exp_dir1 = self.mlruns_dir / exp_id1
        exp_dir2 = self.mlruns_dir / exp_id2
        
        if not exp_dir1.exists() or not exp_dir2.exists():
            print("❌ One or both experiments not found.")
            return
        
        # Load summaries
        summary1 = {}
        summary2 = {}
        
        summary_file1 = exp_dir1 / "summary.json"
        if summary_file1.exists():
            with open(summary_file1) as f:
                summary1 = json.load(f)
        
        summary_file2 = exp_dir2 / "summary.json"
        if summary_file2.exists():
            with open(summary_file2) as f:
                summary2 = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"COMPARISON: {exp_id1} vs {exp_id2}")
        print(f"{'='*80}\n")
        
        # Find common algorithm/dataset combinations
        keys1 = set(summary1.keys())
        keys2 = set(summary2.keys())
        common_keys = keys1.intersection(keys2)
        
        if not common_keys:
            print("No common algorithm/dataset combinations found.")
            return
        
        for key in sorted(common_keys):
            data1 = summary1[key]
            data2 = summary2[key]
            
            print(f"\n{data1['algorithm']} on {data1['dataset']}:")
            print(f"{'='*80}")
            print(f"{'Metric':<20} {'Exp1':<25} {'Exp2':<25} {'Diff':<15}")
            print(f"{'-'*80}")
            
            metrics1 = data1.get('metrics', {})
            metrics2 = data2.get('metrics', {})
            
            for metric_name in ['num_rules', 'accuracy', 'confidence', 'duration_seconds']:
                if metric_name in metrics1 and metric_name in metrics2:
                    m1 = metrics1[metric_name]
                    m2 = metrics2[metric_name]
                    
                    val1 = f"{m1['mean']:.3f} ± {m1['std']:.3f}"
                    val2 = f"{m2['mean']:.3f} ± {m2['std']:.3f}"
                    diff = m2['mean'] - m1['mean']
                    diff_pct = (diff / m1['mean'] * 100) if m1['mean'] != 0 else 0
                    diff_str = f"{diff:+.3f} ({diff_pct:+.1f}%)"
                    
                    print(f"{metric_name:<20} {val1:<25} {val2:<25} {diff_str:<15}")
        
        print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Explore MLflow-like benchmark experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List experiments
    subparsers.add_parser('list', help='List all experiments')
    
    # Show experiment
    show_parser = subparsers.add_parser('show', help='Show experiment details')
    show_parser.add_argument('experiment_id', help='Experiment ID')
    
    # List runs
    runs_parser = subparsers.add_parser('runs', help='List runs in an experiment')
    runs_parser.add_argument('experiment_id', help='Experiment ID')
    runs_parser.add_argument('--status', choices=['FINISHED', 'FAILED', 'RUNNING'], help='Filter by status')
    
    # Show run
    run_parser = subparsers.add_parser('run', help='Show run details')
    run_parser.add_argument('experiment_id', help='Experiment ID')
    run_parser.add_argument('run_id', help='Run ID (can be partial)')
    
    # Compare experiments
    compare_parser = subparsers.add_parser('compare', help='Compare two experiments')
    compare_parser.add_argument('exp_id1', help='First experiment ID')
    compare_parser.add_argument('exp_id2', help='Second experiment ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    explorer = MLflowExplorer()
    
    if args.command == 'list':
        explorer.list_experiments()
    elif args.command == 'show':
        explorer.show_experiment(args.experiment_id)
    elif args.command == 'runs':
        explorer.list_runs(args.experiment_id, args.status)
    elif args.command == 'run':
        explorer.show_run(args.experiment_id, args.run_id)
    elif args.command == 'compare':
        explorer.compare_experiments(args.exp_id1, args.exp_id2)


if __name__ == "__main__":
    main()
