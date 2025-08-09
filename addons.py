#!/usr/bin/env python3

import concurrent.futures
import threading
import traceback
import urllib.request
import urllib.parse
import urllib.response
import datetime
import time
from xml.etree import ElementTree as ET
import pathlib
import contextlib
import shutil
import os
import sys
import zipfile
import re
import argparse
from typing import Dict, List, Callable, Optional

# Added tqdm for progress reporting
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Warning: tqdm not found. Install with 'pip install tqdm or sudo apt install python3-tqdm' for progress bars.")
    print("Continuing without visual progress bars...")

headers = {'User-Agent': 'Mozilla/5.0 (compatible; STKAddonDownloader/0.2; +https://github.com/user/stk-addon-downloader)'}
timeout = 60

# Use current directory for Docker volume mapping
current_dir = pathlib.Path.cwd()
addons_dir = current_dir / 'stk/addons'

# Create necessary XML file paths
news_xml = addons_dir / 'online_news.xml'
addons_xml = addons_dir / 'addons.xml'
installed_xml = addons_dir / 'addons_installed.xml'
def get_part_file_path(path: pathlib.Path) -> pathlib.Path:
    """Get the .part filename for a given path during download."""
    return path.parent / f"{path.name}.part"

def make_request(url: str) -> urllib.request.Request:
    """Create a urllib request with standard headers."""
    return urllib.request.Request(url, data=None, headers=headers)

def get_addon_directory(addon_type: str) -> str:
    """Map addon type to its directory name."""
    type_mapping = {'track': 'tracks', 'kart': 'karts', 'arena': 'tracks'}
    return type_mapping[addon_type]

# Create the addons directory structure
addons_dir.mkdir(parents=True, exist_ok=True)
for dir_name in ['tracks', 'karts']:
    (addons_dir / dir_name).mkdir(exist_ok=True)

STKNS = 'https://online.supertuxkart.net/'
ET.register_namespace('', STKNS)

def _parse_http_timestamp(header_time: Optional[str]) -> int:
    """Parse HTTP timestamp to nanoseconds since epoch."""
    if not header_time:
        return int(datetime.datetime.now().replace(tzinfo=datetime.timezone.utc).timestamp()) * 10**9
    
    assert header_time.endswith('GMT') or header_time.endswith('UTC')
    dt = datetime.datetime.strptime(header_time, '%a, %d %b %Y %H:%M:%S %Z')
    return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp()) * 10**9

def _is_file_up_to_date(target: pathlib.Path, expected_time: int, expected_size: int) -> bool:
    """Check if local file matches expected timestamp and size."""
    if not target.exists():
        return False
    
    stat = target.stat()
    return expected_time == stat.st_mtime_ns and expected_size == stat.st_size

def download_with_progress(resp: urllib.response, target: pathlib.Path) -> None:
    """Download file with progress reporting."""
    header_time = resp.headers.get('Last-Modified')
    header_length = int(resp.headers.get('Content-Length', 0))
    header_timens = _parse_http_timestamp(header_time)
    
    if _is_file_up_to_date(target, header_timens, header_length):
        print(f'http: skip {resp.geturl()} (already up to date)')
        return
    
    filename = target.name
    print(f'http: download {resp.geturl()} ({format_size(header_length)})')
    
    with open(get_part_file_path(target), 'wb') as f:
        if TQDM_AVAILABLE and header_length > 0:
            _download_with_tqdm_progress(resp, f, header_length, filename)
        else:
            _download_with_basic_progress(resp, f, header_length)
    
    if header_length > 0:
        actual_length = get_part_file_path(target).stat().st_size
        assert actual_length == header_length, f"download incomplete: expected {header_length} bytes, got {actual_length} bytes"
    
    get_part_file_path(target).replace(target)
    os.utime(target, ns=(header_timens, header_timens))
    print(f"Download complete: {filename}")

def _download_with_tqdm_progress(resp, file_obj, content_length: int, filename: str) -> None:
    """Download with tqdm progress bar."""
    with tqdm(total=content_length, unit='B', unit_scale=True, 
              desc=f"Downloading {filename}", ascii=True) as pbar:
        chunk_size = 8192
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            file_obj.write(chunk)
            pbar.update(len(chunk))

