import keyboard

def run_dl_simulator(callback, stop_event):
      is_on = False

      def on_press(e):
            nonlocal is_on
            if e.event_type == keyboard.KEY_DOWN:
                  is_on = not is_on
                  callback(is_on)

      hook = keyboard.hook_key('l', on_press, suppress=True)      
      stop_event.wait()
      keyboard.unhook(hook)













# import time

# class DL(object):
#     def __init__(self, pin):
#         self.pin = pin
#         self.state = False
    
#     def turn_on(self):
#         if not self.state:
#             self.state = True
#             t = time.localtime()
#             print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT ON")
        
#     def turn_off(self):
#         if self.state:
#             self.state = False
#             t = time.localtime()
#             print(f"[{time.strftime('%H:%M:%S', t)}] DL: LIGHT OFF")