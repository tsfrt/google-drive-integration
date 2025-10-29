# Google Drive to Databricks Ingestion 📁 ➡️ 💾

This project provides a Databricks notebook interface for ingesting data from Google Drive into **Unity Catalog Volumes** or **DBFS** with a beautiful **visual file browser** and interactive selection interface.

## ✨ Features

- 🎨 **Visual File Browser**: Interactive HTML table with checkboxes for easy file selection
- 🔐 **Secure Authentication**: Uses Databricks secrets for Google Drive credentials
- 💾 **Flexible Storage**: Save to Unity Catalog Volumes or DBFS
- ✅ **Interactive Selection**: Click checkboxes and copy file IDs with one button
- 📊 **Multiple File Types**: Supports Google Workspace files (Docs, Sheets, Slides) and regular files
- 📈 **Progress Tracking**: Real-time download and ingestion progress with visual summaries
- 🎯 **Widget Interface**: Easy-to-use parameter widgets for configuration
- 🌈 **Beautiful UI**: Gradient styling, hover effects, and modern design
- ⚡ **Optimized Performance**: Direct writes to destination (no temporary files), smart handling for different file sizes

## Setup Instructions

### 1. Google Cloud Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

3. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details
   - Click "Create and Continue"
   - Grant appropriate roles (e.g., "Viewer" for read-only access)
   - Click "Done"

4. **Generate Service Account Key**:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Save the downloaded JSON file securely

5. **Share Google Drive Folder** (if using service account):
   - Open Google Drive
   - Right-click on the folder you want to access
   - Click "Share"
   - Add the service account email (found in the JSON file)
   - Grant appropriate permissions

### 2. Databricks Setup

1. **Create Secret Scope**:
   ```bash
   # Using Databricks CLI
   databricks secrets create-scope --scope google_drive_secrets
   ```
   
   Or use the Databricks UI:
   - Go to `https://<databricks-instance>#secrets/createScope`
   - Enter scope name: `google_drive_secrets`
   - Click "Create"

2. **Store Google Drive Credentials**:
   ```bash
   # Using Databricks CLI
   databricks secrets put --scope google_drive_secrets --key google_drive_credentials --string-value "$(cat path/to/your/credentials.json)"
   ```
   
   Or manually:
   - Copy the entire contents of your service account JSON file
   - Store it as a secret in the scope created above

3. **Import the Notebook**:
   - Open your Databricks workspace
   - Click "Workspace" in the sidebar
   - Navigate to your desired location
   - Click "Import"
   - Select "File" and upload `google_drive_ingest.py`

4. **Create a Cluster** (if needed):
   - Ensure you have a running cluster with:
     - Python 3.8 or higher
     - Sufficient memory for file processing

## Usage

### Step 1: Configure Widgets

Once the notebook is imported and attached to a cluster, run the first few cells to create the widgets. Configure the following:

1. **Secret Scope Name**: Enter your secret scope name (e.g., `google_drive_secrets`)
2. **Credentials Key**: Enter the key name for your credentials (e.g., `google_drive_credentials`)
3. **Google Drive Folder ID** (Optional): 
   - Leave empty to list files from root
   - To get a folder ID:
     - Open the folder in Google Drive
     - Copy the ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. **File IDs to Ingest**: Leave empty for now (will be populated via visual interface)
5. **Storage Type**: Choose `volume` for Unity Catalog Volumes or `dbfs` for DBFS
6. **Output Path**: 
   - For Volumes: `/Volumes/catalog/schema/volume/google_drive`
   - For DBFS: `/mnt/ingest/google_drive`
7. **Action**: Select `list_files`

### Step 2: Browse Files with Visual Interface

1. Set the "Action" widget to `list_files`
2. Run the notebook cells
3. You'll see a beautiful interactive table with:
   - ✅ **Checkboxes** for each file
   - 📁 **File type icons** (folders, documents, spreadsheets, etc.)
   - 📝 **File names** and metadata
   - 📊 **File sizes** in MB
   - 📅 **Last modified dates**
   - 🆔 **File IDs** (for reference)

