#!/usr/bin/env python3
"""
Resource monitoring tool for MATILDA stress testing.

Monitors and logs:
- CPU usage (%)
- Memory usage (RSS, VMS)
- Disk I/O
- Execution time
- Process status

Can be used standalone or integrated with stress test scripts.
"""

import argparse
import psutil
import time
import json
import csv
from pathlib import Path
from typing import Dict, Any, Optional
import sys
from datetime import datetime


class ResourceMonitor:
    """Monitor system resources during MATILDA execution."""
    
    def __init__(self, output_file: str = None, interval: float = 1.0):
        """
        Initialize monitor.
        
        :param output_file: Path to save monitoring data (JSON or CSV).
        :param interval: Sampling interval in seconds.
        """
        self.output_file = output_file
        self.interval = interval
        self.samples = []
        self.start_time = None
        self.process = None
    
    def attach_to_process(self, pid: int):
        """
        Attach to existing process.
        
        :param pid: Process ID to monitor.
        """
        try:
            self.process = psutil.Process(pid)
            print(f"✓ Attached to process {pid}: {self.process.name()}")
        except psutil.NoSuchProcess:
            print(f"ERROR: Process {pid} not found")
            sys.exit(1)
    
    def attach_to_current_process(self):
        """Attach to current Python process."""
        self.process = psutil.Process()
        print(f"✓ Monitoring current process: {self.process.pid}")
    
    def sample_resources(self) -> Dict[str, Any]:
        """
        Take a single resource usage sample.
        
        :return: Dictionary with resource metrics.
        """
        if not self.process:
            self.attach_to_current_process()
        
        try:
            # CPU
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Memory
            mem_info = self.process.memory_info()
            mem_rss_mb = mem_info.rss / (1024 * 1024)
            mem_vms_mb = mem_info.vms / (1024 * 1024)
            
            # System memory
            sys_mem = psutil.virtual_memory()
            sys_mem_percent = sys_mem.percent
            
            # Disk I/O (if available)
            try:
                io_counters = self.process.io_counters()
                disk_read_mb = io_counters.read_bytes / (1024 * 1024)
                disk_write_mb = io_counters.write_bytes / (1024 * 1024)
            except (AttributeError, psutil.AccessDenied):
                disk_read_mb = None
                disk_write_mb = None
            
            # Threads
            num_threads = self.process.num_threads()
            
            # Timestamp
            elapsed = time.time() - self.start_time if self.start_time else 0
            
            sample = {
                'timestamp': time.time(),
                'elapsed_seconds': round(elapsed, 2),
                'cpu_percent': round(cpu_percent, 2),
                'memory_rss_mb': round(mem_rss_mb, 2),
                'memory_vms_mb': round(mem_vms_mb, 2),
                'system_memory_percent': round(sys_mem_percent, 2),
                'disk_read_mb': round(disk_read_mb, 2) if disk_read_mb else None,
                'disk_write_mb': round(disk_write_mb, 2) if disk_write_mb else None,
                'num_threads': num_threads,
                'process_status': self.process.status(),
            }
            
            return sample
        
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Warning: Could not sample resources: {e}")
            return None
    
    def start_monitoring(self, duration: Optional[float] = None):
        """
        Start monitoring loop.
        
        :param duration: Duration in seconds (None = infinite).
        """
        print(f"\n{'='*70}")
        print("📊 RESOURCE MONITORING STARTED")
        print(f"{'='*70}")
        print(f"Interval: {self.interval}s")
        if duration:
            print(f"Duration: {duration}s")
        if self.output_file:
            print(f"Output: {self.output_file}")
        print(f"{'='*70}\n")
        
        self.start_time = time.time()
        end_time = self.start_time + duration if duration else None
        
        try:
            while True:
                sample = self.sample_resources()
                if sample:
                    self.samples.append(sample)
                    self._print_sample(sample)
                
                # Check duration
                if end_time and time.time() >= end_time:
                    break
                
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
        
        finally:
            self._save_results()
            self._print_summary()
    
    def _print_sample(self, sample: Dict[str, Any]):
        """Print sample to console."""
        print(f"[{sample['elapsed_seconds']:>6.1f}s] "
              f"CPU: {sample['cpu_percent']:>5.1f}% | "
              f"MEM: {sample['memory_rss_mb']:>8.1f} MB | "
              f"SYS: {sample['system_memory_percent']:>5.1f}% | "
              f"Threads: {sample['num_threads']:>2}")
    
    def _save_results(self):
        """Save monitoring results to file."""
        if not self.output_file or not self.samples:
            return
        
        Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
        
        if self.output_file.endswith('.json'):
            with open(self.output_file, 'w') as f:
                json.dump(self.samples, f, indent=2)
            print(f"\n✓ Saved {len(self.samples)} samples to {self.output_file}")
        
        elif self.output_file.endswith('.csv'):
            with open(self.output_file, 'w', newline='') as f:
                if self.samples:
                    writer = csv.DictWriter(f, fieldnames=self.samples[0].keys())
                    writer.writeheader()
                    writer.writerows(self.samples)
            print(f"\n✓ Saved {len(self.samples)} samples to {self.output_file}")
    
    def _print_summary(self):
        """Print monitoring summary."""
        if not self.samples:
            return
        
        # Calculate statistics
        cpu_values = [s['cpu_percent'] for s in self.samples]
        mem_values = [s['memory_rss_mb'] for s in self.samples]
        
        cpu_avg = sum(cpu_values) / len(cpu_values)
        cpu_max = max(cpu_values)
        mem_avg = sum(mem_values) / len(mem_values)
        mem_max = max(mem_values)
        
        duration = self.samples[-1]['elapsed_seconds']
        
        print(f"\n{'='*70}")
        print("📈 MONITORING SUMMARY")
        print(f"{'='*70}")
        print(f"Duration:        {duration:.2f}s")
        print(f"Samples:         {len(self.samples)}")
        print(f"\nCPU Usage:")
        print(f"  Average:       {cpu_avg:.2f}%")
        print(f"  Peak:          {cpu_max:.2f}%")
        print(f"\nMemory Usage (RSS):")
        print(f"  Average:       {mem_avg:.2f} MB")
        print(f"  Peak:          {mem_max:.2f} MB")
        print(f"{'='*70}")


