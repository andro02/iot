import threading
from simulators.dl import run_dl_simulator

def run_dl(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DL simulator.")
        dl_thread = threading.Thread(
            target=run_dl_simulator,
            args=(callback, stop_event),
            daemon=True
        )
        dl_thread.start()
        threads.append(dl_thread)
        return None
    else:
        from actuators.dl import DL
        print("Starting DL real device.")
        dl = DL(settings['pin'], callback)
        return dl