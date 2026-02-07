let selectedGame = null;
let selectedFirmware = '6xx';

const REQUIRED_LIBS = [
    { name: 'libSceAgc.sprx', display: 'libSceAgc.sprx' },
    { name: 'libSceAgcDriver.sprx', display: 'libSceAgcDriver.sprx' },
    { name: 'libSceNpAuth.sprx', display: 'libSceNpAuth.sprx' },
    { name: 'libSceNpAuthAuthorizedAppDialog.sprx', display: 'libSceNpAuthAuthorizedAppDialog.sprx' },
    { name: 'libSceSaveData.native.sprx', display: 'libSceSaveData.native.sprx' }
];

async function refreshGames() {
    const gamesList = document.getElementById('games-list');
    gamesList.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-white/50"><i class="fa-solid fa-spinner fa-spin text-3xl mb-3"></i><p class="text-sm">Scanning for games…</p></div>';
    
    try {
        // Check if IP is set (by checking the settings)
        const configResponse = await fetch('/api/settings');
        if (!configResponse.ok) {
            throw new Error(`Failed to load settings: ${configResponse.status}`);
        }
        let config;
        try {
            config = await configResponse.json();
        } catch (jsonError) {
            console.error('[BACKPORK] Failed to parse settings JSON:', jsonError);
            throw new Error(`Failed to parse settings: ${jsonError.message}`);
        }
        if (!config.ip) {
            gamesList.innerHTML = `
                <div class="flex flex-col items-center justify-center py-16 text-white/50">
                    <i class="fa-solid fa-exclamation-circle text-4xl mb-3"></i>
                    <p class="text-sm font-medium mb-1">PS5 IP not set</p>
                    <p class="text-xs text-white/50">Set your PS5 IP in Settings first</p>
                </div>
            `;
            showToast('Please set PS5 IP address in Settings first', 'warning');
            return;
        }
        const response = await fetch('/api/backpork/list_games', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK and is JSON
        if (!response.ok) {
            let errorText = '';
            try {
                errorText = await response.text();
            } catch (e) {
                errorText = `Could not read error response: ${e.message}`;
            }
            throw new Error(`Server error: ${response.status} ${response.statusText}. ${errorText.substring(0, 200)}`);
        }
        
        const contentType = response.headers.get('content-type') || '';
        let responseText = '';
        try {
            responseText = await response.clone().text();
        } catch (e) {
            // If we can't clone, we'll try to read it directly below
        }
        
        if (!contentType.includes('application/json')) {
            console.error('[BACKPORK] Non-JSON response detected:', {
                contentType,
                status: response.status,
                preview: responseText.substring(0, 200)
            });
            throw new Error(`Expected JSON but got ${contentType || 'unknown'}. Response preview: ${responseText.substring(0, 200)}`);
        }
        
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('[BACKPORK] JSON parse error:', jsonError);
            console.error('[BACKPORK] Response text:', responseText || 'Could not read response');
            throw new Error(`Failed to parse JSON response: ${jsonError.message}. Response preview: ${(responseText || 'Could not read').substring(0, 200)}`);
        }
        
        if (data.success && data.games && data.games.length > 0) {
            gamesList.innerHTML = '';
            data.games.forEach(game => {
                const gameCard = document.createElement('div');
                gameCard.className = 'ps5-card p-3 cursor-pointer group';
                gameCard.onclick = () => selectGame(game);
                
                const coverContainerId = `cover-${game.title_id.replace(/[^a-zA-Z0-9]/g, '-')}`;
                let coverHtml = '';
                if (game.cover_url) {
                    coverHtml = `
                        <div id="${coverContainerId}" class="relative w-14 h-14 flex-shrink-0 rounded-lg overflow-hidden bg-white/5">
                            <img src="${game.cover_url}" alt="${escapeHtml(game.title)}" 
                                 class="w-full h-full object-cover" 
                                 onerror="this.style.display='none'; document.getElementById('${coverContainerId}-placeholder').style.display='flex';"
                                 loading="lazy">
                            <div id="${coverContainerId}-placeholder" class="absolute inset-0 bg-ps5-blue/20 flex items-center justify-center hidden">
                                <i class="fa-solid fa-gamepad text-xl text-white/50"></i>
                            </div>
                        </div>
                    `;
                } else {
                    coverHtml = `
                        <div class="w-14 h-14 rounded-lg bg-ps5-blue/20 flex items-center justify-center flex-shrink-0">
                            <i class="fa-solid fa-gamepad text-xl text-white/50"></i>
                        </div>
                    `;
                }
                
                const displayTitle = game.title && game.title !== game.title_id ? game.title : game.title_id;
                
                gameCard.innerHTML = `
                    <div class="flex items-center gap-3">
                        ${coverHtml}
                        <div class="flex-1 min-w-0">
                            <h4 class="font-semibold text-sm truncate text-white/95 group-hover:text-white" title="${escapeHtml(displayTitle)}">${escapeHtml(displayTitle)}</h4>
                            <p class="text-xs text-white/45 font-mono truncate" title="${escapeHtml(game.title_id)}">${escapeHtml(game.title_id)}</p>
                        </div>
                        <i class="fa-solid fa-chevron-right text-white/30 group-hover:text-ps5-blue transition-colors flex-shrink-0"></i>
                    </div>
                `;
                gamesList.appendChild(gameCard);
            });
        } else {
            const errorMsg = data.error || 'No games found';
            const formattedError = escapeHtml(errorMsg).replace(/\n/g, '<br>');
            gamesList.innerHTML = `
                <div class="flex flex-col items-center justify-center py-16 text-white/50">
                    <i class="fa-solid fa-exclamation-triangle text-4xl mb-3"></i>
                    <p class="text-sm">${formattedError}</p>
                </div>
            `;
        }
    } catch (error) {
        gamesList.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-white/50">
                <i class="fa-solid fa-exclamation-circle text-4xl mb-3"></i>
                <p class="text-sm">${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function selectGame(game) {
    selectedGame = game;
    
    // Update UI
    document.getElementById('selected-game-name').textContent = game.title + ' (' + game.title_id + ')';
    
    // Show library section
    const libSection = document.getElementById('library-section');
    libSection.classList.remove('hidden');
    
    // Populate libraries list with checkboxes
    const libsList = document.getElementById('libraries-list');
    libsList.innerHTML = '';
    REQUIRED_LIBS.forEach((lib, index) => {
        const libItem = document.createElement('div');
        libItem.className = 'flex items-center gap-3 py-2.5 px-3 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-colors';
        libItem.innerHTML = `
            <input type="checkbox" 
                   id="lib-checkbox-${index}" 
                   class="lib-checkbox w-4 h-4 rounded border-white/20 bg-white/5 text-ps5-blue focus:ring-ps5-blue focus:ring-2 focus:ring-offset-0 focus:ring-offset-transparent" 
                   data-lib-name="${escapeHtml(lib.name)}"
                   checked>
            <label for="lib-checkbox-${index}" class="flex-1 cursor-pointer text-sm font-mono text-white/80">
                ${escapeHtml(lib.display)}
            </label>
        `;
        libsList.appendChild(libItem);
    });
    
    // Create fakelib folder
    createFakelibFolder(game);
}

function getSelectedLibraries() {
    const checkboxes = document.querySelectorAll('.lib-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.getAttribute('data-lib-name'));
}

function toggleAllLibraries(selectAll) {
    const checkboxes = document.querySelectorAll('.lib-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll);
}

async function createFakelibFolder(game) {
    try {
        console.log('[JS] createFakelibFolder called with:', game);
        const response = await fetch('/api/backpork/create_fakelib', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify({ 
                game_path: game.path,
                title_id: game.title_id
            })
        });
        
        // Check if response is OK and is JSON
        if (!response.ok) {
            let errorText = '';
            try {
                errorText = await response.text();
            } catch (e) {
                errorText = `Could not read error response: ${e.message}`;
            }
            throw new Error(`Server error: ${response.status} ${response.statusText}. ${errorText.substring(0, 200)}`);
        }
        
        const contentType = response.headers.get('content-type') || '';
        let responseText = '';
        try {
            responseText = await response.clone().text();
        } catch (e) {
            // If we can't clone, we'll try to read it directly below
        }
        
        if (!contentType.includes('application/json')) {
            console.error('[BACKPORK] Non-JSON response detected:', {
                contentType,
                status: response.status,
                preview: responseText.substring(0, 200)
            });
            throw new Error(`Expected JSON but got ${contentType || 'unknown'}. Response preview: ${responseText.substring(0, 200)}`);
        }
        
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('[BACKPORK] JSON parse error:', jsonError);
            console.error('[BACKPORK] Response text:', responseText || 'Could not read response');
            throw new Error(`Failed to parse JSON response: ${jsonError.message}. Response preview: ${(responseText || 'Could not read').substring(0, 200)}`);
        }
        console.log('[JS] Response from server:', data);
        if (data.success) {
            console.log('Fakelib folder created:', data.message);
            // Check if message contains old path format
            if (data.message && data.message.includes('/user/app/') && data.message.includes('app0/fakelib')) {
                console.error('[JS] WARNING: Server returned old path format! This should not happen.');
                showToast('Error: Server returned old path. Please check server logs.', 'error');
            }
        } else {
            showToast('Warning: ' + (data.error || data.message || 'Unknown error'), 'warning');
        }
    } catch (error) {
        console.error('Error creating fakelib folder:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

async function processLibraries() {
    if (!selectedGame) {
        showToast('Please select a game first', 'error');
        return;
    }
    
    // Get selected libraries
    const selectedLibs = getSelectedLibraries();
    if (selectedLibs.length === 0) {
        showToast('Please select at least one library to process', 'warning');
        return;
    }
    
    const firmware = document.querySelector('input[name="firmware"]:checked').value;
    const btn = document.getElementById('btn-process-libraries');
    const statusDiv = document.getElementById('processing-status');
    
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing ${selectedLibs.length}…`;
    statusDiv.classList.remove('hidden');
    statusDiv.innerHTML = `<div class="text-sm text-white/60 flex items-center gap-2"><i class="fa-solid fa-spinner fa-spin"></i> Starting (${selectedLibs.length} selected)…</div>`;
    
    try {
        const response = await fetch('/api/backpork/process_libraries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                firmware: firmware,
                game_path: selectedGame.path,
                libraries: selectedLibs
            })
        });
        
        // Check if response is OK and is JSON
        if (!response.ok) {
            let errorText = '';
            try {
                errorText = await response.text();
            } catch (e) {
                errorText = `Could not read error response: ${e.message}`;
            }
            throw new Error(`Server error: ${response.status} ${response.statusText}. ${errorText.substring(0, 200)}`);
        }
        
        const contentType = response.headers.get('content-type') || '';
        let responseText = '';
        try {
            responseText = await response.clone().text();
        } catch (e) {
            // If we can't clone, we'll try to read it directly below
        }
        
        if (!contentType.includes('application/json')) {
            console.error('[BACKPORK] Non-JSON response detected:', {
                contentType,
                status: response.status,
                preview: responseText.substring(0, 200)
            });
            throw new Error(`Expected JSON but got ${contentType || 'unknown'}. Response preview: ${responseText.substring(0, 200)}`);
        }
        
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('[BACKPORK] JSON parse error:', jsonError);
            console.error('[BACKPORK] Response text:', responseText || 'Could not read response');
            throw new Error(`Failed to parse JSON response: ${jsonError.message}. Response preview: ${(responseText || 'Could not read').substring(0, 200)}`);
        }
        
        if (data.success) {
            statusDiv.innerHTML = '';
            data.results.forEach(result => {
                const statusItem = document.createElement('div');
                statusItem.className = `p-3 rounded-xl ${result.success ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20'}`;
                
                const formattedMessage = escapeHtml(result.message || result.error || 'Unknown error').replace(/\n/g, '<br>');
                
                statusItem.innerHTML = `
                    <div class="flex items-start gap-3">
                        <i class="fa-solid ${result.success ? 'fa-circle-check text-emerald-400' : 'fa-circle-xmark text-red-400'} text-base mt-0.5 flex-shrink-0"></i>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="text-sm font-semibold font-mono text-white/90">${escapeHtml(result.library)}</span>
                                ${result.steps ? `<span class="text-xs text-white/40">${result.steps.length} steps</span>` : ''}
                            </div>
                            <div class="text-xs text-white/70">${formattedMessage}</div>
                            ${result.steps && result.steps.length > 0 ? `
                                <div class="mt-2 space-y-1">
                                    ${result.steps.map(step => `
                                        <div class="text-xs text-white/50 flex items-center gap-2">
                                            <i class="fa-solid ${step.success ? 'fa-check text-emerald-400' : 'fa-times text-red-400'} text-xs"></i>
                                            <span>${escapeHtml(step.name)}</span>
                                            ${step.error ? `<span class="text-red-400">${escapeHtml(step.error)}</span>` : ''}
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
                statusDiv.appendChild(statusItem);
            });
            
            const allSuccess = data.results.every(r => r.success);
            if (allSuccess) {
                showToast('All libraries processed successfully!', 'success');
            } else {
                showToast('Some libraries failed to process. Check details below.', 'warning');
            }
        } else {
            showToast(data.error || 'Failed to process libraries', 'error');
            const formattedError = escapeHtml(data.error || 'Unknown error').replace(/\n/g, '<br>');
            statusDiv.innerHTML = `<div class="text-sm text-red-400 p-3 bg-red-500/20 rounded-lg border border-red-500/30">${formattedError}</div>`;
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
        statusDiv.innerHTML = `<div class="text-sm text-red-400 p-3 bg-red-500/20 rounded-lg border border-red-500/30">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-magic mr-2"></i>Process & Upload Libraries';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function testFTPConnection() {
    try {
        const configResponse = await fetch('/api/settings');
        if (!configResponse.ok) {
            throw new Error(`Failed to load settings: ${configResponse.status}`);
        }
        let config;
        try {
            config = await configResponse.json();
        } catch (jsonError) {
            console.error('[BACKPORK] Failed to parse settings JSON:', jsonError);
            throw new Error(`Failed to parse settings: ${jsonError.message}`);
        }
        
        if (!config.ip) {
            showToast('Please set PS5 IP address in Settings first', 'warning');
            return;
        }
        
        showToast('Testing FTP connection...', 'info');
        
        const response = await fetch('/api/backpork/test_ftp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK and is JSON
        if (!response.ok) {
            let errorText = '';
            try {
                errorText = await response.text();
            } catch (e) {
                errorText = `Could not read error response: ${e.message}`;
            }
            throw new Error(`Server error: ${response.status} ${response.statusText}. ${errorText.substring(0, 200)}`);
        }
        
        const contentType = response.headers.get('content-type') || '';
        let responseText = '';
        try {
            responseText = await response.clone().text();
        } catch (e) {
            // If we can't clone, we'll try to read it directly below
        }
        
        if (!contentType.includes('application/json')) {
            console.error('[BACKPORK] Non-JSON response detected:', {
                contentType,
                status: response.status,
                preview: responseText.substring(0, 200)
            });
            throw new Error(`Expected JSON but got ${contentType || 'unknown'}. Response preview: ${responseText.substring(0, 200)}`);
        }
        
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('[BACKPORK] JSON parse error:', jsonError);
            console.error('[BACKPORK] Response text:', responseText || 'Could not read response');
            throw new Error(`Failed to parse JSON response: ${jsonError.message}. Response preview: ${(responseText || 'Could not read').substring(0, 200)}`);
        }
        
        if (data.success) {
            showToast('FTP connection successful!', 'success');
        } else {
            showToast('FTP connection failed: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Error testing FTP: ' + error.message, 'error');
    }
}

// Load games on page load
document.addEventListener('DOMContentLoaded', () => {
    refreshGames();
});
