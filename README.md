# Google Drive to Databricks Ingestion

This project provides a Databricks notebook interface for ingesting data from Google Drive into Databricks File System (DBFS) with a user-friendly widget-based interface.

## Features

- 🔐 **Secure Authentication**: Uses Databricks secrets for Google Drive credentials
- 📁 **File Browser**: Lists files and folders from Google Drive
- ✅ **Selective Ingestion**: Choose specific files to ingest
- 📊 **Multiple File Types**: Supports Google Workspace files (Docs, Sheets, Slides) and regular files
- 📈 **Progress Tracking**: Real-time download and ingestion progress
- 🎯 **Widget Interface**: Easy-to-use parameter widgets for configuration

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
4. **Output DBFS Path**: Specify where to store ingested files (e.g., `/mnt/ingest/google_drive`)
5. **Action**: Select `list_files`

### Step 2: List Files

1. Set the "Action" widget to `list_files`
2. Run the notebook cells
3. Review the displayed table of files with:
   - File type icons
   - File names
   - File IDs
   - File sizes
   - Modification dates

### Step 3: Select and Ingest Files

1. Copy the File IDs of the files you want to ingest from the displayed table
2. Paste them into the "File IDs to Ingest" widget (comma-separated)
   - Example: `1abc123def456, 2xyz789ghi012, 3pqr345stu678`
3. Change the "Action" widget to `ingest_files`
4. Run the notebook cells
5. Monitor the progress as files are downloaded and copied to DBFS

### Step 4: Access Ingested Data

After ingestion, your files will be available in the specified DBFS path. You can:

```python
# List ingested files
dbutils.fs.ls("/mnt/ingest/google_drive")

# Read CSV files
df = spark.read.csv("/mnt/ingest/google_drive/your_file.csv", header=True, inferSchema=True)
display(df)

# Read other file types as needed
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

## Architecture

```
┌─────────────────┐
│  Google Drive   │
│                 │
│  ┌──────────┐  │
│  │  Files   │  │
│  └────┬─────┘  │
└───────┼────────┘
        │
        │ Google Drive API
        │
┌───────▼────────────────────────────────┐
│        Databricks Notebook             │
│  ┌──────────────────────────────────┐ │
│  │  Widget Interface                │ │
│  │  - Secret Configuration          │ │
│  │  - File Selection                │ │
│  └──────────────────────────────────┘ │
│  ┌──────────────────────────────────┐ │
│  │  Ingestion Engine                │ │
│  │  - Authentication                │ │
│  │  - File Listing                  │ │
│  │  - Download & Transfer           │ │
│  └──────────────────────────────────┘ │
└────────────┬───────────────────────────┘
             │
             │
      ┌──────▼──────┐
      │    DBFS     │
      │             │
      │ Ingested    │
      │   Files     │
      └─────────────┘
```

## Contributing

Feel free to enhance this notebook with additional features:
- Incremental ingestion (skip already ingested files)
- File filtering by date/size
- Parallel downloads
- Data validation
- Automatic format detection and parsing

## License

This project is provided as-is for use in Databricks environments.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Databricks documentation
3. Check Google Drive API documentation
4. Review error messages in the notebook output

