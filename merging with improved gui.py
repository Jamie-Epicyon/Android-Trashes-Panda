import os
import subprocess
import threading
import urllib.request
import zipfile
import shutil
import tempfile
import json
import csv
import sqlite3
from pathlib import Path

# --- Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXIFTOOL_URL = "https://exiftool.org/exiftool-13.32_64.zip"
EXIFTOOL_DIR = os.path.join(SCRIPT_DIR, "exiftool")
EXIFTOOL_PACKAGE = os.path.join(EXIFTOOL_DIR, "exiftool-13.32_64")
EXIFTOOL_EXE = os.path.join(EXIFTOOL_PACKAGE, "exiftool.exe")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
DB_PATH = "C:/users/jamie/OneDrive/Desktop/trashes/trash.db"

OUTPUT_METADATA = os.path.join(OUTPUT_DIR, "output_metadata.csv")
OUTPUT_TRASHDB = os.path.join(OUTPUT_DIR, "output_trashdb.csv")
MERGED_OUTPUT = os.path.join(OUTPUT_DIR, "merged_output.csv")

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic'}
ZIP_EXTENSIONS = {'.zip'}

# 🪵 Logging function with GUI binding
log_sink = None
def log(msg):
    print(f"[LOG] {msg}")
    if log_sink:
        log_sink.insert('end', f"{msg}\n")
        log_sink.see('end')

# 📦 Download ExifTool if missing
def download_exiftool():
    zip_path = os.path.join(EXIFTOOL_DIR, "exiftool.zip")
    os.makedirs(EXIFTOOL_DIR, exist_ok=True)
    if os.path.exists(EXIFTOOL_EXE):
        log("✅ ExifTool already available.")
        return
    try:
        log("📥 Downloading ExifTool...")
        urllib.request.urlretrieve(EXIFTOOL_URL, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXIFTOOL_DIR)
        os.remove(zip_path)
        for root, _, files in os.walk(EXIFTOOL_PACKAGE):
            for file in files:
                if file.startswith("exiftool") and file.endswith(".exe"):
                    shutil.move(os.path.join(root, file), EXIFTOOL_EXE)
                    log(f"🔧 ExifTool installed: {EXIFTOOL_EXE}")
                    return
        log("⚠️ ExifTool executable not found after extraction.")
    except Exception as e:
        log(f"[ERROR] Download failed: {e}")

# 🔍 Gather image files
def get_image_files_recursive(folder_path):
    return [os.path.join(root, f)
            for root, _, files in os.walk(folder_path)
            for f in files if Path(f).suffix.lower() in IMAGE_EXTENSIONS]

def get_zip_files(folder_path):
    return [os.path.join(root, f)
            for root, _, files in os.walk(folder_path)
            for f in files if Path(f).suffix.lower() in ZIP_EXTENSIONS]

def extract_targeted_items(zip_path):
    temp_dir = tempfile.mkdtemp(prefix="exif_trash_")
    images = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                lowered = name.lower()
                if ".trashes" in lowered or "__macosx" in lowered or "trash" in lowered:
                    zip_ref.extract(name, temp_dir)
        images = get_image_files_recursive(temp_dir)
        return [(zip_path, img) for img in images]
    except Exception as e:
        log(f"[ERROR] Failed to extract from ZIP: {zip_path} — {e}")
        return []

# 🛠 Extract metadata using ExifTool
def extract_metadata(folder_path, progress_callback):
    if not os.path.exists(EXIFTOOL_EXE):
        log("❌ ExifTool not found.")
        return
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log(f"🔍 Scanning: {folder_path}")
    direct = [(None, p) for p in get_image_files_recursive(folder_path)]
    zipped = []
    for zip_path in get_zip_files(folder_path):
        zipped.extend(extract_targeted_items(zip_path))
    all_images = direct + zipped
    log(f"📸 Found {len(all_images)} total image files.")
    try:
        with open(OUTPUT_METADATA, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'DateCreated', 'DateModified', 'Camera', 'Title', 'Extension', 'FilePath'
            ])
            writer.writeheader()
            for idx, (origin, img) in enumerate(all_images):
                tags = ['-json', '-DateTimeOriginal', '-ModifyDate', '-Model', '-Title', '-FileTypeExtension']
                result = subprocess.run([EXIFTOOL_EXE] + tags + [img],
                                        capture_output=True, text=True, cwd=EXIFTOOL_PACKAGE)
                try:
                    metadata = json.loads(result.stdout)[0]
                except:
                    metadata = {}
                full_path = f"{origin} > {img}" if origin else img
                writer.writerow({
                    'DateCreated': metadata.get('DateTimeOriginal', ''),
                    'DateModified': metadata.get('ModifyDate', ''),
                    'Camera': metadata.get('Model', ''),
                    'Title': metadata.get('Title', ''),
                    'Extension': metadata.get('FileTypeExtension', ''),
                    'FilePath': full_path
                })
                progress_callback(idx + 1, len(all_images))
        log(f"✅ Metadata written to: {OUTPUT_METADATA}")
    except Exception as e:
        log(f"[ERROR] Metadata extraction failed: {e}")

