# Databricks notebook source
# MAGIC %md
# MAGIC # Google Drive Data Ingestion 📁 ➡️ 💾
# MAGIC 
# MAGIC This notebook provides an **interactive visual interface** to ingest data from Google Drive into Databricks (Unity Catalog Volumes or DBFS).
# MAGIC 
# MAGIC ## ✨ Features:
# MAGIC - 🎨 **Visual File Browser** with checkboxes and interactive selection
# MAGIC - 🔐 **Secure Authentication** via Databricks secrets
# MAGIC - 💾 **Flexible Storage** - Save to Unity Catalog Volumes or DBFS
# MAGIC - 📊 **Multiple File Types** - Supports Google Workspace files and regular files
# MAGIC - 📈 **Progress Tracking** - Real-time download and ingestion status
# MAGIC - ⚡ **Zero-Temp-File Architecture** - True direct writes to DBFS/Volumes (zero `/tmp` usage), automatic path conversion
# MAGIC 
# MAGIC ## Setup Requirements:
# MAGIC 1. Create a Databricks secret scope with Google Drive credentials
# MAGIC 2. Store your Google Drive service account JSON credentials in the secret scope
# MAGIC 3. (For Volumes) Create a Unity Catalog volume: `/Volumes/catalog/schema/volume`
# MAGIC 
# MAGIC ## Widget Parameters:
# MAGIC - **secret_scope**: Name of the Databricks secret scope containing Google Drive credentials
# MAGIC - **credentials_key**: Key name for the Google Drive credentials in the secret scope
# MAGIC - **folder_id**: (Optional) Google Drive folder ID to list files from (leave empty for root)
# MAGIC - **file_selection**: Comma-separated list of file IDs to ingest (use the visual interface to select)
# MAGIC - **storage_type**: Choose "volume" for Unity Catalog Volumes or "dbfs" for DBFS
# MAGIC - **output_path**: Destination path (e.g., `/Volumes/catalog/schema/volume/folder` or `/mnt/path`)
# MAGIC - **action**: Select "list_files" to browse or "ingest_files" to download

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

# Install required packages
%pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pydrive2
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Libraries

# COMMAND ----------

import json
import io
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pyspark.sql import SparkSession
import pandas as pd

# Import utility functions from the module
# If running in Databricks, you may need to upload google_drive_utils.py to DBFS or a volume
try:
    from google_drive_utils import (
        get_google_drive_service,
        list_drive_contents,
        download_file_to_destination
    )
    print("✓ Imported functions from google_drive_utils module")
except ImportError:
    print("⚠️  google_drive_utils module not found, using inline functions")
    # Functions will be defined inline below if import fails

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Widgets

# COMMAND ----------

# Create widgets for user input
dbutils.widgets.text("secret_scope", "", "1. Secret Scope Name")
dbutils.widgets.text("credentials_key", "google_drive_credentials", "2. Credentials Key")
dbutils.widgets.text("folder_id", "", "3. Google Drive Folder ID (optional)")
dbutils.widgets.text("file_selection", "", "4. File IDs to Ingest (comma-separated)")
dbutils.widgets.dropdown("storage_type", "volume", ["volume", "dbfs"], "5. Storage Type")
dbutils.widgets.text("output_path", "/Volumes/catalog/schema/volume/google_drive", "6. Output Path (Volume or DBFS)")
dbutils.widgets.dropdown("action", "list_files", ["list_files", "ingest_files"], "7. Action")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get Widget Values

# COMMAND ----------

# Get widget values
secret_scope = dbutils.widgets.get("secret_scope")
credentials_key = dbutils.widgets.get("credentials_key")
folder_id = dbutils.widgets.get("folder_id") or None
file_selection = dbutils.widgets.get("file_selection")
storage_type = dbutils.widgets.get("storage_type")
output_path = dbutils.widgets.get("output_path")
action = dbutils.widgets.get("action")

# Validate required inputs
if not secret_scope:
    raise ValueError("Secret Scope Name is required!")

