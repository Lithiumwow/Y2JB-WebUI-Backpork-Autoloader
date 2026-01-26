# Y2JB-WebUI BackPork Autoloader

This is a BackPork integration module for Y2JB-WebUI that automates the process of creating fakelib folders and processing system libraries for PS5 game backporting.

## Features

- **Automated Fakelib Creation**: Automatically creates fakelib folders in game directories
- **Library Processing**: Downloads, patches, signs, and uploads system libraries
- **Selective Processing**: Choose which libraries to process
- **Firmware Support**: Supports both 6xx and 7xx firmware patches
- **Web UI Integration**: Fully integrated into Y2JB-WebUI interface

## File Structure

```
Y2JB-WebUI-Backpork-Autoloader/
├── src/
│   └── backpork_manager.py          # Core BackPork functionality
├── static/
│   └── backpork.js                  # Frontend JavaScript
├── templates/
│   └── backpork.html                # Frontend template
├── BackPork/
│   └── patches/                     # BPS patch files
│       ├── 6xx/                     # Firmware 6xx patches
│       └── 7xx/                     # Firmware 7xx patches
├── make_fself/
│   └── make_fself.py                # Fake signing tool
├── server_backpork_routes.py        # Routes to add to server.py
└── README.md                         # This file
```

## Installation

1. **Copy files to your Y2JB-WebUI installation:**

   ```bash
   # Copy core files
   cp -r src/backpork_manager.py /path/to/Y2JB-WebUI/src/
   cp -r static/backpork.js /path/to/Y2JB-WebUI/static/
   cp -r templates/backpork.html /path/to/Y2JB-WebUI/templates/
   
   # Copy dependencies (adjust paths as needed)
   cp -r BackPork/patches /path/to/Y2JB-WebUI/../BackPork/
   cp -r make_fself /path/to/Y2JB-WebUI/../make_fself/
   ```

2. **Add routes to server.py:**

   - Open `server_backpork_routes.py` and copy the routes
   - Add the import at the top of your `server.py`:
     ```python
     from src.backpork_manager import (
         list_installed_games, create_fakelib_folder, fetch_system_library,
         process_library_for_game, REQUIRED_LIBS
     )
     import subprocess
     ```
   - Add all the routes from `server_backpork_routes.py` to your `server.py`

3. **Update index.html (optional):**

   Add a link to the BackPork page in your navigation:
   ```html
   <a href="/backpork">BackPork</a>
   ```

## Dependencies

- **BackPork patches**: Automatically downloaded from [BackPork repository](https://github.com/BestPig/BackPork/tree/master/patches) and cached locally
- **make_fself.py**: For fake signing ELF files
- **Python packages**: Already included in Y2JB-WebUI requirements
- **Internet connection**: Required for initial patch download (patches are cached for offline use)

## Directory Structure Requirements

The code expects the following structure:
```
Project Root/
├── Y2JB-WebUI/
│   ├── src/
│   │   └── backpork_manager.py
│   ├── static/
│   │   └── backpork.js
│   ├── templates/
│   │   └── backpork.html
│   ├── cache/
│   │   └── backpork/
│   │       └── patches/          # Patches downloaded from GitHub (auto-created)
│   │           ├── 6xx/
│   │           └── 7xx/
│   └── server.py
└── make_fself/
    └── make_fself.py
```

**Note:** Patches are automatically downloaded from the [BackPork repository](https://github.com/BestPig/BackPork/tree/master/patches) on first use and cached locally. No manual patch installation required!

## Usage

1. Start Y2JB-WebUI server
2. Navigate to `/backpork` in your browser
3. Select a game from the list
4. Choose firmware version (6xx or 7xx)
5. Select which libraries to process
6. Click "Process Libraries"

## How It Works

1. **Download**: Fetches system libraries from `/system/common/lib` via FTP
2. **Extract**: Converts SELF files to ELF format
3. **Patch**: Applies BPS patches from BackPork
4. **Sign**: Fake signs the patched ELF files
5. **Upload**: Places signed files in the game's fakelib folder

## Important Notes

- Requires `ftpsrv-ps5.elf` payload to be running (port 2121)
- Files are automatically decrypted during FTP transfer
- **Patches are automatically downloaded from GitHub** - no manual installation needed
- Cache folder: `Y2JB-WebUI/cache/backpork/`
  - Patches are cached in: `cache/backpork/patches/{firmware}/`
- Processed files are saved to: `{game_path}/fakelib/`

## Troubleshooting

- **FTP Connection Errors**: Make sure ftpsrv-ps5.elf payload is running
- **Patch Download Errors**: 
  - Check your internet connection (required for initial download)
  - Verify the patch exists in the [BackPork repository](https://github.com/BestPig/BackPork/tree/master/patches)
  - Check cached patches in `cache/backpork/patches/{firmware}/`
- **Signing Errors**: Check that `make_fself.py` is accessible
- **ELF Format Errors**: Files should auto-decrypt via FTP payload

## Credits & Acknowledgments

This project integrates and builds upon the work of several amazing developers and projects:

### Core Projects

- **[Y2JB](https://github.com/Gezine/Y2JB)** by [@Gezine](https://github.com/Gezine) - The foundation PS5 jailbreak project ([Releases](https://github.com/Gezine/Y2JB/releases/tag/1.3))
- **[Y2JB-WebUI](https://github.com/Nazky/Y2JB-WebUI)** by [@Nazky](https://github.com/Nazky) - The web interface this module integrates with
- **[BackPork](https://github.com/BestPig/BackPork)** by [@BestPig](https://github.com/BestPig) - The PS5 backporting system and BPS patches
- **[PS5-Vault](https://github.com/NookieAI/PS5-Vault)** by [@NookieAI](https://github.com/NookieAI) - PS5 game management tool (inspiration for FTP features) ([Releases](https://github.com/NookieAI/PS5-Vault/releases))

### Tools & Scripts

- **[ps5_elf_sdk_downgrade.py](https://gist.github.com/idlesauce/2ded24b7b5ff296f21792a8202542aaa)** by [@idlesauce](https://github.com/idlesauce) - PS5 ELF SDK version patching tool
- **make_fself.py** - Fake signing tool for PS5 ELF files


## License

This project integrates with projects that use various licenses:
- **BackPork**: GPL-3.0
- **Y2JB-WebUI**: Check original repository
- **Y2JB**: Check original repository

Please respect the licenses of all integrated projects.
