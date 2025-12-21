import time
import keyboard

def run_db_simulator(callback, stop_event):

    def on_press(e):
        callback(True)

    def on_release(e):
        callback(False)

    h1 = keyboard.on_press_key('b', on_press, suppress=True)
    h2 = keyboard.on_release_key('b', on_release, suppress=True)

    while not stop_event.is_set():
        time.sleep(0.1)

    keyboard.unhook(h1)
    keyboard.unhook(h2)