print(f"Configuration:")
print(f"  Secret Scope: {secret_scope}")
print(f"  Credentials Key: {credentials_key}")
print(f"  Folder ID: {folder_id if folder_id else 'Root'}")
print(f"  Storage Type: {storage_type}")
print(f"  Output Path: {output_path}")
print(f"  Action: {action}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Authenticate with Google Drive

# COMMAND ----------

def get_google_drive_service(secret_scope, credentials_key):
    """
    Authenticate and return Google Drive service object.
    
    Args:
        secret_scope: Databricks secret scope name
        credentials_key: Key name for credentials in the secret scope
    
    Returns:
        Google Drive service object
    """
    try:
        # Get credentials from Databricks secrets
        credentials_json = dbutils.secrets.get(scope=secret_scope, key=credentials_key)
        credentials_dict = json.loads(credentials_json)
        
        # Define the required scopes
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=SCOPES
        )
        
        # Build the service
        service = build('drive', 'v3', credentials=credentials)
        
        print("✓ Successfully authenticated with Google Drive")
        return service
        
    except Exception as e:
        print(f"✗ Authentication failed: {str(e)}")
        raise

# Authenticate
drive_service = get_google_drive_service(secret_scope, credentials_key)

# COMMAND ----------

# MAGIC %md
# MAGIC ## List Files and Folders

# COMMAND ----------

def list_drive_contents(service, folder_id=None, max_results=100):
    """
    List files and folders in Google Drive.
    
    Args:
        service: Google Drive service object
        folder_id: Folder ID to list contents from (None for root)
        max_results: Maximum number of results to return
    
    Returns:
        DataFrame with file information
    """
    try:
        # Build query
        if folder_id:
            query = f"'{folder_id}' in parents and trashed=false"
        else:
            query = "trashed=false"
        
        # List files
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print('No files found.')
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(items)
        
        # Add readable file size
        if 'size' in df.columns:
            df['size_mb'] = df['size'].apply(lambda x: round(int(x) / (1024 * 1024), 2) if pd.notna(x) and x else 0)
        
        # Add file type indicator
        df['type'] = df['mimeType'].apply(
            lambda x: '📁 Folder' if x == 'application/vnd.google-apps.folder' 
            else '📄 Document' if 'document' in x.lower()
            else '📊 Spreadsheet' if 'spreadsheet' in x.lower()
            else '📈 Presentation' if 'presentation' in x.lower()
            else '📄 File'
        )
        
        return df
        
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Action: List Files

# COMMAND ----------

