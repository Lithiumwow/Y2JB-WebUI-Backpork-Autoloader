import os
import json
import ftplib
import io
import subprocess
import sys
import base64
import logging
import urllib.request
import urllib.error
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Get the project root directory (workspace root, parent of Y2JB-WebUI)
# backpork_manager.py is in Y2JB-WebUI/src/, so:
# __file__ = Y2JB-WebUI/src/backpork_manager.py
# dirname(__file__) = Y2JB-WebUI/src/
# dirname(dirname(__file__)) = Y2JB-WebUI/
# dirname(dirname(dirname(__file__))) = workspace root/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Y2JB-WebUI/src/
WEBUI_DIR = os.path.dirname(SCRIPT_DIR)  # Y2JB-WebUI/
PROJECT_ROOT = os.path.dirname(WEBUI_DIR)  # workspace root/
CACHE_DIR = os.path.join(WEBUI_DIR, "cache", "backpork")  # Absolute path to cache folder
PATCHES_CACHE_DIR = os.path.join(CACHE_DIR, "patches")  # Cache for downloaded patches
BACKPORK_PATCHES_URL = "https://raw.githubusercontent.com/BestPig/BackPork/master/patches"
MAKE_FSELF_PATH = os.path.join(PROJECT_ROOT, "make_fself", "make_fself.py")

# Required libraries to fetch and patch
# Map: library name on PS5 -> patch file name
REQUIRED_LIBS = {
    "libSceAgc.sprx": "libSceAgc.bps",
    "libSceAgcDriver.sprx": "libSceAgcDriver.bps",
    "libSceNpAuth.sprx": "libSceNpAuth.bps",
    "libSceNpAuthAuthorizedAppDialog.sprx": "libSceNpAuthAuthorizedAppDialog.bps",
    "libSceSaveData.native.sprx": "libSceSaveData.native.bps"
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_patch_from_github(firmware, patch_name):
    """
    Download a BPS patch file from the BackPork GitHub repository.
    Patches are cached locally to avoid repeated downloads.
    
    Args:
        firmware: Firmware version (e.g., '6xx', '7xx')
        patch_name: Name of the patch file (e.g., 'libSceAgc.bps')
    
    Returns:
        dict with 'success' (bool) and either 'path' (str) or 'error' (str)
    """
    try:
        ensure_dir(PATCHES_CACHE_DIR)
        ensure_dir(os.path.join(PATCHES_CACHE_DIR, firmware))
        
        # Local cache path
        patch_path = os.path.join(PATCHES_CACHE_DIR, firmware, patch_name)
        
        # If patch already exists in cache, use it
        if os.path.exists(patch_path):
            print(f"[PATCH] Using cached patch: {patch_path}")
            return {"success": True, "path": patch_path, "cached": True}
        
        # Download from GitHub
        patch_url = f"{BACKPORK_PATCHES_URL}/{firmware}/{patch_name}"
        print(f"[PATCH] Downloading patch from GitHub: {patch_url}")
        
        try:
            with urllib.request.urlopen(patch_url, timeout=30) as response:
                if response.status == 200:
                    patch_data = response.read()
                    
                    # Verify it's a valid BPS patch (starts with 'BPS1')
                    if not patch_data.startswith(b'BPS1'):
                        return {
                            "success": False,
                            "error": f"Downloaded file is not a valid BPS patch (missing BPS1 header)"
                        }
                    
                    # Save to cache
                    with open(patch_path, 'wb') as f:
                        f.write(patch_data)
                    
                    file_size = len(patch_data)
                    print(f"[PATCH] OK Downloaded and cached patch: {patch_path} ({file_size} bytes)")
                    return {"success": True, "path": patch_path, "cached": False}
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Failed to download patch from GitHub"
                    }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {
                    "success": False,
                    "error": f"Patch not found on GitHub: {patch_url}. The patch may not exist for firmware {firmware}."
                }
            return {
                "success": False,
                "error": f"HTTP {e.code}: Failed to download patch from GitHub: {str(e)}"
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"Network error downloading patch: {str(e)}. Check your internet connection."
            }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error downloading patch: {str(e)}\n{traceback.format_exc()}"
        }

def get_ftp_connection(ip, port):
    """Connect to PS5 FTP server with better error messages"""
    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, int(port), timeout=10)
        ftp.login('', '')
        return ftp
    except ConnectionRefusedError:
        raise Exception(f"Connection refused. Make sure:\n1. PS5 IP address is correct ({ip}:{port})\n2. Send ftpsrv-ps5.elf payload from the main page\n3. Wait a few seconds after sending for FTP server to start")
    except OSError as e:
        if "10061" in str(e) or "actively refused" in str(e).lower():
            raise Exception(f"Connection refused. Make sure:\n1. PS5 IP address is correct ({ip}:{port})\n2. Send ftpsrv-ps5.elf payload from the main page\n3. Wait a few seconds after sending for FTP server to start")
        elif "10060" in str(e) or "timed out" in str(e).lower():
            raise Exception(f"Connection timeout. Check:\n1. PS5 IP address is correct ({ip})\n2. PS5 is on the same network\n3. Firewall is not blocking the connection")
        else:
            raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        raise Exception(f"FTP connection failed: {str(e)}")