### Step 3: Select Files Interactively

1. **Click checkboxes** next to the files you want to ingest
   - Use the checkbox in the header to select/deselect all files
   - The selected count updates automatically
2. **Click the "Copy Selected File IDs" button**
   - File IDs are automatically copied to your clipboard
   - You'll see a confirmation message
3. **Paste** the copied IDs into the "File IDs to Ingest" widget

### Step 4: Ingest Files

1. Change the "Action" widget to `ingest_files`
2. Run the notebook cells
3. Monitor the progress:
   - Real-time download progress for each file
   - Visual summary card showing success/failure counts
   - Detailed table of all ingested files
4. Files are automatically saved to your chosen destination (Volume or DBFS)

### Step 5: Access Ingested Data

After ingestion, your files will be available in the specified location. The notebook automatically displays a visual list of all ingested files.

#### From Unity Catalog Volume:
```python
# List files in volume
dbutils.fs.ls("/Volumes/catalog/schema/volume/google_drive")

# Read CSV from volume
df = spark.read.csv("/Volumes/catalog/schema/volume/google_drive/your_file.csv", 
                    header=True, inferSchema=True)
display(df)

# Create Delta table from volume
df.write.format("delta").mode("overwrite").saveAsTable("catalog.schema.table_name")
```

#### From DBFS:
```python
# List files in DBFS
dbutils.fs.ls("/mnt/ingest/google_drive")

# Read CSV from DBFS
df = spark.read.csv("/mnt/ingest/google_drive/your_file.csv", header=True, inferSchema=True)
display(df)
```

## File Type Support

The notebook automatically handles different file types:

| Google Drive Type | Exported As | Extension |
|------------------|-------------|-----------|
| Google Docs | Word Document | .docx |
| Google Sheets | CSV | .csv |
| Google Slides | PowerPoint | .pptx |
| Regular Files | Original Format | Original |

## Security Best Practices

1. **Never hardcode credentials** in the notebook
2. **Use Databricks secrets** for all sensitive information
3. **Limit service account permissions** to only what's necessary
4. **Regularly rotate** service account keys
5. **Use folder-level permissions** in Google Drive to restrict access
6. **Audit access logs** regularly

## Troubleshooting

### Authentication Errors

**Issue**: "Authentication failed" error
- **Solution**: Verify that:
  - Secret scope name is correct
  - Credentials key exists in the scope
  - Service account JSON is valid
  - Google Drive API is enabled

### Permission Errors

**Issue**: "Insufficient permissions" or "Access denied"
- **Solution**: 
  - Ensure the service account email has been granted access to the folder/files
  - Check that the service account has the correct IAM roles
  - Verify the folder ID is correct

### File Download Errors

**Issue**: Files fail to download
- **Solution**:
  - Check file IDs are correct
  - Ensure sufficient disk space in DBFS
  - Verify network connectivity
  - Check file size limits

### Widget Not Showing

**Issue**: Widgets don't appear
- **Solution**:
  - Ensure you're running the notebook in Databricks (not locally)
  - Restart the Python interpreter
  - Check that the notebook is attached to a running cluster

## Advanced Usage

### Filtering Files by Type

You can modify the listing query to filter by file type:

```python
# In the list_drive_contents function, modify the query:
query = f"'{folder_id}' in parents and trashed=false and mimeType='text/csv'"
```

### Batch Processing

For large-scale ingestion, consider:

```python
# Process files in batches
batch_size = 10
for i in range(0, len(file_ids), batch_size):
    batch = file_ids[i:i+batch_size]
    # Process batch
```

### Automated Scheduling

Use Databricks Jobs to schedule regular ingestion:

1. Create a Job from the notebook
2. Set up a schedule (e.g., daily, hourly)
3. Configure alerts for failures

