"""
Ticket Generator Desktop Application
=====================================
Drag and drop CSV file onto the application window to process tickets.
The application will:
1. Read the filename (without extension) and create an event folder
2. Create a 'zones' subfolder inside the event folder
3. Group tickets by categoryKey and create separate CSV files for each zone
"""

import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from pathlib import Path
from collections import defaultdict

# Try to import tkinterdnd2 for drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


class TicketGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ticket Generator - CSV Processor")
        self.root.geometry("600x400")
        self.root.configure(bg="#2b2b2b")
        
        # Get the base directory (where this script is located)
        self.base_dir = Path(__file__).parent
        self.events_dir = self.base_dir / "events"
        
        # Create events directory if it doesn't exist
        self.events_dir.mkdir(exist_ok=True)
        
        self.setup_ui()
        
        if HAS_DND:
            self.setup_drag_and_drop()
        else:
            self.show_dnd_warning()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🎫 Ticket Generator",
            font=("Segoe UI", 24, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        title_label.pack(pady=(0, 20))
        
        # Drop zone frame
        self.drop_frame = tk.Frame(
            main_frame,
            bg="#3c3c3c",
            highlightbackground="#5c5c5c",
            highlightthickness=2,
            relief="flat"
        )
        self.drop_frame.pack(expand=True, fill="both", pady=10)
        
        # Drop zone label
        self.drop_label = tk.Label(
            self.drop_frame,
            text="📂\n\nPrevucite CSV fajl ovdje\n(Drag & Drop)",
            font=("Segoe UI", 14),
            fg="#888888",
            bg="#3c3c3c",
            justify="center"
        )
        self.drop_label.pack(expand=True)
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="",
            font=("Segoe UI", 10),
            fg="#4CAF50",
            bg="#2b2b2b",
            wraplength=550
        )
        self.status_label.pack(pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode="indeterminate",
            length=400
        )
        self.progress.pack(pady=(10, 0))
        self.progress.pack_forget()  # Hide initially
        
        # Manual file selection button (fallback)
        browse_btn = tk.Button(
            main_frame,
            text="📁 Izaberite CSV fajl",
            font=("Segoe UI", 11),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.browse_file
        )
        browse_btn.pack(pady=(20, 0))
    
    def setup_drag_and_drop(self):
        """Setup drag and drop functionality"""
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>", self.on_drop)
        self.drop_frame.dnd_bind("<<DragEnter>>", self.on_drag_enter)
        self.drop_frame.dnd_bind("<<DragLeave>>", self.on_drag_leave)
    
    def show_dnd_warning(self):
        """Show warning if tkinterdnd2 is not installed"""
        warning_text = (
            "⚠️ Drag & Drop nije dostupan.\n"
            "Instalirajte tkinterdnd2: pip install tkinterdnd2\n"
            "Koristite dugme ispod za odabir fajla."
        )
        self.drop_label.config(text=warning_text, fg="#ff9800")
    
    def on_drag_enter(self, event):
        """Handle drag enter event"""
        self.drop_frame.configure(highlightbackground="#4CAF50", highlightthickness=3)
        self.drop_label.config(fg="#4CAF50")
    
    def on_drag_leave(self, event):
        """Handle drag leave event"""
        self.drop_frame.configure(highlightbackground="#5c5c5c", highlightthickness=2)
        self.drop_label.config(fg="#888888")
    
    def on_drop(self, event):
        """Handle file drop event"""
        self.on_drag_leave(event)  # Reset styling
        
        # Get the dropped file path
        file_path = event.data
        
        # Clean up the path (remove curly braces if present)
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]
        
        # Process the file
        self.process_csv_file(file_path)
    
    def browse_file(self):
        """Open file dialog to select CSV file"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Izaberite CSV fajl",
            filetypes=[("CSV fajlovi", "*.csv"), ("Svi fajlovi", "*.*")],
            initialdir=self.base_dir / "codes"
        )
        
        if file_path:
            self.process_csv_file(file_path)
    
    def process_csv_file(self, file_path):
        """Process the dropped/selected CSV file"""
        file_path = Path(file_path)
        
        # Validate file
        if not file_path.exists():
            self.show_error("Fajl ne postoji!")
            return
        
        if file_path.suffix.lower() != ".csv":
            self.show_error("Molimo izaberite CSV fajl!")
            return
        
        # Show progress
        self.progress.pack(pady=(10, 0))
        self.progress.start()
        self.status_label.config(text="Procesiranje...", fg="#2196F3")
        self.root.update()
        
        try:
            # Get filename without extension (event name)
            event_name = file_path.stem
            
            # Create event folder structure
            event_dir = self.events_dir / event_name
            zones_dir = event_dir / "zones"
            
            event_dir.mkdir(exist_ok=True)
            zones_dir.mkdir(exist_ok=True)
            
            # Read and process CSV
            tickets_by_category = defaultdict(list)
            total_tickets = 0
            
            with open(file_path, "r", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Get actual field names from CSV
                fieldnames = reader.fieldnames if reader.fieldnames else []
                
                # Find the correct column names (case-insensitive search)
                def find_column(names, *possible_names):
                    for name in names:
                        for possible in possible_names:
                            if name.lower().strip() == possible.lower():
                                return name
                    return None
                
                ticket_id_col = find_column(fieldnames, "ticketId", "ticket_id", "ticketid")
                qr_code_col = find_column(fieldnames, "QR Code", "qr_code", "qrcode", "QRCode")
                category_key_col = find_column(fieldnames, "categoryKey", "category_key", "categorykey")
                
                if not all([ticket_id_col, qr_code_col, category_key_col]):
                    missing = []
                    if not ticket_id_col:
                        missing.append("ticketId")
                    if not qr_code_col:
                        missing.append("QR Code")
                    if not category_key_col:
                        missing.append("categoryKey")
                    raise ValueError(f"CSV fajl nema potrebne kolone: {', '.join(missing)}\nPronađene kolone: {fieldnames}")
                
                for row in reader:
                    ticket_id = row.get(ticket_id_col, "").strip()
                    qr_code = row.get(qr_code_col, "").strip()
                    category_key = row.get(category_key_col, "").strip()
                    
                    if ticket_id and qr_code and category_key:
                        tickets_by_category[category_key].append({
                            "ticketId": ticket_id,
                            "qr_code": qr_code
                        })
                        total_tickets += 1
            
            # Create zone folders and CSV files
            zones_created = []
            for category_key, tickets in tickets_by_category.items():
                # Create zone folder
                zone_dir = zones_dir / category_key
                zone_dir.mkdir(exist_ok=True)
                
                # Create CSV file for this zone
                csv_file_path = zone_dir / f"{category_key}.csv"
                
                with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=["ticketId", "qr_code"])
                    writer.writeheader()
                    writer.writerows(tickets)
                
                zones_created.append(f"{category_key} ({len(tickets)} karata)")
            
            # Success message
            self.progress.stop()
            self.progress.pack_forget()
            
            success_msg = (
                f"✅ Uspješno procesiranje!\n\n"
                f"Event: {event_name}\n"
                f"Ukupno karata: {total_tickets}\n"
                f"Zone kreirane: {len(zones_created)}\n\n"
                f"Zone:\n" + "\n".join(f"  • {z}" for z in zones_created)
            )
            
            self.status_label.config(text=success_msg, fg="#4CAF50")
            messagebox.showinfo("Uspješno", success_msg)
            
        except Exception as e:
            self.progress.stop()
            self.progress.pack_forget()
            self.show_error(f"Greška pri procesiranju: {str(e)}")
    
    def show_error(self, message):
        """Show error message"""
        self.status_label.config(text=f"❌ {message}", fg="#f44336")
        messagebox.showerror("Greška", message)


def main():
    """Main entry point"""
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = TicketGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