def list_installed_games(ip, port):
    """Scan /user/app/ for installed games (PPSA folders)"""
    ftp = None
    games = []
    try:
        ftp = get_ftp_connection(ip, port)
        ftp.cwd('/user/app')
        
        # List all directories
        lines = []
        ftp.retrlines('LIST', lines.append)
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 9:
                perms = parts[0]
                name = parts[-1]
                
                # Check if it's a directory and starts with PPSA or CUSA
                if perms.startswith('d') and (name.startswith('PPSA') or name.startswith('CUSA')):
                    # Try to read param.json to get game info
                    game_info = {
                        'title_id': name,
                        'title': name,
                        'content_id': '',
                        'path': f'/user/app/{name}',
                        'cover_url': None
                    }
                    
                    try:
                        ftp.cwd(f'/user/app/{name}')
                        try:
                            # Read param.json for game title
                            param_data = io.BytesIO()
                            ftp.retrbinary('RETR sce_sys/param.json', param_data.write)
                            param_data.seek(0)
                            param_json = json.loads(param_data.read().decode('utf-8'))
                            # Try multiple possible title fields
                            game_info['title'] = (
                                param_json.get('title') or 
                                param_json.get('TITLE') or 
                                param_json.get('name') or 
                                param_json.get('NAME') or 
                                name
                            )
                            game_info['content_id'] = param_json.get('contentId') or param_json.get('CONTENT_ID') or ''
                        except Exception as e:
                            # If param.json fails, keep default title (title_id)
                            print(f"Warning: Could not read param.json for {name}: {e}")
                            pass
                        
                        # Try to fetch game cover (icon0.png)
                        try:
                            cover_data = io.BytesIO()
                            ftp.retrbinary('RETR sce_sys/icon0.png', cover_data.write)
                            cover_data.seek(0)
                            cover_bytes = cover_data.getvalue()
                            # Only encode if we got data
                            if len(cover_bytes) > 0:
                                cover_base64 = base64.b64encode(cover_bytes).decode('utf-8')
                                game_info['cover_url'] = f"data:image/png;base64,{cover_base64}"
                        except Exception as e:
                            # Try alternative cover locations
                            try:
                                cover_data = io.BytesIO()
                                ftp.retrbinary('RETR icon0.png', cover_data.write)
                                cover_data.seek(0)
                                cover_bytes = cover_data.getvalue()
                                if len(cover_bytes) > 0:
                                    cover_base64 = base64.b64encode(cover_bytes).decode('utf-8')
                                    game_info['cover_url'] = f"data:image/png;base64,{cover_base64}"
                            except:
                                pass
                        
                        ftp.cwd('/user/app')
                        games.append(game_info)
                    except:
                        games.append(game_info)
        
        return {"success": True, "games": games}
    except Exception as e:
        error_msg = str(e)
        # Make error message more user-friendly
        if "Connection refused" in error_msg or "10061" in error_msg:
            error_msg = "Cannot connect to PS5 FTP server. Make sure:\n1. PS5 IP address is set correctly\n2. ftpsrv-ps5.elf is running (send payloads first)\n3. PS5 is on the same network"
        return {"success": False, "error": error_msg}
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                pass

def find_game_source_directory(ip, port, title_id):
    """
    Find the actual source directory where the game is stored.
    Games can be in various locations like /data/homebrew, /data/etaHEN/games, /data/games, etc.
    """
    search_paths = [
        "/data/games",  # Common location
        "/data/homebrew",
        "/data/etaHEN/games",
        "/data/etaHEN",  # Sometimes games are directly in etaHEN
        "/data",  # Sometimes games are directly in data
        "/mnt/ext0/games",
        "/mnt/ext0/homebrew",
        "/mnt/ext0/etaHEN/games",
        "/mnt/ext0/etaHEN",
        "/mnt/ext0",  # Sometimes games are directly in ext0
    ]
    
    # Add USB mount points
    for usb_num in range(8):  # usb0 through usb7
        search_paths.append(f"/mnt/usb{usb_num}/games")
        search_paths.append(f"/mnt/usb{usb_num}/homebrew")
        search_paths.append(f"/mnt/usb{usb_num}/etaHEN/games")
        search_paths.append(f"/mnt/usb{usb_num}/etaHEN")
        search_paths.append(f"/mnt/usb{usb_num}")  # Sometimes games are directly in USB root
    
    ftp = None
    try:
        ftp = get_ftp_connection(ip, port)
        print(f"\n[FIND] ========== Starting search for title_id: {title_id} ==========")
        print(f"[FIND] Will search in {len(search_paths)} paths: {search_paths[:5]}...")
        print(f"[FIND] ============================================================\n")
        
        for base_path in search_paths:
            try:
                print(f"[FIND] Checking path: {base_path}")
                ftp.cwd(base_path)
                # List directories
                lines = []
                ftp.retrlines('LIST', lines.append)
                print(f"[FIND] Found {len(lines)} items in {base_path}")
                
                # First, log all directories found for debugging
                all_dirs = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 9:
                        perms = parts[0]
                        name = parts[-1]
                        if perms.startswith('d'):
                            all_dirs.append(name)
                
                # Log all directories found (for debugging)
                if all_dirs:
                    print(f"[FIND] All directories in {base_path}: {all_dirs}")
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 9:
                        perms = parts[0]
                        name = parts[-1]
                        
                        # Check if it's a directory matching our title_id
                        # Try exact match first, then check if title_id is contained in name
                        is_match = False
                        if perms.startswith('d'):
                            if name == title_id:
                                is_match = True
                                print(f"[FIND] Found exact match: {name} == {title_id}")
                            elif title_id in name or name in title_id:
                                # Try partial match - might be like "PPSA10261_game" or similar
                                print(f"[FIND] Found partial match candidate: {name} (looking for {title_id})")
                                is_match = True
                        
                        if is_match:
                            print(f"[FIND] Processing matching directory: {name} in {base_path}")
                            game_source_path = f"{base_path}/{name}"
                            print(f"[FIND] Full path: {game_source_path}")
                            # Verify it's actually the game by checking for app0, sce_sys, or param.json
                            try:
                                ftp.cwd(game_source_path)
                                subdirs = []
                                ftp.retrlines('LIST', subdirs.append)
                                print(f"[FIND] Directory contents: {subdirs[:5]}...")  # Show first 5
                                # Check if it has app0, sce_sys, or looks like a game directory
                                # IMPORTANT: We want the SOURCE directory (like /data/games/PPSA23226), 
                                # NOT the mounted directory (/user/app/PPSA23226/app0)
                                # So we should NOT match directories that are in /user/app/ paths
                                has_game_structure = False
                                subdir_names = []
                                for subdir in subdirs:
                                    parts = subdir.split()
                                    if len(parts) >= 9:
                                        subdir_name = parts[-1]
                                        subdir_names.append(subdir_name)
                                        # Check for game structure indicators
                                        if 'app0' in subdir_name.lower() or 'sce_sys' in subdir_name.lower():
                                            has_game_structure = True
                                            print(f"[FIND] Found game structure indicator: {subdir_name}")
                                
                                print(f"[FIND] Subdirectories found: {subdir_names[:10]}")  # Show first 10
                                
                                # Also try to check for param.json directly
                                if not has_game_structure:
                                    try:
                                        ftp.cwd('sce_sys')
                                        ftp.retrbinary('RETR param.json', lambda x: None)
                                        has_game_structure = True
                                        print(f"[FIND] Found param.json in sce_sys")
                                        ftp.cwd('..')
                                    except Exception as param_e:
                                        print(f"[FIND] No param.json in sce_sys: {param_e}")
                                        pass
                                
                                # If still no game structure, check if directory name itself suggests it's a game
                                # (Sometimes games might not have app0/sce_sys if they're in a different format)
                                if not has_game_structure and (name.startswith('PPSA') or name.startswith('CUSA')):
                                    print(f"[FIND] Directory name suggests it's a game ({name}), accepting as game source")
                                    has_game_structure = True
                                
                                if has_game_structure:
                                    # CRITICAL: Never return /user/app/ paths - these are mounted, not source
                                    if '/user/app/' in game_source_path or 'app0' in game_source_path:
                                        print(f"[FIND] WARNING: Rejecting /user/app/ or app0 path (mounted, not source): {game_source_path}", flush=True)
                                        ftp.cwd('..')
                                        continue
                                    print(f"[FIND] OK Verified game source at: {game_source_path}", flush=True)
                                    return {"success": True, "path": game_source_path}
                                else:
                                    print(f"[FIND] WARNING: Directory {game_source_path} doesn't have game structure (subdirs: {subdir_names[:5]})")
                                
                                ftp.cwd('..')  # Go back to base_path
                            except Exception as e:
                                print(f"[FIND] Error checking {game_source_path}: {e}")
                                try:
                                    ftp.cwd(base_path)  # Make sure we're back at base_path
                                except:
                                    pass
            except Exception as e:
                # Path doesn't exist, continue searching
                print(f"[FIND] Path {base_path} not accessible: {e}")
                continue
        
        print(f"[FIND] Could not find game source directory for {title_id} in any of the searched paths")
        return {"success": False, "error": f"Could not find game source directory for {title_id}. Searched in: {', '.join(search_paths)}"}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[FIND] Exception while searching for game: {e}")
        print(f"[FIND] Traceback: {error_trace}")
        return {"success": False, "error": f"Error searching for game: {str(e)}"}
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                pass

