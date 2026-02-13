# Update Log - Y2JB-WebUI BackPork Autoloader

## Last Updated: February 12, 2026

### Payload send & WebUI fixes (Feb 2026)
- **backpork_manager.py**, **backpork.js**, **backpork.html** synced with WebUI that includes payload-send fixes.
- **Host WebUI recommendations** (apply in your Y2JB-WebUI if lapse.js send was failing):
  - Load IP/settings from **`/api/settings`** (not static JSON) so the Connection box is not cached.
  - Add **Loader Port** setting (default 50000; some loaders use 9026) and use it for lapse.js / JS payloads.
  - **SendPayload**: return specific errors (connection refused, timeout, host not found) and strip IP whitespace; 15s timeout.
  - Add **`/api/check_loader`** and a **Test** button next to the IP field to verify loader reachability.

---

## Last Updated: February 4, 2026

### Summary
Project has been updated with the latest components from official reference repositories.

---

## Updates Applied

### 1. ✅ BackPork Patches - Enhanced
**Reference Repository:** [BestPig/BackPork](https://github.com/BestPig/BackPork)

**Changes:**
- Added missing `libSceFiber.bps` to `BackPork/patches/7xx/` directory
- Added missing `libScePsml.bps` to `BackPork/patches/7xx/` directory
- All patch files now verified and synchronized with official BackPork repository
- Added README.md documentation to 7xx patches folder

**Files Updated:**
- `BackPork/patches/7xx/libSceFiber.bps` (NEW)
- `BackPork/patches/7xx/libScePsml.bps` (NEW)
- `BackPork/patches/7xx/README.md` (NEW)

---

### 2. ✅ BackPork Manager - Enhanced Library Support
**File:** `src/backpork_manager.py`

**Changes:**
- Added `libSceFiber.sprx` to REQUIRED_LIBS dictionary
- Added `libScePsml.sprx` to REQUIRED_LIBS dictionary
- These libraries are now available for patching on both 6xx and 7xx firmware versions

**Updated REQUIRED_LIBS:**
```python
REQUIRED_LIBS = {
    "libSceAgc.sprx": "libSceAgc.bps",
    "libSceAgcDriver.sprx": "libSceAgcDriver.bps",
    "libSceFiber.sprx": "libSceFiber.bps",          # NEW
    "libSceNpAuth.sprx": "libSceNpAuth.bps",
    "libSceNpAuthAuthorizedAppDialog.sprx": "libSceNpAuthAuthorizedAppDialog.bps",
    "libScePsml.sprx": "libScePsml.bps",            # NEW
    "libSceSaveData.native.sprx": "libSceSaveData.native.bps"
}
```

---

### 3. ✅ make_fself.py - Verified Current
**Reference Repository:** [ps5-payload-dev/sdk](https://github.com/ps5-payload-dev/sdk)

**Status:** ✓ Already up-to-date (824 lines, identical to official version)
- File verified against official PS5 Payload SDK
- No updates required

---

### 4. ✅ Verified Components
- `static/backpork.js` - Current and compatible
- `templates/backpork.html` - Current and compatible
- `server_backpork_routes.py` - Current and compatible
- `README.md` - Documentation current
- `INSTALLATION.md` - Installation guide current

---

## Compatibility

### Supported Firmware
- **6xx (10.01)**: All 7 libraries available
- **7xx (Firmware 7.61+)**: All 7 libraries available

### Libraries Available for Patching
1. libSceAgc.sprx ✓
2. libSceAgcDriver.sprx ✓
3. libSceFiber.sprx ✓ (newly added)
4. libSceNpAuth.sprx ✓
5. libSceNpAuthAuthorizedAppDialog.sprx ✓
6. libScePsml.sprx ✓ (newly added)
7. libSceSaveData.native.sprx ✓

---

## Verification Checklist

- [x] BackPork patches synchronized with official repository
- [x] Missing 7xx patches added (libSceFiber, libScePsml)
- [x] backpork_manager.py updated with new libraries
- [x] make_fself.py verified as current
- [x] All files pass consistency checks
- [x] No breaking changes introduced
- [x] Backward compatibility maintained

---

## Reference Repositories

| Component | Repository | Branch | Last Verified |
|-----------|-----------|--------|----------------|
| BackPork Patches | github.com/BestPig/BackPork | master | 2026-02-04 |
| PS5 Payload SDK | github.com/ps5-payload-dev/sdk | main | 2026-02-04 |
| Y2JB-WebUI | github.com/Nazky/Y2JB-WebUI | - | Current version |

---

## How to Use New Libraries

The newly added libraries (libSceFiber and libScePsml) are now available in the BackPork web interface:

1. Navigate to `/backpork` in Y2JB-WebUI
2. Select a game
3. Choose firmware version (6xx or 7xx)
4. **New:** libSceFiber.sprx and libScePsml.sprx are now available for selection
5. Process as usual

---

## Notes

- Patches are automatically downloaded from GitHub and cached locally
- No internet connection required after initial cache population
- Cache location: `Y2JB-WebUI/cache/backpork/patches/{firmware}/`
- All components are verified against official reference repositories

---

## Future Updates

To keep this project updated:

1. Monitor [BackPork repository](https://github.com/BestPig/BackPork) for new patches
2. Check [PS5 Payload SDK](https://github.com/ps5-payload-dev/sdk) for make_fself updates
3. Review [Y2JB-WebUI](https://github.com/Nazky/Y2JB-WebUI) for integration improvements

Run `git pull` in the original repositories to stay current.

---

*Update performed automatically from official reference repositories.*
