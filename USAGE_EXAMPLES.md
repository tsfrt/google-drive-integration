# Usage Examples

This document provides practical examples of using the Google Drive ingestion notebook and module.

## Table of Contents

1. [Quick Download Workflow](#quick-download-workflow)
2. [Widget-Based Workflow](#widget-based-workflow)
3. [Using the Python Module](#using-the-python-module)
4. [Advanced Scenarios](#advanced-scenarios)

---

## Quick Download Workflow

The fastest way to download files from Google Drive.

### Step-by-Step

1. **Run the notebook** until you see the file browser
2. **Select files** using checkboxes
3. **Click "Copy Selected File IDs"**
4. **Navigate to the "Quick Download Helper" cell**
5. **Paste the file IDs** into the `quick_download_ids` variable:

```python
quick_download_ids = "1abc123, 2def456, 3ghi789"
```

6. **Run the cell** - Files download immediately!

### Visual Example

```
┌──────────────────────────────────────┐
│  📊 Visual File Browser              │
│  ☑ sales_q1.csv                     │
│  ☑ sales_q2.csv                     │
│  ☐ report.pdf                       │
│                                      │
│  [Copy Selected File IDs]            │
└──────────────────────────────────────┘
                │
                ▼ Copy IDs
┌──────────────────────────────────────┐
│  Quick Download Helper Cell          │
│  quick_download_ids = "1abc, 2def"   │
└──────────────────────────────────────┘
                │
                ▼ Run cell
┌──────────────────────────────────────┐
│  ✓ Downloaded 2 files                │
│  - sales_q1.csv → /Volumes/.../      │
│  - sales_q2.csv → /Volumes/.../      │
└──────────────────────────────────────┘
```

### Advantages

- ⚡ **Fastest method**: No widget configuration needed
- 🎯 **Direct**: Copy → Paste → Run
- 📊 **Clear output**: See exactly what was downloaded

---

## Widget-Based Workflow

Traditional workflow using notebook widgets.

### Step-by-Step

1. **Configure widgets** at the top of the notebook:
   - Secret Scope: `google_drive_secrets`
   - Credentials Key: `google_drive_credentials`
   - Storage Type: `volume` or `dbfs`
   - Output Path: `/Volumes/catalog/schema/volume`
   - Action: `list_files`

2. **Run cells** to see the file browser

3. **Select files** and click "Copy Selected File IDs"

4. **Paste into the "File IDs to Ingest" widget**

5. **Change Action widget** to `ingest_files`

6. **Run all cells** to download

### When to Use

- ✅ Production workflows with consistent configuration
- ✅ Scheduled jobs (widgets can be parameterized)
- ✅ When you need full audit trail
- ✅ Batch processing with many files

---

## Using the Python Module

For custom notebooks or scripts, use the `google_drive_utils` module directly.

### Basic Example

```python
from google_drive_utils import (
    get_google_drive_service,
    list_drive_contents,
    download_file_to_destination
)

# 1. Authenticate
service = get_google_drive_service(
    dbutils,
    secret_scope="google_drive_secrets",
    credentials_key="google_drive_credentials"
)

# 2. List files
files_df = list_drive_contents(service)
print(f"Found {len(files_df)} files")

# 3. Download first 5 files
for idx, row in files_df.head(5).iterrows():
    download_file_to_destination(
        service,
        row['id'],
        row['name'],
        "/Volumes/main/default/data"
    )
```

### Download Specific File Types

```python
# Filter for CSV files only
csv_files = files_df[files_df['mimeType'] == 'text/csv']

for idx, row in csv_files.iterrows():
    print(f"Downloading: {row['name']}")
    download_file_to_destination(
        service,
        row['id'],
        row['name'],
        "/Volumes/main/default/csv_data"
    )
```

### Download Files Modified After Date

```python
import pandas as pd

# Convert modifiedTime to datetime
files_df['modifiedTime'] = pd.to_datetime(files_df['modifiedTime'])

# Filter files modified in last 7 days
cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=7)
recent_files = files_df[files_df['modifiedTime'] > cutoff_date]

print(f"Found {len(recent_files)} recent files")

for idx, row in recent_files.iterrows():
    download_file_to_destination(
        service,
        row['id'],
        row['name'],
        "/Volumes/main/default/recent"
    )
```

### Download Large Files

```python
# For very large files, adjust the buffer size
large_files = files_df[files_df['size_mb'] > 500]

for idx, row in large_files.iterrows():
    print(f"Downloading large file: {row['name']} ({row['size_mb']:.2f} MB)")
    download_file_to_destination(
        service,
        row['id'],
        row['name'],
        "/Volumes/main/default/large_files",
        max_size_for_put=50  # Lower threshold for very large files
    )
```

---

## Advanced Scenarios

### Scenario 1: Incremental Ingestion

Download only files that haven't been ingested yet.

```python
# Load previously ingested files
try:
    ingested_df = spark.table("main.default.ingested_files")
    ingested_ids = set(ingested_df.select("file_id").rdd.flatMap(lambda x: x).collect())
except:
    ingested_ids = set()

# List all files
files_df = list_drive_contents(service)

# Filter out already ingested files
new_files = files_df[~files_df['id'].isin(ingested_ids)]

print(f"New files to ingest: {len(new_files)}")

# Download new files
for idx, row in new_files.iterrows():
    try:
        dest = download_file_to_destination(
            service,
            row['id'],
            row['name'],
            "/Volumes/main/default/data"
        )
        
        # Track ingested file
        spark.sql(f"""
            INSERT INTO main.default.ingested_files
            VALUES ('{row['id']}', '{row['name']}', current_timestamp())
        """)
        
        print(f"✓ Ingested: {row['name']}")
    except Exception as e:
        print(f"✗ Failed: {row['name']} - {e}")
```

### Scenario 2: Download to Different Volumes by File Type

```python
# Define destinations by file type
destinations = {
    'text/csv': '/Volumes/main/default/csv_data',
    'application/pdf': '/Volumes/main/default/documents',
    'application/vnd.google-apps.spreadsheet': '/Volumes/main/default/spreadsheets',
    'image/jpeg': '/Volumes/main/default/images',
    'image/png': '/Volumes/main/default/images'
}

files_df = list_drive_contents(service)

for idx, row in files_df.iterrows():
    mime_type = row['mimeType']
    dest_path = destinations.get(mime_type, '/Volumes/main/default/other')
    
    print(f"Downloading {row['name']} to {dest_path}")
    
    try:
        download_file_to_destination(
            service,
            row['id'],
            row['name'],
            dest_path
        )
    except Exception as e:
        print(f"Failed: {e}")
```

### Scenario 3: Parallel Downloads

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_single_file(file_info):
    """Download a single file and return result."""
    try:
        dest = download_file_to_destination(
            service,
            file_info['id'],
            file_info['name'],
            "/Volumes/main/default/data"
        )
        return {'status': 'success', 'name': file_info['name'], 'path': dest}
    except Exception as e:
        return {'status': 'failed', 'name': file_info['name'], 'error': str(e)}

# List files
files_df = list_drive_contents(service)

# Convert to list of dicts
files_to_download = files_df.to_dict('records')

# Download in parallel (max 5 concurrent)
results = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(download_single_file, file_info) for file_info in files_to_download]
    
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        print(f"{result['status']}: {result['name']}")

# Summary
successful = [r for r in results if r['status'] == 'success']
failed = [r for r in results if r['status'] == 'failed']

print(f"\n✓ Downloaded: {len(successful)}")
print(f"✗ Failed: {len(failed)}")
```

### Scenario 4: Download and Create Delta Tables

```python
# Download CSV files and convert to Delta tables
csv_files = files_df[files_df['mimeType'] == 'text/csv']

for idx, row in csv_files.iterrows():
    file_name = row['name']
    table_name = file_name.replace('.csv', '').replace('-', '_').lower()
    
    # Download file
    dest_path = download_file_to_destination(
        service,
        row['id'],
        file_name,
        "/Volumes/main/default/staging"
    )
    
    # Read CSV and create Delta table
    df = spark.read.csv(dest_path, header=True, inferSchema=True)
    df.write.format("delta").mode("overwrite").saveAsTable(f"main.default.{table_name}")
    
    print(f"✓ Created table: main.default.{table_name}")
```

### Scenario 5: Error Handling with Retry Logic

```python
import time

def download_with_retry(service, file_id, file_name, dest_path, max_retries=3):
    """Download with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return download_file_to_destination(service, file_id, file_name, dest_path)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise

# Use with retry
files_df = list_drive_contents(service)

for idx, row in files_df.iterrows():
    try:
        dest = download_with_retry(
            service,
            row['id'],
            row['name'],
            "/Volumes/main/default/data"
        )
        print(f"✓ {row['name']}")
    except Exception as e:
        print(f"✗ {row['name']}: {e}")
```

---

## Tips & Best Practices

### Performance Tips

1. **Batch Processing**: Download files in small batches (10-20 at a time)
2. **Filter Early**: Use Google Drive API queries to filter files server-side
3. **Parallel Downloads**: Use ThreadPoolExecutor for large file sets
4. **Adjust Buffer Size**: Lower `max_size_for_put` for memory-constrained environments

### Error Handling

1. **Always use try-except** for individual file downloads
2. **Log failures** to a table or file for later retry
3. **Implement retry logic** for transient failures
4. **Validate paths** before downloading

### Organization

1. **Use separate volumes** for different file types
2. **Implement naming conventions** for downloaded files
3. **Track ingestion history** in a Delta table
4. **Clean up old files** periodically

### Security

1. **Never hardcode credentials** - always use Databricks secrets
2. **Use service accounts** with minimal required permissions
3. **Regularly rotate** service account keys
4. **Audit access logs** in Google Cloud Console

---

## Troubleshooting Common Issues

### Issue: Module not found

```python
# Solution: Add module path
import sys
sys.path.append('/Volumes/main/default/modules')
from google_drive_utils import get_google_drive_service
```

### Issue: Permission denied on volume

```python
# Solution: Verify volume exists and you have access
dbutils.fs.ls("/Volumes/main/default/")  # Should list volumes

# Create if needed (requires appropriate permissions)
spark.sql("CREATE VOLUME IF NOT EXISTS main.default.google_drive")
```

### Issue: Large files cause memory errors

```python
# Solution: Lower the buffer threshold
download_file_to_destination(
    service,
    file_id,
    file_name,
    dest_path,
    max_size_for_put=50  # Lower from default 100MB
)
```

---

## Next Steps

- 📖 Read [MODULE_README.md](MODULE_README.md) for detailed module documentation
- 🚀 See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup guide
- ⚡ Check [PERFORMANCE.md](PERFORMANCE.md) for optimization tips
- 🎨 View [VISUAL_FEATURES.md](VISUAL_FEATURES.md) for UI details

Happy ingesting! 🎉

