# BackPork Integration Routes for Y2JB-WebUI
# Add these routes to your server.py file.
# Requires: app, request, jsonify, render_template, get_config, logger (logging.getLogger(__name__)), sys.

from src.backpork_manager import (
    list_installed_games, create_fakelib_folder, fetch_system_library,
    process_library_for_game, REQUIRED_LIBS
)
import subprocess
import sys
import inspect

# BackPork endpoints
@app.route('/backpork')
def backpork_page():
    return render_template('backpork.html')

@app.route('/api/backpork/test_ftp', methods=['POST'])
def api_backpork_test_ftp():
    """Test FTP connection to PS5"""
    try:
        config = get_config()
        ip = config.get("ip")
        port = config.get("ftp_port", "1337")
        
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        
        # Try to connect and list root directory
        from src.backpork_manager import get_ftp_connection
        ftp = None
        try:
            ftp = get_ftp_connection(ip, port)
            # Try to list root directory
            ftp.retrlines('LIST', lambda x: None)
            ftp.quit()
            return jsonify({"success": True, "message": f"FTP connection successful to {ip}:{port}"})
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "10061" in error_msg:
                return jsonify({
                    "success": False, 
                    "error": f"FTP server not running. Make sure:\n1. Send ftpsrv-ps5.elf payload from the main page\n2. Wait a few seconds after sending\n3. Check that port {port} is correct"
                }), 500
            else:
                return jsonify({"success": False, "error": error_msg}), 500
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backpork/list_games', methods=['POST'])
def api_backpork_list_games():
    try:
        config = get_config()
        ip = config.get("ip")
        port = config.get("ftp_port", "1337")
        
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        
        result = list_installed_games(ip, port)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backpork/create_fakelib', methods=['POST'])
