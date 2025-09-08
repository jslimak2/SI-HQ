import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";
import { getFirestore, collection, doc, onSnapshot, addDoc, updateDoc, deleteDoc, getDocs, setDoc, getDoc, query, where, Timestamp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";
import { setLogLevel } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";

// Enable debug logging for Firestore
setLogLevel('Debug');

// --- GLOBAL VARIABLES & INITIALIZATION ---
const appId = typeof __app_id !== 'undefined' ? __app_id : '1:945213178297:web:40f6e200fd00148754b668';
const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

// Firestore data collections
let db, auth;
let userId = 'anonymous';
let bots = [];
let strategies = [];

// UI elements
const activeBotsContainer = document.getElementById('active-bots-container');
const inactiveBotsContainer = document.getElementById('inactive-bots-container');
const strategiesContainer = document.getElementById('strategies-container');
const strategySelect = document.getElementById('strategy-select');
const linkedStrategySelect = document.getElementById('linked-strategy-select');
const botDetailsModal = document.getElementById('bot-details-modal');
const strategyDetailsModal = document.getElementById('strategy-details-modal');
const historyModal = document.getElementById('history-modal');
const botLogModal = document.getElementById('bot-log-modal');

// --- FIREBASE SETUP & AUTHENTICATION ---
window.onload = async function() {
    try {
        // Fetch Firebase config from the backend
        const response = await fetch('/api/firebase-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const firebaseConfig = await response.json();

        // IMPORTANT: Check for a valid projectId before initializing Firebase
        if (!firebaseConfig.projectId || firebaseConfig.projectId === "None") {
            console.warn("Firebase initialization skipped: 'projectId' not provided in the configuration.");
            showMessage('App is running in demo mode. No database connection.', 'error');
            return; // Stop further Firebase-related code execution
        }

        // Initialize Firebase with the fetched config
        const app = initializeApp(firebaseConfig); 
        db = getFirestore(app);
        auth = getAuth(app);

        // Continue with authentication logic
        onAuthStateChanged(auth, async (user) => {
            if (user) {
                userId = user.uid;
                document.getElementById('user-id').textContent = userId;
                setupFirestoreListeners();
                // Set initial page view
                showPage('dashboard-page');

            } else {
                // Attempt to sign in with the provided custom token
                if (initialAuthToken) {
                    await signInWithCustomToken(auth, initialAuthToken);
                } else {
                    // If no token is available, sign in anonymously as a fallback
                    await signInAnonymously(auth);
                }
            }
        });
    } catch (error) {
        console.error("Firebase initialization or authentication failed:", error);
        showMessage('Failed to initialize the app. Check the console.', 'error');
    }
};


// --- FIREBASE LISTENERS ---
function setupFirestoreListeners() {
    // Listen for changes to the strategies collection
    const strategiesRef = collection(db, `artifacts/${appId}/users/${userId}/strategies`);
    onSnapshot(strategiesRef, (snapshot) => {
        strategies = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        renderStrategies();
        renderBotForms();
        console.log("Strategies updated:", strategies);
    }, (error) => {
        console.error("Error fetching strategies:", error);
        showMessage("Failed to load strategies.", 'error');
    });

    // Listen for changes to the bots collection
    const botsRef = collection(db, `artifacts/${appId}/users/${userId}/bots`);
    onSnapshot(botsRef, (snapshot) => {
        bots = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        renderBots();
        console.log("Bots updated:", bots);
    }, (error) => {
        console.error("Error fetching bots:", error);
        showMessage("Failed to load bots.", 'error');
    });
}

window.fetchAndDisplayInvestments = async function() {
    const investmentsList = document.getElementById('investments-list');
    const noInvestmentsMessage = document.getElementById('no-investments-message');
    investmentsList.innerHTML = '';
    noInvestmentsMessage.style.display = 'block';

    try {
        const response = await fetch('/api/available-investments');
        const data = await response.json();

        if (data.success && data.investments.length > 0) {
            noInvestmentsMessage.style.display = 'none';
            data.investments.forEach(game => {
                const gameCard = document.createElement('div');
                gameCard.className = 'bg-gray-100 p-4 rounded-lg shadow-md';
                
                let betsHtml = '';
                if (game.placed_bets && game.placed_bets.length > 0) {
                    betsHtml = `
                        <h4 class="font-semibold text-sm mt-2">Placed Bets:</h4>
                        <ul class="list-disc list-inside text-xs">
                            ${game.placed_bets.map(bet => `<li>Bet on ${bet.teams} by Bot ${bet.wager} (Outcome: ${bet.outcome})</li>`).join('')}
                        </ul>
                    `;
                }

                gameCard.innerHTML = `
                    <h3 class="font-bold text-lg">${game.teams}</h3>
                    <p class="text-gray-600 text-sm">Sport: ${game.sport}</p>
                    <p class="text-gray-600 text-sm">Time: ${new Date(game.commence_time).toLocaleString()}</p>
                    <div class="mt-2">
                        <p class="font-semibold text-sm">Odds:</p>
                        <ul class="flex space-x-4">
                            ${game.odds.map(outcome => `
                                <li class="bg-indigo-500 text-white px-3 py-1 rounded-full text-xs">
                                    ${outcome.name}: ${outcome.price}
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                    ${betsHtml}
                `;
                investmentsList.appendChild(gameCard);
            });
        } else {
            noInvestmentsMessage.textContent = data.message || 'No upcoming games found.';
        }
    } catch (error) {
        console.error("Error fetching available investments:", error);
        noInvestmentsMessage.textContent = 'Failed to load investments. Check console for details.';
    }
}

// --- RENDERING FUNCTIONS ---
function renderStrategies() {
    const container = document.getElementById('strategies-container');
    if (strategies.length === 0) {
        container.innerHTML = `<p class="text-center text-gray-500 mt-4">No strategies found. Add a new one to get started!</p>`;
        return;
    }

    const tableHtml = `
        <div class="overflow-x-auto rounded-lg shadow-sm">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recovery Strategy</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    ${strategies.map(s => {
                        const linkedStrategy = strategies.find(ls => ls.id === s.linked_strategy_id);
                        return `
                            <tr id="strategy-row-${s.id}" class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">${s.name}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${s.type}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${linkedStrategy ? linkedStrategy.name : 'None'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${s.description || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <button onclick="window.showStrategyDetails('${s.id}')" class="text-indigo-600 hover:text-indigo-900 transition duration-300 mr-2">View Details</button>
                                    <button onclick="window.deleteStrategy('${s.id}')" class="text-red-600 hover:text-red-900 transition duration-300">Delete</button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
    container.innerHTML = tableHtml;
}

function renderBotForms() {
    const normalStrategies = strategies.filter(s => s.type === 'normal');
    const recoveryStrategies = strategies.filter(s => s.type === 'recovery');
    
    // Clear and populate strategy select for add bot form
    strategySelect.innerHTML = '<option value="">Select Strategy</option>';
    normalStrategies.forEach(s => {
        const option = document.createElement('option');
        option.value = s.id;
        option.textContent = s.name;
        strategySelect.appendChild(option);
    });

    // Clear and populate linked strategy select for add strategy form
    linkedStrategySelect.innerHTML = '<option value="">Link Recovery Strategy (Optional)</option>';
    recoveryStrategies.forEach(s => {
        const option = document.createElement('option');
        option.value = s.id;
        option.textContent = s.name;
        linkedStrategySelect.appendChild(option);
    });
}

function renderBots() {
    const activeBots = bots.filter(b => b.status === 'Active');
    const inactiveBots = bots.filter(b => b.status !== 'Active');
    
    // Render Active Bots Table
    let activeBotsHtml = `<p class="text-center text-gray-500 mt-4">No bots are currently active.</p>`;
    if (activeBots.length > 0) {
        activeBotsHtml = `
        <div class="overflow-x-auto rounded-lg shadow-sm">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sport</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Max Bets / Week</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">W/L</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last 10</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recovery Strategy</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    ${activeBots.map(b => {
                        const strategy = strategies.find(s => s.id === b.strategy_id);
                        const recoveryStrategy = strategies.find(s => s.id === (strategy ? strategy.linked_strategy_id : null));
                        const last10 = (b.bet_history || []).slice(-10).map(bet => {
                            const outcomeClass = bet.outcome === 'W' ? 'win-char' : 'loss-char';
                            return `<span class="${outcomeClass}">${bet.outcome}</span>`;
                        }).join('');

                        const recoveryButtonText = b.is_recovery_active ? 'Deactivate Recovery' : 'Activate Recovery';
                        const recoveryButtonColor = b.is_recovery_active ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600';
                        const recoveryButtonDisabled = !recoveryStrategy;
                        const recoveryButtonClasses = `p-2 text-white font-semibold rounded-lg transition duration-300 text-xs ${recoveryButtonColor} ${recoveryButtonDisabled ? 'opacity-50 cursor-not-allowed' : ''}`;

                        return `
                            <tr id="bot-row-${b.id}" class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">${b.name}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${strategy ? strategy.name : 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.sport || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.bet_type || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.current_balance.toFixed(2)}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.max_bets_per_week || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.career_wins || 0}/${b.career_losses || 0}</td>
                                <td class="px-6 py-4 whitespace-nowrap font-mono">${last10}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <button onclick="window.toggleRecoveryStrategy('${b.id}')" class="${recoveryButtonClasses}" ${recoveryButtonDisabled ? 'disabled' : ''}>${recoveryButtonText}</button>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">${b.status}</span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4 flex items-center justify-end">
                                    <button onclick="window.toggleBotStatus('${b.id}')" class="text-red-600 hover:text-red-900 transition duration-300">Deactivate</button>
                                    <button onclick="window.showHistoryModal('${b.id}')" class="p-2 bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg hover:bg-gray-300 transition duration-300">View History</button>
                                    <button onclick="window.showLogModal('${b.id}')" class="p-2 bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg hover:bg-gray-300 transition duration-300">View Log</button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
        `;
    }
    activeBotsContainer.innerHTML = activeBotsHtml;

    // Render Inactive Bots Table
    let inactiveBotsHtml = `<p class="text-center text-gray-500 mt-4">No inactive bots found. Add a new bot to get started!</p>`;
    if (inactiveBots.length > 0) {
        inactiveBotsHtml = `
        <div class="overflow-x-auto rounded-lg shadow-sm">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sport</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Max Bets / Week</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">W/L</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last 10</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recovery Strategy</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    ${inactiveBots.map(b => {
                        const strategy = strategies.find(s => s.id === b.strategy_id);
                        const recoveryStrategy = strategies.find(s => s.id === (strategy ? strategy.linked_strategy_id : null));
                        const last10 = (b.bet_history || []).slice(-10).map(bet => {
                            const outcomeClass = bet.outcome === 'W' ? 'win-char' : 'loss-char';
                            return `<span class="${outcomeClass}">${bet.outcome}</span>`;
                        }).join('');

                        const recoveryButtonText = b.is_recovery_active ? 'Deactivate Recovery' : 'Activate Recovery';
                        const recoveryButtonColor = b.is_recovery_active ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600';
                        const recoveryButtonDisabled = !recoveryStrategy;
                        const recoveryButtonClasses = `p-2 text-white font-semibold rounded-lg transition duration-300 text-xs ${recoveryButtonColor} ${recoveryButtonDisabled ? 'opacity-50 cursor-not-allowed' : ''}`;

                        return `
                            <tr id="bot-row-${b.id}" class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">${b.name}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${strategy ? strategy.name : 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.sport || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.bet_type || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.current_balance.toFixed(2)}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.max_bets_per_week || 'N/A'}</td>
                                <td class="px-6 py-4 whitespace-nowrap">${b.career_wins || 0}/${b.career_losses || 0}</td>
                                <td class="px-6 py-4 whitespace-nowrap font-mono">${last10}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <button onclick="window.toggleRecoveryStrategy('${b.id}')" class="${recoveryButtonClasses}" ${recoveryButtonDisabled ? 'disabled' : ''}>${recoveryButtonText}</button>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">${b.status}</span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4">
                                    <button onclick="window.toggleBotStatus('${b.id}')" class="text-green-600 hover:text-green-900 transition duration-300">Activate</button>
                                    <button onclick="window.deleteBot('${b.id}')" class="text-red-600 hover:text-red-900 transition duration-300">Delete</button>
                                    <button onclick="window.showHistoryModal('${b.id}')" class="p-2 bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg hover:bg-gray-300 transition duration-300">View History</button>
                                    <button onclick="window.showLogModal('${b.id}')" class="p-2 bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg hover:bg-gray-300 transition duration-300">View Log</button>
                                    <button onclick="window.showBotDetails('${b.id}')" class="p-2 bg-gray-200 text-gray-800 text-xs font-semibold rounded-lg hover:bg-gray-300 transition duration-300">View Details</button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
        `;
    }
    inactiveBotsContainer.innerHTML = inactiveBotsHtml;
}

// --- UI FUNCTIONS ---
// Expose functions to the global scope
window.showMessage = function(message, type) {
    const msgBox = document.getElementById('message-box');
    msgBox.textContent = message;
    msgBox.className = `message-box visible ${type}`;
    setTimeout(() => {
        msgBox.className = `message-box ${type}`;
    }, 3000);
}

window.closeModal = function(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showLoading() {
    document.getElementById('loading-spinner').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-spinner').classList.add('hidden');
}

window.showBotDetails = function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        console.error('Bot not found for ID:', botId);
        showMessage('Could not find bot details.', 'error');
        return;
    }

    try {
        document.getElementById('modal-bot-id').value = bot.id;
        document.getElementById('modal-bot-name').textContent = bot.name;
        document.getElementById('modal-name').value = bot.name;
        document.getElementById('modal-balance').value = bot.current_balance.toFixed(2);
        document.getElementById('modal-bet-percent').value = bot.bet_percentage;
        document.getElementById('modal-max-bets').value = bot.max_bets_per_week || '';
        
        // Populate strategy dropdown
        const modalStrategySelect = document.getElementById('modal-strategy');
        modalStrategySelect.innerHTML = '';
        strategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.id;
            option.textContent = strategy.name;
            if (strategy.id === bot.strategy_id) {
                option.selected = true;
            }
            modalStrategySelect.appendChild(option);
        });

        botDetailsModal.style.display = 'flex';
    } catch (error) {
        console.error('Error in showBotDetails:', error);
        showMessage('An error occurred while opening the edit modal.', 'error');
    }
}

window.showStrategyDetails = function(strategyId) {
    const strategy = strategies.find(s => s.id === strategyId);
    if (!strategy) {
        console.error('Strategy not found for ID:', strategyId);
        showMessage('Could not find strategy details.', 'error');
        return;
    }

    try {
        document.getElementById('strategy-modal-id').value = strategy.id;
        document.getElementById('strategy-modal-name').textContent = strategy.name;
        document.getElementById('strategy-modal-description').value = strategy.description || '';

        const parametersContainer = document.getElementById('strategy-modal-parameters');
        parametersContainer.innerHTML = '';

        // Dynamically create form inputs for each parameter
        if (strategy.parameters) {
            for (const key in strategy.parameters) {
                const param = strategy.parameters[key];
                const div = document.createElement('div');
                div.className = 'flex flex-col';
                
                const label = document.createElement('label');
                label.className = 'text-sm font-medium text-gray-700 capitalize';
                label.textContent = key.replace(/_/g, ' ');

                const input = document.createElement('input');
                input.type = param.type;
                input.name = key;
                input.value = param.value;
                input.step = param.type === 'number' ? 'any' : null;
                input.className = 'mt-1 block w-full p-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500';
                
                div.appendChild(label);
                div.appendChild(input);
                parametersContainer.appendChild(div);
            }
        } else {
            parametersContainer.innerHTML = '<p class="text-gray-500">No configurable parameters for this strategy.</p>';
        }

        strategyDetailsModal.style.display = 'flex';
    } catch (error) {
        console.error('Error in showStrategyDetails:', error);
        showMessage('An error occurred while opening the strategy details modal.', 'error');
    }
}

window.showHistoryModal = function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        console.error('Bot not found for ID:', botId);
        showMessage('Could not display history. Bot not found.', 'error');
        return;
    }
    
    try {
        document.getElementById('history-bot-name').textContent = bot.name;
        const historyBody = document.getElementById('history-table-body');
        historyBody.innerHTML = '';
        
        if (!bot.bet_history || bot.bet_history.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="6" class="text-center text-gray-500 py-4">No bet history available.</td></tr>';
        } else {
            bot.bet_history.forEach((bet) => {
                const row = document.createElement('tr');
                const outcomeClass = bet.outcome === 'W' ? 'win' : 'loss';
                const payoutValue = bet.payout.toFixed(2);
                const payoutClass = bet.payout >= 0 ? 'profit' : 'loss';
                
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm">${bet.timestamp.toDate().toLocaleString()}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">${bet.teams}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">${bet.wager.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">${bet.odds}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm"><span class="${payoutClass}">${payoutValue}</span></td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm"><span class="${outcomeClass}">${bet.outcome}</span></td>
                `;
                historyBody.appendChild(row);
            });
        }
        historyModal.style.display = 'flex';
    } catch (error) {
        console.error('Error in showHistoryModal:', error);
        showMessage('An error occurred while displaying history. Check console for details.', 'error');
    }
}

window.showLogModal = function(botId) {
    const bot = bots.find(b => b.id === botId);
    if (!bot) {
        showMessage('Could not find bot log.', 'error');
        return;
    }

    document.getElementById('log-bot-name').textContent = bot.name;
    const logContent = document.getElementById('bot-log-content');
    
    if (!bot.log_history || bot.log_history.length === 0) {
        logContent.textContent = 'No log entries found for this bot.';
    } else {
        logContent.textContent = bot.log_history
            .map(entry => `[${entry.timestamp.toDate().toLocaleString()}] ${entry.message}`)
            .join('\n');
    }
    botLogModal.style.display = 'flex';
}

// --- FIREBASE CRUD OPERATIONS ---
async function logBotAction(botId, message) {
    try {
        const botRef = doc(db, `artifacts/${appId}/users/${userId}/bots`, botId);
        const logEntry = {
            message: message,
            timestamp: Timestamp.now()
        };
        await updateDoc(botRef, {
            log_history: [
                ...(bots.find(b => b.id === botId)?.log_history || []),
                logEntry
            ]
        });
    } catch (error) {
    }
}

window.addBot = async function(botData) {
    showLoading();
    try {
        const botRef = await addDoc(collection(db, `artifacts/${appId}/users/${userId}/bots`), {
            ...botData,
            status: 'Inactive',
            is_recovery_active: false,
            career_wins: 0,
            career_losses: 0,
            current_win_streak: 0,
            current_loss_streak: 0,
            bet_history: [],
            log_history: []
        });
        await logBotAction(botRef.id, `Bot initialized and created.`);
        showMessage('Bot added successfully!', 'success');
    } catch (error) {
        console.error("Error adding bot:", error);
        showMessage('Failed to add bot.', 'error');
    } finally {
        hideLoading();
    }
}

window.editBot = async function(botData) {
    showLoading();
    try {
        const botRef = doc(db, `artifacts/${appId}/users/${userId}/bots`, botData.id);
        await updateDoc(botRef, botData);
        showMessage('Bot updated successfully!', 'success');
    } catch (error) {
        console.error("Error updating bot:", error);
        showMessage('Failed to update bot.', 'error');
    } finally {
        hideLoading();
    }
}

window.editStrategy = async function(strategyId, newData) {
    showLoading();
    try {
        const strategyRef = doc(db, `artifacts/${appId}/users/${userId}/strategies`, strategyId);
        await updateDoc(strategyRef, newData);
        showMessage('Strategy updated successfully!', 'success');
    } catch (error) {
        console.error("Error updating strategy:", error);
        showMessage('Failed to update strategy.', 'error');
    } finally {
        hideLoading();
    }
}


window.deleteBot = async function(botId) {
    showLoading();
    try {
        const botRef = doc(db, `artifacts/${appId}/users/${userId}/bots`, botId);
        await deleteDoc(botRef);
        showMessage('Bot deleted successfully!', 'success');
    } catch (error) {
        console.error("Error deleting bot:", error);
        showMessage('Failed to delete bot.', 'error');
    } finally {
        hideLoading();
    }
}

window.addStrategy = async function(strategyData) {
    showLoading();
    try {
        // Add default description and parameters for new strategies
        const defaultParameters = {
            min_odds: { value: 1.5, type: 'number' },
            max_odds: { value: 3.0, type: 'number' },
            bet_size_multiplier: { value: 1, type: 'number' },
        };
        const defaultDescription = `A standard betting strategy that places bets based on odds within a specified range. It can be configured with a bet size multiplier.`;

        const dataWithDefaults = {
            ...strategyData,
            description: defaultDescription,
            parameters: defaultParameters,
        };
        await addDoc(collection(db, `artifacts/${appId}/users/${userId}/strategies`), dataWithDefaults);
        showMessage('Strategy added successfully!', 'success');
    } catch (error) {
        console.error("Error adding strategy:", error);
        showMessage('Failed to add strategy.', 'error');
    } finally {
        hideLoading();
    }
}

window.deleteStrategy = async function(strategyId) {
    showLoading();
    try {
        const strategyRef = doc(db, `artifacts/${appId}/users/${userId}/strategies`, strategyId);
        await deleteDoc(strategyRef);
        showMessage('Strategy deleted successfully!', 'success');
    } catch (error) {
        console.error("Error deleting strategy:", error);
        showMessage('Failed to delete strategy.', 'error');
    } finally {
        hideLoading();
    }
}

window.toggleBotStatus = async function(botId) {
    showLoading();
    try {
        const botRef = doc(db, `artifacts/${appId}/users/${userId}/bots`, botId);
        const botDoc = await getDoc(botRef);
        if (botDoc.exists()) {
            const currentStatus = botDoc.data().status;
            const newStatus = currentStatus === 'Active' ? 'Inactive' : 'Active';
            await updateDoc(botRef, { status: newStatus });
            await logBotAction(botId, `Bot status changed from ${currentStatus} to ${newStatus}.`);
            showMessage(`Bot status changed to ${newStatus}!`, 'success');
        } else {
            showMessage('Bot not found.', 'error');
        }
    } catch (error) {
        console.error("Error toggling bot status:", error);
        showMessage('Failed to toggle bot status.', 'error');
    } finally {
        hideLoading();
    }
}

window.toggleRecoveryStrategy = async function(botId) {
    showLoading();
    try {
        const botRef = doc(db, `artifacts/${appId}/users/${userId}/bots`, botId);
        const botDoc = await getDoc(botRef);
        if (botDoc.exists()) {
            const currentBot = botDoc.data();
            const newRecoveryState = !currentBot.is_recovery_active;
            await updateDoc(botRef, { is_recovery_active: newRecoveryState });
            await logBotAction(botId, `Recovery strategy ${newRecoveryState ? 'activated' : 'deactivated'}.`);
            showMessage(`Recovery strategy ${newRecoveryState ? 'activated' : 'deactivated'}.`, 'success');
        } else {
            showMessage('Bot not found.', 'error');
        }
    } catch (error) {
        console.error("Error toggling recovery strategy:", error);
        showMessage('Failed to toggle recovery strategy.', 'error');
    } finally {
        hideLoading();
    }
}

// --- FORM EVENT LISTENERS ---
document.getElementById('add-bot-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const botData = {
        name: form.name.value,
        starting_balance: parseFloat(form.starting_balance.value),
        current_balance: parseFloat(form.starting_balance.value),
        bet_percentage: parseFloat(form.bet_percentage.value),
        max_bets_per_week: parseInt(form.max_bets_per_week.value, 10),
        strategy_id: form.strategy_id.value,
        sport: form.sport.value,
        bet_type: form.bet_type.value,
    };
    await window.addBot(botData);
    form.reset();
});

document.getElementById('edit-bot-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const botData = {
        id: form['modal-bot-id'].value,
        name: form['modal-name'].value,
        strategy_id: form['modal-strategy'].value,
        bet_percentage: parseFloat(form['modal-bet-percent'].value),
        max_bets_per_week: parseInt(form['modal-max-bets'].value, 10)
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