import threading
import time
from simulators.db import run_db_simulator

def run_db(settings, threads, stop_event, callback):
    if settings['simulated']:
        print("Starting DB simulator (Hold 'B' to buzz)")
        db_thread = threading.Thread(target=run_db_simulator, args=(callback, stop_event))
        db_thread.start()
        threads.append(db_thread)
    else:
        from actuators.db import run_db_loop, DB
        print("Starting DB Real Loop (Hold 'B' to buzz)")
        
        door_buzzer = DB(settings['pin'], callback)
        
        db_thread = threading.Thread(target=run_db_loop, args=(door_buzzer, stop_event))
        db_thread.start()
        threads.append(db_thread)