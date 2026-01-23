# BackPork Integration Routes for Y2JB-WebUI
# Add these routes to your server.py file

from src.backpork_manager import (
    list_installed_games, create_fakelib_folder, fetch_system_library,
    process_library_for_game, REQUIRED_LIBS
)
import subprocess

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
        title_id = data.get('title_id')
        
        if not ip:
            return jsonify({"success": False, "error": "IP Address not set"}), 400
        if not game_path:
            return jsonify({"success": False, "error": "Game path not provided"}), 400
        
        result = create_fakelib_folder(ip, port, game_path, title_id)
        return jsonify(result)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[API] Exception in create_fakelib: {e}")
        print(f"[API] Traceback: {error_trace}")
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
