# main.py
from gui.main import MainApplication
import tkinter as tk
import runtime_config

def main():
    bundle_dir = runtime_config.setup_runtime_environment()
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()
