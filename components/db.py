import threading
import time
from simulators.db import run_db_simulator

def db_callback(state):
    t = time.localtime()
    status = "BUZZ" if state else "SILENCE"
    print(f"[{time.strftime('%H:%M:%S', t)}] DB: {status}")

def run_db(settings, threads, stop_event):
    if settings['simulated']:
        print("Starting DB simulator (Hold 'B' to buzz)")
        db_thread = threading.Thread(target=run_db_simulator, args=(db_callback, stop_event))
        db_thread.start()
        threads.append(db_thread)
    else:
        from actuators.db import run_db_loop, DB
        print("Starting DB Real Loop (Hold 'B' to buzz)")

        door_buzzer = DB(settings['pin'], db_callback)

        db_thread = threading.Thread(target=run_db_loop, args=(door_buzzer, stop_event))
        db_thread.start()
        threads.append(db_thread)