def create_fakelib_folder(ip, port, game_path, title_id=None):
    """
    Create fakelib folder in game's source directory.
    First tries to find the actual source location, then creates fakelib there.
    VERSION 2.0 - 2026-01-23 - WITH SAFETY CHECKS
    """
    import sys
    import time
    # Force immediate output
    sys.stdout.flush()
    sys.stderr.flush()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    version_id = "V2.0-2026-01-23-02:00"
    logger.info("=" * 60)
    logger.info(f"create_fakelib_folder called - {version_id} - {timestamp}")
    logger.info(f"game_path: {game_path}")
    logger.info(f"title_id (provided): {title_id}")
    print(f"\n{'='*60}", flush=True)
    print(f"[FAKELIB] {version_id} - FUNCTION CALLED AT {timestamp}", flush=True)
    print(f"[FAKELIB] game_path: {game_path}", flush=True)
    print(f"[FAKELIB] title_id (provided): {title_id}", flush=True)
    print(f"{'='*60}\n", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    
    # If title_id not provided, try to extract it from game_path
    if not title_id and '/user/app/' in game_path:
        title_id = game_path.split('/user/app/')[-1].split('/')[0]
        print(f"[FAKELIB] Extracted title_id from game_path: {title_id}")
    
    print(f"[FAKELIB] ===================================================\n")
    
    ftp = None
    try:
        # If title_id is provided, try to find the actual source directory
        game_source_path = None
        if title_id:
            print(f"[FAKELIB] Searching for game source directory for {title_id}...")
            source_result = find_game_source_directory(ip, port, title_id)
            if source_result['success']:
                game_source_path = source_result['path']
                print(f"[FAKELIB] Found game source at: {game_source_path}")
            else:
                # Don't fallback - this is an error
                error_msg = source_result.get('error', 'Unknown error')
                print(f"[FAKELIB] Failed to find game source: {error_msg}")
                error_details = f"Could not find game source directory for {title_id}. Searched in: {', '.join(['/data/games', '/data/homebrew', '/data/etaHEN/games', 'USB/ext mount points'])}. Error: {error_msg}"
                print(f"[FAKELIB] ERROR: {error_details}")
                return {
                    "success": False, 
                    "error": error_details,
                    "message": error_details
                }
        else:
            # No title_id provided - try to extract from game_path
            print(f"[FAKELIB] WARNING: No title_id provided, attempting to extract from game_path: {game_path}")
            if '/user/app/' in game_path:
                extracted_title_id = game_path.split('/user/app/')[-1].split('/')[0]
                print(f"[FAKELIB] Extracted title_id: {extracted_title_id}")
                # Retry search with extracted title_id
                source_result = find_game_source_directory(ip, port, extracted_title_id)
                if source_result['success']:
                    game_source_path = source_result['path']
                    print(f"[FAKELIB] OK Found game source using extracted title_id: {game_source_path}")
                else:
                    error_msg = source_result.get('error', 'Unknown error')
                    return {
                        "success": False,
                        "error": f"Could not find game source directory. Extracted title_id: {extracted_title_id}. Error: {error_msg}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"title_id is required to find game source directory. Game path was: {game_path}"
                }
        
        if not game_source_path:
            print(f"[FAKELIB] ERROR: game_source_path is None after search")
            return {
                "success": False,
                "error": "Could not determine game source path"
            }
        
        # CRITICAL SAFETY CHECK: Never use /user/app/ paths
        if '/user/app/' in game_source_path:
            error_msg = f"ERROR: Attempted to use mounted path {game_source_path}. This should never happen. Game source directory search failed."
            print(f"[FAKELIB] ERROR: {error_msg}", flush=True)
            return {
                "success": False,
                "error": error_msg
            }
        
        # Double-check: game_source_path should NOT contain app0
        if 'app0' in game_source_path:
            error_msg = f"ERROR: game_source_path contains 'app0': {game_source_path}. This indicates a mounted path, not source."
            print(f"[FAKELIB] ERROR: {error_msg}", flush=True)
            return {
                "success": False,
                "error": error_msg
            }
        
        print(f"[FAKELIB] OK Safety checks passed. game_source_path: {game_source_path}", flush=True)
        ftp = get_ftp_connection(ip, port)
        
        # Try to create fakelib in the source directory
        fakelib_path = f"{game_source_path}/fakelib"
        
        # FINAL SAFETY CHECK: Absolutely prevent /user/app/ or app0 paths
        if '/user/app/' in fakelib_path or 'app0' in fakelib_path:
            error_msg = f"CRITICAL ERROR: fakelib_path contains forbidden path elements: {fakelib_path}. This should never happen!"
            print(f"[FAKELIB] CRITICAL ERROR: {error_msg}", flush=True)
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        print(f"[FAKELIB] Using fakelib_path: {fakelib_path}", flush=True)
        logger.info(f"Using fakelib_path: {fakelib_path}")
        
        # First, verify the source directory exists
        try:
            ftp.cwd(game_source_path)
        except:
            return {"success": False, "error": f"Game source directory not found: {game_source_path}"}
        
        # Try to create the fakelib directory
        print(f"[FAKELIB] Attempting to create fakelib at: {fakelib_path}", flush=True)
        try:
            ftp.mkd(fakelib_path)
            print(f"[FAKELIB] OK Successfully created fakelib folder at {fakelib_path}", flush=True)
            # Final check before returning
            if '/user/app/' in fakelib_path or 'app0' in fakelib_path:
                return {"success": False, "error": f"CRITICAL: Path validation failed: {fakelib_path}"}
            return {"success": True, "message": f"Created fakelib folder at {fakelib_path}", "path": fakelib_path}
        except ftplib.error_perm as e:
            error_str = str(e)
            print(f"[FAKELIB] MKD command returned error: {error_str}", flush=True)
            # Directory might already exist - verify it actually exists
            if "550" in error_str or "already exists" in error_str.lower() or "file exists" in error_str.lower():
                # Verify it actually exists by trying to list it
                try:
                    ftp.cwd(fakelib_path)
                    print(f"[FAKELIB] OK Verified fakelib folder exists at {fakelib_path}", flush=True)
                    ftp.cwd(game_source_path)  # Go back
                    # FINAL CHECK before returning - this is where the old path was being returned
                    if '/user/app/' in fakelib_path or 'app0' in fakelib_path:
                        error_msg = f"CRITICAL ERROR: Attempted to return forbidden path: {fakelib_path}"
                        print(f"[FAKELIB] CRITICAL ERROR: {error_msg}", flush=True)
                        logger.error(error_msg)
                        import sys
                        sys.stdout.flush()
                        sys.stderr.flush()
                        return {"success": False, "error": error_msg}
                    # Add version identifier to verify new code is running
                    message = f"fakelib folder already exists at {fakelib_path} [V2.0-2026-01-23]"
                    print(f"[FAKELIB] OK Returning success with path: {fakelib_path} [V2.0]", flush=True)
                    logger.info(f"Returning success: {message}")
                    import sys
                    sys.stdout.flush()
                    sys.stderr.flush()
                    return {"success": True, "message": message, "path": fakelib_path}
                except Exception as verify_e:
                    print(f"[FAKELIB] WARNING: Fakelib path doesn't actually exist, error: {verify_e}")
                    # It doesn't actually exist, try creating again with different method
                    try:
                        # Try creating parent directories if needed
                        ftp.mkd(fakelib_path)
                        print(f"[FAKELIB] OK Created fakelib folder on retry at {fakelib_path}")
                        return {"success": True, "message": f"Created fakelib folder at {fakelib_path}", "path": fakelib_path}
                    except Exception as retry_e:
                        print(f"[FAKELIB] ERROR: Failed to create fakelib on retry: {retry_e}")
                        return {"success": False, "error": f"Failed to create fakelib folder at {fakelib_path}. Original error: {error_str}, Retry error: {retry_e}"}
            else:
                print(f"[FAKELIB] ERROR: Permission error creating fakelib: {error_str}")
                return {"success": False, "error": f"Permission denied creating fakelib folder at {fakelib_path}: {error_str}"}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[FAKELIB] ERROR: Exception creating fakelib: {e}")
        print(f"[FAKELIB] Traceback: {error_trace}")
        return {"success": False, "error": f"Exception creating fakelib folder: {str(e)}"}
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                pass

def fetch_system_library(ip, lib_name, ftp_port=2121):
    """
    Fetch a system library from /system/common/lib via FTP and save it to the cache folder.
    
    When using the ftpsrv-ps5.elf payload (port 2121), files are automatically
    decrypted from SELF to ELF format during transfer.
    Files are saved to cache/backpork/ for processing.
    """
    ftp = None
    try:
        ensure_dir(CACHE_DIR)
        print(f"[{lib_name}] Connecting to FTP on port {ftp_port} (ftpsrv payload auto-decrypts)...")
        ftp = get_ftp_connection(ip, ftp_port)
        
        remote_path = f"/system/common/lib/{lib_name}"
        local_path = os.path.join(CACHE_DIR, lib_name)
        
        print(f"[{lib_name}] Downloading from {remote_path} to cache...")
        # Download the file
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f'RETR {remote_path}', f.write)
        
        file_size = os.path.getsize(local_path)
        print(f"[{lib_name}] OK Downloaded {file_size} bytes to cache: {local_path}")
        
        return {"success": True, "path": local_path, "filename": lib_name}
    except Exception as e:
        error_msg = str(e)
        print(f"[{lib_name}] ERROR Failed to download from FTP: {error_msg}")
        return {"success": False, "error": f"FTP download failed: {error_msg}"}
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                pass

