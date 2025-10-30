# Google Drive Utils Module

This document explains the `google_drive_utils.py` module and how to use it.

## Overview

The `google_drive_utils.py` module contains all the core functions for interacting with Google Drive. This modular approach provides:

- ✅ **Reusability**: Functions can be used in notebooks, scripts, or other projects
- ✅ **Maintainability**: Single source of truth for all Google Drive operations
- ✅ **Testability**: Functions can be unit tested independently
- ✅ **Clean Notebooks**: Notebooks focus on workflow, not implementation details

## Module Functions

### Authentication

#### `get_google_drive_service(dbutils, secret_scope, credentials_key)`
Authenticates with Google Drive and returns a service object.

**Parameters:**
- `dbutils`: Databricks utilities object
- `secret_scope` (str): Name of the Databricks secret scope
- `credentials_key` (str): Key name for Google Drive credentials

**Returns:**
- Google Drive service object

**Example:**
```python
from google_drive_utils import get_google_drive_service

service = get_google_drive_service(dbutils, "google_drive_secrets", "google_drive_credentials")
```

### File Listing

#### `list_drive_contents(service, folder_id=None, max_results=100)`
Lists files and folders from Google Drive.

**Parameters:**
- `service`: Google Drive service object
- `folder_id` (str, optional): Folder ID to list from (None for root)
- `max_results` (int): Maximum number of results (default: 100)

**Returns:**
- pandas DataFrame with columns:
  - `id`: File ID
  - `name`: File name
  - `mimeType`: MIME type
  - `size`: Size in bytes
  - `size_mb`: Size in MB
  - `type`: Human-readable type with emoji
  - `createdTime`: Creation timestamp
  - `modifiedTime`: Last modified timestamp
  - `parents`: Parent folder IDs

**Example:**
```python
from google_drive_utils import list_drive_contents

files_df = list_drive_contents(service, folder_id="abc123")
print(f"Found {len(files_df)} files")
```

### File Download

#### `download_file_to_destination(service, file_id, file_name, dest_path, max_size_for_put=100)`
Downloads a file directly from Google Drive to DBFS/Volume.

**Parameters:**
- `service`: Google Drive service object
- `file_id` (str): Google Drive file ID
- `file_name` (str): Name of the file
- `dest_path` (str): Destination path (e.g., `/Volumes/catalog/schema/volume` or `/mnt/data`)
- `max_size_for_put` (int, optional): Size threshold in MB for in-memory buffering (default: 100)

**Returns:**
- str: Final destination path

**Example:**
```python
from google_drive_utils import download_file_to_destination

dest = download_file_to_destination(
    service,
    file_id="xyz789",
    file_name="report.csv",
    dest_path="/Volumes/main/default/data",
    max_size_for_put=100
)
print(f"Downloaded to: {dest}")
```

### Helper Functions

#### `format_file_size(size_bytes)`
Formats file size in human-readable format.

**Example:**
```python
from google_drive_utils import format_file_size

print(format_file_size(1024))        # "1.00 KB"
print(format_file_size(1048576))     # "1.00 MB"
print(format_file_size(1073741824))  # "1.00 GB"
```

#### `get_file_export_format(mime_type)`
Returns export format for Google Workspace files.

**Example:**
```python
from google_drive_utils import get_file_export_format

export_mime, ext = get_file_export_format('application/vnd.google-apps.spreadsheet')
# Returns: ('text/csv', '.csv')
```

#### `validate_destination_path(dbutils, dest_path)`
Validates that a destination path exists and is writable.

**Example:**
```python
from google_drive_utils import validate_destination_path

if validate_destination_path(dbutils, "/Volumes/main/default/data"):
    print("Path is valid and writable")
```

## Installation in Databricks

### Option 1: Upload to Workspace
1. Upload `google_drive_utils.py` to your Databricks workspace
2. Import in notebooks:
```python
import sys
sys.path.append('/Workspace/Users/your.email@domain.com/path/to/module')

from google_drive_utils import get_google_drive_service, list_drive_contents
```

### Option 2: Upload to DBFS
1. Upload to DBFS:
```bash
databricks fs cp google_drive_utils.py dbfs:/FileStore/modules/google_drive_utils.py
```

