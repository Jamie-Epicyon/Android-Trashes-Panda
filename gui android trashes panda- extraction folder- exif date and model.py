import sqlite3
import os
import re
import csv
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

EXTRACTED_DB_DIR = Path("ExtractedDBs")
EXTRACTED_DB_DIR.mkdir(exist_ok=True)

def get_exif_data(image_path):
    exif_time = None
    camera_model = None
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None, None
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    exif_time = datetime.strptime(value, "%Y:%m:%d %H:%M:%S").strftime("%Y/%m/%d %H:%M:%S")
                elif tag == 'Model':
                    camera_model = str(value).strip()
    except Exception as e:
        print(f"⚠️ Error reading EXIF from {image_path}: {e}")
    return exif_time, camera_model

def convert_timestamp(text):
    patterns = [
        (r'(\d{8})[-_](\d{6,8})', 'ymd_hms'),
        (r'(\d{4})-(\d{2})-(\d{2})-(\d{6,8})', 'ymd_dash'),
        (r'\d{13}', 'epoch_ms'),
        (r'\d{10}', 'epoch_s')
    ]
    converted = []
    for pattern, fmt in patterns:
        for match in re.finditer(pattern, text):
            try:
                if fmt == 'ymd_hms':
                    date_part, time_part = match.groups()
                    dt = datetime.strptime(date_part + time_part[:6], "%Y%m%d%H%M%S")
                elif fmt == 'ymd_dash':
                    year, month, day, time_part = match.groups()
                    dt = datetime.strptime(f"{year}{month}{day}{time_part[:6]}", "%Y%m%d%H%M%S")
                elif fmt == 'epoch_ms':
                    timestamp = int(match.group(0)) / 1000
                    dt = datetime.fromtimestamp(timestamp)
                elif fmt == 'epoch_s':
                    timestamp = int(match.group(0))
                    dt = datetime.fromtimestamp(timestamp)
                converted.append(dt.strftime("%Y/%m/%d %H:%M:%S"))
            except (ValueError, OverflowError):
                continue
    return ", ".join(converted) if converted else None

