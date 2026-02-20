import threading
from simulators.db import run_db_simulator

def run_db(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DB simulator.")
        db_thread = threading.Thread(
            target=run_db_simulator,
            args=(callback, stop_event),
            daemon=True
        )
        db_thread.start()
        threads.append(db_thread)
        return None
    else:
        from actuators.db import DB
        print("Starting DB real device.")
        db = DB(settings)
        return db