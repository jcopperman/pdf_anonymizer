import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.ttk import Button, Label, Checkbutton, Frame, Style
from anonymizer.core import PDFAnonymizer
import os

class MainApplication:
    def __init__(self, master):
        self.master = master
        self.master.title("PDF Anonymizer")
        self.master.geometry("600x700")
        self.master.resizable(False, False)
        
        # Configure style
        style = Style()
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Section.TFrame', relief='groove', padding=10)
        
        self.pdf_anonymizer = PDFAnonymizer()
        self.input_file = tk.StringVar()
        self.selected_categories = {}
        
        self.create_widgets()

    def create_widgets(self):
        # Main container with padding
        main_container = Frame(self.master, padding="20 20 20 20")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        Label(header_frame, text="PDF Anonymizer Tool", style='Header.TLabel').pack()

        # File Selection Section
        file_frame = Frame(main_container, style='Section.TFrame')
        file_frame.pack(fill=tk.X, pady=(0, 20))
        
        Label(file_frame, text="Select PDF File", style='Header.TLabel').pack(pady=(0, 10))
        
        file_select_frame = Frame(file_frame)
        file_select_frame.pack(fill=tk.X)
        
        self.file_entry = ttk.Entry(file_select_frame, textvariable=self.input_file, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        Button(file_select_frame, text="Browse", command=self.select_input_file).pack(side=tk.LEFT)

        # PII Detection Section
        detection_frame = Frame(main_container, style='Section.TFrame')
        detection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        Label(detection_frame, text="PII Detection", style='Header.TLabel').pack(pady=(0, 10))
        
        Button(detection_frame, text="Detect PII", command=self.detect_pii, width=20).pack(pady=(0, 10))
        
        # Categories Section
        self.categories_frame = Frame(detection_frame)
        self.categories_frame.pack(fill=tk.BOTH, expand=True)

        # Action Buttons
        button_frame = Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        Button(button_frame, text="Anonymize PDF", command=self.anonymize_pdf, width=20).pack()

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = Label(main_container, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def select_input_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.input_file.set(file_path)
            self.status_var.set("File selected: " + os.path.basename(file_path))

    def detect_pii(self):
        input_path = self.input_file.get()
        if not input_path:
            messagebox.showerror("Error", "Please select an input file.")
            return
        
        try:
            self.status_var.set("Detecting PII...")
            self.master.update()
            
            categories = self.pdf_anonymizer.detect_pii(input_path)
            self.display_categories(categories)
            
            self.status_var.set("PII detection completed")
        except Exception as e:
            self.status_var.set("Error detecting PII")
            messagebox.showerror("Error", f"Failed to detect PII: {e}")

    def display_categories(self, categories):
        # Clear previous category options
        for widget in self.categories_frame.winfo_children():
            widget.destroy()

        if not categories:
            Label(self.categories_frame, text="No PII detected").pack(pady=10)
            return

        # Create scrollable frame for categories
        canvas = tk.Canvas(self.categories_frame)
        scrollbar = ttk.Scrollbar(self.categories_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add categories with count
        self.selected_categories = {}
        for category, matches in categories.items():
            var = tk.BooleanVar(value=True)
            self.selected_categories[category] = var
            
            category_frame = Frame(scrollable_frame)
            category_frame.pack(fill=tk.X, pady=2)
            
            Checkbutton(category_frame, text=f"{category} ({len(matches)})", variable=var).pack(side=tk.LEFT)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def anonymize_pdf(self):
        input_path = self.input_file.get()
        if not input_path:
            messagebox.showerror("Error", "Please select an input file.")
            return

        # Generate output path by appending -anonymized
        file_name, file_ext = os.path.splitext(input_path)
        output_path = f"{file_name}-anonymized{file_ext}"
        
        selected_categories = {cat: var.get() for cat, var in self.selected_categories.items()}
        
        try:
            self.status_var.set("Anonymizing PDF...")
            self.master.update()
            
            success = self.pdf_anonymizer.anonymize_pdf(input_path, output_path, selected_categories)
            
            if success:
                self.status_var.set("PDF anonymized successfully!")
                messagebox.showinfo("Success", f"PDF anonymized successfully!\nSaved as: {os.path.basename(output_path)}")
            else:
                self.status_var.set("Anonymization failed")
                messagebox.showerror("Error", "Anonymization failed.")
        except Exception as e:
            self.status_var.set("Error during anonymization")
            messagebox.showerror("Error", f"An error occurred: {e}")