"""
Google Drive Utilities for Databricks Integration

This module provides utility functions for authenticating with Google Drive,
listing files, and downloading files directly to DBFS/Unity Catalog Volumes.

Usage:
    from google_drive_utils import (
        get_google_drive_service,
        list_drive_contents,
        download_file_to_destination
    )
"""

import json
import io
import os
from typing import Optional, Tuple
import pandas as pd


def get_google_drive_service(dbutils, secret_scope: str, credentials_key: str):
    """
    Authenticate and return Google Drive service object.
    
    Args:
        dbutils: Databricks utilities object
        secret_scope: Databricks secret scope name
        credentials_key: Key name for credentials in the secret scope
    
    Returns:
        Google Drive service object
        
    Raises:
        Exception: If authentication fails
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
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


def list_drive_contents(service, folder_id: Optional[str] = None, max_results: int = 100) -> pd.DataFrame:
    """
    List files and folders in Google Drive.
    
    Args:
        service: Google Drive service object
        folder_id: Folder ID to list contents from (None for root)
        max_results: Maximum number of results to return
    
    Returns:
        DataFrame with file information including:
        - id: File ID
        - name: File name
        - mimeType: MIME type
        - size: File size in bytes
        - size_mb: File size in MB
        - type: Human-readable type with emoji
        - createdTime: Creation timestamp
        - modifiedTime: Last modified timestamp
        - parents: Parent folder IDs
        
    Raises:
        Exception: If listing files fails
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
            df['size_mb'] = df['size'].apply(
                lambda x: round(int(x) / (1024 * 1024), 2) if pd.notna(x) and x else 0
            )
        else:
            df['size_mb'] = 0
        
        # Add file type indicator with emoji
        df['type'] = df['mimeType'].apply(_get_file_type_icon)
        
        return df
        
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        raise


def _get_file_type_icon(mime_type: str) -> str:
    """
    Get emoji icon for file type based on MIME type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        String with emoji and type description
    """
    if mime_type == 'application/vnd.google-apps.folder':
        return '📁 Folder'
    elif 'document' in mime_type.lower():
        return '📄 Document'
    elif 'spreadsheet' in mime_type.lower():
        return '📊 Spreadsheet'
    elif 'presentation' in mime_type.lower():
        return '📈 Presentation'
    elif 'image' in mime_type.lower():
        return '🖼️ Image'
    elif 'video' in mime_type.lower():
        return '🎥 Video'
    elif 'audio' in mime_type.lower():
        return '🎵 Audio'
    elif 'pdf' in mime_type.lower():
        return '📕 PDF'
    else:
        return '📄 File'


def download_file_to_destination(
    service,
    file_id: str,
    file_name: str,
    dest_path: str,
    max_size_for_put: int = 100
) -> str:
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
        
    Raises:
        Exception: If download fails
    """
    try:
        from googleapiclient.http import MediaIoBaseDownload
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='mimeType,name,size').execute()
        mime_type = file_metadata.get('mimeType')
        file_size = int(file_metadata.get('size', 0)) if file_metadata.get('size') else 0
        file_size_mb = file_size / (1024 * 1024)
        
        # Handle Google Workspace files (need to be exported)
        export_formats = {
            'application/vnd.google-apps.document': (
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.docx'
            ),
            'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
            'application/vnd.google-apps.presentation': (
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.pptx'
            ),
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
        fs_path = _convert_to_filesystem_path(final_dest_path)
        
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


def _convert_to_filesystem_path(dbfs_path: str) -> str:
    """
    Convert DBFS/Volume path to filesystem path.
    
    Args:
        dbfs_path: Path in DBFS or Volume notation
        
    Returns:
        Filesystem path that can be used with open()
    """
    # Volume paths are already accessible
    if dbfs_path.startswith('/Volumes/'):
        return dbfs_path
    # Already has /dbfs prefix
    elif dbfs_path.startswith('/dbfs/'):
        return dbfs_path
    # DBFS path without prefix - add it
    else:
        return f"/dbfs{dbfs_path}"


def get_file_export_format(mime_type: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get the export format and extension for a given MIME type.
    
    Args:
        mime_type: MIME type of the file
        
    Returns:
        Tuple of (export_mime_type, extension) or (None, None) for non-exportable files
    """
    export_formats = {
        'application/vnd.google-apps.document': (
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.docx'
        ),
        'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
        'application/vnd.google-apps.presentation': (
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.pptx'
        ),
    }
    return export_formats.get(mime_type, (None, None))


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., "1.23 MB", "456 KB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def validate_destination_path(dbutils, dest_path: str) -> bool:
    """
    Validate that the destination path exists and is writable.
    
    Args:
        dbutils: Databricks utilities object
        dest_path: Destination path to validate
        
    Returns:
        True if path is valid and writable, False otherwise
    """
    try:
        # Try to create the directory
        dbutils.fs.mkdirs(dest_path)
        
        # Try a test write
        test_file = f"{dest_path}/.test_write"
        dbutils.fs.put(test_file, "test", True)
        dbutils.fs.rm(test_file)
        
        return True
    except Exception as e:
        print(f"Path validation failed: {e}")
        return False

