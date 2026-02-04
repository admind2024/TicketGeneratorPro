"""
Ticket Generator Desktop Application
=====================================
Drag and drop CSV file onto the application window to process tickets.
The application will:
1. Read the filename (without extension) and create an event folder
2. Create a 'zones' subfolder inside the event folder
3. Group tickets by categoryKey and create separate CSV files for each zone
4. Generate PDF tickets with QR codes
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os
from pathlib import Path
from collections import defaultdict
from io import BytesIO
import threading
from urllib.parse import urlparse, parse_qs, unquote

# Try to import tkinterdnd2 for drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Import PIL for image handling
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Import qrcode for QR generation
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


class TicketGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ticket Generator - CSV Processor")
        self.root.geometry("900x700")
        self.root.configure(bg="#2b2b2b")
        
        # Get the base directory (where this script is located)
        self.base_dir = Path(__file__).parent
        self.events_dir = self.base_dir / "events"
        
        # Create events directory if it doesn't exist
        self.events_dir.mkdir(exist_ok=True)
        
        # Current event data
        self.current_event_name = None
        self.current_zones_dir = None
        self.zones_data = {}  # {zone_name: {"template": path, "csv": path, "tickets": count}}
        
        # QR position settings (as percentage of image size)
        self.qr_x_percent = tk.DoubleVar(value=75)
        self.qr_y_percent = tk.DoubleVar(value=50)
        self.qr_size_percent = tk.DoubleVar(value=20)
        self.ticket_id_x_percent = tk.DoubleVar(value=75)
        self.ticket_id_y_percent = tk.DoubleVar(value=75)
        self.ticket_id_font_size = tk.IntVar(value=24)
        
        # PDF optimization settings
        self.optimize_pdf = tk.BooleanVar(value=True)
        
        # Create main container
        self.main_container = tk.Frame(self.root, bg="#2b2b2b")
        self.main_container.pack(expand=True, fill="both")
        
        # Step frames
        self.step1_frame = None
        self.step2_frame = None
        
        self.setup_step1()
    
    def clear_main_container(self):
        """Clear all widgets from main container"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
    
    def setup_step1(self):
        """Setup Step 1: CSV Processing UI"""
        self.clear_main_container()
        
        self.step1_frame = tk.Frame(self.main_container, bg="#2b2b2b")
        self.step1_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            self.step1_frame,
            text="🎫 Ticket Generator - Korak 1: Učitaj CSV",
            font=("Segoe UI", 20, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        title_label.pack(pady=(0, 20))
        
        # Drop zone frame
        self.drop_frame = tk.Frame(
            self.step1_frame,
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
            self.step1_frame,
            text="",
            font=("Segoe UI", 10),
            fg="#4CAF50",
            bg="#2b2b2b",
            wraplength=550
        )
        self.status_label.pack(pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.step1_frame,
            mode="indeterminate",
            length=400
        )
        
        # Buttons frame
        buttons_frame = tk.Frame(self.step1_frame, bg="#2b2b2b")
        buttons_frame.pack(pady=(20, 0))
        
        # Manual file selection button
        browse_btn = tk.Button(
            buttons_frame,
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
        browse_btn.pack(side="left", padx=5)
        
        # Next button (initially disabled)
        self.next_btn = tk.Button(
            buttons_frame,
            text="Dalje ➡️",
            font=("Segoe UI", 11),
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            activeforeground="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.go_to_step2,
            state="disabled"
        )
        self.next_btn.pack(side="left", padx=5)
        
        # Setup drag and drop after creating widgets
        if HAS_DND:
            self.setup_drag_and_drop()
        else:
            self.show_dnd_warning()
    
    def setup_step2(self):
        """Setup Step 2: PDF Generation UI"""
        self.clear_main_container()
        
        self.step2_frame = tk.Frame(self.main_container, bg="#2b2b2b")
        self.step2_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            self.step2_frame,
            text=f"🎫 Ticket Generator - Korak 2: Generiši PDF\nEvent: {self.current_event_name}",
            font=("Segoe UI", 18, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        title_label.pack(pady=(0, 15))
        
        # Main content frame with two columns
        content_frame = tk.Frame(self.step2_frame, bg="#2b2b2b")
        content_frame.pack(expand=True, fill="both")
        
        # Left column - Zones table
        left_frame = tk.Frame(content_frame, bg="#2b2b2b")
        left_frame.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        zones_label = tk.Label(
            left_frame,
            text="Zone:",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        zones_label.pack(anchor="w")
        
        # Zones listbox with scrollbar
        zones_container = tk.Frame(left_frame, bg="#3c3c3c")
        zones_container.pack(expand=True, fill="both", pady=5)
        
        scrollbar = ttk.Scrollbar(zones_container)
        scrollbar.pack(side="right", fill="y")
        
        self.zones_listbox = tk.Listbox(
            zones_container,
            font=("Segoe UI", 11),
            bg="#3c3c3c",
            fg="#ffffff",
            selectbackground="#4CAF50",
            selectforeground="#ffffff",
            yscrollcommand=scrollbar.set,
            height=10
        )
        self.zones_listbox.pack(expand=True, fill="both")
        scrollbar.config(command=self.zones_listbox.yview)
        
        # Populate zones
        for zone_name, zone_info in self.zones_data.items():
            template_status = "✅" if zone_info.get("template") else "❌"
            self.zones_listbox.insert(tk.END, f"{template_status} {zone_name} ({zone_info['tickets']} karata)")
        
        self.zones_listbox.bind("<<ListboxSelect>>", self.on_zone_select)
        
        # Template selection button
        template_btn = tk.Button(
            left_frame,
            text="🖼️ Izaberi template za zonu",
            font=("Segoe UI", 10),
            bg="#FF9800",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            command=self.select_template_for_zone
        )
        template_btn.pack(pady=10)
        
        # Right column - QR Position settings
        right_frame = tk.Frame(content_frame, bg="#3c3c3c", padx=15, pady=15)
        right_frame.pack(side="right", fill="y", padx=(10, 0))
        
        settings_label = tk.Label(
            right_frame,
            text="⚙️ Podešavanja pozicije",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#3c3c3c"
        )
        settings_label.pack(pady=(0, 15))
        
        # QR Code X position
        self.create_slider(right_frame, "QR X pozicija (%):", self.qr_x_percent, 0, 100)
        
        # QR Code Y position
        self.create_slider(right_frame, "QR Y pozicija (%):", self.qr_y_percent, 0, 100)
        
        # QR Code size
        self.create_slider(right_frame, "QR veličina (%):", self.qr_size_percent, 5, 50)
        
        # Ticket ID X position
        self.create_slider(right_frame, "Ticket ID X (%):", self.ticket_id_x_percent, 0, 100)
        
        # Ticket ID Y position
        self.create_slider(right_frame, "Ticket ID Y (%):", self.ticket_id_y_percent, 0, 100)
        
        # Font size
        self.create_slider(right_frame, "Font veličina:", self.ticket_id_font_size, 10, 72)
        
        # Separator
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", pady=10)
        
        # Optimize PDF checkbox
        optimize_frame = tk.Frame(right_frame, bg="#3c3c3c")
        optimize_frame.pack(fill="x", pady=5)
        
        optimize_check = tk.Checkbutton(
            optimize_frame,
            text="📦 Optimizuj PDF (manji fajl)",
            variable=self.optimize_pdf,
            font=("Segoe UI", 10),
            fg="#ffffff",
            bg="#3c3c3c",
            selectcolor="#2b2b2b",
            activebackground="#3c3c3c",
            activeforeground="#ffffff"
        )
        optimize_check.pack(anchor="w")
        
        optimize_hint = tk.Label(
            optimize_frame,
            text="JPEG kompresija, manja rezolucija",
            font=("Segoe UI", 8),
            fg="#888888",
            bg="#3c3c3c"
        )
        optimize_hint.pack(anchor="w", padx=20)
        
        # Preview button
        preview_btn = tk.Button(
            right_frame,
            text="👁️ Preview",
            font=("Segoe UI", 10),
            bg="#9C27B0",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            command=self.show_preview
        )
        preview_btn.pack(pady=10)
        
        # Bottom buttons
        bottom_frame = tk.Frame(self.step2_frame, bg="#2b2b2b")
        bottom_frame.pack(fill="x", pady=(15, 0))
        
        # Back button
        back_btn = tk.Button(
            bottom_frame,
            text="⬅️ Nazad",
            font=("Segoe UI", 11),
            bg="#757575",
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.setup_step1
        )
        back_btn.pack(side="left")
        
        # Generate All button
        self.generate_all_btn = tk.Button(
            bottom_frame,
            text="🎫 Generiši SVE ulaznice",
            font=("Segoe UI", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.generate_all_tickets
        )
        self.generate_all_btn.pack(side="right")
        
        # Generate selected button
        self.generate_selected_btn = tk.Button(
            bottom_frame,
            text="🎫 Generiši za izabranu zonu",
            font=("Segoe UI", 11),
            bg="#2196F3",
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.generate_selected_zone_tickets
        )
        self.generate_selected_btn.pack(side="right", padx=10)
        
        # Status label
        self.step2_status = tk.Label(
            self.step2_frame,
            text="",
            font=("Segoe UI", 10),
            fg="#4CAF50",
            bg="#2b2b2b"
        )
        self.step2_status.pack(pady=(10, 0))
        
        # Progress frame (hidden initially)
        self.progress_frame = tk.Frame(self.step2_frame, bg="#2b2b2b")
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=("Segoe UI", 10),
            fg="#2196F3",
            bg="#2b2b2b"
        )
        self.progress_label.pack()
        
        self.pdf_progress = ttk.Progressbar(
            self.progress_frame,
            mode="determinate",
            length=400
        )
        self.pdf_progress.pack(pady=5)
        
        self.progress_percent = tk.Label(
            self.progress_frame,
            text="0%",
            font=("Segoe UI", 12, "bold"),
            fg="#4CAF50",
            bg="#2b2b2b"
        )
        self.progress_percent.pack()
    
    def create_slider(self, parent, label_text, variable, min_val, max_val):
        """Create a labeled slider"""
        frame = tk.Frame(parent, bg="#3c3c3c")
        frame.pack(fill="x", pady=5)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 9),
            fg="#cccccc",
            bg="#3c3c3c"
        )
        label.pack(anchor="w")
        
        slider_frame = tk.Frame(frame, bg="#3c3c3c")
        slider_frame.pack(fill="x")
        
        slider = ttk.Scale(
            slider_frame,
            from_=min_val,
            to=max_val,
            variable=variable,
            orient="horizontal"
        )
        slider.pack(side="left", expand=True, fill="x")
        
        value_label = tk.Label(
            slider_frame,
            textvariable=variable,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#3c3c3c",
            width=5
        )
        value_label.pack(side="right")
    
    def setup_drag_and_drop(self):
        """Setup drag and drop functionality"""
        if hasattr(self, 'drop_frame') and self.drop_frame.winfo_exists():
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
        if hasattr(self, 'drop_label'):
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
        self.on_drag_leave(event)
        file_path = event.data
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]
        self.process_csv_file(file_path)
    
    def browse_file(self):
        """Open file dialog to select CSV file"""
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
        
        if not file_path.exists():
            self.show_error("Fajl ne postoji!")
            return
        
        if file_path.suffix.lower() != ".csv":
            self.show_error("Molimo izaberite CSV fajl!")
            return
        
        self.progress.pack(pady=(10, 0))
        self.progress.start()
        self.status_label.config(text="Procesiranje...", fg="#2196F3")
        self.root.update()
        
        try:
            event_name = file_path.stem
            event_dir = self.events_dir / event_name
            zones_dir = event_dir / "zones"
            
            event_dir.mkdir(exist_ok=True)
            zones_dir.mkdir(exist_ok=True)
            
            tickets_by_category = defaultdict(list)
            total_tickets = 0
            
            with open(file_path, "r", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = reader.fieldnames if reader.fieldnames else []
                
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
                    qr_code_raw = row.get(qr_code_col, "").strip()
                    category_key = row.get(category_key_col, "").strip()
                    
                    # Extract QR data from URL if needed
                    qr_code = self.extract_qr_data(qr_code_raw)
                    
                    if ticket_id and qr_code and category_key:
                        tickets_by_category[category_key].append({
                            "ticketId": ticket_id,
                            "qr_code": qr_code
                        })
                        total_tickets += 1
            
            # Store data for step 2
            self.current_event_name = event_name
            self.current_zones_dir = zones_dir
            self.zones_data = {}
            
            zones_created = []
            for category_key, tickets in tickets_by_category.items():
                zone_dir = zones_dir / category_key
                zone_dir.mkdir(exist_ok=True)
                
                csv_file_path = zone_dir / f"{category_key}.csv"
                
                with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=["ticketId", "qr_code"])
                    writer.writeheader()
                    writer.writerows(tickets)
                
                # Find template image in zone folder
                template_path = self.find_template_image(zone_dir)
                
                self.zones_data[category_key] = {
                    "template": template_path,
                    "csv": csv_file_path,
                    "tickets": len(tickets),
                    "dir": zone_dir
                }
                
                zones_created.append(f"{category_key} ({len(tickets)} karata)")
            
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
            self.next_btn.config(state="normal")
            
        except Exception as e:
            self.progress.stop()
            self.progress.pack_forget()
            self.show_error(f"Greška pri procesiranju: {str(e)}")
    
    def extract_qr_data(self, qr_code_raw):
        """Extract QR data from URL or return as-is if not a URL"""
        if not qr_code_raw:
            return qr_code_raw
        
        # Check if it's a URL with data parameter
        if qr_code_raw.startswith("http"):
            try:
                parsed = urlparse(qr_code_raw)
                query_params = parse_qs(parsed.query)
                if "data" in query_params:
                    # Get the data parameter and decode URL encoding
                    data = query_params["data"][0]
                    return unquote(data)
            except:
                pass
        
        # If not a URL or parsing failed, just decode any URL encoding
        return unquote(qr_code_raw)
    
    def find_template_image(self, zone_dir):
        """Find the first image file in the zone directory"""
        image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
        for file in zone_dir.iterdir():
            if file.suffix.lower() in image_extensions:
                return file
        return None
    
    def go_to_step2(self):
        """Navigate to step 2"""
        if not self.zones_data:
            messagebox.showwarning("Upozorenje", "Prvo učitajte CSV fajl!")
            return
        self.setup_step2()
    
    def on_zone_select(self, event):
        """Handle zone selection"""
        selection = self.zones_listbox.curselection()
        if selection:
            index = selection[0]
            zone_name = list(self.zones_data.keys())[index]
            zone_info = self.zones_data[zone_name]
            template = zone_info.get("template")
            if template:
                self.step2_status.config(
                    text=f"Template: {template.name}",
                    fg="#4CAF50"
                )
            else:
                self.step2_status.config(
                    text="⚠️ Nema template slike za ovu zonu",
                    fg="#FF9800"
                )
    
    def select_template_for_zone(self):
        """Select template image for selected zone"""
        selection = self.zones_listbox.curselection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Izaberite zonu!")
            return
        
        index = selection[0]
        zone_name = list(self.zones_data.keys())[index]
        zone_info = self.zones_data[zone_name]
        
        file_path = filedialog.askopenfilename(
            title=f"Izaberite template za {zone_name}",
            filetypes=[
                ("Slike", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Svi fajlovi", "*.*")
            ],
            initialdir=zone_info["dir"]
        )
        
        if file_path:
            self.zones_data[zone_name]["template"] = Path(file_path)
            # Refresh listbox
            self.zones_listbox.delete(0, tk.END)
            for zn, zi in self.zones_data.items():
                template_status = "✅" if zi.get("template") else "❌"
                self.zones_listbox.insert(tk.END, f"{template_status} {zn} ({zi['tickets']} karata)")
            self.step2_status.config(text=f"✅ Template postavljen: {Path(file_path).name}", fg="#4CAF50")
    
    def show_preview(self):
        """Show preview of ticket with QR code"""
        selection = self.zones_listbox.curselection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Izaberite zonu!")
            return
        
        index = selection[0]
        zone_name = list(self.zones_data.keys())[index]
        zone_info = self.zones_data[zone_name]
        
        if not zone_info.get("template"):
            messagebox.showwarning("Upozorenje", "Nema template slike za ovu zonu!")
            return
        
        if not HAS_PIL:
            messagebox.showerror("Greška", "Pillow nije instaliran!")
            return
        
        # Create preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"Preview - {zone_name}")
        preview_window.configure(bg="#2b2b2b")
        
        # Generate sample ticket image
        template_img = Image.open(zone_info["template"])
        sample_ticket = self.create_ticket_image(
            template_img,
            "SAMPLE-TICKET-ID",
            "https://example.com/qr"
        )
        
        # Resize for preview
        max_size = (600, 400)
        sample_ticket.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(sample_ticket)
        
        label = tk.Label(preview_window, image=photo, bg="#2b2b2b")
        label.image = photo  # Keep reference
        label.pack(padx=20, pady=20)
        
        close_btn = tk.Button(
            preview_window,
            text="Zatvori",
            command=preview_window.destroy,
            bg="#757575",
            fg="white",
            relief="flat",
            padx=20,
            pady=5
        )
        close_btn.pack(pady=(0, 20))
    
    def create_ticket_image(self, template_img, ticket_id, qr_data):
        """Create a ticket image with QR code and ticket ID overlaid"""
        # Make a copy
        img = template_img.copy()
        img_width, img_height = img.size
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Calculate QR size and position
        qr_size = int(img_width * self.qr_size_percent.get() / 100)
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        
        qr_x = int(img_width * self.qr_x_percent.get() / 100 - qr_size / 2)
        qr_y = int(img_height * self.qr_y_percent.get() / 100 - qr_size / 2)
        
        # Ensure QR is within bounds
        qr_x = max(0, min(qr_x, img_width - qr_size))
        qr_y = max(0, min(qr_y, img_height - qr_size))
        
        # Paste QR code
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        qr_img = qr_img.convert("RGBA")
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add ticket ID text
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", self.ticket_id_font_size.get())
        except:
            font = ImageFont.load_default()
        
        text_x = int(img_width * self.ticket_id_x_percent.get() / 100)
        text_y = int(img_height * self.ticket_id_y_percent.get() / 100)
        
        # Draw text with outline for better visibility
        outline_color = "white"
        text_color = "black"
        
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((text_x + dx, text_y + dy), ticket_id, font=font, fill=outline_color, anchor="mm")
        draw.text((text_x, text_y), ticket_id, font=font, fill=text_color, anchor="mm")
        
        return img
    
    def generate_selected_zone_tickets(self):
        """Generate PDF tickets for selected zone"""
        selection = self.zones_listbox.curselection()
        if not selection:
            messagebox.showwarning("Upozorenje", "Izaberite zonu!")
            return
        
        index = selection[0]
        zone_name = list(self.zones_data.keys())[index]
        
        # Disable buttons
        self.disable_generate_buttons()
        
        # Run in background thread
        thread = threading.Thread(target=self.generate_zone_pdf_wrapper, args=(zone_name,))
        thread.daemon = True
        thread.start()
    
    def generate_zone_pdf_wrapper(self, zone_name):
        """Wrapper to enable buttons after generation"""
        try:
            self.generate_zone_pdf(zone_name)
        finally:
            self.root.after(0, self.enable_generate_buttons)
    
    def generate_all_tickets(self):
        """Generate PDF tickets for all zones"""
        zones_without_template = [zn for zn, zi in self.zones_data.items() if not zi.get("template")]
        
        if zones_without_template:
            result = messagebox.askyesno(
                "Upozorenje",
                f"Sljedeće zone nemaju template:\n{', '.join(zones_without_template)}\n\nŽelite li nastaviti sa ostalim zonama?"
            )
            if not result:
                return
        
        zones_to_generate = [zn for zn, zi in self.zones_data.items() if zi.get("template")]
        
        if not zones_to_generate:
            messagebox.showwarning("Upozorenje", "Nema zona sa template-om!")
            return
        
        # Disable buttons
        self.disable_generate_buttons()
        
        # Run in background thread
        thread = threading.Thread(target=self.generate_all_zones_background, args=(zones_to_generate,))
        thread.daemon = True
        thread.start()
    
    def generate_all_zones_background(self, zones_to_generate):
        """Generate PDFs for all zones in background"""
        total_zones = len(zones_to_generate)
        
        try:
            for i, zone_name in enumerate(zones_to_generate):
                self.root.after(0, lambda zn=zone_name, idx=i, total=total_zones: 
                    self.step2_status.config(text=f"Generišem zonu {idx+1}/{total}: {zn}", fg="#2196F3"))
                self.generate_zone_pdf(zone_name, show_folder=False)
            
            self.root.after(0, lambda: messagebox.showinfo("Završeno", f"PDF fajlovi su generisani za {total_zones} zona!"))
            self.root.after(0, lambda: self.step2_status.config(text=f"✅ Završeno! Generisano {total_zones} PDF fajlova.", fg="#4CAF50"))
        finally:
            self.root.after(0, self.enable_generate_buttons)
    
    def update_progress(self, current, total, zone_name):
        """Update progress bar from main thread"""
        percent = int((current / total) * 100)
        self.pdf_progress["value"] = percent
        self.progress_percent.config(text=f"{percent}% ({current}/{total})")
        self.progress_label.config(text=f"Generišem: {zone_name}")
    
    def disable_generate_buttons(self):
        """Disable generate buttons during PDF generation"""
        self.generate_all_btn.config(state="disabled", bg="#9E9E9E", cursor="arrow")
        self.generate_selected_btn.config(state="disabled", bg="#9E9E9E", cursor="arrow")
    
    def enable_generate_buttons(self):
        """Enable generate buttons after PDF generation"""
        self.generate_all_btn.config(state="normal", bg="#4CAF50", cursor="hand2")
        self.generate_selected_btn.config(state="normal", bg="#2196F3", cursor="hand2")
    
    def generate_zone_pdf(self, zone_name, show_folder=True):
        """Generate PDF with 4 tickets per A4 page for a zone"""
        zone_info = self.zones_data[zone_name]
        
        if not zone_info.get("template"):
            self.root.after(0, lambda: self.step2_status.config(text=f"⚠️ {zone_name}: Nema template!", fg="#FF9800"))
            return
        
        if not HAS_REPORTLAB or not HAS_PIL:
            self.root.after(0, lambda: messagebox.showerror("Greška", "Potrebne biblioteke nisu instalirane!"))
            return
        
        # Read tickets from CSV
        tickets = []
        with open(zone_info["csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tickets.append(row)
        
        if not tickets:
            self.root.after(0, lambda: self.step2_status.config(text=f"⚠️ {zone_name}: Nema karata!", fg="#FF9800"))
            return
        
        # Show progress bar
        self.root.after(0, lambda: self.progress_frame.pack(pady=(10, 0)))
        self.root.after(0, lambda: self.update_progress(0, len(tickets), zone_name))
        
        # Load template
        template_img = Image.open(zone_info["template"])
        
        # Check if optimization is enabled
        optimize = self.optimize_pdf.get()
        
        # If optimizing, resize template once for better performance
        if optimize:
            # Target width for optimized images (pixels) - good balance for A4 print
            target_width = 800
            ratio = target_width / template_img.width
            target_height = int(template_img.height * ratio)
            template_img = template_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Create PDF
        pdf_path = zone_info["dir"] / f"{zone_name}_tickets.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        page_width, page_height = A4
        
        # Calculate ticket size (4 per page, with margins)
        margin = 20
        ticket_width = page_width - 2 * margin
        ticket_height = (page_height - 5 * margin) / 4
        
        total_tickets = len(tickets)
        
        # Process tickets
        for i, ticket in enumerate(tickets):
            position_on_page = i % 4
            
            if position_on_page == 0 and i > 0:
                c.showPage()
            
            # Create ticket image
            ticket_img = self.create_ticket_image(
                template_img,
                ticket["ticketId"],
                ticket["qr_code"]
            )
            
            # Calculate position on page
            y_position = page_height - margin - (position_on_page + 1) * (ticket_height + margin / 2)
            
            # Convert PIL image to reportlab
            img_buffer = BytesIO()
            
            if optimize:
                # Convert to RGB (JPEG doesn't support RGBA)
                if ticket_img.mode == 'RGBA':
                    # Create white background
                    rgb_img = Image.new('RGB', ticket_img.size, (255, 255, 255))
                    rgb_img.paste(ticket_img, mask=ticket_img.split()[3])
                    ticket_img = rgb_img
                elif ticket_img.mode != 'RGB':
                    ticket_img = ticket_img.convert('RGB')
                
                # Save as JPEG with compression
                ticket_img.save(img_buffer, format='JPEG', quality=90, optimize=False)
            else:
                # Save as PNG (larger but lossless)
                ticket_img.save(img_buffer, format='PNG')
            
            img_buffer.seek(0)
            
            # Draw image on PDF
            c.drawImage(
                ImageReader(img_buffer),
                margin,
                y_position,
                width=ticket_width,
                height=ticket_height,
                preserveAspectRatio=True,
                anchor='c'
            )
            
            # Update progress every 10 tickets or at the end
            if (i + 1) % 10 == 0 or i == total_tickets - 1:
                current = i + 1
                self.root.after(0, lambda c=current, t=total_tickets, zn=zone_name: self.update_progress(c, t, zn))
        
        c.save()
        
        # Hide progress and show success
        self.root.after(0, lambda: self.progress_frame.pack_forget())
        self.root.after(0, lambda: self.step2_status.config(
            text=f"✅ PDF generisan: {pdf_path.name} ({len(tickets)} karata)",
            fg="#4CAF50"
        ))
        
        # Open the folder
        if show_folder:
            self.root.after(0, lambda: os.startfile(zone_info["dir"]))
    
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
