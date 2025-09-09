// --- FIREBASE IMPORTS - WITH FALLBACK FOR DEMO MODE ---
// We'll try to dynamically import Firebase, but work without it if not available
let firebaseAvailable = false;
let initializeApp, getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged;
let getFirestore, collection, doc, onSnapshot, addDoc, updateDoc, deleteDoc, getDocs, setDoc, getDoc, query, where, orderBy, limit, Timestamp, setLogLevel;

// Initialize Firebase asynchronously
async function initializeFirebaseModules() {
    try {
        const [appModule, authModule, firestoreModule] = await Promise.all([
            import("https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js").catch(() => null),
            import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js").catch(() => null),
            import("https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js").catch(() => null)
        ]);
        
        if (appModule && authModule && firestoreModule) {
            ({ initializeApp } = appModule);
            ({ getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } = authModule);
            ({ getFirestore, collection, doc, onSnapshot, addDoc, updateDoc, deleteDoc, getDocs, setDoc, getDoc, query, where, orderBy, limit, Timestamp, setLogLevel } = firestoreModule);
            firebaseAvailable = true;
            console.log("Firebase modules loaded successfully");
        } else {
            throw new Error("One or more Firebase modules failed to load");
        }
    } catch (error) {
        console.warn("Firebase modules not available, running in demo-only mode:", error.message);
        firebaseAvailable = false;
    }
}

// --- GLOBAL VARIABLES & INITIALIZATION ---
const appId = typeof __app_id !== 'undefined' ? __app_id : '1:945213178297:web:40f6e200fd00148754b668';
const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

// Firestore data collections
let db, auth;
let userId = 'anonymous';
let bots = [];
let strategies = [];
let userSettings = {};

// UI elements
const activeBotsContainer = document.getElementById('active-bots-container');
const inactiveBotsContainer = document.getElementById('inactive-bots-container');
const strategiesContainer = document.getElementById('strategies-container');
const messageBox = document.getElementById('message-box');
const loadingSpinner = document.getElementById('loading-spinner');

// --- HELPER FUNCTIONS ---
function showMessage(text, isError = false) {
    messageBox.textContent = text;
    messageBox.className = `message-box ${isError ? 'error' : 'success'}`;
    messageBox.style.display = 'block';
    setTimeout(() => {
        messageBox.style.display = 'none';
    }, 5000);
}

function showLoading() {
    loadingSpinner.classList.remove('hidden');
}

function hideLoading() {
    loadingSpinner.classList.add('hidden');
}

// Function to show a modal
window.showModal = function(modalId) {
    document.getElementById(modalId).style.display = 'flex';
};

// Function to close a modal
window.closeModal = function(modalId) {
    document.getElementById(modalId).style.display = 'none';
};

// --- CRUD OPERATIONS & DATA DISPLAY ---

// Function to fetch and display strategies
async function fetchStrategies() {
    showLoading();
    try {
        const q = collection(db, `users/${userId}/strategies`);
        onSnapshot(q, (querySnapshot) => {
            strategies = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            displayStrategies();
            updateStrategySelects();
            hideLoading();
        }, (error) => {
            console.error("Error fetching strategies:", error);
            showMessage("Failed to load strategies.", true);
            hideLoading();
        });
    } catch (e) {
        console.error("Error fetching strategies:", e);
        showMessage("Failed to load strategies. Ensure Firebase is configured correctly.", true);
        hideLoading();
    }
}

// Function to fetch and display bots
async function fetchBots() {
    showLoading();
    try {
        const q = collection(db, `users/${userId}/bots`);
        onSnapshot(q, (querySnapshot) => {
            bots = querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            displayBots();
            updateOverallStats();
            hideLoading();
        }, (error) => {
            console.error("Error fetching bots:", error);
            showMessage("Failed to load bots.", true);
            hideLoading();
        });
    } catch (e) {
        console.error("Error fetching bots:", e);
        showMessage("Failed to load bots. Ensure Firebase is configured correctly.", true);
        hideLoading();
    }
}

// Update the strategy dropdowns with the latest strategies
function updateStrategySelects() {
    const strategySelects = document.querySelectorAll('#strategy-select, #modal-strategy, #linked-strategy-select');
    strategySelects.forEach(select => {
        const isLinkedSelect = select.id === 'linked-strategy-select';
        const defaultOption = isLinkedSelect ? "<option value=''>Link Recovery Strategy (Optional)</option>" : "<option value=''>Select Strategy</option>";
        select.innerHTML = defaultOption;

        strategies.forEach(strategy => {
            // Only allow 'recovery' type for the linked strategy select
            if (isLinkedSelect && strategy.type !== 'recovery') {
                return;
            }
            const option = document.createElement('option');
            option.value = strategy.id;
            option.textContent = strategy.name;
            select.appendChild(option);
        });
    });
}

