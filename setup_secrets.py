"""
Setup script for configuring Databricks secrets for Google Drive integration.

This script helps you set up the necessary secrets in Databricks for the
Google Drive ingestion notebook.

Usage:
    python setup_secrets.py --scope-name <scope_name> --credentials-file <path_to_json>

Requirements:
    - Databricks CLI installed and configured
    - Google Drive service account JSON credentials file
"""

import argparse
import json
import subprocess
import sys
import os


def check_databricks_cli():
    """Check if Databricks CLI is installed and configured."""
    try:
        result = subprocess.run(
            ["databricks", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Databricks CLI found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Databricks CLI not found or not configured")
        print("\nPlease install and configure Databricks CLI:")
        print("  1. Install: pip install databricks-cli")
        print("  2. Configure: databricks configure --token")
        return False


def validate_credentials_file(filepath):
    """Validate that the credentials file exists and is valid JSON."""
    if not os.path.exists(filepath):
        print(f"✗ Credentials file not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r') as f:
            credentials = json.load(f)
        
        # Check for required fields in service account JSON
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in credentials]
        
        if missing_fields:
            print(f"✗ Credentials file missing required fields: {', '.join(missing_fields)}")
            return False
        
        if credentials.get('type') != 'service_account':
            print("⚠️  Warning: Credentials type is not 'service_account'")
        
        print(f"✓ Valid credentials file for: {credentials.get('client_email')}")
        return True
        
    except json.JSONDecodeError:
        print("✗ Credentials file is not valid JSON")
        return False


def create_secret_scope(scope_name):
    """Create a Databricks secret scope."""
    print(f"\nCreating secret scope: {scope_name}")
    
    try:
        # Check if scope already exists
        result = subprocess.run(
            ["databricks", "secrets", "list-scopes"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if scope_name in result.stdout:
            print(f"⚠️  Secret scope '{scope_name}' already exists")
            response = input("Do you want to continue and update the credentials? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Aborted.")
                return False
        else:
            # Create the scope
            subprocess.run(
                ["databricks", "secrets", "create-scope", "--scope", scope_name],
                check=True
            )
            print(f"✓ Created secret scope: {scope_name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error creating secret scope: {e}")
        return False


def store_credentials(scope_name, key_name, credentials_file):
    """Store Google Drive credentials in Databricks secrets."""
    print(f"\nStoring credentials in secret scope...")
    
    try:
        # Read credentials file
        with open(credentials_file, 'r') as f:
            credentials_json = f.read()
        
        # Store in Databricks secrets
        # Using stdin to pass the JSON securely
        process = subprocess.Popen(
            ["databricks", "secrets", "put", "--scope", scope_name, "--key", key_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=credentials_json)
        
        if process.returncode == 0:
            print(f"✓ Credentials stored successfully")
            print(f"  Scope: {scope_name}")
            print(f"  Key: {key_name}")
            return True
        else:
            print(f"✗ Error storing credentials: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_secret(scope_name, key_name):
    """Verify that the secret was stored successfully."""
    print(f"\nVerifying secret...")
    
    try:
        result = subprocess.run(
            ["databricks", "secrets", "list", "--scope", scope_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        if key_name in result.stdout:
            print(f"✓ Secret verified: {key_name}")
            return True
        else:
            print(f"✗ Secret not found: {key_name}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Error verifying secret: {e}")
        return False


def print_next_steps(scope_name, key_name):
    """Print instructions for next steps."""
    print("\n" + "="*80)
    print("✓ SETUP COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Import the notebook 'google_drive_ingest.py' into your Databricks workspace")
    print("2. Attach the notebook to a cluster")
    print("3. Configure the notebook widgets with:")
    print(f"   - Secret Scope Name: {scope_name}")
    print(f"   - Credentials Key: {key_name}")
    print("4. Share your Google Drive folder with the service account email")
    print("5. Run the notebook to list and ingest files")
    print("\nFor detailed instructions, see README.md")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Setup Databricks secrets for Google Drive integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_secrets.py --scope-name google_drive_secrets --credentials-file credentials.json
  python setup_secrets.py -s my_secrets -c /path/to/service-account.json -k drive_creds
        """
    )
    
    parser.add_argument(
        "--scope-name", "-s",
        required=True,
        help="Name of the Databricks secret scope to create"
    )
    
    parser.add_argument(
        "--credentials-file", "-c",
        required=True,
        help="Path to the Google Drive service account JSON credentials file"
    )
    
    parser.add_argument(
        "--key-name", "-k",
        default="google_drive_credentials",
        help="Key name for storing the credentials (default: google_drive_credentials)"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("Google Drive + Databricks Setup")
    print("="*80)
    
    # Step 1: Check Databricks CLI
    if not check_databricks_cli():
        sys.exit(1)
    
    # Step 2: Validate credentials file
    if not validate_credentials_file(args.credentials_file):
        sys.exit(1)
    
    # Step 3: Create secret scope
    if not create_secret_scope(args.scope_name):
        sys.exit(1)
    
    # Step 4: Store credentials
    if not store_credentials(args.scope_name, args.key_name, args.credentials_file):
        sys.exit(1)
    
    # Step 5: Verify secret
    if not verify_secret(args.scope_name, args.key_name):
        sys.exit(1)
    
    # Step 6: Print next steps
    print_next_steps(args.scope_name, args.key_name)


if __name__ == "__main__":
    main()

