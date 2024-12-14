import multiprocessing
import sys
from proxy import ProxyServer
from server import Server
import time


def start_worker(port):
    """Start a worker server in its own process"""
    worker = Server(port)
    try:
        worker.run()
    except KeyboardInterrupt:
        print(f"Worker {port} shutting down...")
    except Exception as e:
        print(f"Worker {port} failed: {e}")
    finally:
        sys.exit(0)

def start_proxy(proxy_port, worker_ports):
    """Start the proxy server in its own process"""
    proxy = ProxyServer(proxy_port, worker_ports)
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("Proxy server shutting down...")
    except Exception as e:
        print(f"Proxy server failed: {e}")
    finally:
        sys.exit(0)

def main():
    worker_ports = ['9001', '9002', '9003', '9004', '9005']
    proxy_port = 9000
    
    worker_processes = []
    for port in worker_ports:
        process = multiprocessing.Process(
            target=start_worker,
            args=(port,),
            name=f"worker-{port}"
        )
        process.daemon = True
        process.start()
        worker_processes.append(process)
        
    proxy_process = multiprocessing.Process(
        target=start_proxy,
        args=(proxy_port, worker_ports),
        name="proxy"
    )
    proxy_process.start()
    
    try:
        while True:
            for i, process in enumerate(worker_processes):
                if not process.is_alive():
                    port = worker_ports[i]
                    print(f"Worker {port} died, restarting...")
                    
                    new_process = multiprocessing.Process(
                        target=start_worker,
                        args=(port,),
                        name=f"worker-{port}"
                    )
                    new_process.daemon = True
                    new_process.start()
                    worker_processes[i] = new_process
                    
            if not proxy_process.is_alive():
                print("Proxy server died, restarting...")
                proxy_process = multiprocessing.Process(
                    target=start_proxy,
                    args=(proxy_port, worker_ports),
                    name="proxy"
                )
                proxy_process.start()
                
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down all servers...")
        for process in worker_processes:
            process.terminate()
            process.join()
        proxy_process.terminate()
        proxy_process.join()
        
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    main()