def _download_with_basic_progress(resp, file_obj, content_length: int) -> None:
    """Download with basic text progress bar."""
    chunk_size = 8192
    bytes_read = 0
    progress_markers = '#' * 25
    
    if content_length > 0:
        print(f"[{' ' * 25}] 0%", end='\r', flush=True)
        
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        bytes_read += len(chunk)
        file_obj.write(chunk)
        
        if content_length > 0:
            percent = min(100, int(bytes_read * 100 / content_length))
            filled_length = int(25 * bytes_read / content_length)
            bar = f"[{progress_markers[:filled_length]}{'.' * (25-filled_length)}] {percent}%"
            print(bar, end='\r', flush=True)
    
    print(' ' * 60, end='\r')  # Clear progress line

def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name)-1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def get_addons(skip_update: bool = False) -> Dict[str, Dict]:
    if not skip_update:
        print("Fetching addon database...")
        with contextlib.closing(urllib.request.urlopen(make_request('https://online.supertuxkart.net/dl/xml/online_news.xml'), timeout=timeout)) as resp:
            download_with_progress(resp, news_xml)
        addons_url = ET.parse(news_xml).find('include').get('file')
        with contextlib.closing(urllib.request.urlopen(make_request(addons_url), timeout=timeout)) as resp:
            download_with_progress(resp, addons_xml)
    
    print("Parsing addon database...")
    addons_etree = ET.parse(addons_xml)
    addons_dict = dict()
    for item in addons_etree.iter():
        if 'id' not in item.keys():
            continue
        if not int(item.get('status', '0')) & 0x1: # not approved
            continue
        if int(addons_dict.setdefault(item.get('id'), dict()).get('revision', '-1')) <= int(item.get('revision')):
            addons_dict[item.get('id')] = {'type': item.tag, **dict(item.items())}
    
    print(f"Found {len(addons_dict)} approved addons")
    return addons_dict

def get_installed_addons() -> Dict[str, Dict]:
    if installed_xml.exists():
        print("Reading installed addons list...")
        addons_etree = ET.parse(installed_xml)
        addons_dict = {}
        all_addons_count = 0
        
        for item in addons_etree.iter():
            if 'id' not in item.keys():
                continue
            
            all_addons_count += 1
            addon_data = {'type': item.tag.removeprefix(f"{{{STKNS}}}"), **dict(item.items())}
            
            # Only count as "installed" if explicitly marked as installed
            if addon_data.get('installed', 'false') == 'true':
                addons_dict[item.get('id')] = addon_data
            # But we need to track all addons for the XML management
            else:
                addons_dict[item.get('id')] = addon_data
        
        actually_installed = sum(1 for addon in addons_dict.values() 
                               if addon.get('installed', 'false') == 'true')
        print(f"Found {actually_installed} installed addons ({all_addons_count} total in database)")
        return addons_dict
    else:
        print("No installed addons list found, creating a new one")
        return {}

def clean_unsupported_format_addons(addon_data: Dict, addons_dict: Dict) -> None:
    """Remove addons with unsupported track format (<=5)."""
    if (addon_data['installed'] != 'false' and 
        addon_data['type'] != 'kart'):
        
        format_id = int(addons_dict.get(addon_data['id'], {}).get('format', 999))
        if format_id <= 5:
            addon_id = addon_data['id']
            print(f"warn: {addon_id} has unsupported format {format_id}")
            _mark_addon_uninstalled(addon_data)
            _remove_addon_directory(addon_data)

def clean_unapproved_addons(addon_data: Dict) -> None:
    """Remove addons that are not approved."""
    status = int(addon_data.get('status', '1'))  # assume approved if no status
    if (addon_data['installed'] != 'false' and 
        not status & 0x1):  # not approved
        
        addon_id = addon_data['id']
        print(f"warn: {addon_id} has unsupported status {status}")
        _mark_addon_uninstalled(addon_data)
        _remove_addon_directory(addon_data)

def verify_addon_installation(addon_data: Dict) -> None:
    """Verify that an addon is actually installed on disk."""
    if addon_data['installed'] == 'false':
        return
        
    addon_id = addon_data['id']
    install_path = addons_dir / get_addon_directory(addon_data['type']) / addon_id
    
    if install_path.exists():
        if install_path.is_dir():
            return
        else:
            install_path.unlink()
    
    print(f"warn: {addon_id} is not installed")
    _mark_addon_uninstalled(addon_data)

