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
partfile = lambda p: p.parent / f"{p.name}.part"
mkreq = lambda u: urllib.request.Request(u, data=None, headers=headers)
type_to_dir = lambda x: {'track': 'tracks', 'kart': 'karts', 'arena': 'tracks'}[x]

# Create the addons directory structure
addons_dir.mkdir(parents=True, exist_ok=True)
for dir_name in ['tracks', 'karts']:
    (addons_dir / dir_name).mkdir(exist_ok=True)

STKNS = 'https://online.supertuxkart.net/'
ET.register_namespace('', STKNS)

# Enhanced download function with progress reporting
def download_with_progress(resp: urllib.response, target: pathlib.Path) -> None:
    header_time = resp.headers.get('Last-Modified')
    header_length = int(resp.headers.get('Content-Length', 0))
    assert not header_time or header_time.endswith('GMT') or header_time.endswith('UTC')
    header_timens = int((datetime.datetime.strptime(header_time, '%a, %d %b %Y %H:%M:%S %Z') if header_time else datetime.datetime.now()).replace(tzinfo=datetime.timezone.utc).timestamp()) * 10**9
    
    if target.exists() and (stat := target.stat()) and header_timens == stat.st_mtime_ns and header_length == stat.st_size:
        print(f'http: skip {resp.geturl()} (already up to date)')
        return
    
    filename = target.name
    print(f'http: download {resp.geturl()} ({format_size(header_length)})')
    
    with open(partfile(target), 'wb') as f:
        if TQDM_AVAILABLE and header_length > 0:
            # Create progress bar
            with tqdm(total=header_length, unit='B', unit_scale=True, 
                      desc=f"Downloading {filename}", ascii=True) as pbar:
                chunk_size = 8192
                bytes_read = 0
                
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    f.write(chunk)
                    pbar.update(len(chunk))
        else:
            # Basic progress without tqdm
            chunk_size = 8192
            bytes_read = 0
            progress_markers = ('#' * 25).ljust(25)
            
            if header_length > 0:
                print(f"[{' ' * 25}] 0%", end='\r', flush=True)
                
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                f.write(chunk)
                
                if header_length > 0:
                    percent = min(100, int(bytes_read * 100 / header_length))
                    filled_length = int(25 * bytes_read / header_length)
                    bar = f"[{progress_markers[:filled_length]}{'.' * (25-filled_length)}] {percent}%"
                    print(bar, end='\r', flush=True)
            
            print(' ' * 60, end='\r')  # Clear progress line
    
    if header_length > 0:
        actual_length = partfile(target).stat().st_size
        assert actual_length == header_length, f"download incomplete: expected {header_length} bytes, got {actual_length} bytes"
    
    partfile(target).replace(target)
    os.utime(target, ns=(header_timens, header_timens))
    print(f"Download complete: {filename}")