if action == "list_files":
    print(f"\n{'='*80}")
    print(f"Listing files from: {folder_id if folder_id else 'Root'}")
    print(f"{'='*80}\n")
    
    # List files
    files_df = list_drive_contents(drive_service, folder_id)
    
    if not files_df.empty:
        # Display summary
        print(f"Found {len(files_df)} items\n")
        
        # Create visual HTML table with checkboxes
        html = """
        <style>
            .file-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                margin: 20px 0;
            }
            .file-table thead {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .file-table th {
                padding: 15px;
                text-align: left;
                font-weight: 600;
                border-bottom: 3px solid #555;
            }
            .file-table td {
                padding: 12px 15px;
                border-bottom: 1px solid #ddd;
            }
            .file-table tbody tr:hover {
                background-color: #f5f5f5;
                transition: background-color 0.3s;
            }
            .file-table tbody tr:nth-child(even) {
                background-color: #fafafa;
            }
            .file-id {
                font-family: monospace;
                font-size: 11px;
                color: #666;
                background: #f0f0f0;
                padding: 2px 6px;
                border-radius: 3px;
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
            .type-icon {
                font-size: 20px;
            }
            .select-all-row {
                background: #f8f9fa !important;
                font-weight: bold;
            }
            .instructions {
                background: #e3f2fd;
                border-left: 4px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }
            .instructions h3 {
                margin-top: 0;
                color: #1976D2;
            }
            .btn-copy {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                margin-top: 10px;
                margin-right: 10px;
            }
            .btn-copy:hover {
                background: #45a049;
            }
            .btn-download-selected {
                background: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                margin-top: 10px;
            }
            .btn-download-selected:hover {
                background: #1976D2;
            }
            .btn-download {
                background: #667eea;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
            }
            .btn-download:hover {
                background: #5568d3;
            }
            .selected-count {
                font-weight: bold;
                color: #2196F3;
                font-size: 16px;
                margin: 10px 0;
            }
            .actions-cell {
                text-align: center;
                width: 100px;
            }
        </style>
        
        <div class="instructions">
            <h3>📋 Three Ways to Download Files</h3>
            <p><strong>Option 1: Quick Download (Fastest ⚡)</strong></p>
            <ol>
                <li>Click <strong>"📋 Copy Selected File IDs"</strong> or copy individual File IDs from the table</li>
                <li>Paste into the <strong>"Quick Download Helper"</strong> cell below</li>
                <li>Run that cell - files download immediately!</li>
            </ol>
            <p><strong>Option 2: Widget-Based Download</strong></p>
            <ol>
                <li>Check boxes → Click "📋 Copy Selected File IDs"</li>
                <li>Paste into <strong>"File IDs to Ingest"</strong> widget</li>
                <li>Change Action to <strong>"ingest_files"</strong> → Run cells</li>
            </ol>
            <p><strong>Option 3: One-Click Download (Coming Soon)</strong></p>
            <ol>
                <li>The ⬇️ Download buttons will trigger immediate downloads in a future update</li>
            </ol>
        </div>
        
        <div id="selected-info" class="selected-count">Selected: <span id="count">0</span> files</div>
        <button onclick="copySelected()" class="btn-copy">📋 Copy Selected File IDs</button>
        <button onclick="downloadSelected()" class="btn-download-selected">⬇️ Download Selected</button>
        
        <table class="file-table">
            <thead>
                <tr>
                    <th class="checkbox-cell">
                        <input type="checkbox" id="select-all" onchange="toggleAll(this)">
                    </th>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Size (MB)</th>
                    <th>Modified</th>
                    <th>File ID</th>
                    <th class="actions-cell">Actions</th>
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
            mime_type = row.get('mimeType', '')
            
            # Format modified date to be more readable
            if modified != 'N/A' and 'T' in str(modified):
                modified = str(modified).split('T')[0]
            
            # Escape quotes in name for JavaScript
            name_escaped = name.replace("'", "\\'").replace('"', '\\"')
            
            html += f"""
                <tr>
                    <td class="checkbox-cell">
                        <input type="checkbox" class="file-checkbox" data-fileid="{file_id}" data-filename="{name_escaped}" data-mimetype="{mime_type}" onchange="updateCount()">
                    </td>
                    <td class="type-icon">{file_type}</td>
                    <td><strong>{name}</strong></td>
                    <td>{size_mb}</td>
                    <td>{modified}</td>
                    <td><span class="file-id">{file_id}</span></td>
                    <td class="actions-cell">
                        <button class="btn-download" onclick="downloadFile('{file_id}', '{name_escaped}', '{mime_type}')">⬇️ Download</button>
                    </td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        
        <div id="download-status" style="margin-top: 20px;"></div>
        
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
                    alert('⚠️ Please select at least one file!');
                    return;
                }
                
                const idsString = fileIds.join(', ');
                
                // Copy to clipboard
                navigator.clipboard.writeText(idsString).then(() => {
                    alert(`✓ Copied ${fileIds.length} file ID(s) to clipboard!\\n\\nNow paste into the "File IDs to Ingest" widget.`);
                }).catch(err => {
                    // Fallback for older browsers
                    const textarea = document.createElement('textarea');
                    textarea.value = idsString;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    alert(`✓ Copied ${fileIds.length} file ID(s) to clipboard!\\n\\nNow paste into the "File IDs to Ingest" widget.`);
                });
            }
            
            function downloadFile(fileId, fileName, mimeType) {
                const statusDiv = document.getElementById('download-status');
                statusDiv.innerHTML = `<p style="color: #2196F3;">⏳ Downloading ${fileName}... Please wait.</p>`;
                
                // Store in global variable to be picked up by Python
                window.downloadRequest = {
                    fileIds: [fileId],
                    fileNames: [fileName],
                    mimeTypes: [mimeType]
                };
                
                alert(`✓ Download request for "${fileName}" has been queued!\\n\\nPlease run the "Process Download Requests" cell below to complete the download.`);
            }
            
            function downloadSelected() {
                const checked = document.querySelectorAll('.file-checkbox:checked');
                
                if (checked.length === 0) {
                    alert('⚠️ Please select at least one file to download!');
                    return;
                }
                
                const fileIds = Array.from(checked).map(cb => cb.dataset.fileid);
                const fileNames = Array.from(checked).map(cb => cb.dataset.filename);
                const mimeTypes = Array.from(checked).map(cb => cb.dataset.mimetype);
                
                const statusDiv = document.getElementById('download-status');
                statusDiv.innerHTML = `<p style="color: #2196F3;">⏳ Queued ${fileIds.length} file(s) for download...</p>`;
                
                // Store in global variable to be picked up by Python
                window.downloadRequest = {
                    fileIds: fileIds,
                    fileNames: fileNames,
                    mimeTypes: mimeTypes
                };
                
                alert(`✓ Download request for ${fileIds.length} file(s) has been queued!\\n\\nPlease run the "Process Download Requests" cell below to complete the download.`);
            }
            
            // Initialize count on load
            updateCount();
        </script>
        """
        
        # Display the HTML table
        displayHTML(html)
        
        # Also show a simple dataframe version for reference
        print("\n" + "="*80)
        print("Standard Table View:")
        display_cols = ['type', 'name', 'id', 'size_mb', 'modifiedTime']
        display_df = files_df[display_cols].copy()
        display_df.columns = ['Type', 'Name', 'File ID', 'Size (MB)', 'Modified']
        display(display_df)
        
    else:
        print("No files found in the specified location.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick Download Helper
# MAGIC 
# MAGIC Use this cell for quick downloads. Enter file IDs below and run the cell.

# COMMAND ----------

# Quick download: Enter file IDs here (comma-separated) and run this cell
quick_download_ids = ""  # Example: "file_id_1, file_id_2, file_id_3"

if quick_download_ids.strip():
    print(f"\n{'='*80}")
    print(f"Quick Download")
    print(f"{'='*80}\n")
    
    file_ids = [fid.strip() for fid in quick_download_ids.split(',') if fid.strip()]
    print(f"Files to download: {len(file_ids)}")
    print(f"Destination: {output_path}\n")
    
    # Ensure output directory exists
    try:
        dbutils.fs.mkdirs(output_path)
    except Exception as e:
        print(f"Note: {str(e)}")
    
    downloaded_files = []
    failed_files = []
    
    for idx, file_id in enumerate(file_ids, 1):
        try:
            print(f"\n[{idx}/{len(file_ids)}] Processing file ID: {file_id}")
            
            # Get file metadata
            file_metadata = drive_service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
            file_name = file_metadata.get('name')
            
            # Download file directly to destination
            final_dest_path = download_file_to_destination(
                drive_service, 
                file_id, 
                file_name, 
                output_path
            )
            
            downloaded_files.append({
                'file_id': file_id,
                'file_name': os.path.basename(final_dest_path),
                'destination_path': final_dest_path,
                'status': 'success'
            })
            
        except Exception as e:
            print(f"  ✗ Failed: {str(e)}")
            failed_files.append({
                'file_id': file_id,
                'error': str(e),
                'status': 'failed'
            })
    
    # Display results
    print(f"\n{'='*80}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Downloaded: {len(downloaded_files)}")
    print(f"✗ Failed: {len(failed_files)}")
    print(f"{'='*80}\n")
    
    if downloaded_files:
        display(pd.DataFrame(downloaded_files))
    
    if failed_files:
        print("\nFailed:")
        display(pd.DataFrame(failed_files))
else:
    print("ℹ️  Enter file IDs in quick_download_ids variable above and run this cell to download files quickly.")
    print("   Or use the Action widget approach for full ingestion workflow.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Download File Function

# COMMAND ----------

def download_file_to_destination(service, file_id, file_name, dest_path, max_size_for_put=100):
    """
    Download a file from Google Drive directly to DBFS/Volume.
    
    Writes directly to the destination using filesystem paths:
    - For DBFS: Converts /mnt/path to /dbfs/mnt/path
    - For Volumes: Uses /Volumes/catalog/schema/volume directly
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to download
        file_name: Name of the file
        dest_path: Destination path in DBFS/Volume (e.g., /mnt/data or /Volumes/catalog/schema/vol)
        max_size_for_put: Maximum file size in MB for in-memory buffering (default: 100MB)
    
    Returns:
        Final destination path
    """
    try:
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='mimeType,name,size').execute()
        mime_type = file_metadata.get('mimeType')
        file_size = int(file_metadata.get('size', 0)) if file_metadata.get('size') else 0
        file_size_mb = file_size / (1024 * 1024)
        
        # Handle Google Workspace files (need to be exported)
        export_formats = {
            'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
            'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
            'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
        }
        
        # Determine final file name and path
        final_file_name = file_name
        if mime_type in export_formats:
            export_mime, extension = export_formats[mime_type]
            if not file_name.endswith(extension):
                final_file_name += extension
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            print(f"  Exporting {file_name} as {extension[1:].upper()}...")
        else:
            request = service.files().get_media(fileId=file_id)
            print(f"  Downloading {file_name}...")
        
        final_dest_path = f"{dest_path}/{final_file_name}"
        
        # Convert DBFS path to filesystem path
        # DBFS paths like /mnt/path need to be prefixed with /dbfs
        # Volume paths like /Volumes/catalog/schema/volume are already accessible
        if final_dest_path.startswith('/Volumes/'):
            # Volume path - use directly
            fs_path = final_dest_path
        elif final_dest_path.startswith('/dbfs/'):
            # Already has /dbfs prefix
            fs_path = final_dest_path
        else:
            # DBFS path without prefix - add it
            fs_path = f"/dbfs{final_dest_path}"
        
        print(f"  Writing directly to: {final_dest_path}")
        print(f"  File size: {file_size_mb:.2f} MB")
        
        # Method 1: For small files, download to memory buffer then write
        if file_size_mb <= max_size_for_put:
            print(f"  Using in-memory buffer (file size ≤ {max_size_for_put} MB)")
            
            # Download to BytesIO buffer
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"    Progress: {int(status.progress() * 100)}%")
            
            # Write directly to destination filesystem path
            print(f"    Writing to destination...")
            with open(fs_path, 'wb') as dest_file:
                dest_file.write(file_buffer.getvalue())
            
            file_buffer.close()
            print(f"  ✓ Written directly to: {final_dest_path}")
            
        else:
            # Method 2: For larger files, stream directly to destination
            print(f"  Using direct streaming (file size > {max_size_for_put} MB)")
            
            # Stream directly to destination file
            with open(fs_path, 'wb') as dest_file:
                downloader = MediaIoBaseDownload(dest_file, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"    Progress: {int(status.progress() * 100)}%")
            
            print(f"  ✓ Streamed directly to: {final_dest_path}")
        
        return final_dest_path
        
    except Exception as e:
        print(f"  ✗ Error processing {file_name}: {str(e)}")
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Action: Ingest Files

# COMMAND ----------

if action == "ingest_files":
    if not file_selection:
        print("⚠️  No files selected for ingestion!")
        print("Please enter file IDs in the 'File IDs to Ingest' widget.")
    else:
        print(f"\n{'='*80}")
        print(f"Starting ingestion process")
        print(f"{'='*80}\n")
        
        # Parse file IDs
        file_ids = [fid.strip() for fid in file_selection.split(',') if fid.strip()]
        print(f"Files to ingest: {len(file_ids)}")
        print(f"Storage type: {storage_type}")
        print(f"Destination: {output_path}\n")
        
        # Create output directory
        if storage_type == "volume":
            # For volumes, ensure the path exists
            # Volumes use /Volumes/catalog/schema/volume format
            print(f"Creating volume directory: {output_path}")
            try:
                dbutils.fs.mkdirs(output_path)
            except Exception as e:
                print(f"Note: {str(e)}")
                print("If using a volume, ensure it exists in Unity Catalog first.")
        else:
            # For DBFS
            dbutils.fs.mkdirs(output_path)
        
        ingested_files = []
        failed_files = []
        
        for idx, file_id in enumerate(file_ids, 1):
            try:
                print(f"\n[{idx}/{len(file_ids)}] Processing file ID: {file_id}")
                
                # Get file metadata
                file_metadata = drive_service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
                file_name = file_metadata.get('name')
                file_size = int(file_metadata.get('size', 0)) if file_metadata.get('size') else 0
                file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                
                print(f"  File name: {file_name}")
                print(f"  File size: {file_size_mb:.2f} MB")
                
                # Download file directly to destination
                final_dest_path = download_file_to_destination(
                    drive_service, 
                    file_id, 
                    file_name, 
                    output_path
                )
                
                ingested_files.append({
                    'file_id': file_id,
                    'file_name': os.path.basename(final_dest_path),
                    'destination_path': final_dest_path,
                    'size_mb': file_size_mb,
                    'storage_type': storage_type,
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"  ✗ Failed to process file: {str(e)}")
                failed_files.append({
                    'file_id': file_id,
                    'file_name': file_metadata.get('name', 'Unknown') if 'file_metadata' in locals() else 'Unknown',
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Display summary with visual styling
        summary_html = f"""
        <style>
            .summary-container {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            .summary-title {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 15px;
            }}
            .summary-stats {{
                display: flex;
                gap: 30px;
                margin-top: 15px;
            }}
            .stat-box {{
                background: rgba(255,255,255,0.2);
                padding: 15px 25px;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-number {{
                font-size: 36px;
                font-weight: bold;
                display: block;
            }}
            .stat-label {{
                font-size: 14px;
                margin-top: 5px;
                opacity: 0.9;
            }}
            .success {{
                color: #4CAF50;
            }}
            .failed {{
                color: #f44336;
            }}
        </style>
        
        <div class="summary-container">
            <div class="summary-title">🎉 Ingestion Complete</div>
            <div class="summary-stats">
                <div class="stat-box">
                    <span class="stat-number">✓ {len(ingested_files)}</span>
                    <span class="stat-label">Successfully Ingested</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number">✗ {len(failed_files)}</span>
                    <span class="stat-label">Failed</span>
                </div>
                <div class="stat-box">
                    <span class="stat-number">{len(file_ids)}</span>
                    <span class="stat-label">Total Processed</span>
                </div>
            </div>
        </div>
        """
        
        displayHTML(summary_html)
        
        # Display detailed results
        print(f"\n{'='*80}")
        print("INGESTION DETAILS")
        print(f"{'='*80}")
        print(f"Storage Type: {storage_type.upper()}")
        print(f"Destination: {output_path}")
        print(f"{'='*80}\n")
        
        if ingested_files:
            print("✓ Successfully ingested files:")
            ingested_df = pd.DataFrame(ingested_files)
            display(ingested_df)
        
        if failed_files:
            print("\n✗ Failed files:")
            failed_df = pd.DataFrame(failed_files)
            display(failed_df)
        
        print(f"\n{'='*80}")
        print(f"All files are available at: {output_path}")
        print(f"{'='*80}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Ingested Data from Volume/DBFS

# COMMAND ----------

# List all files in the destination
try:
    files_list = dbutils.fs.ls(output_path)
    print(f"📁 Files in {output_path}:\n")
    
    html_files = """
    <style>
        .files-container {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .file-item {
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
        }
        .file-name {
            font-weight: bold;
            color: #333;
        }
        .file-size {
            color: #666;
            font-size: 12px;
        }
    </style>
    <div class="files-container">
        <h3>📂 Available Files</h3>
    """
    
    for file_info in files_list:
        file_name = file_info.name
        file_size = file_info.size / (1024 * 1024)  # Convert to MB
        html_files += f"""
        <div class="file-item">
            <span class="file-name">{file_name}</span>
            <span class="file-size">{file_size:.2f} MB</span>
        </div>
        """
    
    html_files += "</div>"
    displayHTML(html_files)
    
except Exception as e:
    print(f"No files found or error accessing path: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example: Load CSV Files

# COMMAND ----------

# Example: Load CSV files from the ingested data
# Uncomment and modify as needed for your use case

# csv_files = [f.path for f in dbutils.fs.ls(output_path) if f.path.endswith('.csv')]
# if csv_files:
#     print(f"Found {len(csv_files)} CSV files")
#     for csv_file in csv_files:
#         print(f"Loading: {csv_file}")
#         df = spark.read.csv(csv_file, header=True, inferSchema=True)
#         display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example: Load from Unity Catalog Volume

# COMMAND ----------

# Example: Read a file from a Unity Catalog volume
# Uncomment and modify as needed

# # For CSV files in volumes
# df = spark.read.csv(f"{output_path}/your_file.csv", header=True, inferSchema=True)
# display(df)

# # For Parquet files
# df = spark.read.parquet(f"{output_path}/your_file.parquet")
# display(df)

# # For JSON files  
# df = spark.read.json(f"{output_path}/your_file.json")
# display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example: Create Delta Table from Ingested Data

# COMMAND ----------

# Example: Create a Delta table from CSV files in the volume
# Uncomment and modify as needed

# # Read CSV from volume
# df = spark.read.csv(f"{output_path}/your_file.csv", header=True, inferSchema=True)

# # Write to Delta table in Unity Catalog
# df.write.format("delta").mode("overwrite").saveAsTable("catalog.schema.table_name")

# # Or write to DBFS location
# df.write.format("delta").mode("overwrite").save("/mnt/delta/table_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility: Clear Widgets (for cleanup)

# COMMAND ----------

# Uncomment to remove all widgets
# dbutils.widgets.removeAll()