def _mark_addon_uninstalled(addon_data: Dict) -> None:
    """Helper to mark an addon as uninstalled."""
    addon_data['installed'] = 'false'
    addon_data['installed-revision'] = '0'

def _remove_addon_directory(addon_data: Dict) -> None:
    """Helper to remove addon directory if it exists."""
    addon_id = addon_data['id']
    install_path = addons_dir / get_addon_directory(addon_data['type']) / addon_id
    if install_path.exists():
        shutil.rmtree(install_path)

def validate_addon_data(addon_data: Dict, addons_dict: Dict) -> None:
    """Run all addon validation checks."""
    clean_unsupported_format_addons(addon_data, addons_dict)
    clean_unapproved_addons(addon_data)
    verify_addon_installation(addon_data)

def write_installed_addons(addons_dict: Dict, installed_addons: Dict, warn: bool = False) -> None:
    """Write the installed addons XML file."""
    print("Updating installed addons list...")
    addons_to_build = []
    for addon_id in set((*addons_dict.keys(), *installed_addons.keys())):
        if addons_dict.get(addon_id) is None:
            if warn:
                print(f"warn: {addon_id} is not found in official addons")
                validate_addon_data(installed_addons[addon_id], addons_dict)
            addons_to_build.append(installed_addons[addon_id])
        else:
            addon_data = addons_dict[addon_id]
            installed = installed_addons.get(addon_id, {})
            installed_values = _build_addon_metadata(addon_data, installed)
            if warn:
                validate_addon_data(installed_values, addons_dict)
            addons_to_build.append(installed_values)
    addons_to_build.sort(key=_get_addon_sort_key)
    
    _write_addons_xml(addons_to_build)
    print(f"Updated {len(addons_to_build)} addons in the installed list")

def _build_addon_metadata(addon_data: Dict, installed: Dict) -> Dict:
    """Build addon metadata for XML output."""
    installed_values = {
        'name': addon_data['name'],
        'id': addon_data['id'],
        'designer': addon_data['designer'],
        'status': addon_data['status'],
        'date': addon_data['date'],
        'installed': 'false',
        'installed-revision': '0',
        'size': addon_data['size'],
        'icon-revision': addon_data['revision'],
        'icon-name': addon_data.get('image', '').split('/')[-1],
        'type': addon_data['type'],
    }
    installed_values.update({k: v for k, v in installed.items() 
                           if k in ('installed', 'installed-revision')})
    return installed_values

def _get_addon_sort_key(addon_data: Dict) -> str:
    """Get sort key for addon ordering in XML."""
    type_priority = {"kart": "aaa", "track": "aab", "arena": "aac"}
    return type_priority[addon_data['type']] + addon_data['id']

def _write_addons_xml(addons_to_build: List[Dict]) -> None:
    """Write the addons XML file with proper escaping."""
    builder = ET.TreeBuilder()
    builder.start('addons', {'xmlns': STKNS})
    
    # Apply XML attribute escaping for STK compatibility
    original_escape = ET._escape_attrib
    ET._escape_attrib = _escape_stk_attributes
    
    try:
        for data in addons_to_build:
            builder.start(data['type'], {k: v for k, v in data.items() if k != 'type'})
            builder.end(data['type'])
        builder.end('addons')
        
        tree = ET.ElementTree(element=builder.close())
        ET.indent(tree)
        tree.write(installed_xml, xml_declaration=True, encoding='utf-8')
    finally:
        # Restore original escaping function
        ET._escape_attrib = original_escape

def _escape_stk_attributes(val: str) -> str:
    """Custom XML attribute escaping for STK compatibility."""
    safe_chars = set("!'()+,-./0123456789;ABCDEFGHIJKLMNOPQRSTUVWXYZ[]_abcdefghijklmnopqrstuvwxyz|")
    return "".join(ch if ch in safe_chars else f'&#x{ord(ch):X};' for ch in val)

