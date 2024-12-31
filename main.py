import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from utils.pdf_utils import PDFAnonymizer
from collections import defaultdict
import runtime_config

class PIIPreviewWindow(tk.Toplevel):
    def __init__(self, parent, matches):
        super().__init__(parent)
        self.title("PII Detection Preview")
        self.geometry("800x600")
        
        # Store selected items
        self.selected_items = defaultdict(bool)
        
        # Create main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create category selection frame
        category_frame = ttk.LabelFrame(main_frame, text="PII Categories")
        category_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add "Select All" checkbox
        self.select_all_var = tk.BooleanVar(value=True)
        select_all_cb = ttk.Checkbutton(
            category_frame,
            text="Select All",
            variable=self.select_all_var,
            command=self.toggle_all
        )
        select_all_cb.pack(anchor=tk.W)
        
        # Create scrolled frame for categories
        self.categories_frame = ttk.Frame(category_frame)
        self.categories_frame.pack(fill=tk.X)
        
        # Create preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Detection Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add preview text widget with scrollbar
        preview_scroll = ttk.Scrollbar(preview_frame)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, width=80, yscrollcommand=preview_scroll.set)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        preview_scroll.config(command=self.preview_text.yview)
        
        # Create buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Add buttons
        ttk.Button(button_frame, text="Apply Selected", command=self.apply_selections).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)
        
        # Populate categories and preview
        self.populate_categories(matches)
        self.show_preview(matches)

    def populate_categories(self, matches):
        for category in matches.keys():
            var = tk.BooleanVar(value=True)
            self.selected_items[category] = var
            cb = ttk.Checkbutton(
                self.categories_frame,
                text=f"{category} ({len(matches[category])} found)",
                variable=var
            )
            cb.pack(anchor=tk.W)

    def show_preview(self, matches):
        self.preview_text.delete('1.0', tk.END)
        for category, items in matches.items():
            if not items:
                continue
            self.preview_text.insert(tk.END, f"\n{category}:\n")
            for item in items[:5]:  # Show first 5 examples per category
                self.preview_text.insert(tk.END, f"• Found: {item.text}\n  Will be replaced with: {item.replacement}\n")
            if len(items) > 5:
                self.preview_text.insert(tk.END, f"  ... and {len(items) - 5} more\n")

    def toggle_all(self):
        state = self.select_all_var.get()
        for var in self.selected_items.values():
            var.set(state)

    def apply_selections(self):
        self.result = {
            category: var.get()
            for category, var in self.selected_items.items()
        }
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Anonymizer")
        self.root.geometry("400x200")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add file selection
        self.file_frame = ttk.LabelFrame(main_frame, text="PDF File Selection", padding="5")
        self.file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(self.file_frame, text="Browse", command=self.select_file).pack(side=tk.RIGHT)
        
        # Add process button
        self.process_btn = ttk.Button(main_frame, text="Analyze PDF", command=self.process_file)
        self.process_btn.pack(pady=20)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=10)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.file_path.set(file_path)

    def process_file(self):
        file_path = self.file_path.get()
        if not file_path or not os.path.isfile(file_path):
            messagebox.showwarning("Warning", "Please select a valid PDF file.")
            return

        try:
            self.status_var.set("Analyzing PDF...")
            self.root.update()
            
            # Create anonymizer and detect PII
            anonymizer = PDFAnonymizer()
            matches = anonymizer.detect_pii(file_path)
            
            if not any(matches.values()):
                messagebox.showinfo("Result", "No PII detected in the PDF.")
                self.status_var.set("")
                return
            
            # Show preview window
            preview_window = PIIPreviewWindow(self.root, matches)
            self.root.wait_window(preview_window)
            
            if hasattr(preview_window, 'result') and preview_window.result is not None:
                # Get output path
                output_path = file_path.replace('.pdf', '_anonymized.pdf')
                
                # Process PDF with selected categories
                if anonymizer.anonymize_pdf(file_path, output_path, preview_window.result):
                    messagebox.showinfo("Success", f"PDF has been anonymized and saved as:\n{output_path}")
                else:
                    messagebox.showerror("Error", "Failed to anonymize PDF.")
            
            self.status_var.set("")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_var.set("")

def main():
    bundle_dir = runtime_config.setup_runtime_environment()
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()