function displayBots() {
    const activeBots = bots.filter(bot => bot.status === 'running');
    const inactiveBots = bots.filter(bot => bot.status !== 'running');

    function createBotTable(container, botsList, title, showControls = true) {
        if (botsList.length === 0) {
            container.innerHTML = `<p class="text-center text-gray-500 py-4">No ${title.toLowerCase()} found.</p>`;
            return;
        }
        const table = document.createElement('table');
        table.className = 'min-w-full divide-y divide-gray-200';
        table.innerHTML = `
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sport</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bet %</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">P/L</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                ${botsList.map(bot => {
                    const strategy = strategies.find(s => s.id === bot.strategy_id);
                    const strategyName = strategy ? strategy.name : 'Unknown';
                    const profitLoss = (bot.current_balance - bot.starting_balance).toFixed(2);
                    const profitLossClass = profitLoss >= 0 ? 'text-green-600' : 'text-red-600';
                    const statusColor = bot.status === 'running' ? 'bg-blue-500' : 'bg-gray-500';
                    const statusText = bot.status.charAt(0).toUpperCase() + bot.status.slice(1);
                    return `
                        <tr>
                            <td class="px-6 py-4 whitespace-nowrap font-semibold">${bot.name}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${bot.sport}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${strategyName}</td>
                            <td class="px-6 py-4 whitespace-nowrap">$${bot.current_balance.toFixed(2)}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${bot.bet_percentage}%</td>
                            <td class="px-6 py-4 whitespace-nowrap ${profitLossClass}">$${profitLoss}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColor} text-white">${statusText}</span></td>
                            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                <button onclick="window.showBotDetails('${bot.id}')" class="text-indigo-600 hover:text-indigo-900 mx-1">Edit</button>
                                <button onclick="window.showBotHistory('${bot.id}')" class="text-blue-600 hover:text-blue-900 mx-1">History</button>
                                <button onclick="window.showBotLog('${bot.id}')" class="text-gray-600 hover:text-gray-900 mx-1">Log</button>
                                <button onclick="window.toggleBotStatus('${bot.id}', '${bot.status}')" class="text-green-600 hover:text-green-900 mx-1">${bot.status === 'running' ? 'Stop' : 'Start'}</button>
                                <button onclick="window.deleteBot('${bot.id}')" class="text-red-600 hover:text-red-900 ml-1">Delete</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        `;
        container.innerHTML = '';
        container.appendChild(table);
    }

    createBotTable(activeBotsContainer, activeBots, 'Active Bots');
    createBotTable(inactiveBotsContainer, inactiveBots, 'Inactive Bots');
}

function displayStrategies() {
    const container = strategiesContainer;
    if (strategies.length === 0) {
        container.innerHTML = `<p class="text-center text-gray-500 py-4">No strategies found. Add one above!</p>`;
        return;
    }
    const table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-200';
    table.innerHTML = `
        <thead class="bg-gray-50">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Linked Strategy</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                <th class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
            </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
            ${strategies.map(strategy => {
                const linkedStrategy = strategies.find(s => s.id === strategy.linked_strategy_id);
                const linkedStrategyName = linkedStrategy ? linkedStrategy.name : 'None';
                return `
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap font-semibold">${strategy.name}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${strategy.type}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${linkedStrategyName}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${strategy.description || 'N/A'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button onclick="window.showStrategyDetails('${strategy.id}')" class="text-indigo-600 hover:text-indigo-900 mx-1">Edit</button>
                            <button onclick="window.deleteStrategy('${strategy.id}')" class="text-red-600 hover:text-red-900 ml-1">Delete</button>
                        </td>
                    </tr>
                `;
            }).join('')}
        </tbody>
    `;
    container.innerHTML = '';
    container.appendChild(table);
}

// Update overall stats dashboard
function updateOverallStats() {
    const totalProfit = bots.reduce((sum, bot) => sum + (bot.current_balance - bot.starting_balance), 0);
    const totalWagers = bots.reduce((sum, bot) => sum + bot.total_wagers, 0);
    const totalWins = bots.reduce((sum, bot) => sum + bot.total_wins, 0);

    const winRate = totalWagers > 0 ? ((totalWins / totalWagers) * 100).toFixed(2) : '0.00';
    const profitClass = totalProfit >= 0 ? 'text-green-600' : 'text-red-600';
    const sortedBots = [...bots].sort((a, b) => (b.current_balance - b.starting_balance) - (a.current_balance - a.starting_balance));
    const bestBot = sortedBots[0];
    const worstBot = sortedBots[sortedBots.length - 1];

    document.getElementById('total-profit').textContent = `$${totalProfit.toFixed(2)}`;
    document.getElementById('total-profit').className = `text-3xl font-bold ${profitClass}`;
    document.getElementById('total-wagers').textContent = totalWagers;
    document.getElementById('win-rate').textContent = `${winRate}%`;

    if (bestBot) {
        document.getElementById('best-bot-name').textContent = bestBot.name;
        document.getElementById('best-bot-profit').textContent = `$${(bestBot.current_balance - bestBot.starting_balance).toFixed(2)}`;
    }
    if (worstBot) {
        document.getElementById('worst-bot-name').textContent = worstBot.name;
        document.getElementById('worst-bot-profit').textContent = `$${(worstBot.current_balance - worstBot.starting_balance).toFixed(2)}`;
    }
}

// --- MODAL FUNCTIONS ---

window.showBotDetails = function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        console.error('Bot not found:', botId);
        return;
    }
    
    // Populate the modal fields
    document.getElementById('modal-bot-id').value = bot.id;
    document.getElementById('modal-bot-name').textContent = bot.name;
    document.getElementById('modal-name').value = bot.name;
    document.getElementById('modal-balance').value = bot.current_balance;
    document.getElementById('modal-bet-percent').value = bot.bet_percentage;
    document.getElementById('modal-max-bets').value = bot.max_bets_per_week;

    // Populate the strategy dropdown
    const strategySelect = document.getElementById('modal-strategy');
    strategySelect.innerHTML = ''; // Clear previous options
    strategies.forEach(strategy => {
        const option = document.createElement('option');
        option.value = strategy.id;
        option.textContent = strategy.name;
        if (strategy.id === bot.strategy_id) {
            option.selected = true;
        }
        strategySelect.appendChild(option);
    });

    // Populate allowable platforms checkboxes
    const allowablePlatforms = bot.allowable_platforms || ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet']; // Default to all if not set
    const platformCheckboxes = [
        'modal-platform-draftkings',
        'modal-platform-fanduel', 
        'modal-platform-betmgm',
        'modal-platform-caesars',
        'modal-platform-pointsbet'
    ];
    const platformValues = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet'];
    
    platformCheckboxes.forEach((checkboxId, index) => {
        const checkbox = document.getElementById(checkboxId);
        if (checkbox) {
            checkbox.checked = allowablePlatforms.includes(platformValues[index]);
        }
    });

    // Show the modal
    window.showModal('bot-details-modal');
};

window.showStrategyDetails = function(strategyId) {
    const strategy = strategies.find(s => s.id === strategyId);
    if (!strategy) {
        console.error('Strategy not found:', strategyId);
        return;
    }

    // Populate the modal fields
    document.getElementById('strategy-modal-id').value = strategy.id;
    document.getElementById('strategy-modal-name').textContent = strategy.name;
    document.getElementById('strategy-modal-description').value = strategy.description || '';

    const parametersContainer = document.getElementById('strategy-modal-parameters');
    parametersContainer.innerHTML = ''; // Clear previous inputs
    if (strategy.parameters) {
        for (const key in strategy.parameters) {
            const param = strategy.parameters[key];
            const inputGroup = document.createElement('div');
            inputGroup.innerHTML = `
                <label for="param-${key}" class="block text-sm font-medium text-gray-700">${key.replace(/_/g, ' ')}</label>
                <input type="${param.type}" id="param-${key}" name="${key}" value="${param.value}" class="mt-1 block w-full p-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500">
            `;
            parametersContainer.appendChild(inputGroup);
        }
    }

    // Show the modal
    window.showModal('strategy-details-modal');
};

window.showBotHistory = async function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        console.error('Bot not found:', botId);
        return;
    }

    document.getElementById('history-bot-name').textContent = bot.name;
    const tableBody = document.getElementById('history-table-body');
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Loading history...</td></tr>';

    try {
        const q = query(collection(db, `users/${userId}/bets`), where("bot_id", "==", botId), orderBy("timestamp", "desc"), limit(50));
        const querySnapshot = await getDocs(q);

        tableBody.innerHTML = ''; // Clear loading message
        if (querySnapshot.empty) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No bet history found for this bot.</td></tr>';
        } else {
            querySnapshot.forEach(doc => {
                const bet = doc.data();
                const row = `
                    <tr class="hover:bg-gray-50">
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(bet.timestamp.toDate()).toLocaleString()}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${bet.team_bet_on} vs. ${bet.opponent_team}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">$${bet.wager.toFixed(2)}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${bet.odds}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">$${bet.payout.toFixed(2)}</td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${bet.outcome === 'Win' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                ${bet.outcome}
                            </span>
                        </td>
                    </tr>
                `;
                tableBody.innerHTML += row;
            });
        }
    } catch (error) {
        console.error("Error fetching bot history:", error);
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-red-500">Error loading history.</td></tr>';
    }
    
    // Show the modal
    window.showModal('history-modal');
};

window.showBotLog = async function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        console.error('Bot not found:', botId);
        return;
    }
    document.getElementById('log-bot-name').textContent = bot.name;
    const logContent = document.getElementById('bot-log-content');
    logContent.textContent = 'Loading log...';

    try {
        const logDocRef = doc(db, `users/${userId}/bot_logs`, botId);
        const docSnap = await getDoc(logDocRef);

        if (docSnap.exists() && docSnap.data().log) {
            logContent.textContent = docSnap.data().log;
        } else {
            logContent.textContent = 'No log available for this bot.';
        }
    } catch (error) {
        console.error("Error fetching bot log:", error);
        logContent.textContent = 'Failed to load log. Please check the console for details.';
    }

    // Show the modal
    window.showModal('bot-log-modal');
};

// --- DATA MODIFICATION FUNCTIONS ---

window.addBot = async function(botData) {
    showLoading();
    try {
        const botRef = collection(db, `users/${userId}/bots`);
        await addDoc(botRef, {
            ...botData,
            status: 'stopped',
            current_balance: parseFloat(botData.starting_balance),
            total_wagers: 0,
            total_wins: 0,
            profit_loss: 0,
            last_run: null
        });
        showMessage("Bot added successfully!");
    } catch (e) {
        console.error("Error adding bot: ", e);
        showMessage("Failed to add bot. Check the console for details.", true);
    } finally {
        hideLoading();
    }
};

window.editBot = async function(botData) {
    showLoading();
    try {
        const botRef = doc(db, `users/${userId}/bots`, botData.id);
        await updateDoc(botRef, {
            name: botData.name,
            strategy_id: botData.strategy_id,
            bet_percentage: botData.bet_percentage,
            max_bets_per_week: botData.max_bets_per_week
        });
        showMessage("Bot updated successfully!");
    } catch (e) {
        console.error("Error updating bot: ", e);
        showMessage("Failed to update bot.", true);
    } finally {
        hideLoading();
    }
};

window.deleteBot = async function(botId) {
    if (!confirm("Are you sure you want to delete this bot? This action is permanent.")) return;
    showLoading();
    try {
        const botRef = doc(db, `users/${userId}/bots`, botId);
        await deleteDoc(botRef);
        showMessage("Bot deleted successfully!");
    } catch (e) {
        console.error("Error deleting bot: ", e);
        showMessage("Failed to delete bot.", true);
    } finally {
        hideLoading();
    }
};

window.toggleBotStatus = async function(botId, currentStatus) {
    showLoading();
    const newStatus = currentStatus === 'running' ? 'stopped' : 'running';
    try {
        const botRef = doc(db, `users/${userId}/bots`, botId);
        await updateDoc(botRef, {
            status: newStatus
        });
        showMessage(`Bot status changed to ${newStatus}.`);
    } catch (e) {
        console.error("Error toggling bot status:", e);
        showMessage("Failed to change bot status.", true);
    } finally {
        hideLoading();
    }
};

window.addStrategy = async function(strategyData) {
    showLoading();
    try {
        const strategyRef = collection(db, `users/${userId}/strategies`);
        await addDoc(strategyRef, {
            ...strategyData,
            parameters: {}
        });
        showMessage("Strategy added successfully!");
    } catch (e) {
        console.error("Error adding strategy: ", e);
        showMessage("Failed to add strategy.", true);
    } finally {
        hideLoading();
    }
};

window.editStrategy = async function(strategyId, strategyData) {
    showLoading();
    try {
        const strategyRef = doc(db, `users/${userId}/strategies`, strategyId);
        await updateDoc(strategyRef, strategyData);
        showMessage("Strategy updated successfully!");
    } catch (e) {
        console.error("Error updating strategy: ", e);
        showMessage("Failed to update strategy.", true);
    } finally {
        hideLoading();
    }
};

window.deleteStrategy = async function(strategyId) {
    if (!confirm("Are you sure you want to delete this strategy? This will affect any bots using it.")) return;
    showLoading();
    try {
        const strategyRef = doc(db, `users/${userId}/strategies`, strategyId);
        await deleteDoc(strategyRef);
        showMessage("Strategy deleted successfully!");
    } catch (e) {
        console.error("Error deleting strategy: ", e);
        showMessage("Failed to delete strategy.", true);
    } finally {
        hideLoading();
    }
};

window.fetchAndDisplayInvestments = async function() {
    console.warn('fetchAndDisplayInvestments is deprecated. Use loadCachedInvestments or refreshInvestments instead.');
    await window.loadCachedInvestments();
};

window.loadCachedInvestments = async function() {
    const investmentsContainer = document.getElementById('investments-container');
    const noInvestmentsMessage = document.getElementById('no-investments-message');
    const sportTabsContainer = document.getElementById('sport-tabs-container');

    investmentsContainer.innerHTML = '';
    sportTabsContainer.innerHTML = '';
    noInvestmentsMessage.classList.add('hidden');
    showLoading();

    try {
        const response = await fetch(`/api/investments?user_id=${userId}&refresh=false`);
        const data = await response.json();

        if (data.success && data.investments.length > 0) {
            displayInvestments(data.investments);
            updateCacheStatus(data);
        } else {
            noInvestmentsMessage.classList.remove('hidden');
            updateCacheStatus({ cached: false, has_cache: false });
        }
    } catch (e) {
        console.error("Error loading cached investments:", e);
        showMessage("Failed to load investments.", true);
        noInvestmentsMessage.classList.remove('hidden');
        updateCacheStatus({ cached: false, has_cache: false });
    } finally {
        hideLoading();
    }
};

window.refreshInvestments = async function() {
    const refreshButton = document.getElementById('refresh-investments-btn');
    const refreshIcon = document.getElementById('refresh-icon');
    
    // Disable button and show spinning animation
    refreshButton.disabled = true;
    refreshButton.classList.add('opacity-75', 'cursor-not-allowed');
    refreshIcon.classList.add('animate-spin');

    const investmentsContainer = document.getElementById('investments-container');
    const noInvestmentsMessage = document.getElementById('no-investments-message');
    const sportTabsContainer = document.getElementById('sport-tabs-container');

    investmentsContainer.innerHTML = '';
    sportTabsContainer.innerHTML = '';
    noInvestmentsMessage.classList.add('hidden');
    showLoading();

    try {
        const response = await fetch(`/api/investments?user_id=${userId}&refresh=true`);
        const data = await response.json();

        if (data.success && data.investments.length > 0) {
            displayInvestments(data.investments);
            updateCacheStatus(data);
            showMessage(`Refreshed ${data.investments.length} games. Made ${data.api_calls_made} API calls.`);
        } else {
            noInvestmentsMessage.classList.remove('hidden');
            updateCacheStatus({ cached: false, has_cache: false });
            showMessage("No games found. API may be unavailable.", true);
        }
    } catch (e) {
        console.error("Error refreshing investments:", e);
        showMessage("Failed to refresh investments. Check API key and connection.", true);
        noInvestmentsMessage.classList.remove('hidden');
        updateCacheStatus({ cached: false, has_cache: false });
    } finally {
        hideLoading();
        
        // Re-enable button and stop spinning
        refreshButton.disabled = false;
        refreshButton.classList.remove('opacity-75', 'cursor-not-allowed');
        refreshIcon.classList.remove('animate-spin');
    }
};

function displayInvestments(investments) {
    const investmentsContainer = document.getElementById('investments-container');
    const sportTabsContainer = document.getElementById('sport-tabs-container');
    
    const groupedBySport = investments.reduce((acc, investment) => {
        const sport = investment.sport;
        if (!acc[sport]) {
            acc[sport] = [];
        }
        acc[sport].push(investment);
        return acc;
    }, {});

    let firstSport = true;
    for (const sport in groupedBySport) {
        // Create Tab Button
        const tabButton = document.createElement('button');
        tabButton.textContent = sport;
        tabButton.className = `tab-button ${firstSport ? 'active' : ''}`;
        tabButton.setAttribute('data-sport', sport);
        tabButton.onclick = () => window.showSportTab(sport);
        sportTabsContainer.appendChild(tabButton);

        const tabContent = document.createElement('div');
        tabContent.id = `tab-content-${sport}`;
        tabContent.className = `tab-content space-y-4 ${firstSport ? 'active' : ''}`;

        const allTeams = new Set();
        groupedBySport[sport].forEach(inv => {
            const teams = inv.teams.split(' vs ');
            allTeams.add(teams[0]);
            allTeams.add(teams[1]);
        });
        const sortedTeams = Array.from(allTeams).sort();

        // Enhanced Filtering System
        const filterDiv = document.createElement('div');
        filterDiv.className = 'flex flex-wrap items-center gap-4 my-4 p-4 bg-gray-50 rounded-lg';
        
        // Team Filter
        const teamFilterDiv = document.createElement('div');
        teamFilterDiv.className = 'flex items-center space-x-2';
        const teamFilterLabel = document.createElement('label');
        teamFilterLabel.textContent = 'Team:';
        teamFilterLabel.className = 'font-semibold text-gray-700 text-sm';
        const teamFilterSelect = document.createElement('select');
        teamFilterSelect.className = 'block p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm';
        teamFilterSelect.id = `team-filter-${sport}`;
        teamFilterSelect.onchange = (e) => window.filterInvestments(sport);
        
        const allTeamsOption = document.createElement('option');
        allTeamsOption.value = 'all';
        allTeamsOption.textContent = 'All Teams';
        teamFilterSelect.appendChild(allTeamsOption);

        sortedTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team;
            option.textContent = team;
            teamFilterSelect.appendChild(option);
        });

        teamFilterDiv.appendChild(teamFilterLabel);
        teamFilterDiv.appendChild(teamFilterSelect);
        
        // Sportsbook Filter
        const sportsbookFilterDiv = document.createElement('div');
        sportsbookFilterDiv.className = 'flex items-center space-x-2';
        const sportsbookFilterLabel = document.createElement('label');
        sportsbookFilterLabel.textContent = 'Sportsbook:';
        sportsbookFilterLabel.className = 'font-semibold text-gray-700 text-sm';
        const sportsbookFilterSelect = document.createElement('select');
        sportsbookFilterSelect.className = 'block p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm';
        sportsbookFilterSelect.id = `sportsbook-filter-${sport}`;
        sportsbookFilterSelect.onchange = (e) => window.filterInvestments(sport);
        
        // Collect unique sportsbooks
        const allSportsbooks = new Set();
        groupedBySport[sport].forEach(inv => {
            if (inv.bookmakers) {
                inv.bookmakers.forEach(bookmaker => allSportsbooks.add(bookmaker.title));
            }
        });
        
        const allSportsbooksOption = document.createElement('option');
        allSportsbooksOption.value = 'all';
        allSportsbooksOption.textContent = 'All Sportsbooks';
        sportsbookFilterSelect.appendChild(allSportsbooksOption);

        Array.from(allSportsbooks).sort().forEach(sportsbook => {
            const option = document.createElement('option');
            option.value = sportsbook;
            option.textContent = sportsbook;
            sportsbookFilterSelect.appendChild(option);
        });

        sportsbookFilterDiv.appendChild(sportsbookFilterLabel);
        sportsbookFilterDiv.appendChild(sportsbookFilterSelect);

        // Market Type Filter
        const marketFilterDiv = document.createElement('div');
        marketFilterDiv.className = 'flex items-center space-x-2';
        const marketFilterLabel = document.createElement('label');
        marketFilterLabel.textContent = 'Market:';
        marketFilterLabel.className = 'font-semibold text-gray-700 text-sm';
        const marketFilterSelect = document.createElement('select');
        marketFilterSelect.className = 'block p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm';
        marketFilterSelect.id = `market-filter-${sport}`;
        marketFilterSelect.onchange = (e) => window.filterInvestments(sport);
        
        // Collect unique market types
        const allMarkets = new Set();
        groupedBySport[sport].forEach(inv => {
            if (inv.bookmakers) {
                inv.bookmakers.forEach(bookmaker => {
                    bookmaker.markets.forEach(market => {
                        const marketName = market.name || marketNameMapping[market.key] || market.key;
                        allMarkets.add(marketName);
                    });
                });
            }
        });
        
        const allMarketsOption = document.createElement('option');
        allMarketsOption.value = 'all';
        allMarketsOption.textContent = 'All Markets';
        marketFilterSelect.appendChild(allMarketsOption);

        Array.from(allMarkets).sort().forEach(market => {
            const option = document.createElement('option');
            option.value = market;
            option.textContent = market;
            marketFilterSelect.appendChild(option);
        });

        marketFilterDiv.appendChild(marketFilterLabel);
        marketFilterDiv.appendChild(marketFilterSelect);

        // Clear Filters Button
        const clearFiltersBtn = document.createElement('button');
        clearFiltersBtn.className = 'px-3 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 transition duration-200';
        clearFiltersBtn.textContent = 'Clear Filters';
        clearFiltersBtn.onclick = () => window.clearFilters(sport);

        filterDiv.appendChild(teamFilterDiv);
        filterDiv.appendChild(sportsbookFilterDiv);
        filterDiv.appendChild(marketFilterDiv);
        filterDiv.appendChild(clearFiltersBtn);
        tabContent.appendChild(filterDiv);

        // Create Investments List for the sport
        const investmentsList = document.createElement('div');
        investmentsList.className = 'space-y-4';
        investmentsList.id = `investments-list-${sport}`;
        
        groupedBySport[sport].forEach(investment => {
            const investmentCard = createInvestmentCard(investment);
            investmentsList.appendChild(investmentCard);
        });
        tabContent.appendChild(investmentsList);
        investmentsContainer.appendChild(tabContent);
        firstSport = false;
    }
}

function updateCacheStatus(data) {
    const cacheIndicator = document.getElementById('cache-indicator');
    const cacheText = document.getElementById('cache-text');
    
    if (data.cached) {
        cacheIndicator.className = 'w-3 h-3 rounded-full bg-green-500';
        const refreshTime = new Date(data.last_refresh).toLocaleString();
        cacheText.textContent = `Cached data from ${refreshTime}`;
    } else if (data.last_refresh) {
        cacheIndicator.className = 'w-3 h-3 rounded-full bg-blue-500';
        const refreshTime = new Date(data.last_refresh).toLocaleString();
        cacheText.textContent = `Fresh data from ${refreshTime}`;
    } else {
        cacheIndicator.className = 'w-3 h-3 rounded-full bg-gray-400';
        cacheText.textContent = 'No data available';
    }
}

window.showSportTab = function(sport) {
    // Correctly select the button using the data-sport attribute
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.tab-button[data-sport='${sport}']`).classList.add('active');

    // Show the corresponding tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`tab-content-${sport}`).classList.add('active');
};