def update_database(db_file, image_folder):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0].lower() for row in cursor.fetchall()]
    if 'trashes' not in tables:
        print(f"❌ 'trashes' table not found in {db_file}")
        print(f"📋 Available tables: {tables}")
        conn.close()
        return False

    cursor.execute("PRAGMA table_info(trashes)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'converted_title' not in columns:
        cursor.execute("ALTER TABLE trashes ADD COLUMN converted_title TEXT")
    if 'exif_created' not in columns:
        cursor.execute("ALTER TABLE trashes ADD COLUMN exif_created TEXT")
    if 'file_type' not in columns:
        cursor.execute("ALTER TABLE trashes ADD COLUMN file_type TEXT")
    if 'file_path' not in columns:
        cursor.execute("ALTER TABLE trashes ADD COLUMN file_path TEXT")
    if 'camera_model' not in columns:
        cursor.execute("ALTER TABLE trashes ADD COLUMN camera_model TEXT")

    image_files = list(Path(image_folder).rglob("*.[jJpP][pPnN][gG]"))
    image_lookup = {f.stem: f for f in image_files}

    cursor.execute("SELECT rowid, title FROM trashes")
    rows = cursor.fetchall()

    for rowid, title in rows:
        converted = convert_timestamp(title)
        exif_time = None
        file_type = None
        file_path = None
        camera_model = None
        if title in image_lookup:
            image_path = image_lookup[title]
            exif_time, camera_model = get_exif_data(image_path)
            file_type = image_path.suffix.lower().lstrip(".")
            file_path = str(image_path)
        cursor.execute(
            "UPDATE trashes SET converted_title = ?, exif_created = ?, file_type = ?, file_path = ?, camera_model = ? WHERE rowid = ?",
            (converted, exif_time, file_type, file_path, camera_model, rowid)
        )
    conn.commit()
    conn.close()
    return True

def export_to_csv(db_file, output_csv):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    query = """
    SELECT 
        title AS 'Original Title',
        converted_title AS 'Extracted Timestamps',
        exif_created AS 'EXIF Created',
        file_type AS 'File Type',
        camera_model AS 'Camera Model',
        date_deleted AS 'Unixepoch Timestamp',
        datetime((date_deleted / 1000), 'unixepoch', 'localtime') AS Deleted_CST,
        file_path AS 'File Path'
    FROM trashes
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(column_names)
            writer.writerows(rows)
        print(f"📁 Data exported to {output_csv}")
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
    finally:
        conn.close()

def find_and_process_zip(root_folder):
    root = Path(root_folder)
    temp_dir = Path(tempfile.mkdtemp())
    try:
        for zip_path in root.rglob("*.zip"):
            print(f"\n🔍 Scanning ZIP: {zip_path.name}")
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    members = z.namelist()
                    db_candidates = [m for m in members if m.endswith("trash.db")]
                    image_candidates = [
                        m for m in members
                        if m.lower().endswith((".jpg", ".jpeg", ".png")) and "com.sec.android.gallery3d" in m
                    ]
                    if not db_candidates:
                        print("❌ No trash.db found.")
                        continue
                    for db_member in db_candidates:
                        db_target_path = EXTRACTED_DB_DIR / f"{zip_path.stem}_{Path(db_member).name}"
                        db_target_path.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(db_member) as source, open(db_target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        print(f"📦 Extracted DB: {db_target_path}")
                        try:
                            conn = sqlite3.connect(db_target_path)
                            cursor = conn.cursor()
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = [row[0].lower() for row in cursor.fetchall()]
                            conn.close()
                        except Exception as e:
                            print(f"⚠️ Could not open {db_target_path}: {e}")
                            continue
                        if 'trashes' not in tables:
                            print(f"⚠️ Skipping {db_target_path} — no 'trashes' table found.")
                            continue
                        if not image_candidates:
                            print("❌ No image files found.")
                            continue
                        for img in image_candidates:
                            z.extract(img, temp_dir)
                        image_folder = temp_dir / Path(image_candidates[0]).parts[0]
                        success = update_database(db_target_path, image_folder)
                        if success:
                            export_to_csv(db_target_path, "output.csv")
                            print("🎉 Successfully processed and exported.")
                            return
            except zipfile.BadZipFile:
                print(f"⚠️ Skipping invalid ZIP: {zip_path}")
        print("\n❌ No ZIP found with both a valid trash.db and image files.")
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"⚠️ Could not delete temp folder: {e}")

# GUI
def run_processing(folder_path, status_label):
    try:
        status_label.config(text="🔄 Processing...")
        find_and_process_zip(folder_path)
        status_label.config(text="✅ Done! Output saved as output.csv")
    except Exception as e:
        status_label.config(text="❌ Error occurred")
        messagebox.showerror("Error", str(e))

def browse_folder(entry, status_label):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)
        threading.Thread(target=run_processing, args=(folder, status_label)).start()

def create_gui():
    root = tk.Tk()
    root.title("Trashes Panda Processor")
    root.geometry("500x180")
    root.resizable(False, False)

    tk.Label(root, text="Select Folder Containing ZIPs:", font=("Segoe UI", 10)).pack(pady=10)

    frame = tk.Frame(root)
    frame.pack()

    entry = tk.Entry(frame, width=50)
    entry.pack(side=tk.LEFT, padx=5)

    status_label = tk.Label(root, text="", font=("Segoe UI", 9), fg="blue")
    status_label.pack(pady=20)

    browse_btn = tk.Button(frame, text="Browse", command=lambda: browse_folder(entry, status_label))
    browse_btn.pack(side=tk.LEFT)

    root.mainloop()

# 🏁 Launch the GUI
if __name__ == "__main__":
    create_gui()
