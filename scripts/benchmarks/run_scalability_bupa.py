#!/usr/bin/env python3
"""
Run scalability tests on Bupa-scaled datasets with proper timeouts.

Tests: Bupa (baseline), Bupa-100K, Bupa-500K, Bupa-1M
"""

import sys
import time
import json
import psutil
import subprocess
from pathlib import Path
from datetime import datetime


class ScalabilityTester:
    """Run MATILDA on scaled datasets with resource monitoring."""
    
    def __init__(self, output_dir: str = "results/scalability"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        
    def test_dataset(self, db_path: str, dataset_name: str, timeout: int = 1800):
        """
        Test MATILDA on a dataset with timeout and monitoring.
        
        :param db_path: Path to database
        :param dataset_name: Name for results
        :param timeout: Timeout in seconds (default 30min)
        """
        print(f"\n{'='*70}")
        print(f"🧪 Testing: {dataset_name}")
        print(f"📁 Database: {db_path}")
        print(f"⏱️  Timeout: {timeout}s ({timeout//60}min)")
        print(f"{'='*70}\n")
        
        if not Path(db_path).exists():
            print(f"❌ Database not found: {db_path}")
            return None
        
        # Get database size
        db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)
        print(f"📦 Database size: {db_size_mb:.1f} MB")
        
        # Prepare test script (with absolute path to avoid import issues)
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        src_path = os.path.join(project_root, 'src')
        
        test_code = f"""
import sys
import time
import os

# Add src to path using absolute path
project_root = r'{project_root}'
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Use absolute path for database
db_abs_path = os.path.join(project_root, '{db_path}')

start = time.time()
db = AlchemyUtility(f'sqlite:///{{db_abs_path}}')
m = MATILDA(db, {{'nb_occurrence': 3, 'max_table': 3, 'max_vars': 4}})
rules = list(m.discover_rules(traversal_algorithm='dfs', max_table=3, max_vars=4))
runtime = time.time() - start

print(f'RULES:{{len(rules)}}')
print(f'RUNTIME:{{runtime:.2f}}')
"""
        
        # Write temporary test script
        test_file = self.output_dir / f"test_{dataset_name}.py"
        test_file.write_text(test_code)
        
        # Run with timeout
        start_time = time.time()
        process = None
        
        try:
            # Start process
            process = subprocess.Popen(
                ['python3', str(test_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor resources
            max_memory_mb = 0
            max_cpu_percent = 0
            
            try:
                proc = psutil.Process(process.pid)
                
                while True:
                    # Check if process finished
                    if process.poll() is not None:
                        break
                    
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        print(f"\n⏱️  TIMEOUT after {elapsed:.1f}s")
                        process.terminate()
                        time.sleep(2)
                        if process.poll() is None:
                            process.kill()
                        
                        result = {
                            'dataset': dataset_name,
                            'db_path': db_path,
                            'db_size_mb': db_size_mb,
                            'status': 'TIMEOUT',
                            'timeout_seconds': timeout,
                            'rules': 0,
                            'runtime': elapsed,
                            'max_memory_mb': max_memory_mb,
                            'max_cpu_percent': max_cpu_percent,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.results.append(result)
                        return result
                    
                    # Get resource usage
                    try:
                        mem_info = proc.memory_info()
                        memory_mb = mem_info.rss / (1024 * 1024)
                        cpu_percent = proc.cpu_percent(interval=0.1)
                        
                        max_memory_mb = max(max_memory_mb, memory_mb)
                        max_cpu_percent = max(max_cpu_percent, cpu_percent)
                        
                        # Progress update every 60s
                        if int(elapsed) % 60 == 0 and int(elapsed) > 0:
                            print(f"  [{int(elapsed//60)}min] Memory: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    
                    time.sleep(1)
            
            except psutil.NoSuchProcess:
                pass
            
            # Get results
            stdout, stderr = process.communicate()
            runtime = time.time() - start_time
            
            # Parse output
            rules = 0
            reported_runtime = runtime
            for line in stdout.split('\n'):
                if line.startswith('RULES:'):
                    rules = int(line.split(':')[1])
                elif line.startswith('RUNTIME:'):
                    reported_runtime = float(line.split(':')[1])
            
            # Determine status
            if process.returncode == 0:
                status = 'SUCCESS'
                print(f"\n✅ SUCCESS")
                print(f"  Rules: {rules}")
                print(f"  Runtime: {reported_runtime:.2f}s ({reported_runtime/60:.1f}min)")
                print(f"  Rules/sec: {rules/reported_runtime if reported_runtime > 0 else 0:.2f}")
            else:
                status = 'ERROR'
                print(f"\n❌ ERROR (exit code {process.returncode})")
                if stderr:
                    print(f"  Error: {stderr[:500]}")
            
            result = {
                'dataset': dataset_name,
                'db_path': db_path,
                'db_size_mb': db_size_mb,
                'status': status,
                'rules': rules,
                'runtime': reported_runtime,
                'rules_per_second': rules / reported_runtime if reported_runtime > 0 else 0,
                'max_memory_mb': max_memory_mb,
                'max_cpu_percent': max_cpu_percent,
                'exit_code': process.returncode,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"\n❌ EXCEPTION: {e}")
            if process and process.poll() is None:
                process.kill()
            
            result = {
                'dataset': dataset_name,
                'db_path': db_path,
                'db_size_mb': db_size_mb,
                'status': 'EXCEPTION',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results.append(result)
            return result
    
    def save_results(self):
        """Save all results to JSON."""
        output_file = self.output_dir / f"scalability_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'results': self.results,
                'summary': self._generate_summary()
            }, f, indent=2)
        
        print(f"\n💾 Results saved: {output_file}")
        return output_file
    
    def _generate_summary(self):
        """Generate summary statistics."""
        successful = [r for r in self.results if r.get('status') == 'SUCCESS']
        
        return {
            'total_tests': len(self.results),
            'successful': len(successful),
            'timeouts': len([r for r in self.results if r.get('status') == 'TIMEOUT']),
            'errors': len([r for r in self.results if r.get('status') == 'ERROR']),
            'total_rules': sum(r.get('rules', 0) for r in successful),
            'total_runtime': sum(r.get('runtime', 0) for r in successful)
        }
    
    def print_summary(self):
        """Print summary table."""
        print(f"\n{'='*70}")
        print("📊 SCALABILITY TEST SUMMARY")
        print(f"{'='*70}\n")
        
        print(f"{'Dataset':<20} {'Status':<10} {'Rules':<10} {'Time':<12} {'Rate':<15}")
        print("-" * 70)
        
        for r in self.results:
            status = r.get('status', 'UNKNOWN')
            rules = r.get('rules', 0)
            runtime = r.get('runtime', 0)
            rate = f"{r.get('rules_per_second', 0):.2f} r/s" if status == 'SUCCESS' else '-'
            time_str = f"{runtime:.1f}s" if runtime < 300 else f"{runtime/60:.1f}min"
            
            status_icon = {
                'SUCCESS': '✅',
                'TIMEOUT': '⏱️ ',
                'ERROR': '❌',
                'EXCEPTION': '💥'
            }.get(status, '❓')
            
            print(f"{r['dataset']:<20} {status_icon} {status:<8} {rules:<10} {time_str:<12} {rate:<15}")
        
        print("\n" + "="*70)


def main():
    import os
    
    # Get absolute project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    tester = ScalabilityTester(str(project_root / "results" / "scalability"))
    
    # Test configuration: (db_path, name, timeout_seconds) - all absolute paths
    tests = [
        (str(project_root / "data/input/Bupa.db"), "Bupa-345", 180),                   # 3min (baseline - 345 tuples)
        (str(project_root / "data/large_scale/Bupa_1k.db"), "Bupa-1K", 600),          # 10min (1K tuples)
        (str(project_root / "data/large_scale/Bupa_5k.db"), "Bupa-5K", 1800),         # 30min (5K tuples)
        (str(project_root / "data/large_scale/Bupa_10k.db"), "Bupa-10K", 3600),       # 60min (10K tuples)
    ]
    
    print("\n🚀 Starting Scalability Tests")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🧪 {len(tests)} datasets to test\n")
    
    for db_path, name, timeout in tests:
        tester.test_dataset(db_path, name, timeout)
    
    # Save and display results
    tester.save_results()
    tester.print_summary()


if __name__ == "__main__":
    main()