window.filterInvestments = function(sport) {
    const listContainer = document.getElementById(`investments-list-${sport}`);
    const investmentCards = listContainer.querySelectorAll('.investment-card');
    
    const teamFilter = document.getElementById(`team-filter-${sport}`).value;
    const sportsbookFilter = document.getElementById(`sportsbook-filter-${sport}`).value;
    const marketFilter = document.getElementById(`market-filter-${sport}`).value;
    
    investmentCards.forEach(card => {
        let showCard = true;
        
        // Team filtering
        if (teamFilter !== 'all') {
            const teamsText = card.querySelector('.font-bold').textContent;
            const [team1, team2] = teamsText.split(' vs ');
            if (team1 !== teamFilter && team2 !== teamFilter) {
                showCard = false;
            }
        }
        
        // Sportsbook filtering
        if (showCard && sportsbookFilter !== 'all') {
            const sportsbookHeaders = card.querySelectorAll('h4');
            let hasMatchingSportsbook = false;
            sportsbookHeaders.forEach(header => {
                if (header.textContent.trim() === sportsbookFilter) {
                    hasMatchingSportsbook = true;
                }
            });
            if (!hasMatchingSportsbook) {
                showCard = false;
            }
        }
        
        // Market filtering
        if (showCard && marketFilter !== 'all') {
            const marketHeaders = card.querySelectorAll('h5');
            let hasMatchingMarket = false;
            marketHeaders.forEach(header => {
                if (header.textContent.trim().toLowerCase() === marketFilter.toLowerCase()) {
                    hasMatchingMarket = true;
                }
            });
            if (!hasMatchingMarket) {
                showCard = false;
            }
        }
        
        // Show/hide investment cards based on sportsbook and market filters
        if (showCard && (sportsbookFilter !== 'all' || marketFilter !== 'all')) {
            // Show card but hide non-matching sportsbooks/markets
            const sportsbookDivs = card.querySelectorAll('div[class*="border"]');
            sportsbookDivs.forEach(div => {
                const sportsbookHeader = div.querySelector('h4');
                if (sportsbookHeader) {
                    const shouldShowSportsbook = sportsbookFilter === 'all' || 
                        sportsbookHeader.textContent.trim() === sportsbookFilter;
                    
                    if (shouldShowSportsbook && marketFilter !== 'all') {
                        // Hide non-matching markets within this sportsbook
                        const marketDivs = div.querySelectorAll('div.mb-3');
                        marketDivs.forEach(marketDiv => {
                            const marketHeader = marketDiv.querySelector('h5');
                            if (marketHeader) {
                                const shouldShowMarket = marketHeader.textContent.trim().toLowerCase() === marketFilter.toLowerCase();
                                marketDiv.style.display = shouldShowMarket ? 'block' : 'none';
                            }
                        });
                        div.style.display = 'block';
                    } else if (shouldShowSportsbook) {
                        // Show all markets for this sportsbook
                        const marketDivs = div.querySelectorAll('div.mb-3');
                        marketDivs.forEach(marketDiv => {
                            marketDiv.style.display = 'block';
                        });
                        div.style.display = 'block';
                    } else {
                        div.style.display = 'none';
                    }
                }
            });
        } else if (showCard) {
            // Show all sportsbooks and markets
            const sportsbookDivs = card.querySelectorAll('div[class*="border"]');
            sportsbookDivs.forEach(div => {
                div.style.display = 'block';
                const marketDivs = div.querySelectorAll('div.mb-3');
                marketDivs.forEach(marketDiv => {
                    marketDiv.style.display = 'block';
                });
            });
        }
        
        card.style.display = showCard ? 'block' : 'none';
    });
};