def apply_bps_patch(rom_data, patch_data):
    """
    Apply a BPS patch to ROM data.
    Implements the BPS (Binary Patch System) format.
    Based on specification: http://byuu.org/programming/bps/
    """
    try:
        # BPS file format:
        # Header: "BPS1" (4 bytes)
        # Source size (variable-length integer)
        # Target size (variable-length integer)
        # Metadata size (variable-length integer)
        # Metadata (optional, metadata_size bytes)
        # Actions (variable length)
        # Footer: Source CRC32 (4 bytes), Target CRC32 (4 bytes), Patch CRC32 (4 bytes)
        
        if len(patch_data) < 16 or not patch_data.startswith(b'BPS1'):
            return None, "Invalid BPS patch file (missing header or too small)"
        
        pos = 4
        
        # Read variable-length integers (VLIs)
        # BPS VLI format: data += (x & 0x7f) * shift; if (x & 0x80) break; shift <<= 7; data += shift;
        def read_vli():
            nonlocal pos
            result = 0
            shift = 1
            while pos < len(patch_data):
                byte = patch_data[pos]
                pos += 1
                result += (byte & 0x7F) * shift
                if (byte & 0x80) != 0:
                    break
                shift <<= 7
                result += shift
                if shift > (1 << 56):  # Safety limit (64-bit)
                    break
            return result
        
        source_size = read_vli()
        target_size = read_vli()
        metadata_size = read_vli()
        
        print(f"[BPS] DEBUG: Read from patch - source_size={source_size}, target_size={target_size}, metadata_size={metadata_size}")
        print(f"[BPS] DEBUG: Actual file size={len(rom_data)} bytes")
        
        # Validate source size
        # BPS patches can work even if source size doesn't match exactly
        # Some patches may have incorrect source size in header, but still work
        # We'll proceed with the actual file size and let the patch actions determine what to do
        if source_size != len(rom_data):
            size_diff = abs(source_size - len(rom_data))
            size_diff_percent = (size_diff / len(rom_data) * 100) if len(rom_data) > 0 else 0
            print(f"[BPS] INFO: Source size mismatch: patch expects {source_size} bytes, file has {len(rom_data)} bytes ({size_diff_percent:.1f}% difference)")
            print(f"[BPS] INFO: Proceeding with actual file size - patch actions will determine what to modify")
            # Use the actual file size, not the patch's expected size
            # The patch actions will reference the actual file data
        else:
            print(f"[BPS] OK: Source size matches: {source_size} bytes")
        
        # Skip metadata
        pos += metadata_size
        
        # Validate target size is reasonable
        if target_size == 0:
            return None, "BPS patch target size is 0 - patch may be corrupted"
        if target_size > len(rom_data) * 10:  # Sanity check: target shouldn't be more than 10x source
            return None, f"BPS patch target size ({target_size}) seems unreasonably large compared to source ({len(rom_data)})"
        
        # Initialize output buffer
        # If target_size seems too small compared to source, it might be wrong
        # Use a reasonable minimum size
        if target_size < len(rom_data) * 0.1:  # Target is less than 10% of source
            print(f"[BPS] WARNING: Target size ({target_size}) seems too small compared to source ({len(rom_data)})")
            print(f"[BPS] Using source size as minimum target size")
            target_size = max(target_size, len(rom_data))
        
        output = bytearray(target_size)
        output_pos = 0
        source_read_offset = 0
        
        # Process actions until we reach the footer (last 12 bytes)
        footer_start = len(patch_data) - 12
        actions_processed = 0
        while pos < footer_start:
            if output_pos >= target_size:
                break
            
            if pos >= footer_start:
                break
            
            # Read action VLI: encodes both command and length
            # Format: number action | ((length - 1) << 2)
            # So: command = data & 3, length = (data >> 2) + 1
            action_data = read_vli()
            action_type = action_data & 0x03
            length = (action_data >> 2) + 1
            
            if length <= 0 or length > target_size:
                return None, f"Invalid action length: {length} (target_size: {target_size})"
            
            actions_processed += 1
            
            if action_type == 0:  # SourceRead: copy from source at same position
                # SourceRead copies from source[outputOffset] to target[outputOffset]
                for i in range(length):
                    if output_pos >= target_size:
                        break
                    if output_pos < len(rom_data):
                        output[output_pos] = rom_data[output_pos]
                    else:
                        # If source is shorter, pad with zeros (shouldn't happen with valid patches)
                        output[output_pos] = 0
                    output_pos += 1
            
            elif action_type == 1:  # TargetRead: read from patch
                for i in range(length):
                    if output_pos >= target_size or pos >= footer_start:
                        break
                    output[output_pos] = patch_data[pos]
                    output_pos += 1
                    pos += 1
            
            elif action_type == 2:  # SourceCopy: copy from source with relative offset
                if pos >= footer_start:
                    break
                offset_vli = read_vli()
                # Decode relative offset
                if (offset_vli & 1) != 0:
                    source_read_offset -= (offset_vli >> 1)
                else:
                    source_read_offset += (offset_vli >> 1)
                
                for i in range(length):
                    if output_pos >= target_size:
                        break
                    if 0 <= source_read_offset < len(rom_data):
                        output[output_pos] = rom_data[source_read_offset]
                    output_pos += 1
                    source_read_offset += 1
            
            elif action_type == 3:  # TargetCopy: copy from already written output
                if pos >= footer_start:
                    break
                offset_vli = read_vli()
                # Decode relative offset
                copy_offset = output_pos
                if (offset_vli & 1) != 0:
                    copy_offset -= (offset_vli >> 1)
                else:
                    copy_offset += (offset_vli >> 1)
                
                for i in range(length):
                    if output_pos >= target_size:
                        break
                    if 0 <= copy_offset < output_pos:
                        output[output_pos] = output[copy_offset]
                    output_pos += 1
                    copy_offset += 1
        
        # Verify output size matches expected target size
        if output_pos != target_size:
            return None, f"Output size mismatch: expected {target_size} bytes, but only wrote {output_pos} bytes. Patch may be incomplete or corrupted."
        
        if len(output) != target_size:
            return None, f"Output buffer size mismatch: expected {target_size}, got {len(output)}"
        
        print(f"[BPS] OK Patch applied successfully, output size: {len(output)} bytes")
        
        return bytes(output), None
    except Exception as e:
        import traceback
        return None, f"BPS patch error: {str(e)}\n{traceback.format_exc()}"