# 🗃 Export trash.db contents
def export_trashdb_to_csv():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title as title,
                   date_deleted as "Unixepoch Timestamp",
                   datetime(date_deleted / 1000, 'unixepoch', 'localtime') as Deleted_CST
            FROM trashes
        """)
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        with open(OUTPUT_TRASHDB, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(colnames)
            writer.writerows(rows)
        conn.close()
        log(f"✅ trash.db exported to: {OUTPUT_TRASHDB}")
    except Exception as e:
        log(f"[ERROR] trash.db export failed: {e}")

# 🔗 Merge metadata + trash info
def merge_outputs():
    if not os.path.exists(OUTPUT_METADATA) or not os.path.exists(OUTPUT_TRASHDB):
        log("⚠️ Missing metadata or trashdb CSV.")
        return
    try:
        with open(OUTPUT_METADATA, 'r', encoding='utf-8') as f_meta, open(OUTPUT_TRASHDB, 'r', encoding='utf-8') as f_trash:
            meta_reader = csv.DictReader(f_meta)
            trash_reader = csv.DictReader(f_trash)
            meta_data = list(meta_reader)
            trash_data = list(trash_reader)
    except Exception as e:
        log(f"[ERROR] Failed to read input files: {e}")
        return

    merged_rows = []
    for mrow in meta_data:
        file_path = mrow.get("FilePath", "")
        matched = None
        for trow in trash_data:
            title = trow.get("title", "")
            if title and title in file_path:
                matched = trow
                break

        combined = {
            "title": matched.get("title", "") if matched else "",
            "Unixepoch Timestamp": matched.get("Unixepoch Timestamp", "") if matched else "Not found",
            "Deleted_CST": matched.get("Deleted_CST", "") if matched else "Not found",
            "DateCreated": mrow.get("DateCreated", ""),
            "DateModified": mrow.get("DateModified", ""),
            "Camera": mrow.get("Camera", ""),
            "Extension": mrow.get("Extension", ""),
            "FilePath": mrow.get("FilePath", "")
        }
        merged_rows.append(combined)

    column_order = [
        "title",
        "Unixepoch Timestamp",
        "Deleted_CST",
        "DateCreated",
        "DateModified",
        "Camera",
        "Extension",
        "FilePath"
    ]

    try:
        with open(MERGED_OUTPUT, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=column_order)
            writer.writeheader()
            for row in merged_rows:
                writer.writerow({col: row.get(col, '') for col in column_order})
        log(f"✅ Merged CSV written to: {MERGED_OUTPUT}")
        subprocess.run(f'explorer "{MERGED_OUTPUT}"', shell=True)
    except Exception as e:
        log(f"[ERROR] Failed to write merged CSV: {e}")
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# --- GUI Setup ---
root = tk.Tk()
root.title("Exif + Trashes Merger")
root.geometry("640x480")
root.resizable(False, False)

# Folder select frame
frame = ttk.Frame(root, padding=10)
frame.pack(fill=tk.X)

folder_entry = ttk.Entry(frame, width=50)
folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

def browse_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder)
        update_count(folder)

browse_btn = ttk.Button(frame, text="📂 Browse", command=browse_folder)
browse_btn.pack(side=tk.LEFT)

count_label = ttk.Label(root, text="📸 Total image files: 0")
count_label.pack(pady=(5, 5))

# Progress bar
progress = ttk.Progressbar(root, length=600, mode='determinate')
progress.pack(pady=(5, 10))

# Status console
log_box = ScrolledText(root, height=12, wrap=tk.WORD)
log_box.pack(fill=tk.BOTH, padx=10, pady=(0, 10), expand=True)
log_sink = log_box  # bind to logger

# Action buttons
button_frame = ttk.Frame(root, padding=10)
button_frame.pack()

def update_count(folder):
    direct = get_image_files_recursive(folder)
    zipped = sum(len(extract_targeted_items(z)) for z in get_zip_files(folder))
    count_label.config(text=f"📸 Total image files: {len(direct) + zipped}")

def start_extraction():
    folder = folder_entry.get()
    if not folder or not os.path.isdir(folder):
        messagebox.showerror("Error", "Select a valid folder.")
        return
    progress["value"] = 0
    progress["maximum"] = 1
    def update_progress(done, total):
        progress["maximum"] = total
        progress["value"] = done
    threading.Thread(target=extract_metadata, args=(folder, update_progress), daemon=True).start()

def run_trash_query():
    threading.Thread(target=export_trashdb_to_csv, daemon=True).start()

def run_merge():
    threading.Thread(target=merge_outputs, daemon=True).start()

def open_exif_folder():
    if os.path.exists(EXIFTOOL_PACKAGE):
        subprocess.run(f'explorer "{EXIFTOOL_PACKAGE}"', shell=True)
    else:
        messagebox.showerror("Not Found", f"ExifTool folder missing:\n{EXIFTOOL_PACKAGE}")

ttk.Button(button_frame, text="🛠️ Extract Metadata", command=start_extraction).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="📊 Export trash.db", command=run_trash_query).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="🔗 Merge Outputs", command=run_merge).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="🧪 Open ExifTool Folder", command=open_exif_folder).pack(side=tk.LEFT, padx=5)

log(f"📁 Script directory: {SCRIPT_DIR}")
download_exiftool()
root.mainloop()