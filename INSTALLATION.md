# Installation Guide

## Quick Setup

### Step 1: Copy Files

Copy these files to your Y2JB-WebUI installation:

**Core Files:**
- `src/backpork_manager.py` → `Y2JB-WebUI/src/backpork_manager.py`
- `static/backpork.js` → `Y2JB-WebUI/static/backpork.js`
- `templates/backpork.html` → `Y2JB-WebUI/templates/backpork.html`

**Dependencies:**
- `BackPork/patches/` → `{project_root}/BackPork/patches/`
- `make_fself/` → `{project_root}/make_fself/`

### Step 2: Modify server.py

1. **Add imports** (near the top, with other imports):
```python
from src.backpork_manager import (
    list_installed_games, create_fakelib_folder, fetch_system_library,
    process_library_for_game, REQUIRED_LIBS
)
import subprocess
```

2. **Add routes** (copy all routes from `server_backpork_routes.py`):
   - `/backpork` - Main page route
   - `/api/backpork/test_ftp` - Test FTP connection
   - `/api/backpork/list_games` - List installed games
   - `/api/backpork/create_fakelib` - Create fakelib folder
   - `/api/backpork/process_libraries` - Process libraries

### Step 3: Update Navigation (Optional)

Add a link to the BackPork page in your main navigation (usually in `templates/index.html`):

```html
<a href="/backpork" class="nav-link">
    <i class="fa-solid fa-code-branch"></i> BackPork
</a>
```

### Step 4: Verify Structure

Ensure your project structure looks like this:

```
Project Root/
├── Y2JB-WebUI/
│   ├── src/
│   │   └── backpork_manager.py      ✓
│   ├── static/
│   │   └── backpork.js              ✓
│   ├── templates/
│   │   └── backpork.html            ✓
│   └── server.py                    ✓ (modified)
├── BackPork/
│   └── patches/
│       ├── 6xx/                     ✓
│       └── 7xx/                     ✓
└── make_fself/
    └── make_fself.py                 ✓
```

### Step 5: Test

1. Start your Y2JB-WebUI server
2. Navigate to `http://localhost:8000/backpork`
3. You should see the BackPork interface

## File Modifications Summary

### Files Added:
- `src/backpork_manager.py` (new)
- `static/backpork.js` (new)
- `templates/backpork.html` (new)

### Files Modified:
- `server.py` (added routes and imports)

### Dependencies Required:
- `BackPork/patches/` folder with BPS files
- `make_fself/make_fself.py` for signing

## Verification Checklist

- [ ] `backpork_manager.py` copied to `Y2JB-WebUI/src/`
- [ ] `backpork.js` copied to `Y2JB-WebUI/static/`
- [ ] `backpork.html` copied to `Y2JB-WebUI/templates/`
- [ ] Routes added to `server.py`
- [ ] Imports added to `server.py`
- [ ] `BackPork/patches/` folder exists with 6xx and 7xx subfolders
- [ ] `make_fself/make_fself.py` exists
- [ ] Server starts without errors
- [ ] `/backpork` page loads in browser
