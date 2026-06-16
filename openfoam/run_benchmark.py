import json
import subprocess
import zipfile
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent
zip_path = root_dir.parent / "rotating-cylinders.zip"
template_zip_path = root_dir / "output_template.zip"
snakefile_path = root_dir / "Snakefile"

# Extraction
if zip_path.exists():
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(root_dir)
    print(f"Successfully extracted benchmark to: {root_dir}")
else:
    print(f"Error: Could not find {zip_path} at {root_dir.parent}")
    exit(1)

# Validate template zip exists
if not template_zip_path.exists():
    print(f"Error: Could not find output_template.zip at {template_zip_path}")
    exit(1)

# Iterate through all parameter files
for param_file in root_dir.glob("parameters_*.json"):
    with open(param_file, "r") as f:
        data = json.load(f)
        config_name = data.get("configuration")

        if not config_name:
            print(f"Skipping {param_file.name}: No configuration name found.")
            continue

        # Create output directory for the configuration
        output_dir = root_dir / "results" / config_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy the selected parameter file to the output directory with a standardised name
        with open(output_dir / "parameters.json", "w") as outfile:
            json.dump(data, outfile, indent=2)

        # Extract OpenFOAM template files from output_template.zip into the output directory
        with zipfile.ZipFile(template_zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print(f"Extracted output_template.zip to: {output_dir}")

        # Run the Snakemake workflow for the configuration
        try:
            subprocess.run([
                "snakemake",
                "-s", str(snakefile_path),
                "--use-singularity",
                "--cores", "all",
                "--resources", "serial_run=1",
                "--force"
            ], check=True, cwd=output_dir)
            print(f"Workflow executed successfully for {config_name}.")
        except subprocess.CalledProcessError as e:
            print(f"Workflow failed for {config_name} with return code {e.returncode}.")

        # Zip all output files except solution_metrics.json, then remove the originals
        output_zip_path = output_dir / f"{config_name}_files.zip"
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in output_dir.rglob("*"):
                if item.is_file() and item.name not in {"solution_metrics.json", "parameters.json"} and item != output_zip_path:
                    zf.write(item, item.relative_to(output_dir))
                    item.unlink()
        
        # Remove any empty subdirectories left after zipping
        for item in sorted(output_dir.rglob("*"), reverse=True):
            if item.is_dir():
                try:
                    item.rmdir()
                except OSError:
                    pass
        print(f"Outputs zipped to: {output_zip_path.name}")

print("\nAll configurations processed.")

# --- CLEANUP SECTION ---
print("\nStarting cleanup...")

for param_file in root_dir.glob("parameters_*.json"):
    try:
        os.remove(param_file)
        print(f"Deleted: {param_file.name}")
    except Exception as e:
        print(f"Error deleting {param_file.name}: {e}")

print("Cleanup complete.")
