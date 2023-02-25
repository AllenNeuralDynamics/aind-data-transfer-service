import tkinter as tk
from tkinter import ttk
from screeninfo import get_monitors


def run_app():

    root = tk.Tk()
    root.title("AIND Data Upload App")
    monitor_info = get_monitors()[0]
    monitor_width = monitor_info.width
    monitor_height = monitor_info.height
    app_width = int(0.8*monitor_width)
    app_height = int(0.8*monitor_height)

    root.geometry(f"{app_width}x{app_height}")
    tabControl = ttk.Notebook(root)

    tab1 = ttk.Frame(tabControl)
    tab2 = ttk.Frame(tabControl)

    tabControl.add(tab1, text='Collect Metadata')
    tabControl.add(tab2, text='Upload Data')
    tabControl.pack(expand=1, fill="both")

    ttk.Label(tab1,
          text="subject_id: ").grid(column=0,
                               row=0,
                               pady=30)
    ttk.Label(tab2,
          text="Upload data:").grid(column=0,
                                    row=0,
                                    padx=10,
                                    pady=30)
    subject_id_entry = ttk.Entry(tab1)
    subject_id_entry.grid(row=0, column=1)
    root.mainloop()


if __name__ == "__main__":
    run_app()
