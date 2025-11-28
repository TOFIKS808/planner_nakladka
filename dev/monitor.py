import time
import sys
import os

try:
    import psutil
except ImportError:
    print("Error: 'psutil' module is not installed.")
    print("Please install it using: pip install psutil")
    sys.exit(1)

def find_main_process():
    """Finds the process running 'main.py'."""
    current_pid = os.getpid()
    candidates = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            # Skip the current process (this monitor script)
            if proc.pid == current_pid:
                continue
                
            if proc.info['cmdline'] and any('main.py' in arg for arg in proc.info['cmdline']):
                candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if not candidates:
        return None
        
    # Sort by memory usage (RSS) descending to find the main application
    # The main app will likely use more memory than a wrapper or simple script
    candidates.sort(key=lambda p: p.info['memory_info'].rss, reverse=True)
    
    # Log candidates for debugging
    print(f"Found {len(candidates)} candidate processes:")
    for p in candidates:
        mem_mb = p.info['memory_info'].rss / (1024 * 1024)
        print(f" - PID: {p.pid}, Name: {p.info['name']}, Memory: {mem_mb:.2f} MB, Cmd: {p.info['cmdline']}")
        
    return candidates[0]

def monitor():
    print("Searching for 'main.py' process...")
    proc = find_main_process()
    
    if not proc:
        print("Could not find 'main.py' running.")
        print("Please make sure the application is started.")
        return

    log_file_path = os.path.join(os.path.dirname(__file__), 'monitor.log')
    
    print(f"Found process: {proc.info['name']} (PID: {proc.info['pid']})")
    print(f"Logging to: {log_file_path}")
    print("-" * 55)
    header = f"{'Time':<10} | {'CPU %':<10} | {'Memory (MB)':<15} | {'Status':<10}"
    print(header)
    print("-" * 55)

    try:
        # Initial call to cpu_percent returns 0, so we ignore it or wait
        proc.cpu_percent(interval=None)
        
        # Initialize file with header
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            log_file.write(f"{header}\n")
            log_file.write("-" * 55 + "\n")

        while True:
            if not proc.is_running():
                print("\nProcess ended.")
                break
            
            # Get metrics
            # interval=1.0 blocks for 1 second to calculate CPU usage
            cpu = proc.cpu_percent(interval=1.0)
            
            try:
                mem_info = proc.memory_info()
                mem_mb = mem_info.rss / (1024 * 1024)
                status = proc.status()
            except psutil.NoSuchProcess:
                print("\nProcess ended.")
                break

            current_time = time.strftime("%H:%M:%S")
            log_line = f"{current_time:<10} | {cpu:<10.1f} | {mem_mb:<15.2f} | {status:<10}"
            print(log_line)
            
            # Log to file (append mode, open/close every time to ensure immediate update)
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"{log_line}\n")
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except psutil.NoSuchProcess:
        print("\nProcess ended.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    monitor()
