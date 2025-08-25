#!/usr/bin/env python
"""
Helper script to start Celery worker and beat scheduler for development.

This script provides an easy way to start both the Celery worker and beat
scheduler processes for the notification system.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

def start_celery_services():
    """Start Celery worker and beat scheduler"""
    
    # Ensure we're in the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("🚀 Starting Celery services for notification system...")
    
    processes = []
    
    try:
        # Start Celery worker
        print("📝 Starting Celery worker...")
        worker_cmd = [
            sys.executable, '-m', 'celery', 
            '-A', 'real_estate_management', 
            'worker', 
            '--loglevel=info',
            '--concurrency=2',
            '--queues=notifications,celery'
        ]
        
        worker_process = subprocess.Popen(
            worker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(('worker', worker_process))
        
        # Give worker time to start
        time.sleep(3)
        
        # Start Celery beat scheduler
        print("⏰ Starting Celery beat scheduler...")
        beat_cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'real_estate_management',
            'beat',
            '--loglevel=info',
            '--scheduler=django_celery_beat.schedulers:DatabaseScheduler'
        ]
        
        beat_process = subprocess.Popen(
            beat_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(('beat', beat_process))
        
        print("✅ Celery services started successfully!")
        print("\nRunning processes:")
        for name, process in processes:
            print(f"  - {name}: PID {process.pid}")
        
        print("\n📊 To monitor tasks, you can also run:")
        print("  python -m celery -A real_estate_management flower")
        
        print("\n🛑 Press Ctrl+C to stop all services")
        
        # Monitor processes
        while True:
            time.sleep(1)
            
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print(f"❌ {name} process died with return code {process.returncode}")
                    return
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping Celery services...")
        
        # Terminate all processes
        for name, process in processes:
            print(f"Stopping {name}...")
            process.terminate()
            
        # Wait for processes to terminate
        for name, process in processes:
            try:
                process.wait(timeout=10)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
                process.wait()
                
        print("✅ All Celery services stopped")
        
    except Exception as e:
        print(f"❌ Error starting Celery services: {e}")
        
        # Clean up any started processes
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()


if __name__ == '__main__':
    start_celery_services()