window.clearFilters = function(sport) {
    document.getElementById(`team-filter-${sport}`).value = 'all';
    document.getElementById(`sportsbook-filter-${sport}`).value = 'all';
    document.getElementById(`market-filter-${sport}`).value = 'all';
    window.filterInvestments(sport);
};

// --- AUTHENTICATION FUNCTIONS ---

let currentUser = null;
let isAuthenticated = false;

window.showAuthForm = function(formType) {
    const signinForm = document.getElementById('signin-form');
    const signupForm = document.getElementById('signup-form');
    
    if (formType === 'signin') {
        signinForm.style.display = 'block';
        signupForm.style.display = 'none';
    } else if (formType === 'signup') {
        signinForm.style.display = 'none';
        signupForm.style.display = 'block';
    }
};

function showAccountManagement() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('account-management-section').classList.remove('hidden');
    updateAccountUI();
}

function showAuthSection() {
    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('account-management-section').classList.add('hidden');
}

function updateAccountUI() {
    if (currentUser) {
        document.getElementById('user-email-display').textContent = currentUser.email || 'Demo Mode';
        document.getElementById('profile-email').value = currentUser.email || '';
        document.getElementById('profile-display-name').value = currentUser.displayName || '';
    }
}

async function signInUser(email, password) {
    if (!firebaseAvailable) {
        // Demo mode sign in
        currentUser = { email: 'demo@example.com', displayName: 'Demo User' };
        isAuthenticated = true;
        showAccountManagement();
        showMessage('Signed in successfully (Demo Mode)', false);
        return;
    }

    try {
        showLoading();
        const { signInWithEmailAndPassword } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        currentUser = userCredential.user;
        isAuthenticated = true;
        showAccountManagement();
        showMessage('Signed in successfully!', false);
    } catch (error) {
        console.error('Sign in error:', error);
        showMessage(`Sign in failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

async function signUpUser(email, password, confirmPassword) {
    if (password !== confirmPassword) {
        showMessage('Passwords do not match', true);
        return;
    }

    if (!firebaseAvailable) {
        // Demo mode sign up
        currentUser = { email: email, displayName: 'Demo User' };
        isAuthenticated = true;
        showAccountManagement();
        showMessage('Account created successfully (Demo Mode)', false);
        return;
    }

    try {
        showLoading();
        const { createUserWithEmailAndPassword } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        currentUser = userCredential.user;
        isAuthenticated = true;
        showAccountManagement();
        showMessage('Account created successfully!', false);
    } catch (error) {
        console.error('Sign up error:', error);
        showMessage(`Sign up failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

async function signOutUser() {
    if (!firebaseAvailable) {
        // Demo mode sign out
        currentUser = null;
        isAuthenticated = false;
        showAuthSection();
        showMessage('Signed out successfully', false);
        return;
    }

    try {
        showLoading();
        const { signOut } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
        await signOut(auth);
        currentUser = null;
        isAuthenticated = false;
        showAuthSection();
        showMessage('Signed out successfully', false);
    } catch (error) {
        console.error('Sign out error:', error);
        showMessage(`Sign out failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

async function updateUserProfile(profileData) {
    if (!firebaseAvailable) {
        // Demo mode update
        if (currentUser) {
            currentUser.email = profileData.email;
            currentUser.displayName = profileData.displayName;
            updateAccountUI();
            showMessage('Profile updated successfully (Demo Mode)', false);
        }
        return;
    }

    try {
        showLoading();
        const { updateProfile, updateEmail } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
        
        if (profileData.displayName !== currentUser.displayName) {
            await updateProfile(currentUser, { displayName: profileData.displayName });
        }
        
        if (profileData.email !== currentUser.email) {
            await updateEmail(currentUser, profileData.email);
        }
        
        updateAccountUI();
        showMessage('Profile updated successfully!', false);
    } catch (error) {
        console.error('Profile update error:', error);
        showMessage(`Profile update failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

async function updateUserPassword(currentPassword, newPassword, confirmNewPassword) {
    if (newPassword !== confirmNewPassword) {
        showMessage('New passwords do not match', true);
        return;
    }

    if (!firebaseAvailable) {
        // Demo mode password change
        showMessage('Password changed successfully (Demo Mode)', false);
        return;
    }

    try {
        showLoading();
        const { updatePassword, reauthenticateWithCredential, EmailAuthProvider } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
        
        // Re-authenticate user before password change
        const credential = EmailAuthProvider.credential(currentUser.email, currentPassword);
        await reauthenticateWithCredential(currentUser, credential);
        
        // Update password
        await updatePassword(currentUser, newPassword);
        showMessage('Password updated successfully!', false);
        
        // Clear form
        document.getElementById('password-form').reset();
    } catch (error) {
        console.error('Password update error:', error);
        showMessage(`Password update failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

async function deleteUserAccount() {
    const confirmDelete = confirm('Are you sure you want to delete your account? This action cannot be undone and will remove all your data.');
    
    if (!confirmDelete) return;

    if (!firebaseAvailable) {
        // Demo mode account deletion
        currentUser = null;
        isAuthenticated = false;
        showAuthSection();
        showMessage('Account deleted successfully (Demo Mode)', false);
        return;
    }

    try {
        showLoading();
        
        // Delete user data from Firestore first
        if (db && currentUser) {
            const userDocRef = doc(db, 'users', currentUser.uid);
            await deleteDoc(userDocRef);
        }
        
        // Delete the user account
        await currentUser.delete();
        
        currentUser = null;
        isAuthenticated = false;
        showAuthSection();
        showMessage('Account deleted successfully', false);
    } catch (error) {
        console.error('Account deletion error:', error);
        showMessage(`Account deletion failed: ${error.message}`, true);
    } finally {
        hideLoading();
    }
}

function createInvestmentCard(investment) {
    const card = document.createElement('div');
    card.className = 'investment-card bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
    
    // Format commence time
    const commenceTime = new Date(investment.commence_time);
    const formattedTime = commenceTime.toLocaleString();

    // Generate placed bets HTML
    const placedBetsHtml = investment.placed_bets.length > 0
        ? `
            <div class="mt-4 p-3 bg-green-50 rounded-lg text-green-800 font-semibold text-sm">
                Placed Bets: ${investment.placed_bets.map(bet => `${bet.bet_type}`).join(', ')}
            </div>
        `
        : '';
    
    // Handle both old format (odds) and new format (bookmakers)
    let bookmakers = investment.bookmakers || [];
    
    // If using old format, convert it to new format for backward compatibility
    if (!bookmakers.length && investment.odds) {
        bookmakers = [{
            key: 'demo',
            title: 'Demo Sportsbook',
            markets: [{
                key: 'h2h',
                name: 'Demo Odds',
                outcomes: investment.odds
            }]
        }];
    }
    
    // Sportsbook brand colors mapping
    const sportsbookColors = {
        'DraftKings': { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
        'FanDuel': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
        'BetMGM': { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
        'Caesars': { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
        'PointsBet': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
        'Barstool': { bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-200' },
        'WynnBET': { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' }
    };

    // Market name mapping to handle undefined/missing titles
    const marketNameMapping = {
        'h2h': 'Moneyline',
        'spreads': 'Spreads', 
        'totals': 'Totals',
        'outrights': 'Outrights'
    };

    // Generate bookmakers HTML
    const bookmakersHtml = bookmakers.map(bookmaker => {
        const colors = sportsbookColors[bookmaker.title] || { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
        
        const marketsHtml = bookmaker.markets.map(market => {
            // Fix UNDEFINED market names by using key as fallback
            const marketName = market.name || marketNameMapping[market.key] || market.key || 'UNDEFINED';
            
            const outcomesHtml = market.outcomes.map(outcome => {
                let displayText = outcome.name;
                if (outcome.point !== undefined) {
                    displayText += ` (${outcome.point > 0 ? '+' : ''}${outcome.point})`;
                }
                const priceText = outcome.price > 0 ? `+${outcome.price}` : outcome.price;
                
                return `
                    <div class="text-center p-2 border border-gray-100 rounded">
                        <div class="text-xs font-medium text-gray-600">${displayText}</div>
                        <div class="text-sm font-bold text-gray-900">${priceText}</div>
                    </div>
                `;
            }).join('');
            
            return `
                <div class="mb-3">
                    <h5 class="text-xs font-semibold text-gray-500 uppercase mb-2">${marketName}</h5>
                    <div class="grid grid-cols-2 gap-1">
                        ${outcomesHtml}
                    </div>
                </div>
            `;
        }).join('');
        
        return `
            <div class="border ${colors.border} ${colors.bg} rounded-lg p-3 mb-2">
                <h4 class="text-sm font-semibold ${colors.text} mb-3">${bookmaker.title}</h4>
                ${marketsHtml}
            </div>
        `;
    }).join('');

    card.innerHTML = `
        <div class="mb-4">
            <h3 class="text-lg font-bold text-gray-900">${investment.teams}</h3>
            <p class="text-sm text-gray-600">${formattedTime}</p>
            <p class="text-xs text-gray-500">${investment.sport}</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            ${bookmakersHtml}
        </div>
        ${placedBetsHtml}
    `;
    return card;
}

// --- USER SETTINGS FUNCTIONALITY ---

async function loadUserSettings() {
    try {
        const response = await fetch(`/api/user-settings?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success) {
            userSettings = data.settings;
            updateSettingsUI();
        }
    } catch (e) {
        console.error("Error loading user settings:", e);
        // Use default settings
        userSettings = {
            auto_refresh_on_login: true,
            cache_expiry_minutes: 30
        };
    }
}

async function saveUserSettings(newSettings) {
    try {
        const response = await fetch('/api/user-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                settings: newSettings
            })
        });
        
        const data = await response.json();
        if (data.success) {
            userSettings = { ...userSettings, ...newSettings };
            showMessage('Settings saved successfully!');
            return true;
        } else {
            showMessage('Failed to save settings: ' + data.message, true);
            return false;
        }
    } catch (e) {
        console.error("Error saving user settings:", e);
        showMessage('Failed to save settings.', true);
        return false;
    }
}

function updateSettingsUI() {
    // Update settings form with current values
    document.getElementById('auto-refresh-checkbox').checked = userSettings.auto_refresh_on_login || true;
    document.getElementById('cache-expiry-select').value = userSettings.cache_expiry_minutes || 30;
    
    // Update cache statistics
    updateSettingsStats();
}

async function updateSettingsStats() {
    try {
        const response = await fetch(`/api/investments/stats?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('settings-last-refresh').textContent = 
                data.last_refresh ? new Date(data.last_refresh).toLocaleString() : 'Never';
            document.getElementById('settings-cached-games').textContent = data.total_games || 0;
            document.getElementById('settings-api-saved').textContent = data.api_calls_saved || 0;
        }
    } catch (e) {
        console.error("Error updating settings stats:", e);
    }
}

// --- AUTHENTICATION & INITIAL DATA LOAD ---

async function checkAutoRefresh() {
    if (userSettings.auto_refresh_on_login) {
        // Auto refresh is enabled, check if we're on investments page
        const investmentsPage = document.getElementById('investments-page');
        if (investmentsPage && investmentsPage.style.display === 'block') {
            await window.refreshInvestments();
        }
    }
}


// --- AUTHENTICATION & INITIAL DATA LOAD ---

async function initializeFirebase() {
    // First, try to load Firebase modules
    await initializeFirebaseModules();
    
    if (!firebaseAvailable) {
        console.warn("Firebase modules not available, running in demo-only mode");
        showMessage('App is running in demo mode. No database connection.', false);
        return;
    }

    try {
        // Enable debug logging for Firestore if available
        if (setLogLevel) {
            setLogLevel('Debug');
        }
        
        // Fetch Firebase config from the backend
        const response = await fetch('/api/firebase-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const firebaseConfig = await response.json();

        // IMPORTANT: Check for a valid projectId before initializing Firebase
        if (!firebaseConfig.projectId || firebaseConfig.projectId === "None") {
            console.warn("Firebase initialization skipped: 'projectId' not provided in the configuration.");
            showMessage('App is running in demo mode. No database connection.', false);
            return; // Stop further Firebase-related code execution
        }

        const app = initializeApp(firebaseConfig);
        auth = getAuth(app);
        db = getFirestore(app);

        // Sign in anonymously or with a custom token
        if (initialAuthToken) {
            await signInWithCustomToken(auth, initialAuthToken);
        } else {
            await signInAnonymously(auth);
        }
    } catch (e) {
        console.error("Error during Firebase initialization or sign-in:", e);
        showMessage("Failed to initialize Firebase. Please check your configuration and API key.", true);
    }
}

function startListeners() {
    if (!firebaseAvailable || !auth || !onAuthStateChanged) {
        // In demo mode without Firebase, just set up the UI
        console.log("Running in demo mode, skipping Firebase auth listeners");
        userId = 'demo-user';
        document.getElementById('user-id').textContent = 'Demo Mode';
        
        // Load demo settings
        loadUserSettings();
        hideLoading();
        return;
    }

    onAuthStateChanged(auth, async (user) => {
        if (user) {
            userId = user.uid;
            document.getElementById('user-id').textContent = userId;
            
            // Load user settings first
            await loadUserSettings();
            
            // Then load other data
            fetchBots();
            fetchStrategies();
            
            // Check auto-refresh after everything is loaded
            setTimeout(checkAutoRefresh, 1000);
        } else {
            console.log("No user is signed in.");
            document.getElementById('user-id').textContent = 'Not signed in';
            hideLoading();
        }
    });
}

// --- EVENT LISTENERS ---

document.getElementById('add-bot-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const botData = {
        name: form.name.value,
        starting_balance: parseFloat(form.starting_balance.value),
        bet_percentage: parseFloat(form.bet_percentage.value),
        max_bets_per_week: parseInt(form.max_bets_per_week.value, 10),
        strategy_id: form.strategy_id.value,
        sport: form.sport.value,
        bet_type: form.bet_type.value
    };
    await window.addBot(botData);
    form.reset();
});

document.getElementById('edit-bot-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    
    // Collect selected allowable platforms
    const allowablePlatforms = [];
    const platformCheckboxes = form.querySelectorAll('input[name="allowable_platforms"]:checked');
    platformCheckboxes.forEach(checkbox => {
        allowablePlatforms.push(checkbox.value);
    });
    
    const botData = {
        id: form['modal-bot-id'].value,
        name: form['modal-name'].value,
        strategy_id: form['modal-strategy'].value,
        bet_percentage: parseFloat(form['modal-bet-percent'].value),
        max_bets_per_week: parseInt(form['modal-max-bets'].value, 10),
        allowable_platforms: allowablePlatforms
    };
    await window.editBot(botData);
    window.closeModal('bot-details-modal');
});

document.getElementById('add-strategy-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const strategyData = {
        name: form.name.value,
        type: form.type.value,
        linked_strategy_id: form.linked_strategy_id.value || null
    };
    await window.addStrategy(strategyData);
    form.reset();
});

document.getElementById('edit-strategy-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const strategyId = form['strategy-modal-id'].value;
    const newDescription = form['description'].value;
    const newParameters = {};
    const parameterInputs = document.getElementById('strategy-modal-parameters').querySelectorAll('input');

    parameterInputs.forEach(input => {
        const key = input.name;
        const type = input.type;
        let value = input.value;

        // Convert to number if the original type was number
        if (type === 'number') {
            value = parseFloat(value);
        }

        newParameters[key] = {
            value,
            type,
        };
    });

    await window.editStrategy(strategyId, {
        description: newDescription,
        parameters: newParameters
    });
    window.closeModal('strategy-details-modal');
});

// Settings form event listener
document.getElementById('settings-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    
    const newSettings = {
        auto_refresh_on_login: form['auto_refresh_on_login'].checked,
        cache_expiry_minutes: parseInt(form['cache_expiry_minutes'].value, 10)
    };
    
    const saved = await saveUserSettings(newSettings);
    if (saved) {
        window.closeModal('settings-modal');
    }
});

// Account page event listeners
document.getElementById('signin-form-element').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    await signInUser(form.email.value, form.password.value);
    form.reset();
});

document.getElementById('signup-form-element').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    await signUpUser(form.email.value, form.password.value, form.confirmPassword.value);
    form.reset();
});

document.getElementById('demo-signin-btn').addEventListener('click', async function() {
    currentUser = { email: 'demo@example.com', displayName: 'Demo User' };
    isAuthenticated = true;
    showAccountManagement();
    showMessage('Signed in successfully (Demo Mode)', false);
});

document.getElementById('profile-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    await updateUserProfile({
        email: form.email.value,
        displayName: form.displayName.value
    });
});

document.getElementById('password-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    await updateUserPassword(
        form.currentPassword.value,
        form.newPassword.value,
        form.confirmNewPassword.value
    );
});

document.getElementById('preferences-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    
    const preferences = {
        autoRefresh: form.autoRefresh.checked,
        notifications: form.notifications.checked,
        theme: form.theme.value
    };
    
    // Save preferences (extend existing settings functionality)
    const newSettings = {
        ...userSettings,
        ...preferences
    };
    
    await saveUserSettings(newSettings);
    showMessage('Preferences saved successfully!', false);
});

document.getElementById('logout-btn').addEventListener('click', signOutUser);

document.getElementById('delete-account-btn').addEventListener('click', deleteUserAccount);

// Initialize account page state
function initializeAccountPage() {
    // Check if user is already authenticated (e.g., from previous session)
    if (firebaseAvailable && auth && auth.currentUser) {
        currentUser = auth.currentUser;
        isAuthenticated = true;
        showAccountManagement();
    } else {
        showAuthSection();
    }
}

// Initial load
initializeFirebase().then(() => {
    startListeners();
    initializeAccountPage();
});