def _filter_default(addon_data: Dict) -> bool:
    """Default filter: tracks, arenas, and featured karts.
    
    For karts, only includes those marked as 'featured' by STK servers.
    Featured karts have the 0x80 (128) bit set in their status field,
    indicating they are high-quality or officially recommended karts.
    All tracks and arenas are included regardless of featured status.
    """
    return addon_data.get('type') != 'kart' or bool(int(addon_data.get('status', '0')) & 0x80)

def _filter_all(addon_data: Dict) -> bool:
    """Accept all addons."""
    return True

def _filter_tracks_only(addon_data: Dict) -> bool:
    """Only tracks and arenas (no karts)."""
    return addon_data.get('type') != 'kart'

def _filter_high_rated(addon_data: Dict) -> bool:
    """Only highly rated addons (>= 2.8 stars)."""
    return float(addon_data.get('rating', 0)) >= 2.8

def _filter_recent(addon_data: Dict) -> bool:
    """Only recently updated addons (within last year)."""
    one_year_seconds = 86400 * 365
    return time.time() - int(addon_data.get('date', 0)) < one_year_seconds

def get_filter_function(filter_type: str) -> Callable[[Dict], bool]:
    """Get filter function based on filter type."""
    filters = {
        'default': _filter_default,
        'all': _filter_all,
        'tracks-only': _filter_tracks_only,
        'high-rated': _filter_high_rated,
        'recent': _filter_recent
    }
    
    return filters.get(filter_type, _filter_default)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='SuperTuxKart Addon Downloader (Docker Edition)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Filter options:
  default     - Tracks, arenas, and featured karts (default)
  all         - All available addons
  tracks-only - Only tracks and arenas
  high-rated  - Addons with rating >= 2.8 stars
  recent      - Addons updated within last year
        '''
    )
    
    parser.add_argument(
        '--filter', '-f',
        choices=['default', 'all', 'tracks-only', 'high-rated', 'recent'],
        default='default',
        help='Filter type for addon selection'
    )
    
    parser.add_argument(
        '--non-interactive', '-n',
        action='store_true',
        help='Run without interactive prompts (auto-confirm installation)'
    )
    
    parser.add_argument(
        '--skip-update',
        action='store_true',
        help='Skip updating addon database (use cached version)'
    )
    
    parser.add_argument(
        '--list-only', '-l',
        action='store_true',
        help='List addons that would be installed without downloading'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Show detailed filtering information and debug output'
    )
    
    return parser.parse_args()

lock = threading.Lock()
def download_and_extract_addons(addon_data: Dict) -> str:
    addon_id = addon_data['id']
    addon_name = addon_data['name']
    addon_type = addon_data['type']
    addon_size = format_size(int(addon_data['size']))
    
    print(f"\n[{addon_type}] {addon_name} ({addon_id}) - {addon_size}")
    
    tmpdir = addons_dir / 'tmp'
    tmpdir.mkdir(parents=True, exist_ok=True)
    download_name = addon_data.get('file').split('/')[-1]
    assert download_name.endswith('.zip')
    
    try:
        with contextlib.closing(urllib.request.urlopen(make_request(addon_data.get('file')), timeout=timeout)) as resp:
            download_with_progress(resp, tmpdir / download_name)
        
        extractdir = addons_dir / get_addon_directory(addon_data.get('type')) / addon_data['id']
        if extractdir.exists() and extractdir.is_dir():
            print(f"Removing old version of {addon_id}...")
            shutil.rmtree(extractdir)
        
        extractdir.mkdir(parents=True, exist_ok=True)
        print(f"Extracting {addon_id} to {str(extractdir)}...")
        
        with zipfile.ZipFile(tmpdir / download_name, 'r') as zip:
            # Get total number of files for progress reporting
            file_count = len(zip.infolist())
            
            if TQDM_AVAILABLE and file_count > 5:
                with tqdm(total=file_count, desc=f"Extracting {addon_id}", unit="files", ascii=True) as pbar:
                    for i, file in enumerate(zip.infolist()):
                        zip.extract(file, extractdir)
                        pbar.update(1)
            else:
                zip.extractall(extractdir)
                print(f"Extracted {file_count} files")
        
        with lock:
            installed_addons.setdefault(addon_data['id'], dict())['installed'] = 'true'
            installed_addons[addon_data['id']]['installed-revision'] = addon_data['revision']
            write_installed_addons(addons_dict, installed_addons)
        
        (tmpdir / download_name).unlink()
        print(f"✓ Successfully installed {addon_name} ({addon_id})")
        return "success"
    
    except Exception as e:
        print(f"✗ Failed to install {addon_name} ({addon_id}): {str(e)}")
        return "error"

def install_addons(all_addons, installed_addons, install_filter=lambda _: True, non_interactive=False, list_only=False, debug=False) -> None:
    addons_to_install = list()
    
    print("\nFinding addons to install or update...")
    if debug:
        print("Debugging filter decisions:\n")
    
    for addon_id, addon_data in all_addons.items():
        installed = installed_addons.get(addon_id)
        addon_type = addon_data.get('type', 'unknown')
        
        # Check if addon needs installation/update
        needs_install = (not installed or 
                        installed.get('installed') != 'true' or 
                        int(installed.get('installed-revision', '0')) < int(addon_data.get('revision', '0')))
        
        if not needs_install:
            if debug:
                status = "up to date" if installed and installed.get('installed') == 'true' else "not needed"
                print(f"  SKIP {addon_type} {addon_id}: {status}")
            continue
        
        # Check if addon is approved
        if not int(addon_data.get('status', '0')) & 0x1:
            if debug:
                print(f"  SKIP {addon_type} {addon_id}: not approved (status={addon_data.get('status', '0')})")
            continue
        
        # Check format compatibility for tracks
        if addon_data.get('type') != 'kart' and int(addon_data.get('format', '0')) <= 5:
            if debug:
                print(f"  SKIP {addon_type} {addon_id}: unsupported format {addon_data.get('format', '0')} (need >5)")
            continue
        
        # Apply user filter
        if not install_filter(addon_data):
            if debug:
                if addon_data.get('type') == 'kart':
                    status = int(addon_data.get('status', '0'))
                    featured = bool(status & 0x80)
                    print(f"  SKIP {addon_type} {addon_id}: not featured (status={status}, featured={featured})")
                else:
                    print(f"  SKIP {addon_type} {addon_id}: filtered out by user filter")
            continue
        
        if debug:
            print(f"  INCLUDE {addon_type} {addon_id}: rev.{addon_data.get('revision', '0')}")
        addons_to_install.append(addon_data)
    
    if debug:
        print(f"\nFilter summary:")
        print(f"- Total addons in database: {len(all_addons)}")
        print(f"- Addons selected for installation: {len(addons_to_install)}")
        
    if not addons_to_install:
        print("All addons are up to date! Nothing to install.")
        return
        
    # Group addons by type for better reporting
    addons_by_type = {}
    for addon in addons_to_install:
        addon_type = addon.get('type')
        if addon_type not in addons_by_type:
            addons_by_type[addon_type] = []
        addons_by_type[addon_type].append(addon)
    
    print("\nAddons to install:")
    for addon_type, addons in addons_by_type.items():
        print(f"- {addon_type.capitalize()}s: {len(addons)}")
        for addon in addons[:5]:  # Show just the first 5 addons of each type
            print(f"  * {addon['name']} (rev. {addon['revision']})")
        if len(addons) > 5:
            print(f"  * ... and {len(addons) - 5} more {addon_type}s")
    
    total_size = sum(int(addon.get('size', 0)) for addon in addons_to_install)
    print(f"\nTotal download size: {format_size(total_size)}")
    
    if list_only:
        print("\n--list-only specified, not downloading.")
        sys.stdout.flush()  # Ensure output appears before any background progress bars
        return
    
    # Interactive confirmation unless non-interactive mode
    if not non_interactive:
        if input("\nProceed with installation? [Y/n]: ").lower() in ('n', 'no'):
            print("Installation cancelled.")
            return
    else:
        print("\nNon-interactive mode: proceeding with installation...")
    
    print(f"\nInstalling {len(addons_to_install)} addons using {min(5, len(addons_to_install))} worker threads...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_addon = {executor.submit(download_and_extract_addons, i): i for i in addons_to_install}
        status = {"total": len(addons_to_install), "completed": 0, "error": 0}
        
        # Create a progress bar for overall installation
        if TQDM_AVAILABLE:
            overall_progress = tqdm(total=len(addons_to_install), desc="Overall progress", unit="addons", ascii=True)
        
        for future in concurrent.futures.as_completed(future_to_addon):
            addon_data = future_to_addon[future]
            try:
                result = future.result()
                if result == "success":
                    status["completed"] += 1
                else:
                    status["error"] += 1
            except Exception as e:
                print(f"Error processing addon: {e}")
                if '--debug' in sys.argv:
                    traceback.print_exc()
                status["error"] += 1
            
            if TQDM_AVAILABLE:
                overall_progress.update(1)
                overall_progress.set_postfix(completed=status["completed"], error=status["error"])
            else:
                print(f"\nProgress: {status['completed'] + status['error']}/{status['total']} "
                      f"(✓ {status['completed']} | ✗ {status['error']})")
        
        if TQDM_AVAILABLE:
            overall_progress.close()
    
    print("\n" + "="*50)
    print(f"Installation Summary:")
    print(f"- Total addons: {status['total']}")
    print(f"- Successfully installed: {status['completed']}")
    print(f"- Failed: {status['error']}")
    print("="*50)

def verify_docker_setup() -> None:
    """Verify the directory structure is correct for Docker volume mapping"""
    try:
        # Check if we're in the correct directory structure for Docker
        docker_compose_path = current_dir / 'docker-compose.yml'
        if not docker_compose_path.exists() and not (current_dir / 'compose.yaml').exists():
            print("Note: No docker-compose.yml/compose.yaml found in current directory.")
            print("Make sure this script is run from the same directory as your Docker Compose file.")
        
        # Verify the addons directory structure
        expected_dir = current_dir / 'stk/addons'
        if expected_dir != addons_dir:
            print(f"Warning: Expected addons directory at {expected_dir}, but using {addons_dir}")
        
        # Create directories if they don't exist
        for type_dir in ['tracks', 'karts']:
            addon_type_dir = addons_dir / type_dir
            addon_type_dir.mkdir(parents=True, exist_ok=True)
            print(f"Verified directory: {addon_type_dir}")
        
        print("Docker setup verification complete.")
        print("Remember to restart your STK Docker container after adding new addons.")
        
    except Exception as e:
        print(f"Error verifying Docker setup: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    args = parse_arguments()
    
    print("="*50)
    print("SuperTuxKart Addon Downloader (Docker Edition)")
    print("="*50)
    print(f"Addons directory: {addons_dir}")
    print(f"Filter: {args.filter}")
    print(f"Mode: {'Non-interactive' if args.non_interactive else 'Interactive'}")
    
    try:
        # Verify Docker setup
        verify_docker_setup()
        
        print("\nReading installed addons...")
        installed_addons = get_installed_addons()
        
        print(f"\nFetching addon database{'(cached)' if args.skip_update else ''}...")
        addons_dict = get_addons(skip_update=args.skip_update)
        
        # Count addons by type
        addon_counts = {"track": 0, "kart": 0, "arena": 0}
        for addon_id, addon_data in addons_dict.items():
            addon_type = addon_data.get('type')
            if addon_type in addon_counts:
                addon_counts[addon_type] += 1
        
        print("\nAvailable addons:")
        for addon_type, count in addon_counts.items():
            print(f"- {addon_type.capitalize()}s: {count}")
        
        # Get filter function
        install_filter = get_filter_function(args.filter)
        
        filter_descriptions = {
            'default': 'Tracks, arenas, and featured karts (high-quality karts recommended by STK)',
            'all': 'All available addons',
            'tracks-only': 'Only tracks and arenas (no karts)',
            'high-rated': 'Highly rated addons (≥ 2.8 stars)',
            'recent': 'Recently updated addons (within last year)'
        }
        
        print(f"\nSelected filter: {filter_descriptions[args.filter]}")
        
        try:
            install_addons(
                addons_dict, 
                installed_addons, 
                install_filter=install_filter,
                non_interactive=args.non_interactive,
                list_only=args.list_only,
                debug=args.debug
            )
                            
        finally:
            if not args.list_only:
                print("\nFinalizing installation...")
                write_installed_addons(addons_dict, installed_addons, warn=True)
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        if '--debug' in sys.argv:
            traceback.print_exc()
    
    if not args.list_only:
        print("\nDone! Remember to restart your STK Docker container to apply the changes.")