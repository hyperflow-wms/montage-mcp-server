#!/usr/bin/env python3
"""
Download remote files listed in a Pegasus replica catalog (rc.txt).

This script parses an rc.txt file and downloads all non-local files
(i.e., files with pool != "local"). It automatically handles .gz
decompression for FITS files.

Usage:
    python3 download-rc-files.py <rc.txt> [output_dir]

Arguments:
    rc.txt      - Path to the replica catalog file
    output_dir  - Optional output directory (default: current directory)

Example:
    python3 download-rc-files.py ~/workflows/M17/rc.txt ~/workflows/M17/data
"""

import sys
import os
import re
import urllib.request
import urllib.error
import gzip
import shutil
from pathlib import Path


def parse_rc_line(line):
    """
    Parse a line from rc.txt in Pegasus replica catalog format.

    Format: filename "url"  pool="pool_label"

    Returns:
        tuple: (filename, url, pool) or None if line is invalid
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # Match: filename "url" pool="label"
    match = re.match(r'^(\S+)\s+"([^"]+)"\s+pool="([^"]+)"', line)
    if match:
        filename, url, pool = match.groups()
        return (filename, url, pool)
    return None


def download_file(url, output_path, filename):
    """
    Download a file from URL to output_path.

    Args:
        url: Source URL
        output_path: Destination file path
        filename: Display name for progress messages

    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        print(f"  Downloading: {filename}")
        print(f"  From: {url}")

        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress
        with urllib.request.urlopen(url, timeout=300) as response:
            total_size = response.headers.get('Content-Length')
            if total_size:
                total_size = int(total_size)
                print(f"  Size: {total_size / (1024*1024):.2f} MB")

            with open(output_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file, length=1024*1024)

        print(f"  ✓ Saved to: {output_path}")
        return True

    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"  ✗ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def decompress_gz(gz_path, output_path):
    """
    Decompress a .gz file.

    Args:
        gz_path: Path to .gz file
        output_path: Path for decompressed output

    Returns:
        bool: True if decompression successful
    """
    try:
        print(f"  Decompressing: {gz_path.name} -> {output_path.name}")
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove .gz file after successful decompression
        gz_path.unlink()
        print(f"  ✓ Decompressed to: {output_path}")
        return True
    except Exception as e:
        print(f"  ✗ Decompression error: {str(e)}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    rc_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()

    if not rc_file.exists():
        print(f"Error: rc.txt file not found: {rc_file}")
        sys.exit(1)

    print(f"Parsing replica catalog: {rc_file}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)

    # Parse rc.txt
    entries = []
    with open(rc_file, 'r') as f:
        for line in f:
            parsed = parse_rc_line(line)
            if parsed:
                entries.append(parsed)

    # Filter remote files (non-local)
    remote_entries = [(fname, url, pool) for fname, url, pool in entries
                     if pool != "local"]

    if not remote_entries:
        print("No remote files to download.")
        return

    print(f"\nFound {len(entries)} total entries:")
    print(f"  Local files: {len(entries) - len(remote_entries)}")
    print(f"  Remote files: {len(remote_entries)}")
    print()

    # Download remote files
    success_count = 0
    fail_count = 0

    for i, (filename, url, pool) in enumerate(remote_entries, 1):
        print(f"[{i}/{len(remote_entries)}] {filename} (pool={pool})")

        # Determine output path
        # URL might end with .gz but filename doesn't - handle both cases
        url_is_gz = url.endswith('.gz')

        if url_is_gz:
            # Download as .gz then decompress
            temp_gz = output_dir / (filename + '.gz')
            final_path = output_dir / filename

            if download_file(url, temp_gz, filename):
                if decompress_gz(temp_gz, final_path):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        else:
            # Download directly
            output_path = output_dir / filename
            if download_file(url, output_path, filename):
                success_count += 1
            else:
                fail_count += 1

        print()

    # Summary
    print("=" * 70)
    print(f"Download complete:")
    print(f"  Successful: {success_count}/{len(remote_entries)}")
    print(f"  Failed: {fail_count}/{len(remote_entries)}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
