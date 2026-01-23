# BackPork Integration

This integration adds BackPork functionality to Y2JB-WebUI, allowing you to easily set up fakelib folders and patch system libraries for PS5 games.

## Features

- Send BackPork and FTP payloads to PS5
- List installed games from PS5
- Create fakelib folders for selected games
- Fetch system libraries from `/system/common/lib`
- Apply BPS patches to libraries
- Fake sign patched libraries
- Upload patched libraries to game fakelib folders

## Setup

1. **Place required files:**
   - `ps5-backpork.elf` or `backpork.elf` in `payloads/` folder
   - `ftpsrv-ps5.elf` in `payloads/` folder
   - `make_fself.py` in `make_fself/` folder (should already be cloned)

2. **Ensure patches are available:**
   - Patches should be in `BackPork/patches/6xx/` and `BackPork/patches/7xx/`
   - These are BPS format patch files

## Important Notes

### SELF to ELF Decryption

**CRITICAL:** Libraries from `/system/common/lib` are in SELF format (encrypted). BPS patches require ELF format (decrypted) files.

Before patching, you need to decrypt SELF files to ELF format. You can use:
- `ps5_elf_sdk_downgrade.py` (mentioned in BackPork README)
- Or other SELF decryption tools

The current implementation will detect SELF files and show an error message if you try to patch them directly.

### Workflow

1. **Send Payloads:** Click "Send BackPork & FTP Payloads" to load the required payloads on your PS5
2. **Select Firmware:** Choose your firmware version (6xx or 7xx)
3. **Refresh Games:** Click "Refresh" to scan for installed games
4. **Select Game:** Click on a game to select it (fakelib folder will be created automatically)
5. **Process Libraries:** Click "Process & Upload Libraries" to:
   - Fetch libraries from `/system/common/lib`
   - Apply BPS patches
   - Fake sign the patched libraries
   - Upload to the game's fakelib folder

## File Structure

```
workspace/
├── BackPork/
│   └── patches/
│       ├── 6xx/
│       │   ├── libSceAgc.bps
│       │   ├── libSceAgcDriver.bps
│       │   └── ...
│       └── 7xx/
│           ├── libSceAgc.bps
│           └── ...
├── make_fself/
│   └── make_fself.py
└── Y2JB-WebUI/
    ├── payloads/
    │   ├── ps5-backpork.elf (or backpork.elf)
    │   └── ftpsrv-ps5.elf
    └── cache/
        └── backpork/  (temporary files during processing)
```

## Troubleshooting

- **"Patch file not found"**: Make sure BackPork repository is cloned and patches are in the correct directory
- **"Library is in SELF format"**: You need to decrypt the SELF file to ELF format first
- **"make_fself.py not found"**: Make sure make_fself directory is in the workspace root
- **"Failed to fetch library"**: Check FTP connection and ensure ftpsrv-ps5.elf is running on PS5

## Future Improvements

- Add automatic SELF to ELF decryption
- Support for more library types
- Batch processing for multiple games
- Progress indicators for long operations
