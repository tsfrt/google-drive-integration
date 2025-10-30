# Google Drive File Browser & Download 📁⬇️

**Simple, beautiful interface for downloading files from Google Drive to Databricks.**

Perfect for non-technical users who need to browse and download files from Google Drive into Unity Catalog Volumes or DBFS.

## ✨ Features

### Download from Google Drive
- 🎨 **Beautiful File Browser**: Interactive table with checkboxes and gradient styling
- 👥 **Non-Technical Friendly**: Anyone can use it - no coding required
- ⚡ **Simple Workflow**: Browse → Select → Copy → Paste → Download
- 📊 **Multiple File Types**: Supports Google Workspace files (Docs, Sheets, Slides) and regular files
- 📈 **Progress Tracking**: Real-time download progress with visual summaries

### Upload to Google Drive
- 📤 **Export Delta Tables**: Upload any Delta table to Google Drive as CSV or Parquet
- 🎯 **Row Limiting**: Export full tables or just a subset of rows
- 🔗 **Direct Links**: Get Google Drive links to uploaded files
- 💾 **Two Formats**: Export as CSV (for sharing) or Parquet (for data professionals)

### Technical Features
- 🔐 **Secure**: Uses Databricks secrets for Google Drive credentials
- 💾 **Flexible Storage**: Save to Unity Catalog Volumes or DBFS (auto-detected)
- 🌈 **Modern UI**: Gradient styling, hover effects, clean design
- ⚡ **Zero-Temp-File Architecture**: Direct writes to destination (no `/tmp` usage)
- 🔧 **Modular Design**: All Python functions in `google_drive_utils.py` module for developers

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

### Step 1: Configure Settings (One Time Setup)

1. **Import the notebook** into your Databricks workspace
2. **Attach to a cluster** (any size works)
3. **Configure the 4 simple widgets**:
   - **Secret Scope**: Your Databricks secret scope name (e.g., `google_drive_secrets`)
   - **Credentials Key**: Key for your Google Drive credentials (e.g., `google_drive_credentials`)
   - **Folder ID** (Optional): Leave empty for root, or paste a specific folder ID
   - **Output Path**: Where to save files (e.g., `/Volumes/main/default/google_drive`)

### Step 2: Browse Your Files

1. **Run all cells** (⌘/Ctrl + Shift + Enter in Databricks)
2. **See your files** in the beautiful interactive browser
3. **Select files** using the checkboxes
   - Check individual files or use "Select All"
   - See the count update in real-time

### Step 3: Download Files

1. **Click "Copy Selected File IDs"** button
2. **Scroll down** to the "Download Files" cell
3. **Paste the IDs** into the `FILE_IDS_TO_DOWNLOAD` variable
4. **Run the cell** - that's it!

### Visual Workflow

```
┌─────────────────────────────┐
│  ⚙️ Configure Settings      │
│  - Secret Scope             │
│  - Output Path              │
└──────────┬──────────────────┘
           │
           ▼ Run All Cells
┌─────────────────────────────┐
│  📂 Beautiful File Browser  │
│  ☑ sales_report.csv         │
│  ☑ data.xlsx                │
│  ☐ meeting_notes.pdf        │
│                             │
│  [Copy Selected File IDs]   │
└──────────┬──────────────────┘
           │
           ▼ Paste IDs
┌─────────────────────────────┐
│  ⬇️ Download Files Cell     │
│  FILE_IDS = "id1, id2"      │
└──────────┬──────────────────┘
           │
           ▼ Run Cell
┌─────────────────────────────┐
│  ✅ Download Complete!      │
│  ✓ sales_report.csv         │
│  ✓ data.xlsx                │
│                             │
│  💾 Saved to: /Volumes/...  │
└─────────────────────────────┘
```

### Step 4: Use Your Downloaded Files

The last cell in the notebook shows all downloaded files. You can then:

```python
# Read a CSV file
df = spark.read.csv("/Volumes/main/default/google_drive/sales_report.csv", 
                    header=True, inferSchema=True)
display(df)

# Create a Delta table
df.write.format("delta").mode("overwrite").saveAsTable("main.default.sales_report")

# Or access from DBFS
df = spark.read.csv("dbfs:/mnt/data/report.csv", header=True, inferSchema=True)
```

### Step 5: Export Delta Tables to Google Drive (Optional)

Upload processed data back to Google Drive:

```python
# In the "Export Delta Table" cell:
TABLE_NAME = "main.default.sales_data"
OUTPUT_FILE_NAME = "monthly_sales_report"
EXPORT_FORMAT = "csv"  # or "parquet"
MAX_ROWS = 10000  # Optional: limit rows

# Run the cell - that's it!
```

**Use cases:**
- Share analysis results with non-Databricks users
- Distribute reports via Google Drive
- Backup important tables
- Export data for external tools

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
✅ New: Google Drive → DBFS/Volume (direct stream!)
```

### Zero-Temp-File Architecture
The notebook writes directly to DBFS/Volumes using filesystem mount points:
- **DBFS paths**: `/mnt/path` → `/dbfs/mnt/path` (direct write)
- **Volume paths**: `/Volumes/catalog/schema/volume` (direct write)
- **No `/tmp` usage**: Files never touch temporary storage

### Smart File Handling
- **Small files (≤100MB)**: Downloaded to memory buffer, written directly to destination
- **Large files (>100MB)**: Streamed directly to destination with chunked downloads
- **Zero temporary files**: All writes go directly to final destination

### Benefits
- ⚡ **Faster ingestion**: Eliminates ALL intermediate storage
- 💾 **Zero disk overhead**: No temporary files created
- 🚀 **Better scalability**: More efficient for large file sets
- 🔄 **Cleaner process**: No cleanup needed, no leftover files
- 🎯 **Simpler logic**: Direct writes with standard Python file operations

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

