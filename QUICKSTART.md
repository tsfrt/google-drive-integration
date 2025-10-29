# Quick Start Guide 🚀

Get started with Google Drive to Databricks ingestion in 5 minutes!

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

## First Ingestion (Interactive)

### Step 1: Configure
Set widget values:
- **Secret Scope**: `google_drive_secrets`
- **Credentials Key**: `google_drive_credentials`
- **Storage Type**: `volume`
- **Output Path**: `/Volumes/main/default/google_drive_ingest`
- **Action**: `list_files`

### Step 2: Browse & Select
1. Run the notebook
2. See the visual file browser
3. Check boxes next to files you want
4. Click "Copy Selected File IDs"

### Step 3: Ingest
1. Paste file IDs into widget
2. Change Action to `ingest_files`
3. Run notebook
4. Watch the magic happen! ✨

### Step 4: Use Your Data
```python
# Read ingested CSV
df = spark.read.csv("/Volumes/main/default/google_drive_ingest/data.csv", 
                    header=True, inferSchema=True)
display(df)

# Create Delta table
df.write.format("delta").mode("overwrite").saveAsTable("main.default.my_table")
```

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

## Support

- 🐛 Found a bug? Open an issue
- 💡 Have a suggestion? Submit a PR
- ❓ Need help? Check the troubleshooting section in README.md

Happy ingesting! 🎉