## Dependencies

See `requirements.txt` for the complete list of dependencies:

- `google-auth` - Google authentication library
- `google-api-python-client` - Google Drive API client
- `pydrive2` - Additional Google Drive utilities
- `pandas` - Data manipulation

## Unity Catalog Volumes vs DBFS

### Unity Catalog Volumes (Recommended)
- ✅ **Better governance**: Full Unity Catalog integration
- ✅ **Fine-grained access control**: User/group level permissions
- ✅ **Better organization**: Catalog → Schema → Volume hierarchy
- ✅ **Audit logging**: Complete lineage and access tracking
- ✅ **Future-proof**: Databricks' recommended storage approach

**Path format**: `/Volumes/catalog/schema/volume_name/folder`

### DBFS (Legacy)
- ⚠️ **Simpler setup**: No Unity Catalog setup required
- ⚠️ **Less governance**: Basic file system permissions
- ⚠️ **Legacy approach**: May be deprecated in future

**Path format**: `/mnt/folder` or `/dbfs/path`

## Architecture

```
┌─────────────────────────────────┐
│       Google Drive              │
│                                 │
│  📁 Folders & Files             │
│  - Documents (→ .docx)          │
│  - Spreadsheets (→ .csv)        │
│  - Presentations (→ .pptx)      │
│  - Regular files                │
└────────────┬────────────────────┘
             │ Google Drive API
             │ (Service Account Auth)
             │
┌────────────▼─────────────────────────────────┐
│      Databricks Notebook                     │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  🎨 Visual Widget Interface            │ │
│  │  - Interactive file browser            │ │
│  │  - Checkbox selection                  │ │
│  │  - One-click copy file IDs             │ │
│  │  - Storage type selection              │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  🔧 Ingestion Engine                   │ │
│  │  - Google Drive authentication         │ │
│  │  - File listing & metadata             │ │
│  │  - Download & transfer                 │ │
│  │  - Progress tracking                   │ │
│  └────────────────────────────────────────┘ │
└──────────────┬───────────────────────────────┘
               │
               ├──────────────────┬─────────────────
               │                  │
    ┌──────────▼──────────┐  ┌───▼──────────────┐
    │  Unity Catalog      │  │      DBFS        │
    │    Volumes          │  │   (Legacy)       │
    │                     │  │                  │
    │ /Volumes/catalog/   │  │  /mnt/path       │
    │   schema/volume/    │  │  /dbfs/path      │
    │                     │  │                  │
    │ 🔒 Governed         │  │ 📁 Simple        │
    │ 📊 Delta Tables     │  │ 📄 Files         │
    └─────────────────────┘  └──────────────────┘
```

## Performance Optimization

The notebook uses an optimized ingestion approach:

### Direct Write Strategy
Instead of the traditional two-step process:
```
❌ Old: Google Drive → Local Temp → DBFS/Volume
✅ New: Google Drive → DBFS/Volume (direct)
```

### Smart File Handling
- **Small files (≤100MB)**: Downloaded to memory buffer, written directly
- **Large files (>100MB)**: Streamed with chunked downloads for memory efficiency
- **No temporary directory**: Eliminates intermediate storage and I/O overhead

### Benefits
- ⚡ **Faster ingestion**: Eliminates redundant copy operations
- 💾 **Lower disk usage**: No temporary file accumulation
- 🚀 **Better scalability**: More efficient for large file sets
- 🔄 **Cleaner process**: Automatic cleanup, no leftover temp files

## Contributing

Feel free to enhance this notebook with additional features:
- Incremental ingestion (skip already ingested files)
- File filtering by date/size
- Parallel downloads using ThreadPoolExecutor
- Data validation
- Automatic format detection and parsing
- Retry logic for failed downloads

## License

This project is provided as-is for use in Databricks environments.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Databricks documentation
3. Check Google Drive API documentation
4. Review error messages in the notebook output

