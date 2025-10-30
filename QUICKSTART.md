# Quick Start Guide 🚀

Download files from Google Drive to Databricks in 5 minutes - **No coding required!**

## Prerequisites

- [ ] Databricks workspace with Unity Catalog enabled (for volumes)
- [ ] Google Cloud account with Drive API access
- [ ] Google Drive folder you want to ingest from

## 5-Minute Setup

### 1️⃣ Google Cloud Setup (2 minutes)

```bash
# 1. Go to Google Cloud Console (https://console.cloud.google.com)
# 2. Enable Google Drive API
# 3. Create a Service Account
# 4. Download the JSON key file
# 5. Share your Google Drive folder with the service account email
```

**Service Account Email Format**: `service-account-name@project-id.iam.gserviceaccount.com`

### 2️⃣ Databricks Secrets (1 minute)

Using Databricks CLI:
```bash
# Install CLI
pip install databricks-cli

# Configure
databricks configure --token

# Create secret scope
databricks secrets create-scope --scope google_drive_secrets

# Store credentials
databricks secrets put --scope google_drive_secrets --key google_drive_credentials --string-value "$(cat credentials.json)"
```

Or use the provided setup script:
```bash
python setup_secrets.py --scope-name google_drive_secrets --credentials-file credentials.json
```

### 3️⃣ Create Unity Catalog Volume (1 minute)

In Databricks SQL or notebook:
```sql
-- Create catalog and schema if they don't exist
CREATE CATALOG IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS main.default;

-- Create volume for ingestion
CREATE VOLUME IF NOT EXISTS main.default.google_drive_ingest;
```

### 4️⃣ Import and Run Notebook (1 minute)

1. Import `google_drive_ingest.py` to your Databricks workspace
2. Attach to a running cluster
3. Run all cells to install dependencies

## Using the Notebook (Super Simple!)

### Step 1: Configure (One Time)
Fill in the 4 widget values at the top:
- **Secret Scope**: `google_drive_secrets`
- **Credentials Key**: `google_drive_credentials`
- **Folder ID**: Leave empty (or paste a folder ID)
- **Output Path**: `/Volumes/main/default/google_drive`

### Step 2: Browse Files
1. Click **"Run All"** in Databricks
2. Wait a few seconds
3. See your Google Drive files in a beautiful table!

### Step 3: Select & Download
1. **Check the boxes** next to files you want
2. Click **"Copy Selected File IDs"**
3. **Scroll down** to the "Download Files" cell
4. **Paste** the IDs where it says `FILE_IDS_TO_DOWNLOAD = ""`
5. **Run that cell** - files download automatically! ✨

### Step 4: Use Your Data
```python
# Files are saved to your output path
# Read a CSV file
df = spark.read.csv("/Volumes/main/default/google_drive/data.csv", 
                    header=True, inferSchema=True)
display(df)

# Create a Delta table
df.write.format("delta").mode("overwrite").saveAsTable("main.default.my_table")
```

**That's it!** No complex workflows, no confusing options. Just browse, select, download.

## Visual Guide

```
┌─────────────────────────────────────────────────────┐
│  📊 Visual File Browser                             │
├─────────────────────────────────────────────────────┤
│  ☑ Select All                                       │
│                                                     │
│  ☑ 📊 Sales_Report.xlsx      12.5 MB   2024-10-15  │
│  ☐ 📄 Meeting_Notes.docx      0.8 MB   2024-10-14  │
│  ☑ 📈 Dashboard.pptx          5.2 MB   2024-10-13  │
│  ☑ 📁 Data_Archive            0 MB     2024-10-12  │
│                                                     │
│  Selected: 3 files                                  │
│  [📋 Copy Selected File IDs]                        │
└─────────────────────────────────────────────────────┘

                     ⬇️  Click Copy

┌─────────────────────────────────────────────────────┐
│  ✅ Copied to clipboard!                            │
│  Paste into "File IDs to Ingest" widget            │
└─────────────────────────────────────────────────────┘

                     ⬇️  Paste & Run

┌─────────────────────────────────────────────────────┐
│  🎉 Ingestion Complete                              │
│                                                     │
│  ✓ 3 Successfully Ingested                          │
│  ✗ 0 Failed                                         │
│  📊 3 Total Processed                               │
│                                                     │
│  Files available at:                                │
│  /Volumes/main/default/google_drive_ingest          │
└─────────────────────────────────────────────────────┘
```

## Common Issues & Solutions

### Issue: "Authentication failed"
**Solution**: Check that:
- Secret scope name is correct
- Credentials JSON is valid
- Service account has Drive API access

### Issue: "Permission denied"
**Solution**: Share the Google Drive folder with your service account email

### Issue: "Volume not found"
**Solution**: Create the volume first:
```sql
CREATE VOLUME IF NOT EXISTS main.default.google_drive_ingest;
```

### Issue: "No files found"
**Solution**: 
- Check folder ID is correct (or leave empty for root)
- Verify service account has access to the folder

## Next Steps

- 📖 Read the full [README.md](README.md) for detailed documentation
- 🔧 Customize ingestion settings
- 🔄 Set up automated scheduled ingestion
- 📊 Create Delta tables from ingested data
- 🚀 Build data pipelines

## Performance Features

### ⚡ Zero-Temp-File Architecture
The notebook uses a **true direct write** approach with **ZERO temporary files**:

```
Traditional:  Google Drive → /tmp → Copy → DBFS/Volume → Cleanup
Optimized:    Google Drive → DBFS/Volume (direct stream!)
```

**How it works:**
- **DBFS paths**: Automatically converts `/mnt/path` to `/dbfs/mnt/path` for direct write
- **Volume paths**: Uses `/Volumes/catalog/schema/volume` natively
- **No temp files**: Files never touch `/tmp` or any intermediate storage

**Benefits:**
- ✅ Faster ingestion (no intermediate steps)
- ✅ Zero disk overhead (no temp files at all)
- ✅ No cleanup needed (nothing to clean!)
- ✅ Better scalability (simpler I/O)
- ✅ Works seamlessly with volumes and DBFS

### Smart File Handling
- **Small files (≤100MB)**: Downloaded to memory buffer → written directly to destination
- **Large files (>100MB)**: Streamed directly to destination with progress tracking
- **All sizes**: Zero temporary files created

## Tips & Tricks

### Tip 1: Organize by folders
Create separate volumes for different Google Drive folders:
```sql
CREATE VOLUME main.sales.reports;
CREATE VOLUME main.marketing.documents;
```

### Tip 2: Schedule regular ingestion
Create a Databricks Job to run the notebook daily:
- Schedule: `0 0 * * *` (midnight daily)
- Cluster: Small cluster is sufficient
- Parameters: Set via widgets

### Tip 3: Filter by file type
Modify the query in `list_drive_contents()`:
```python
# Only CSV files
query = f"'{folder_id}' in parents and mimeType='text/csv' and trashed=false"

# Only Google Sheets
query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
```

### Tip 4: Incremental ingestion
Track ingested files to avoid duplicates:
```python
# Keep a table of ingested file IDs
ingested_ids = spark.table("main.default.ingested_files").select("file_id").collect()
# Skip already ingested files
```

### Tip 5: Batch processing
For very large file sets, process in batches:
```python
# In the widget, paste file IDs in groups of 20-50
# Run multiple times for different batches
```

## Support

- 🐛 Found a bug? Open an issue
- 💡 Have a suggestion? Submit a PR
- ❓ Need help? Check the troubleshooting section in README.md

Happy ingesting! 🎉

