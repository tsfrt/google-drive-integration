# Databricks notebook source
# MAGIC %md
# MAGIC # Google Drive Data Ingestion
# MAGIC 
# MAGIC This notebook provides an interface to ingest data from Google Drive into Databricks.
# MAGIC 
# MAGIC ## Setup Requirements:
# MAGIC 1. Create a Databricks secret scope with Google Drive credentials
# MAGIC 2. Store your Google Drive service account JSON or OAuth credentials in the secret scope
# MAGIC 3. Install required libraries: `%pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
# MAGIC 
# MAGIC ## Widgets:
# MAGIC - **secret_scope**: Name of the Databricks secret scope containing Google Drive credentials
# MAGIC - **credentials_key**: Key name for the Google Drive credentials in the secret scope
# MAGIC - **folder_id**: (Optional) Google Drive folder ID to list files from (leave empty for root)
# MAGIC - **file_selection**: Comma-separated list of file IDs to ingest (populated after listing)
# MAGIC - **output_path**: DBFS path where ingested files will be stored

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
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pyspark.sql import SparkSession
import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Widgets

# COMMAND ----------

# Create widgets for user input
dbutils.widgets.text("secret_scope", "", "1. Secret Scope Name")
dbutils.widgets.text("credentials_key", "google_drive_credentials", "2. Credentials Key")
dbutils.widgets.text("folder_id", "", "3. Google Drive Folder ID (optional)")
dbutils.widgets.text("file_selection", "", "4. File IDs to Ingest (comma-separated)")
dbutils.widgets.text("output_path", "/mnt/ingest/google_drive", "5. Output DBFS Path")
dbutils.widgets.dropdown("action", "list_files", ["list_files", "ingest_files"], "6. Action")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get Widget Values

# COMMAND ----------

# Get widget values
secret_scope = dbutils.widgets.get("secret_scope")
credentials_key = dbutils.widgets.get("credentials_key")
folder_id = dbutils.widgets.get("folder_id") or None
file_selection = dbutils.widgets.get("file_selection")
output_path = dbutils.widgets.get("output_path")
action = dbutils.widgets.get("action")

# Validate required inputs
if not secret_scope:
    raise ValueError("Secret Scope Name is required!")

print(f"Configuration:")
print(f"  Secret Scope: {secret_scope}")
print(f"  Credentials Key: {credentials_key}")
print(f"  Folder ID: {folder_id if folder_id else 'Root'}")
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
        
        # Create a display DataFrame with relevant columns
        display_cols = ['type', 'name', 'id', 'size_mb', 'modifiedTime']
        display_df = files_df[display_cols].copy()
        display_df.columns = ['Type', 'Name', 'File ID', 'Size (MB)', 'Modified']
        
        # Display the files
        display(display_df)
        
        print("\n" + "="*80)
        print("To ingest files:")
        print("1. Copy the File IDs from the table above")
        print("2. Paste them into the 'File IDs to Ingest' widget (comma-separated)")
        print("3. Change the Action widget to 'ingest_files'")
        print("4. Run the next cells")
        print("="*80)
    else:
        print("No files found in the specified location.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Download File Function

# COMMAND ----------

def download_file(service, file_id, file_name, local_path):
    """
    Download a file from Google Drive.
    
    Args:
        service: Google Drive service object
        file_id: ID of the file to download
        file_name: Name of the file
        local_path: Local path to save the file
    
    Returns:
        Path to the downloaded file
    """
    try:
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='mimeType,name').execute()
        mime_type = file_metadata.get('mimeType')
        
        # Handle Google Workspace files (need to be exported)
        export_formats = {
            'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
            'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
            'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
        }
        
        file_path = os.path.join(local_path, file_name)
        
        if mime_type in export_formats:
            # Export Google Workspace file
            export_mime, extension = export_formats[mime_type]
            if not file_name.endswith(extension):
                file_path += extension
            
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            print(f"  Exporting {file_name} as {extension[1:].upper()}...")
        else:
            # Download regular file
            request = service.files().get_media(fileId=file_id)
            print(f"  Downloading {file_name}...")
        
        # Download the file
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"    Progress: {int(status.progress() * 100)}%")
        
        fh.close()
        print(f"  ✓ Downloaded to: {file_path}")
        
        return file_path
        
    except Exception as e:
        print(f"  ✗ Error downloading {file_name}: {str(e)}")
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
        
        # Create temporary local directory
        import tempfile
        local_temp_dir = tempfile.mkdtemp()
        print(f"Temporary directory: {local_temp_dir}\n")
        
        # Create output directory in DBFS
        dbutils.fs.mkdirs(output_path)
        
        ingested_files = []
        failed_files = []
        
        for idx, file_id in enumerate(file_ids, 1):
            try:
                print(f"\n[{idx}/{len(file_ids)}] Processing file ID: {file_id}")
                
                # Get file metadata
                file_metadata = drive_service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
                file_name = file_metadata.get('name')
                
                print(f"  File name: {file_name}")
                
                # Download file
                local_file_path = download_file(drive_service, file_id, file_name, local_temp_dir)
                
                # Copy to DBFS
                dbfs_path = f"{output_path}/{os.path.basename(local_file_path)}"
                dbutils.fs.cp(f"file://{local_file_path}", dbfs_path)
                print(f"  ✓ Copied to DBFS: {dbfs_path}")
                
                ingested_files.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'dbfs_path': dbfs_path,
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"  ✗ Failed to process file: {str(e)}")
                failed_files.append({
                    'file_id': file_id,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(local_temp_dir)
        
        # Display summary
        print(f"\n{'='*80}")
        print("INGESTION SUMMARY")
        print(f"{'='*80}")
        print(f"✓ Successfully ingested: {len(ingested_files)}")
        print(f"✗ Failed: {len(failed_files)}")
        print(f"{'='*80}\n")
        
        if ingested_files:
            print("Successfully ingested files:")
            ingested_df = pd.DataFrame(ingested_files)
            display(ingested_df)
        
        if failed_files:
            print("\nFailed files:")
            failed_df = pd.DataFrame(failed_files)
            display(failed_df)
        
        print(f"\nAll files are available at: {output_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Ingested Data (Optional)

# COMMAND ----------

# Example: Load CSV files from the ingested data
# Uncomment and modify as needed for your use case

# csv_files = [f.path for f in dbutils.fs.ls(output_path) if f.path.endswith('.csv')]
# if csv_files:
#     print(f"Found {len(csv_files)} CSV files")
#     for csv_file in csv_files:
#         print(f"  - {csv_file}")
#         df = spark.read.csv(csv_file, header=True, inferSchema=True)
#         display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility: Clear Widgets (for cleanup)

# COMMAND ----------

# Uncomment to remove all widgets
# dbutils.widgets.removeAll()