def monitor_command(command: list, output_file: str = None, 
                   interval: float = 1.0) -> int:
    """
    Execute command and monitor its resource usage.
    
    :param command: Command to execute (list of args).
    :param output_file: Path to save monitoring data.
    :param interval: Sampling interval in seconds.
    :return: Exit code of command.
    """
    import subprocess
    
    print(f"🚀 Launching command: {' '.join(command)}\n")
    
    # Start process
    process = subprocess.Popen(command)
    
    # Monitor
    monitor = ResourceMonitor(output_file, interval)
    monitor.attach_to_process(process.pid)
    
    # Start monitoring in separate thread
    import threading
    monitor_thread = threading.Thread(
        target=lambda: monitor.start_monitoring()
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Wait for process to complete
    try:
        return_code = process.wait()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted, terminating process...")
        process.terminate()
        process.wait()
        return_code = -1
    
    # Stop monitoring
    time.sleep(interval * 2)  # Allow final samples
    monitor._save_results()
    monitor._print_summary()
    
    return return_code


def main():
    parser = argparse.ArgumentParser(
        description='Monitor system resources during MATILDA execution.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor current process for 60 seconds
  python scripts/utils/monitor_resources.py --duration 60 --output monitoring.json
  
  # Monitor specific process
  python scripts/utils/monitor_resources.py --pid 12345 --output monitoring.csv
  
  # Monitor a command
  python scripts/utils/monitor_resources.py --command "python src/main.py" --output monitoring.json
  
  # Integration with stress test
  python scripts/utils/monitor_resources.py --command \
    "python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db" \
    --output results/monitoring_1M.json --interval 2
        """
    )
    
    parser.add_argument('--pid', type=int,
                       help='Process ID to monitor')
    parser.add_argument('--command', nargs='+',
                       help='Command to execute and monitor')
    parser.add_argument('--duration', type=float,
                       help='Monitoring duration in seconds (for current/pid mode)')
    parser.add_argument('--interval', type=float, default=1.0,
                       help='Sampling interval in seconds (default: 1.0)')
    parser.add_argument('--output', '-o',
                       help='Output file (.json or .csv)')
    
    args = parser.parse_args()
    
    if args.command:
        # Monitor command
        return monitor_command(args.command, args.output, args.interval)
    
    else:
        # Monitor process
        monitor = ResourceMonitor(args.output, args.interval)
        
        if args.pid:
            monitor.attach_to_process(args.pid)
        else:
            monitor.attach_to_current_process()
        
        monitor.start_monitoring(args.duration)
        return 0


if __name__ == '__main__':
    sys.exit(main())