2. Import in notebooks:
```python
import sys
sys.path.append('/dbfs/FileStore/modules')

from google_drive_utils import get_google_drive_service, list_drive_contents
```

### Option 3: Upload to Volume (Recommended)
1. Upload to Unity Catalog Volume:
```python
# In Databricks notebook
dbutils.fs.cp(
    "file:///path/to/google_drive_utils.py",
    "/Volumes/main/default/modules/google_drive_utils.py"
)
```

2. Import in notebooks:
```python
import sys
sys.path.append('/Volumes/main/default/modules')

from google_drive_utils import get_google_drive_service, list_drive_contents
```

### Option 4: Package as Python Package
For production use, create a proper Python package:

```
google_drive_databricks/
├── setup.py
├── google_drive_databricks/
│   ├── __init__.py
│   └── utils.py
```

Install with:
```bash
pip install -e .
```

## Complete Usage Example

```python
# Import functions
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
files_df = list_drive_contents(service, folder_id=None)
print(f"Found {len(files_df)} files")
display(files_df)

# 3. Download specific files
dest_path = "/Volumes/main/default/google_drive"

for idx, row in files_df.head(5).iterrows():
    file_id = row['id']
    file_name = row['name']
    
    try:
        final_path = download_file_to_destination(
            service,
            file_id,
            file_name,
            dest_path
        )
        print(f"✓ Downloaded: {final_path}")
    except Exception as e:
        print(f"✗ Failed to download {file_name}: {e}")
```

## Error Handling

All functions include proper error handling and will raise exceptions with descriptive messages:

```python
try:
    service = get_google_drive_service(dbutils, "wrong_scope", "wrong_key")
except Exception as e:
    print(f"Authentication failed: {e}")
    # Handle error appropriately

try:
    files_df = list_drive_contents(service, folder_id="invalid_id")
except Exception as e:
    print(f"Failed to list files: {e}")
    # Handle error appropriately
```

## Performance Considerations

### File Size Threshold
The `max_size_for_put` parameter controls memory buffering:

- **Small files (≤ threshold)**: Downloaded to memory, written once
- **Large files (> threshold)**: Streamed directly to destination

**Recommendations:**
- Default (100MB): Good for most clusters
- 50MB: For memory-constrained environments
- 200MB: For large driver nodes with plenty of RAM

### Path Conversion
The module automatically converts paths for DBFS access:
- `/mnt/path` → `/dbfs/mnt/path`
- `/Volumes/...` → Used directly (already mounted)

## Testing

To test the module:

```python
# Test authentication
try:
    service = get_google_drive_service(dbutils, "google_drive_secrets", "google_drive_credentials")
    print("✓ Authentication successful")
except Exception as e:
    print(f"✗ Authentication failed: {e}")

# Test file listing
try:
    files_df = list_drive_contents(service)
    print(f"✓ Listed {len(files_df)} files")
except Exception as e:
    print(f"✗ Listing failed: {e}")

# Test download
try:
    test_file_id = "your_test_file_id"
    dest = download_file_to_destination(
        service,
        test_file_id,
        "test.txt",
        "/Volumes/main/default/test"
    )
    print(f"✓ Downloaded to: {dest}")
except Exception as e:
    print(f"✗ Download failed: {e}")
```

## Best Practices

1. **Import only what you need**:
```python
from google_drive_utils import get_google_drive_service, download_file_to_destination
```

2. **Reuse the service object**:
```python
# Don't create multiple services
service = get_google_drive_service(dbutils, scope, key)
# Reuse for all operations
```

3. **Handle errors gracefully**:
```python
try:
    download_file_to_destination(...)
except Exception as e:
    logging.error(f"Download failed: {e}")
    # Continue with next file or handle appropriately
```

4. **Use type hints** (if modifying the module):
```python
from typing import Optional
def my_function(param: str) -> Optional[str]:
    pass
```

## Contributing

To add new functions to the module:

1. Follow the existing pattern
2. Add comprehensive docstrings
3. Include error handling
4. Update this README with examples
5. Test thoroughly in Databricks environment

## License

Same as the main project - provided as-is for Databricks use.

