Trashes Panda — Android Trash Database & EXIF Metadata Merger  

8/8/2025 New version is up for update to exif tool, more stable version forthcoming

Updated July 16 2025

================================================================================
🆕 What’s New?

- EXE Provided! Use the ready-to-run Windows executable (.exe)—no Python installation required.
- EXIF extraction powered by ExifTool for richer, more accurate metadata on modern Android images (HEIC, TIFF, etc).
- Modern, responsive GUI: Progress bars, log console, and ZIP/folder discovery.
- Handles ZIPs and folders: Finds images anywhere—directly or embedded in ZIPs.
- No DB changes: *Does not* alter your original trash.db.
- Modular output: CSVs for EXIF metadata and DB records, cleanly merged.

================================================================================
📂 How Android's trash.db Works (Why This Matters)

Many Android devices (especially Samsung Gallery and others) use a hidden trash system instead of immediately deleting photos. Here’s what happens:

1. When you delete a photo:
   - The image is moved to a system trash/recycle folder (sometimes only accessible via root or backup).
   - Record(s) about deletions are written to a SQLite database called trash.db.

2. About trash.db:
   - Typically located at:
     /data/user/<userid>/com.samsung.android.providers.trash/databases/trash.db
   - Contains a table (often called trashes) with columns like:
     - title: The original filename of the deleted image (e.g. IMG_20230101_123000.jpg)
     - date_deleted: Unix timestamp (in milliseconds) when the photo was deleted
     - (Sometimes more, depending on Android version or app variation)
   - Sometimes, no other image metadata is stored—this is why it’s crucial to supplement with EXIF from the actual files.

3. Why extra EXIF metadata is needed:
   - trash.db doesn’t tell you when the photo was originally taken—only when it was deleted.
   - Photos’ original timestamps, camera details, and other information are embedded inside the media files themselves, in a header called EXIF.

================================================================================
🧠 What This Tool Does

Trashes Panda lets you:
- Analyze both: trash.db deletion records and the actual EXIF/photo metadata of the trashed images.
- Finds images even if they are embedded in ZIP backup archives or scattered in folders.

🏆 How EXIF Parsing is Performed
- Uses ExifTool (industry gold standard) for pulling out:
    - DateCreated (original capture timestamp)
    - DateModified
    - Camera Model
    - Extension
    - ...and more
- Automatically locates media files (JPG, PNG, HEIC, TIFF) either directly in folders or inside ZIPs extracted from the trashes folder (with full path/ZIP context for chain-of-custody).
- Parses EXIF directly from every image it can find; output is comprehensive and handles more types and variants than past Python-only solutions (e.g., Pillow).

================================================================================
🚦 How to Use

1. Installation & Prerequisites

- Windows users: You can use the provided .exe! No need for Python.
    - Just double-click exif_trashes_merger.exe to launch the GUI.
- If using Python source: Requires Python 3.7+, will auto-download ExifTool if missing.
- No manual ExifTool install is needed.

2. Workflow

1. Place your trash.db and/or ZIP(s)/images in a convenient folder (USB, export, cloud download, etc).
2. Run the program:
   - .exe: Double-click exif_trashes_merger.exe
   - Python script: python exif_trashes_merger.py
3. In the GUI:
   - Browse to the target folder containing trash.db and images or ZIPs.
   - Confirm detected image files count.
   - Click:
     - 🛠️ Extract Metadata — finds images (even those inside ZIPs), extracts metadata using ExifTool.
     - 📊 Export trash.db — saves records from the trashes table to CSV.
     - 🔗 Merge Outputs — links/photo titles from DB to extracted EXIF: outputs a single, rich merged CSV.
     - 🧪 Open ExifTool Folder — for troubleshooting if ExifTool is required.
   - All output files go into the output/ subfolder.

================================================================================
📄 Output File Overview

| File                   | Description                                                  |
|------------------------|-------------------------------------------------------------|
| output_metadata.csv    | All image EXIF data (incl. capture date, camera, extension) |
| output_trashdb.csv     | Records extracted from the trashes SQLite table             |
| merged_output.csv      | All-in-one view: links DB entries to media/EXIF metadata    |

Merged Output Columns

| Column                | Description                                                      |
|-----------------------|------------------------------------------------------------------|
| title                 | Filename, as listed in the trash.db (IMG_...jpg etc.)           |
| Unixepoch Timestamp   | Raw deletion time (from trash.db)                               |
| Deleted_CST           | Deletion time (converted to your PC local time)                 |
| DateCreated           | When photo/video was taken (EXIF DateTimeOriginal)              |
| DateModified          | When the file was last changed                                  |
| Camera                | Camera/device model name                                        |
| Extension             | File extension (JPG, HEIC, PNG, etc)                            |
| FilePath              | Where the file was found; shows ZIP/relative path where relevant|

================================================================================
❓ Why Use EXIFTool (and this utility)

- Comprehensive: Handles modern formats and variants (HEIC, 10-bit JPEG, etc) that older Python libraries miss.
- Forensically robust: Parses deeply into nested folders and ZIPs; keeps evidence chains intact by showing origin.
- No accidental DB changes: Analysis-only; no schema changes that could pop data out of typical forensics toolchains.

================================================================================
⚙️ Example Use Cases

- Build a timeline: See exactly when photos were shot, when trashed, and by what device.
- Forensics: Correlate user deletion actions with actual file history; detect if photos are pre/post-dated.
- Investigate multi-device or cloud photo deletion (when photos come from different camera models).

================================================================================
🧑‍💻 Credits

- ExifTool by Phil Harvey (https://exiftool.org/)

================================================================================
🙏 Special Thanks

A special thanks to:
- Charlie (northloopforensics on GitHub: https://github.com/northloopforensics)
- Matt (dabeersboys on GitHub: https://github.com/dabeersboys)

for their support, feedback, and contributions that improved this project.

================================================================================
📝 Changelog (2025-07-16)

- EXE now included for Windows (no setup needed!)
- EXIF parsing now with ExifTool for maximum file/metadata coverage.
- Major GUI improvements: better logs, progress, modular process.
- Output is now split into clear single-purpose files, fully merged for timeline use.
- Database is read-only for maximum evidence safety.

================================================================================
Questions, forensic requests, or enhancements?
File an issue or contact us—we welcome professional casework and suggestions!
