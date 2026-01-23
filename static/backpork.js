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
    gamesList.innerHTML = '<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin text-2xl"></i><p class="mt-2 text-sm">Scanning for games...</p></div>';
    
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
                <div class="text-center py-8 opacity-50">
                    <i class="fa-solid fa-exclamation-circle text-4xl mb-2"></i>
                    <p class="mb-2">PS5 IP Address not set</p>
                    <p class="text-xs opacity-70">Please go to Settings and set your PS5 IP address first</p>
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
                gameCard.className = 'surface border rounded-lg p-4 hover:border-brand-blue/30 transition-all cursor-pointer hover:shadow-lg';
                gameCard.onclick = () => selectGame(game);
                
                // Create cover image or placeholder - make it larger
                const coverContainerId = `cover-${game.title_id.replace(/[^a-zA-Z0-9]/g, '-')}`;
                let coverHtml = '';
                if (game.cover_url) {
                    coverHtml = `
                        <div id="${coverContainerId}" class="relative w-20 h-20 flex-shrink-0">
                            <img src="${game.cover_url}" alt="${escapeHtml(game.title)}" 
                                 class="w-20 h-20 object-cover rounded-lg border-2 border-white/20 shadow-md" 
                                 onerror="this.style.display='none'; document.getElementById('${coverContainerId}-placeholder').style.display='flex';"
                                 loading="lazy">
                            <div id="${coverContainerId}-placeholder" class="w-20 h-20 bg-gradient-to-br from-brand-blue/30 to-brand-light/30 rounded-lg border-2 border-white/20 flex items-center justify-center hidden shadow-md">
                                <i class="fa-solid fa-gamepad text-3xl opacity-50"></i>
                            </div>
                        </div>
                    `;
                } else {
                    coverHtml = `
                        <div class="w-20 h-20 bg-gradient-to-br from-brand-blue/30 to-brand-light/30 rounded-lg border-2 border-white/20 flex items-center justify-center flex-shrink-0 shadow-md">
                            <i class="fa-solid fa-gamepad text-3xl opacity-50"></i>
                        </div>
                    `;
                }
                
                // Ensure title is visible - use title_id as fallback
                const displayTitle = game.title && game.title !== game.title_id ? game.title : game.title_id;
                
                gameCard.innerHTML = `
                    <div class="flex items-center gap-4">
                        ${coverHtml}
                        <div class="flex-1 min-w-0">
                            <h4 class="font-bold text-base mb-1 truncate" title="${escapeHtml(displayTitle)}">${escapeHtml(displayTitle)}</h4>
                            <p class="text-xs opacity-60 font-mono truncate" title="${escapeHtml(game.title_id)}">${escapeHtml(game.title_id)}</p>
                        </div>
                        <i class="fa-solid fa-chevron-right opacity-40 flex-shrink-0 text-xl"></i>
                    </div>
                `;
                gamesList.appendChild(gameCard);
            });
        } else {
            const errorMsg = data.error || 'No games found';
            // Replace newlines with <br> for better display
            const formattedError = escapeHtml(errorMsg).replace(/\n/g, '<br>');
            gamesList.innerHTML = `
                <div class="text-center py-8 opacity-50">
                    <i class="fa-solid fa-exclamation-triangle text-4xl mb-2"></i>
                    <p>${formattedError}</p>
                </div>
            `;
        }
    } catch (error) {
        gamesList.innerHTML = `
            <div class="text-center py-8 opacity-50">
                <i class="fa-solid fa-exclamation-circle text-4xl mb-2"></i>
                <p>Error: ${error.message}</p>
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
        libItem.className = 'flex items-center gap-3 p-3 bg-gray-200 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700 hover:border-brand-blue/50 transition-colors';
        libItem.innerHTML = `
            <input type="checkbox" 
                   id="lib-checkbox-${index}" 
                   class="lib-checkbox w-4 h-4 text-brand-blue bg-gray-100 border-gray-300 rounded focus:ring-brand-blue focus:ring-2" 
                   data-lib-name="${escapeHtml(lib.name)}"
                   checked>
            <label for="lib-checkbox-${index}" class="flex-1 cursor-pointer">
                <span class="text-sm font-mono">${escapeHtml(lib.display)}</span>
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
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i>Processing ${selectedLibs.length} library(ies)...`;
    statusDiv.classList.remove('hidden');
    statusDiv.innerHTML = `<div class="text-sm opacity-70"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Starting library processing (${selectedLibs.length} selected)...</div>`;
    
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
                statusItem.className = `p-3 rounded-lg mb-2 ${result.success ? 'bg-green-500/20 border border-green-500/30' : 'bg-red-500/20 border border-red-500/30'}`;
                
                // Format the message with line breaks
                const formattedMessage = escapeHtml(result.message || result.error || 'Unknown error').replace(/\n/g, '<br>');
                
                statusItem.innerHTML = `
                    <div class="flex items-start gap-3">
                        <i class="fa-solid ${result.success ? 'fa-check-circle text-green-400' : 'fa-times-circle text-red-400'} text-lg mt-0.5"></i>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="text-sm font-bold font-mono">${escapeHtml(result.library)}</span>
                                ${result.steps ? `<span class="text-xs opacity-60">(${result.steps.length} steps)</span>` : ''}
                            </div>
                            <div class="text-xs opacity-80">${formattedMessage}</div>
                            ${result.steps && result.steps.length > 0 ? `
                                <div class="mt-2 space-y-1">
                                    ${result.steps.map(step => `
                                        <div class="text-xs opacity-60 flex items-center gap-2">
                                            <i class="fa-solid ${step.success ? 'fa-check text-green-400' : 'fa-times text-red-400'} text-xs"></i>
                                            <span>${escapeHtml(step.name)}</span>
                                            ${step.error ? `<span class="text-red-400 ml-2">- ${escapeHtml(step.error)}</span>` : ''}
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
