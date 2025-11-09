#!/usr/bin/env python3
"""
Kill processes using specific ports
Cross-platform port killer using Python's psutil or basic methods
"""
import os
import sys
import signal

def kill_port_basic(port):
    """Kill process on port using basic system commands"""
    import subprocess

    # Try to find and kill the process
    try:
        # For Linux/Unix systems
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            # Try lsof
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                print(f"  [Python] Killing process {pid} on port {port}")
                os.kill(pid, signal.SIGKILL)
                return True
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError):
        pass

    return False

def kill_port_psutil(port):
    """Kill process on port using psutil library"""
    try:
        import psutil

        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"  [psutil] Killing process {proc.pid} ({proc.name()}) on port {port}")
                        proc.kill()
                        proc.wait(timeout=3)
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        pass

    return False

def kill_ports(ports):
    """Kill processes on specified ports"""
    for port in ports:
        # Try psutil first (more reliable)
        if not kill_port_psutil(port):
            # Fall back to basic method
            kill_port_basic(port)

if __name__ == '__main__':
    # Kill Flask port
    ports_to_kill = [5000]

    # Add XKOP ports (8001-8020)
    ports_to_kill.extend(range(8001, 8021))

    kill_ports(ports_to_kill)