def api_backpork_create_fakelib():
    try:
        config = get_config()
        ip = config.get("ip")
        port = config.get("ftp_port", "1337")
        data = request.json
        game_path = data.get('game_path')
        title_id = data.get('title_id')  # Extract title_id from game object
        
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        if not game_path:
            return jsonify({"success": False, "error": "Game path not provided"}), 400
        
        logger.info("=" * 60)
        logger.info("/api/backpork/create_fakelib called")
        logger.info(f"game_path={game_path}")
        logger.info(f"title_id={title_id}")
        logger.info(f"IP={ip}, Port={port}")
        logger.info("=" * 60)
        sys.stdout.flush()
        sys.stderr.flush()
        
        result = create_fakelib_folder(ip, port, game_path, title_id)
        
        logger.info("=" * 60)
        logger.info("/api/backpork/create_fakelib result")
        logger.info(f"success={result.get('success')}")
        logger.info(f"message={result.get('message')}")
        logger.info(f"error={result.get('error')}")
        logger.info(f"path={result.get('path')}")
        logger.info("=" * 60)
        sys.stdout.flush()
        sys.stderr.flush()
        
        return jsonify(result)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[API] Exception in create_fakelib: {e}")
        print(f"[API] Traceback: {error_trace}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backpork/test_code', methods=['GET'])
def api_backpork_test_code():
    """Test endpoint to verify code is running"""
    import src.backpork_manager
    source_file = inspect.getsourcefile(src.backpork_manager.create_fakelib_folder)
    with open(source_file, 'r') as f:
        lines = f.readlines()
        if len(lines) > 257 and '[FAKELIB] ==========' in lines[257]:
            return jsonify({"success": True, "message": "New code is loaded", "line_258": lines[257].strip()})
        else:
            return jsonify({"success": False, "message": "Old code might be running", "line_258": lines[257].strip() if len(lines) > 257 else "N/A"})

@app.route('/api/backpork/discover_paths', methods=['POST'])
def api_backpork_discover_paths():
    """Discover where games are actually stored"""
    try:
        config = get_config()
        ip = config.get("ip")
        port = config.get("ftp_port", "1337")
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        from src.backpork_manager import get_ftp_connection
        import ftplib
        ftp = None
        accessible_paths = []
        game_directories = []
        try:
            ftp = get_ftp_connection(ip, port)
            potential_paths = [
                "/data", "/data/games", "/data/homebrew", "/data/etaHEN", "/data/etaHEN/games",
                "/mnt", "/mnt/ext0", "/mnt/ext0/games", "/mnt/ext0/homebrew", "/mnt/ext0/etaHEN",
                "/user", "/user/app",
            ]
            for usb_num in range(8):
                potential_paths.extend([
                    f"/mnt/usb{usb_num}", f"/mnt/usb{usb_num}/games",
                    f"/mnt/usb{usb_num}/homebrew", f"/mnt/usb{usb_num}/etaHEN", f"/mnt/usb{usb_num}/etaHEN/games",
                ])
            for path in potential_paths:
                try:
                    ftp.cwd(path)
                    lines = []
                    ftp.retrlines('LIST', lines.append)
                    accessible_paths.append({
                        "path": path, "item_count": len(lines),
                        "items": [line.split()[-1] for line in lines[:10]]
                    })
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 9:
                            name = parts[-1]
                            if (name.startswith('PPSA') or name.startswith('CUSA')) and parts[0].startswith('d'):
                                game_directories.append({"path": f"{path}/{name}", "title_id": name})
                except Exception:
                    pass
            return jsonify({
                "success": True,
                "accessible_paths": accessible_paths,
                "game_directories": game_directories
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    pass
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backpork/process_libraries', methods=['POST'])
def api_backpork_process_libraries():
    try:
        config = get_config()
        ip = config.get("ip")
        port = config.get("ftp_port", "1337")
        data = request.json
        firmware = data.get('firmware')  # '6xx' or '7xx'
        game_path = data.get('game_path')
        selected_libs = data.get('libraries', list(REQUIRED_LIBS.keys()))
        
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        if not firmware:
            return jsonify({"success": False, "error": "Firmware version not selected"}), 400
        if not game_path:
            return jsonify({"success": False, "error": "Game path not provided"}), 400
        
        results = []
        print(f"\n[BACKPORK] ========== Starting library processing ==========")
        print(f"[BACKPORK] IP: {ip}, Port: {port}")
        print(f"[BACKPORK] Firmware: {firmware}, Game path: {game_path}")
        print(f"[BACKPORK] Libraries to process: {selected_libs}")
        print(f"[BACKPORK] ===================================================\n")
        
        for lib_name in selected_libs:
            print(f"\n[BACKPORK] Processing library: {lib_name}")
            print(f"[BACKPORK] ===================================================")
            try:
                result = process_library_for_game(ip, port, lib_name, firmware, game_path)
                print(f"[BACKPORK] Result for {lib_name}: success={result.get('success')}, error={result.get('error')}")
                results.append({
                    "library": lib_name,
                    "success": result.get("success", False),
                    "message": result.get("message") or result.get("error", "Unknown error"),
                    "steps": result.get("steps", [])
                })
                if result.get("success"):
                    print(f"[BACKPORK] ✓ {lib_name} processed successfully")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"[BACKPORK] ✗ {lib_name} failed: {error_msg}")
                    sys.stdout.flush()
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"[BACKPORK] ✗✗✗ EXCEPTION processing {lib_name}: {e}")
                print(f"[BACKPORK] Full traceback:")
                print(error_trace)
                sys.stdout.flush()
                sys.stderr.flush()
                results.append({
                    "library": lib_name,
                    "success": False,
                    "message": f"Exception: {str(e)}",
                    "steps": []
                })
        
        all_success = all(r["success"] for r in results)
        return jsonify({
            "success": all_success,
            "results": results
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[BACKPORK] ✗✗✗ TOP-LEVEL EXCEPTION in process_libraries: {e}")
        print(f"[BACKPORK] Full traceback:")
        print(error_trace)
        sys.stdout.flush()
        sys.stderr.flush()
        return jsonify({"success": False, "error": str(e), "traceback": error_trace}), 500
