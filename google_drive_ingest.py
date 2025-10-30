# Databricks notebook source
# MAGIC %md
# MAGIC # Google Drive File Browser & Download 📁⬇️
# MAGIC 
# MAGIC Simple interface to browse and download files from Google Drive to Databricks.
# MAGIC 
# MAGIC ## How to Use:
# MAGIC 1. **Configure** your Google Drive credentials in the settings below
# MAGIC 2. **Run all cells** to see your files
# MAGIC 3. **Select files** using checkboxes in the file browser
# MAGIC 4. **Copy file IDs** and paste them into the download cell
# MAGIC 5. **Run the download cell** to save files to your volume

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📦 Install Required Packages

# COMMAND ----------

%pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client --quiet
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📚 Import Libraries

# COMMAND ----------

import sys
# Add the path where google_drive_utils.py is located
# Uncomment and adjust the path if needed:
# sys.path.append('/Volumes/catalog/schema/volume_name')

# Import utility functions
from google_drive_utils import (
    get_google_drive_service,
    list_drive_contents,
    download_file_to_destination
)

import pandas as pd

print("✓ Libraries imported successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚙️ Settings
# MAGIC 
# MAGIC Configure your Google Drive connection settings below.

# COMMAND ----------

# Create configuration widgets
dbutils.widgets.text("secret_scope", "", "Secret Scope")
dbutils.widgets.text("credentials_key", "google_drive_credentials", "Credentials Key")
dbutils.widgets.text("folder_id", "", "Folder ID (optional)")
dbutils.widgets.text("output_path", "/Volumes/main/default/google_drive", "Output Path")

# Get widget values
SECRET_SCOPE = dbutils.widgets.get("secret_scope")
CREDENTIALS_KEY = dbutils.widgets.get("credentials_key")
FOLDER_ID = dbutils.widgets.get("folder_id") or None
OUTPUT_PATH = dbutils.widgets.get("output_path")

# Validate
if not SECRET_SCOPE:
    raise ValueError("⚠️ Please enter your Secret Scope name in the widget above!")

print("✓ Configuration loaded")
print(f"  📁 Folder: {FOLDER_ID if FOLDER_ID else 'Root (all files)'}")
print(f"  💾 Output: {OUTPUT_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔐 Connect to Google Drive

# COMMAND ----------

# Authenticate with Google Drive
drive_service = get_google_drive_service(dbutils, SECRET_SCOPE, CREDENTIALS_KEY)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📂 Browse Your Files
# MAGIC 
# MAGIC Your Google Drive files are listed below. Select files using the checkboxes.

# COMMAND ----------

# List files from Google Drive
files_df = list_drive_contents(drive_service, FOLDER_ID, max_results=100)

if files_df.empty:
    print("ℹ️ No files found. Check your folder ID or ensure the service account has access.")
else:
    print(f"✓ Found {len(files_df)} files\n")
    
    # Create interactive HTML file browser
    html = """
    <style>
        .file-browser {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
        }
        .file-table {
            width: 100%;
            border-collapse: collapse;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 20px 0;
            background: white;
        }
        .file-table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .file-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        .file-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        .file-table tbody tr:hover {
            background-color: #f5f7fa;
        }
        .checkbox-cell {
            text-align: center;
            width: 40px;
        }
        .checkbox-cell input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .file-id {
            font-family: monospace;
            font-size: 11px;
            color: #666;
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .instructions {
            background: linear-gradient(135deg, #e3f2fd 0%, #e1bee7 100%);
            border-left: 4px solid #2196F3;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }
        .instructions h3 {
            margin-top: 0;
            color: #1565C0;
        }
        .instructions ol {
            margin-bottom: 0;
        }
        .instructions li {
            margin: 8px 0;
        }
        .btn-copy {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .btn-copy:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .selected-count {
            font-weight: bold;
            color: #667eea;
            font-size: 18px;
            margin: 10px 0;
        }
        .type-icon {
            font-size: 20px;
        }
    </style>
    
    <div class="file-browser">
        <div class="instructions">
            <h3>📋 How to Download Files</h3>
            <ol>
                <li><strong>Select files</strong> by clicking the checkboxes below</li>
                <li><strong>Click the "Copy Selected File IDs" button</strong></li>
                <li><strong>Scroll down</strong> to the "Download Files" cell</li>
                <li><strong>Paste</strong> the file IDs into the download cell</li>
                <li><strong>Run the download cell</strong> to save files to your volume</li>
            </ol>
        </div>
        
        <div id="selected-info" class="selected-count">
            Selected: <span id="count">0</span> file(s)
        </div>
        
        <button onclick="copySelected()" class="btn-copy">
            📋 Copy Selected File IDs
        </button>
        
        <table class="file-table">
            <thead>
                <tr>
                    <th class="checkbox-cell">
                        <input type="checkbox" id="select-all" onchange="toggleAll(this)">
                    </th>
                    <th>Type</th>
                    <th>File Name</th>
                    <th>Size (MB)</th>
                    <th>Last Modified</th>
                    <th>File ID</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add rows for each file
    for idx, row in files_df.iterrows():
        file_type = row.get('type', '📄 File')
        name = row.get('name', 'Unknown')
        file_id = row.get('id', '')
        size_mb = row.get('size_mb', 0)
        modified = row.get('modifiedTime', 'N/A')
        
        # Format date
        if modified != 'N/A' and 'T' in str(modified):
            modified = str(modified).split('T')[0]
        
        # Escape for JavaScript
        name_escaped = name.replace("'", "\\'").replace('"', '\\"')
        
        html += f"""
            <tr>
                <td class="checkbox-cell">
                    <input type="checkbox" class="file-checkbox" 
                           data-fileid="{file_id}" 
                           data-filename="{name_escaped}" 
                           onchange="updateCount()">
                </td>
                <td class="type-icon">{file_type}</td>
                <td><strong>{name}</strong></td>
                <td>{size_mb:.2f}</td>
                <td>{modified}</td>
                <td><span class="file-id">{file_id}</span></td>
            </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <button onclick="copySelected()" class="btn-copy">
            📋 Copy Selected File IDs
        </button>
    </div>
    
    <script>
        function toggleAll(checkbox) {
            const checkboxes = document.querySelectorAll('.file-checkbox');
            checkboxes.forEach(cb => cb.checked = checkbox.checked);
            updateCount();
        }
        
        function updateCount() {
            const checked = document.querySelectorAll('.file-checkbox:checked');
            document.getElementById('count').textContent = checked.length;
        }
        
        function copySelected() {
            const checked = document.querySelectorAll('.file-checkbox:checked');
            const fileIds = Array.from(checked).map(cb => cb.dataset.fileid);
            
            if (fileIds.length === 0) {
                alert('⚠️ Please select at least one file first!');
                return;
            }
            
            const idsString = fileIds.join(', ');
            
            // Copy to clipboard
            navigator.clipboard.writeText(idsString).then(() => {
                alert(`✅ Copied ${fileIds.length} file ID(s)!\\n\\nNow scroll down and paste into the "Download Files" cell.`);
            }).catch(err => {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = idsString;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert(`✅ Copied ${fileIds.length} file ID(s)!\\n\\nNow scroll down and paste into the "Download Files" cell.`);
            });
        }
        
        // Initialize count
        updateCount();
    </script>
    """
    
    # Display the file browser
    displayHTML(html)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⬇️ Download Files
# MAGIC 
# MAGIC Paste the copied file IDs below and run this cell to download them.

# COMMAND ----------

# Paste your file IDs here (comma-separated)
FILE_IDS_TO_DOWNLOAD = ""

# Example: FILE_IDS_TO_DOWNLOAD = "1abc123, 2def456, 3ghi789"

if FILE_IDS_TO_DOWNLOAD.strip():
    print("="*80)
    print("📥 DOWNLOADING FILES")
    print("="*80)
    print()
    
    # Parse file IDs
    file_ids = [fid.strip() for fid in FILE_IDS_TO_DOWNLOAD.split(',') if fid.strip()]
    print(f"Files to download: {len(file_ids)}")
    print(f"Destination: {OUTPUT_PATH}")
    print()
    
    # Ensure output directory exists
    try:
        dbutils.fs.mkdirs(OUTPUT_PATH)
    except Exception as e:
        print(f"⚠️ Note: {str(e)}")
    
    # Download files
    downloaded = []
    failed = []
    
    for idx, file_id in enumerate(file_ids, 1):
        try:
            print(f"\n[{idx}/{len(file_ids)}] Downloading file ID: {file_id}")
            
            # Get file metadata
            file_metadata = drive_service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
            file_name = file_metadata.get('name')
            
            print(f"  📄 File: {file_name}")
            
            # Download file
            final_path = download_file_to_destination(
                drive_service,
                file_id,
                file_name,
                OUTPUT_PATH
            )
            
            downloaded.append({
                'file_name': file_name,
                'destination': final_path,
                'status': '✓ Success'
            })
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed.append({
                'file_id': file_id,
                'error': str(e),
                'status': '✗ Failed'
            })
    
    # Display summary
    print()
    print("="*80)
    print("📊 DOWNLOAD SUMMARY")
    print("="*80)
    print(f"✓ Successfully downloaded: {len(downloaded)}")
    print(f"✗ Failed: {len(failed)}")
    print("="*80)
    print()
    
    if downloaded:
        print("✓ Downloaded files:")
        display(pd.DataFrame(downloaded))
    
    if failed:
        print("\n✗ Failed downloads:")
        display(pd.DataFrame(failed))
    
    print(f"\n💾 All files are saved to: {OUTPUT_PATH}")
    
else:
    print("ℹ️ To download files:")
    print("   1. Select files in the File Browser above")
    print("   2. Click 'Copy Selected File IDs'")
    print("   3. Paste the IDs into FILE_IDS_TO_DOWNLOAD above")
    print("   4. Run this cell")
    print()
    print("   Example:")
    print('   FILE_IDS_TO_DOWNLOAD = "1abc123, 2def456"')

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 View Downloaded Files
# MAGIC 
# MAGIC List files in your output directory.

# COMMAND ----------

try:
    files = dbutils.fs.ls(OUTPUT_PATH)
    
    if files:
        print(f"📁 Files in {OUTPUT_PATH}:")
        print()
        
        files_info = []
        for f in files:
            size_mb = f.size / (1024 * 1024)
            files_info.append({
                'Name': f.name,
                'Size (MB)': f'{size_mb:.2f}',
                'Path': f.path
            })
        
        display(pd.DataFrame(files_info))
    else:
        print(f"ℹ️ No files found in {OUTPUT_PATH}")
        print("   Download some files first using the cells above.")
        
except Exception as e:
    print(f"⚠️ Could not access {OUTPUT_PATH}")
    print(f"   Error: {e}")
    print("   Make sure the path exists and you have access.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC 
# MAGIC ## 📤 Export Delta Table to Google Drive
# MAGIC 
# MAGIC Upload a Delta table from Databricks back to Google Drive as CSV or Parquet.

# COMMAND ----------

# Import the export function
from google_drive_utils import export_table_to_google_drive

# Configure your export
TABLE_NAME = ""  # Example: "main.default.sales_data"
OUTPUT_FILE_NAME = ""  # Example: "sales_report"
EXPORT_FORMAT = "csv"  # Options: "csv" or "parquet"
UPLOAD_FOLDER_ID = FOLDER_ID  # Uses the same folder from settings above, or change to a different folder ID
MAX_ROWS = None  # Set a number to limit rows (e.g., 10000), or leave as None for all rows

# Example:
# TABLE_NAME = "main.default.sales_data"
# OUTPUT_FILE_NAME = "monthly_sales_report"
# EXPORT_FORMAT = "csv"
# MAX_ROWS = 10000  # Export only first 10,000 rows

if TABLE_NAME.strip():
    print("="*80)
    print("📤 EXPORTING TABLE TO GOOGLE DRIVE")
    print("="*80)
    print()
    
    try:
        # Export and upload
        file_id = export_table_to_google_drive(
            spark,
            drive_service,
            TABLE_NAME,
            OUTPUT_FILE_NAME,
            folder_id=UPLOAD_FOLDER_ID,
            file_format=EXPORT_FORMAT,
            max_rows=MAX_ROWS
        )
        
        print()
        print("="*80)
        print("✅ EXPORT COMPLETE!")
        print("="*80)
        print(f"Table: {TABLE_NAME}")
        print(f"Format: {EXPORT_FORMAT.upper()}")
        print(f"File ID: {file_id}")
        print(f"Folder: {'Root' if not UPLOAD_FOLDER_ID else UPLOAD_FOLDER_ID}")
        print()
        print("💡 You can now access this file in Google Drive!")
        print("="*80)
        
    except Exception as e:
        print()
        print("="*80)
        print("❌ EXPORT FAILED")
        print("="*80)
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  - Table name is incorrect (use: catalog.schema.table)")
        print("  - Table doesn't exist or you don't have access")
        print("  - Google Drive API permissions issue")
        print("="*80)
        
else:
    print("ℹ️ To export a Delta table to Google Drive:")
    print()
    print("   1. Enter the full table name (e.g., 'main.default.my_table')")
    print("   2. Choose an output file name")
    print("   3. Select format: 'csv' or 'parquet'")
    print("   4. Optionally limit rows with MAX_ROWS")
    print("   5. Run this cell")
    print()
    print("   Example:")
    print('   TABLE_NAME = "main.default.sales_data"')
    print('   OUTPUT_FILE_NAME = "sales_report"')
    print('   EXPORT_FORMAT = "csv"')
    print('   MAX_ROWS = 10000  # Optional')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC 
# MAGIC ## 💡 Tips
# MAGIC 
# MAGIC - **Change folders**: Update the "Folder ID" widget and re-run cells
# MAGIC - **Download more files**: Just run the "Download Files" cell again with new IDs
# MAGIC - **Export tables**: Use the cell above to push Delta tables back to Google Drive
# MAGIC - **View files**: Use the "View Downloaded Files" cell to see what's been downloaded
# MAGIC 
# MAGIC ## 🔧 Advanced
# MAGIC 
# MAGIC For programmatic access, import the utility module:
# MAGIC ```python
# MAGIC from google_drive_utils import (
# MAGIC     download_file_to_destination,
# MAGIC     export_table_to_google_drive
# MAGIC )
# MAGIC 
# MAGIC # Download from Google Drive
# MAGIC download_file_to_destination(drive_service, file_id, file_name, OUTPUT_PATH)
# MAGIC 
# MAGIC # Upload to Google Drive
# MAGIC export_table_to_google_drive(spark, drive_service, "catalog.schema.table", "output.csv")
# MAGIC ```
# MAGIC 
# MAGIC See `MODULE_README.md` and `USAGE_EXAMPLES.md` for more details.
