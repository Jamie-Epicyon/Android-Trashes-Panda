
A quick readme written mostly by AI, will update when possible

Update: 2025-07-16 I've replaced pillow with exiftool and made changes to the GUI. This is slower but the exif data is more complete.  I'll provide a better readme at some point.



Trashes Panda — Android Trash Database Parser & EXIF Extractor
===============================================================

🧠 What This Tool Does
----------------------
Trashes Panda is a forensic utility designed to extract and enrich metadata from Android's trash system. It processes ZIP archives containing the `trash.db` database and associated image files (typically from Samsung Gallery or similar apps), and outputs a detailed CSV report with timestamps, EXIF data, and file metadata.

📁 How Android's `trash.db` Works
---------------------------------
On many Android devices (especially Samsung), when a user deletes a photo, it is not immediately removed from storage. Instead:

- The image is moved to a hidden trash folder.
- Metadata about the deleted file is stored in a SQLite database called `trash.db`.
- This database is typically located at:
  /data/user/<userid>/com.samsung.android.providers.trash/databases/trash.db

The `trash.db` file contains a table (usually named `trashes`) with columns like:

- `title`: the original filename of the deleted image
- `date_deleted`: the timestamp (in Unix epoch milliseconds) when the file was deleted

However, this database alone does not contain full metadata about the image itself — such as when it was taken or which device captured it.

🔍 What This Tool Adds
----------------------
Trashes Panda enhances the raw database by:

1. 🧠 Parsing timestamps from the `title` field  
   - Recognizes formats like `YYYYMMDD_HHMMSS`, `YYYY-MM-DD-HHMMSS`, and Unix timestamps
   - Converts them into human-readable local time

2. 📸 Extracting EXIF metadata from image files  
   - Reads the `DateTimeOriginal` tag to determine when the photo was taken
   - Extracts the `Model` tag to identify the camera or device used

3. 🧾 Enriching the database with:
   - `converted_title`: parsed timestamp from filename
   - `exif_created`: timestamp from EXIF metadata
   - `file_type`: file extension (e.g. jpg, png)
   - `file_path`: full path to the matched image
   - `camera_model`: device model from EXIF

4. 📤 Exporting all enriched data to a CSV file (`output.csv`) for analysis

🖥️ How to Use
--------------
1. Launch the GUI by running:
   python trashes_panda_gui.py

2. Click "Browse" and select a folder containing ZIP files extracted from an Android device.

3. The tool will:
   - Scan each ZIP for a valid `trash.db` and image files
   - Extract and process the data
   - Output a file called `output.csv` in the same directory

📄 Output Columns
-----------------
| Column               | Description                                      |
|----------------------|--------------------------------------------------|
| Original Title       | Filename from the trash.db                       |
| Extracted Timestamps | Parsed from filename (if available)              |
| EXIF Created         | Timestamp from EXIF metadata                     |
| File Type            | File extension (e.g. jpg, png)                   |
| Camera Model         | Device model from EXIF metadata                  |
| Unixepoch Timestamp  | Deletion time from trash.db (raw)                |
| Deleted_CST          | Deletion time converted to local time            |
| File Path            | Path to the matched image file                   |

🛠️ Requirements
---------------
- Python 3.7+
- Pillow (for EXIF parsing):
  pip install pillow

📦 Optional: Bundle as .exe
---------------------------
You can use PyInstaller to create a standalone Windows executable:

  pyinstaller --onefile --windowed --icon=panda.ico trashes_panda_gui.py

🧪 Forensic Use Cases
---------------------
- Recover deleted photo metadata from Android devices
- Correlate deletion times with original capture times
- Identify the device used to take a photo
- Audit user activity from extracted backups
