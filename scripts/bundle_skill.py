import zipfile
import os
import argparse
from pathlib import Path

def create_zip(version: str):
    source_dir = "../agent-skills/loanlens-finance"
    out_dir = Path("archives")
    out_dir.mkdir(exist_ok=True)
    
    zip_filename = out_dir / f"loanlens-finance-{version}.zip"
    
    if not os.path.exists(source_dir):
        print(f"Error: Source directory {source_dir} does not exist.")
        return

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in ('venv', '__pycache__', '.pytest_cache')]
            
            for file in files:
                file_path = os.path.join(root, file)
                # Keep the folder structure inside the zip
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)
                
    print(f"✅ Successfully bundled skill artifact: {zip_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bundle the loanlens-finance skill into a versioned zip artifact.")
    parser.add_argument("--version", "-v", required=True, help="Version string for the artifact (e.g., 'v2', 'v3.1')")
    args = parser.parse_args()
    
    create_zip(args.version)
