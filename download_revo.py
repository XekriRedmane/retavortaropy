"""
CLI tool to download or update the revo-fonto dictionary repository.
Saves the path to ~/.retavortaropy/config.json so other tools can find it.
"""

import argparse
import pathlib
import subprocess
import sys

from config import save_config, load_config


REPO_URL = "https://github.com/revuloj/revo-fonto.git"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download or update the revo-fonto Esperanto dictionary repository."
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default="./revo-fonto",
        help="Directory to clone into (default: ./revo-fonto)",
    )
    args = parser.parse_args()

    dest = pathlib.Path(args.destination).resolve()

    if dest.exists() and (dest / ".git").exists():
        # Already cloned — update with git pull
        print(f"Repository already exists at {dest}, updating...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(dest),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error running git pull: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(result.stdout.strip())
    else:
        # Clone the repository
        print(f"Cloning revo-fonto to {dest}...")
        result = subprocess.run(
            ["git", "clone", REPO_URL, str(dest)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error running git clone: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print("Clone complete.")

    # Save the revo subdirectory path and genfiles path to config
    revo_path = dest / "revo"
    genfiles_path = dest.parent / "genfiles"
    config = load_config()
    config["revo_fonto_path"] = str(revo_path)
    config["genfiles_path"] = str(genfiles_path)
    save_config(config)

    print(f"Saved revo path: {revo_path}")
    print(f"Saved genfiles path: {genfiles_path}")
    print("Other tools will now use these paths automatically.")


if __name__ == "__main__":
    main()