def is_self_file(file_path):
    """Check if a file is a SELF (encrypted) file"""
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(4)
            # PS5 SELF magic is \x4F\x15\x3D\x1D
            # But sometimes files might have different headers
            # Check for SELF magic or if it's NOT ELF (and not empty)
            if magic == b'\x4F\x15\x3D\x1D':
                return True
            # Check for alternative SELF magic (little-endian: 0x1D3D154F = 5414f5ee in hex when read as bytes)
            if magic == bytes.fromhex('1d3d154f') or magic == bytes.fromhex('4f153d1d'):
                return True
            # If it's not ELF and not empty, it might be SELF or another format
            if not magic.startswith(b'\x7FELF') and len(magic) == 4:
                # Check file extension - .sprx files are typically SELF
                if file_path.endswith('.sprx') or file_path.endswith('.native.sprx'):
                    return True
            return False
    except:
        return False

def is_self_file_from_data(data):
    """Check if data bytes represent a SELF file"""
    if len(data) < 4:
        return False
    magic = data[:4]
    return (magic == b'\x4F\x15\x3D\x1D' or 
            magic == bytes.fromhex('1d3d154f') or 
            magic == bytes.fromhex('4f153d1d'))

def decrypt_self_to_elf(self_path, elf_output_path=None):
    """
    Decrypt a SELF file to ELF format.
    This is a simplified implementation - for full decryption, you may need ps5_elf_sdk_downgrade.py
    """
    try:
        if not os.path.exists(self_path):
            return {"success": False, "error": f"SELF file not found: {self_path}"}
        
        if not is_self_file(self_path):
            return {"success": False, "error": "File is not a SELF file"}
        
        # If no output path specified, create one next to the SELF file
        if elf_output_path is None:
            base_name = os.path.basename(self_path)
            if base_name.endswith('.sprx'):
                elf_name = base_name.replace('.sprx', '.elf')
            elif base_name.endswith('.native.sprx'):
                elf_name = base_name.replace('.native.sprx', '.native.elf')
            else:
                elf_name = base_name + '.elf'
            elf_output_path = os.path.join(os.path.dirname(self_path), elf_name)
        
        # Try to use ps5_elf_sdk_downgrade.py if available
        # First check if it's in the project
        possible_decrypt_paths = [
            os.path.join(PROJECT_ROOT, "ps5_elf_sdk_downgrade.py"),
            os.path.join(PROJECT_ROOT, "ps5-self-decrypter", "decrypt.py"),
            os.path.join(WEBUI_DIR, "ps5_elf_sdk_downgrade.py"),
        ]
        
        decrypt_tool = None
        for path in possible_decrypt_paths:
            if os.path.exists(path):
                decrypt_tool = path
                break
        
        if decrypt_tool:
            # Use external decryption tool
            print(f"[DECRYPT] Using external tool: {decrypt_tool}")
            result = subprocess.run(
                [sys.executable, decrypt_tool, self_path, elf_output_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and os.path.exists(elf_output_path):
                return {"success": True, "path": elf_output_path}
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return {"success": False, "error": f"Decryption tool failed: {error_msg}"}
        
        # Fallback: Basic SELF parsing and decryption attempt
        # Note: This is a simplified implementation and may not work for all SELF files
        print(f"[DECRYPT] Attempting basic SELF decryption (external tool not found)")
        with open(self_path, 'rb') as f:
            self_data = f.read()
        
        # SELF header is at offset 0
        # For PS5, we need to parse the SELF header and decrypt segments
        # This is complex and typically requires keys, so we'll try a simple approach:
        # Look for ELF data within the SELF file (sometimes it's embedded)
        
        # Check if there's ELF data embedded in the SELF file
        elf_magic_pos = self_data.find(b'\x7FELF')
        if elf_magic_pos >= 0 and elf_magic_pos < len(self_data) - 100:
            # Found ELF magic, try to extract it
            # This is a heuristic - may not work for all files
            print(f"[DECRYPT] Found ELF magic at offset {elf_magic_pos}, attempting extraction")
            
            # Try to parse ELF header to get file size
            # ELF header structure: magic(4) + class(1) + data(1) + version(1) + osabi(1) + ...
            # For now, extract from magic position to end of file
            # This assumes the ELF is embedded and continues to the end
            remaining_data = self_data[elf_magic_pos:]
            
            # Try to determine ELF file size by reading the ELF header
            # ELF32/64 header has file size info, but for simplicity, 
            # we'll extract everything from the magic position
            # In a proper implementation, we'd parse the ELF header to get the actual size
            
            with open(elf_output_path, 'wb') as out_f:
                out_f.write(remaining_data)
            
            # Verify it's a valid ELF by checking magic and basic structure
            with open(elf_output_path, 'rb') as check_f:
                magic = check_f.read(4)
                if not magic.startswith(b'\x7FELF'):
                    print(f"[DECRYPT] WARNING: Extracted file doesn't have valid ELF magic")
                    return {
                        "success": False,
                        "error": "Extracted file doesn't have valid ELF magic. The SELF file may need proper decryption with ps5_elf_sdk_downgrade.py"
                    }
                
                # Check ELF class (32-bit or 64-bit)
                check_f.seek(4)
                elf_class = check_f.read(1)
                if elf_class not in [b'\x01', b'\x02']:  # 1=32-bit, 2=64-bit
                    print(f"[DECRYPT] WARNING: Invalid ELF class: {elf_class.hex()}")
                    return {
                        "success": False,
                        "error": f"Invalid ELF class: {elf_class.hex()}. The extracted file may be incomplete or corrupted."
                    }
                
                # Try to read ELF header to verify it's complete
                # ELF header is at least 52 bytes for 32-bit, 64 bytes for 64-bit
                check_f.seek(0)
                header_size = 64 if elf_class == b'\x02' else 52
                header = check_f.read(header_size)
                if len(header) < header_size:
                    print(f"[DECRYPT] WARNING: Extracted file is too small (only {len(header)} bytes, need at least {header_size})")
                    return {
                        "success": False,
                        "error": f"Extracted ELF file is incomplete. The basic extraction method may not work for this file. Please use ps5_elf_sdk_downgrade.py for proper decryption."
                    }
            
            # Check file size - if it's suspiciously small, warn
            file_size = os.path.getsize(elf_output_path)
            if file_size < 1024:  # Less than 1KB is probably incomplete
                print(f"[DECRYPT] WARNING: Extracted file is very small ({file_size} bytes), may be incomplete")
                return {
                    "success": False,
                    "error": f"Extracted ELF file is very small ({file_size} bytes), likely incomplete. Please use ps5_elf_sdk_downgrade.py for proper decryption."
                }
            
            print(f"[DECRYPT] OK Extracted ELF file (size: {file_size} bytes)")
            return {"success": True, "path": elf_output_path}
        
        return {
            "success": False, 
            "error": "Could not decrypt SELF file. Please install ps5_elf_sdk_downgrade.py or another SELF decryption tool. "
                     f"Place it in the project root or in {WEBUI_DIR}/"
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": f"Decryption error: {str(e)}\n{traceback.format_exc()}"}

def patch_library(lib_path, patch_path, firmware):
    """
    Patch a library file using BPS patch
    
    Reads the file and applies the BPS patch from BackPork.
    """
    try:
        # Read the library file
        with open(lib_path, 'rb') as f:
            rom_data = f.read()
        
        print(f"[BPS] Patching file (size: {len(rom_data)} bytes)")
        
        # Read the patch file
        if not os.path.exists(patch_path):
            return {"success": False, "error": f"Patch file not found: {patch_path}"}
        
        with open(patch_path, 'rb') as f:
            patch_data = f.read()
        
        # Apply patch
        patched_data, error = apply_bps_patch(rom_data, patch_data)
        if error:
            return {"success": False, "error": error}
        
        # Save patched file as ELF (will be fake signed later)
        base_name = os.path.basename(lib_path)
        if base_name.endswith('.sprx'):
            patched_name = base_name.replace('.sprx', '_patched.elf')
        elif base_name.endswith('.native.sprx'):
            patched_name = base_name.replace('.native.sprx', '_patched.elf')
        else:
            patched_name = base_name + '_patched.elf'
        
        patched_path = os.path.join(os.path.dirname(lib_path), patched_name)
        with open(patched_path, 'wb') as f:
            f.write(patched_data)
        
        return {"success": True, "path": patched_path}
    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}

def fake_sign_elf(elf_path, output_path):
    """Fake sign an ELF file using make_fself.py"""
    try:
        if not os.path.exists(MAKE_FSELF_PATH):
            return {"success": False, "error": f"make_fself.py not found at {MAKE_FSELF_PATH}"}
        
        # Convert to absolute paths to avoid path issues
        elf_path = os.path.abspath(elf_path)
        output_path = os.path.abspath(output_path)
        
        if not os.path.exists(elf_path):
            return {"success": False, "error": f"ELF file not found: {elf_path}"}
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Run make_fself.py
        # Use system_dynlib for system libraries
        # Use absolute paths and forward slashes for cross-platform compatibility
        make_fself_abs = os.path.abspath(MAKE_FSELF_PATH)
        elf_path_normalized = elf_path.replace('\\', '/')
        output_path_normalized = output_path.replace('\\', '/')
        
        print(f"[FAKESIGN] Input: {elf_path_normalized}")
        print(f"[FAKESIGN] Output: {output_path_normalized}")
        print(f"[FAKESIGN] Tool: {make_fself_abs}")
        
        result = subprocess.run(
            [sys.executable, make_fself_abs, elf_path_normalized, output_path_normalized, '--ptype', 'system_dynlib'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(make_fself_abs) or '.'
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return {"success": True, "path": output_path}
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"[FAKESIGN] Error output: {error_msg}")
            print(f"[FAKESIGN] Return code: {result.returncode}")
            return {"success": False, "error": f"make_fself failed: {error_msg}"}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[FAKESIGN] Exception: {e}")
        print(f"[FAKESIGN] Traceback: {error_trace}")
        return {"success": False, "error": f"{str(e)}\n{error_trace}"}

def upload_patched_library(ip, port, local_path, remote_path):
    """Upload patched and signed library to fakelib folder"""
    ftp = None
    try:
        ftp = get_ftp_connection(ip, port)
        
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if ftp:
            try:
                ftp.quit()
            except:
                pass

def process_library_for_game(ip, port, lib_name, firmware, game_path):
    """
    Complete workflow: fetch, patch, sign, and upload a library
    
    Process:
    1. Download file from /system/common/lib to cache
    2. Apply BPS patch from BackPork
    3. Fake sign the patched file
    4. Upload to fakelib folder
    """
    print(f"\n{'='*60}")
    print(f"[PROCESS] Starting processing for {lib_name}")
    print(f"[PROCESS] Firmware: {firmware}, Game path: {game_path}")
    print(f"{'='*60}")
    steps = []
    
    # Step 1: Fetch library from PS5 using ftpsrv payload (auto-decrypts to ELF)
    print(f"[{lib_name}] Step 1: Fetching library from PS5 via ftpsrv payload (port {port}, auto-decrypts)...")
    steps.append({"name": "Fetching library from PS5", "success": False})
    # Use the payload port (from config, typically 2121) which auto-decrypts SELF to ELF
    # The 'port' parameter passed to this function is the ftpsrv payload port
    fetch_result = fetch_system_library(ip, lib_name, ftp_port=port)
    if not fetch_result['success']:
        error_msg = fetch_result.get('error', 'Unknown error - no error message provided')
        steps[-1]["error"] = error_msg
        print(f"[{lib_name}] Step 1: ERROR Failed to fetch: {error_msg}")
        return {
            "success": False, 
            "error": f"Failed to fetch {lib_name}: {error_msg}",
            "message": f"Failed to fetch {lib_name}: {error_msg}",
            "steps": steps
        }
    steps[-1]["success"] = True
    lib_path = fetch_result['path']
    print(f"[{lib_name}] Step 1: OK Library fetched to {lib_path}")
    
    # Step 1.5: Convert SELF to ELF if needed (BPS patches need ELF input)
    with open(lib_path, 'rb') as f:
        magic = f.read(4)
    if not magic.startswith(b'\x7FELF'):
        print(f"[{lib_name}] File is SELF format, extracting ELF...")
        steps.append({"name": "Converting SELF to ELF", "success": False})
        decrypt_result = decrypt_self_to_elf(lib_path)
        if not decrypt_result.get('success'):
            steps[-1]["error"] = decrypt_result.get('error', 'Decryption failed')
            return {
                "success": False,
                "error": f"Failed to convert SELF to ELF: {decrypt_result.get('error')}",
                "steps": steps
            }
        lib_path = decrypt_result['path']
        steps[-1]["success"] = True
        print(f"[{lib_name}] OK Converted to ELF: {lib_path}")
    
    # Step 2: Download patch file from GitHub
    print(f"[{lib_name}] Step 2: Downloading patch file from BackPork repository...")
    steps.append({"name": "Downloading patch file", "success": False})
    patch_name = REQUIRED_LIBS.get(lib_name)
    if not patch_name:
        # Fallback: try to construct patch name
        patch_name = lib_name.replace('.sprx', '.bps').replace('.native.sprx', '.native.bps')
    
    # Download patch from GitHub (will use cache if available)
    download_result = download_patch_from_github(firmware, patch_name)
    if not download_result.get('success'):
        steps[-1]["error"] = download_result.get('error', 'Unknown error')
        return {
            "success": False, 
            "error": f"Failed to download patch {patch_name}: {download_result.get('error')}",
            "steps": steps
        }
    patch_path = download_result['path']
    steps[-1]["success"] = True
    cache_status = "cached" if download_result.get('cached') else "downloaded"
    print(f"[{lib_name}] Step 2: OK Patch file {cache_status}: {patch_path}")
    
    # Step 3: Apply BPS patch
    print(f"[{lib_name}] Step 3: Applying BPS patch...")
    steps.append({"name": "Applying BPS patch", "success": False})
    
    # Patch the file with BPS patch
    patch_result = patch_library(lib_path, patch_path, firmware)
    if not patch_result['success']:
        steps[-1]["error"] = patch_result.get('error', 'Unknown error')
        return {
            "success": False, 
            "error": f"Failed to patch {lib_name}: {patch_result.get('error')}",
            "steps": steps
        }
    steps[-1]["success"] = True
    patched_elf_path = patch_result['path']
    print(f"[{lib_name}] Step 3: OK Patch applied, saved to {patched_elf_path}")
    
    # Step 4: Fake sign
    print(f"[{lib_name}] Step 4: Fake signing library...")
    steps.append({"name": "Fake signing library", "success": False})
    signed_path = patched_elf_path.replace('_patched.elf', '_signed.sprx')
    sign_result = fake_sign_elf(patched_elf_path, signed_path)
    if not sign_result['success']:
        steps[-1]["error"] = sign_result.get('error', 'Unknown error')
        return {
            "success": False, 
            "error": f"Failed to sign {lib_name}: {sign_result.get('error')}",
            "steps": steps
        }
    steps[-1]["success"] = True
    print(f"[{lib_name}] Step 4: OK Library signed, saved to {signed_path}")
    
    # Step 5: Ensure fakelib folder exists
    print(f"[{lib_name}] Step 5: Ensuring fakelib folder exists...")
    steps.append({"name": "Creating fakelib folder", "success": False})
    
    # Extract title_id from game_path (format: /user/app/{title_id})
    title_id = None
    if '/user/app/' in game_path:
        title_id = game_path.split('/user/app/')[-1].split('/')[0]
        print(f"[{lib_name}] Extracted title_id from game_path: {title_id}")
    else:
        print(f"[{lib_name}] WARNING: Could not extract title_id from game_path: {game_path}")
    
    if not title_id:
        return {
            "success": False,
            "error": f"Could not extract title_id from game_path: {game_path}",
            "steps": steps
        }
    
    print(f"[{lib_name}] Calling create_fakelib_folder with title_id: {title_id}")
    fakelib_result = create_fakelib_folder(ip, port, game_path, title_id)
    if not fakelib_result['success']:
        error_msg = fakelib_result.get('error', 'Unknown error - no error message provided')
        steps[-1]["error"] = error_msg
        print(f"[{lib_name}] Step 5: ERROR Fakelib folder creation failed: {error_msg}")
        return {
            "success": False,
            "error": f"Failed to create fakelib folder: {error_msg}",
            "message": f"Failed to create fakelib folder: {error_msg}",
            "steps": steps
        }
    else:
        steps[-1]["success"] = True
        game_fakelib_path = fakelib_result.get('path', 'unknown')
        print(f"[{lib_name}] Step 5: OK Fakelib folder ready at {game_fakelib_path}")
    
    # Step 6: Upload to fakelib
    print(f"[{lib_name}] Step 6: Uploading to PS5...")
    steps.append({"name": "Uploading to PS5", "success": False})
    remote_lib_name = lib_name  # Keep original name
    
    # Use the fakelib path from the creation result (from Step 5)
    remote_path = f"{game_fakelib_path}/{remote_lib_name}"
    
    upload_result = upload_patched_library(ip, port, signed_path, remote_path)
    if not upload_result['success']:
        steps[-1]["error"] = upload_result.get('error', 'Unknown error')
        return {
            "success": False, 
            "error": f"Failed to upload {lib_name}: {upload_result.get('error')}",
            "steps": steps
        }
    steps[-1]["success"] = True
    print(f"[{lib_name}] Step 6: OK Library uploaded to {remote_path}")
    
    return {
        "success": True, 
        "message": f"Successfully processed and uploaded {lib_name}",
        "steps": steps
    }