def format_size(size_bytes):
    """Format bytes to human-readable size"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name)-1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def get_addons(skip_update=False) -> dict:
    if not skip_update:
        print("Fetching addon database...")
        with contextlib.closing(urllib.request.urlopen(mkreq('https://online.supertuxkart.net/dl/xml/online_news.xml'), timeout=timeout)) as resp:
            download_with_progress(resp, news_xml)
        addons_url = ET.parse(news_xml).find('include').get('file')
        with contextlib.closing(urllib.request.urlopen(mkreq(addons_url), timeout=timeout)) as resp:
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

def get_installed_addons() -> dict:
    if installed_xml.exists():
        print("Reading installed addons list...")
        addons_etree = ET.parse(installed_xml)
        addons_dict = dict()
        for item in addons_etree.iter():
            if 'id' not in item.keys():
                continue
            addons_dict[item.get('id')] = {'type': item.tag.removeprefix(f"{{{STKNS}}}"), **dict(item.items())}
        print(f"Found {len(addons_dict)} installed addons")
        return addons_dict
    else:
        print("No installed addons list found, creating a new one")
        return dict()

def write_installed_addons(addons_dict: dict, installed_addons: dict, warn=False) -> None:
    def format_5_track_cleaner(addon_data: dict) -> None:
        if addon_data['installed'] != 'false' and \
                addon_data['type'] != 'kart' and \
                (format_id := int(addons_dict.get(addon_data['id'], dict()).get('format', 9**9))) <= 5:
            addon_id = addon_data['id']
            print(f"warn: {addon_id=} has an unsupported {format_id=}")
            addon_data['installed'] = 'false'
            addon_data['installed-revision'] = '0'
            if (install_path := (addons_dir / type_to_dir(addon_data['type']) / addon_id)).exists():
                shutil.rmtree(install_path)
                
    def bad_status_track_cleaner(addon_data: dict) -> None:
        status = int(addon_data.get('status', '1')) # assume approved if no status
        if addon_data['installed'] != 'false' and \
                not status & 0x1: # not approved
            addon_id = addon_data['id']
            print(f"warn: {addon_id=} has unsupported {status=}")
            addon_data['installed'] = 'false'
            addon_data['installed-revision'] = '0'
            if (install_path := (addons_dir / type_to_dir(addon_data['type']) / addon_id)).exists():
                shutil.rmtree(install_path)
                
    def addon_is_really_installed(addon_data: dict) -> None:
        format_5_track_cleaner(addon_data)
        bad_status_track_cleaner(addon_data)
        if addon_data['installed'] == 'false':
            return
        addon_id = addon_data['id']
        if (install_path := (addons_dir / type_to_dir(addon_data['type']) / addon_id)).exists():
            if install_path.is_dir():
                return
            else:
                install_path.unlink()
        print(f"warn: {addon_id=} is not installed")
        addon_data['installed'] = 'false'
        addon_data['installed-revision'] = '0'
    
    print("Updating installed addons list...")
    addons_to_build = list()
    for addon_id in set((*addons_dict.keys(), *installed_addons.keys())):
        if addons_dict.get(addon_id) is None:
            if warn:
                print(f"warn: {addon_id=} is not found in official addons")
                addon_is_really_installed(installed_addons[addon_id])
            addons_to_build.append(installed_addons[addon_id])
        else:
            addon_data = addons_dict[addon_id]
            installed = installed_addons.get(addon_id, dict())
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
            installed_values.update({k:v for k, v in installed.items() if k in ('installed', 'installed-revision')})
            if warn:
                addon_is_really_installed(installed_values)
            addons_to_build.append(installed_values)
    map_type_to_prio = lambda x: {"kart": "aaa", "track": "aab", "arena": "aac"}[x]
    addons_to_build.sort(key=lambda x: map_type_to_prio(x['type'])+x['id'])
    builder = ET.TreeBuilder()
    builder.start('addons', {'xmlns': STKNS})
    # ---- monkey patch start ----
    def escape_attrib_stk(val):
        safe = set("!'()+,-./0123456789;ABCDEFGHIJKLMNOPQRSTUVWXYZ[]_abcdefghijklmnopqrstuvwxyz|")
        res = [ch if ch in safe else '&#x{:X};'.format(ord(ch)) for ch in val]
        return "".join(res)
    ET._escape_attrib = escape_attrib_stk
    # ---- monkey patch end ----
    for data in addons_to_build:
        builder.start(data['type'], {k: v for k, v in data.items() if k != 'type'})
        builder.end(data['type'])
    builder.end('addons')
    tree = ET.ElementTree(element=builder.close())
    ET.indent(tree)
    tree.write(installed_xml, xml_declaration=True, encoding='utf-8')
    print(f"Updated {len(addons_to_build)} addons in the installed list")

lock = threading.Lock()
def download_and_extract_addons(addon_data: dict) -> str:
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
        with contextlib.closing(urllib.request.urlopen(mkreq(addon_data.get('file')), timeout=timeout)) as resp:
            download_with_progress(resp, tmpdir / download_name)
        
        extractdir = addons_dir / type_to_dir(addon_data.get('type')) / addon_data['id']
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

def install_addons(all_addons, installed_addons, install_filter=lambda _: True) -> None:
    addons_to_install = list()
    
    print("\nFinding addons to install or update...")
    for addon_id, addon_data in all_addons.items():
        installed = installed_addons.get(addon_id)
        if not installed or installed.get('installed') != 'true' or int(installed.get('installed-revision')) < int(addon_data.get('revision')):
            if not int(addon_data.get('status', '0')) & 0x1: # not approved
                continue
            if install_filter(addon_data) and (addon_data.get('type') == 'kart' or int(addon_data.get('format')) > 5): # track format 5 is unsupported
                addons_to_install.append(addon_data)
    
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
    
    if input("\nProceed with installation? [Y/n]: ").lower() in ('n', 'no'):
        print("Installation cancelled.")
        return
    
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
            except Exception:
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

def verify_docker_setup():
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
    print("="*50)
    print("SuperTuxKart Addon Downloader (Docker Edition)")
    print("="*50)
    print(f"Addons directory: {addons_dir}")
    
    try:
        # Verify Docker setup
        verify_docker_setup()
        
        print("\nReading installed addons...")
        installed_addons = get_installed_addons()
        
        print("\nFetching addon database...")
        addons_dict = get_addons()
        
        # Count addons by type
        addon_counts = {"track": 0, "kart": 0, "arena": 0}
        for addon_id, addon_data in addons_dict.items():
            addon_type = addon_data.get('type')
            if addon_type in addon_counts:
                addon_counts[addon_type] += 1
        
        print("\nAvailable addons:")
        for addon_type, count in addon_counts.items():
            print(f"- {addon_type.capitalize()}s: {count}")
        
        try:
            # Use a more descriptive filter with an explanation
            print("\nInstallation filter options:")
            
            # Allow selection of different filter options
            filter_option = input("\nChoose installation filter [1-5]:\n"
                                 "1. Default (tracks, arenas, and featured karts)\n"
                                 "2. All addons (including all karts)\n"
                                 "3. Only tracks and arenas\n"
                                 "4. Only high-rated addons (rating >= 2.8)\n"
                                 "5. Only recently updated addons (within last year)\n"
                                 "Your choice: ")
            
            if filter_option == "1":
                # Default filter - tracks, arenas, and featured karts
                install_filter = lambda d: d.get('type') != 'kart' or int(d.get('status', '0')) & 0x80
                print("\nSelected: Tracks, arenas, and featured karts")
            elif filter_option == "2":
                # All addons
                install_filter = lambda d: True
                print("\nSelected: All addons")
            elif filter_option == "3":
                # Only tracks and arenas
                install_filter = lambda d: d.get('type') != 'kart'
                print("\nSelected: Only tracks and arenas")
            elif filter_option == "4":
                # High rated
                install_filter = lambda d: float(d.get('rating', 0)) >= 2.8
                print("\nSelected: Highly rated addons (≥ 2.8 stars)")
            elif filter_option == "5":
                # Recently updated
                one_year_ago = time.time() - 86400 * 365
                install_filter = lambda d: time.time() - int(d.get('date', 0)) < 86400 * 365
                print("\nSelected: Recently updated addons (within last year)")
            else:
                # Default if invalid option
                print("Invalid option, using default filter.")
                install_filter = lambda d: d.get('type') != 'kart' or int(d.get('status', '0')) & 0x80
            
            install_addons(addons_dict, installed_addons, install_filter=install_filter)
                            
        finally:
            print("\nFinalizing installation...")
            write_installed_addons(addons_dict, installed_addons, warn=True)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        traceback.print_exc()
    
    print("\nDone! Remember to restart your STK Docker container to apply the changes.")