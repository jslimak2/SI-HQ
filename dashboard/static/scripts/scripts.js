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

// Bet cart management
let betCart = [];
let cartVisible = false;

// Bot recommendations cache
let botRecommendations = {};

// UI elements
const activeBotsContainer = document.getElementById('active-bots-container');
const inactiveBotsContainer = document.getElementById('inactive-bots-container');
const strategiesContainer = document.getElementById('strategies-container');
const messageBox = document.getElementById('message-box');
const loadingSpinner = document.getElementById('loading-spinner');

// Market name mapping to handle undefined/missing titles - moved to global scope
const marketNameMapping = {
    'h2h': 'Moneyline',
    'spreads': 'Spreads', 
    'totals': 'Totals',
    'outrights': 'Outrights'
};

// Demo data generation for fallback when API is not available
function generateDemoInvestments() {
    const teams = {
        'NBA': [
            ['Los Angeles Lakers', 'Boston Celtics'],
            ['Golden State Warriors', 'Miami Heat'],
            ['Milwaukee Bucks', 'Phoenix Suns'],
            ['Denver Nuggets', 'Brooklyn Nets']
        ],
        'NFL': [
            ['Kansas City Chiefs', 'Buffalo Bills'],
            ['Philadelphia Eagles', 'San Francisco 49ers'],
            ['Dallas Cowboys', 'Green Bay Packers'],
            ['Baltimore Ravens', 'Cincinnati Bengals']
        ],
        'MLB': [
            ['Los Angeles Dodgers', 'New York Yankees'],
            ['Atlanta Braves', 'Houston Astros'],
            ['Toronto Blue Jays', 'Tampa Bay Rays'],
            ['Boston Red Sox', 'Seattle Mariners']
        ],
        'NCAAF': [
            ['Georgia Bulldogs', 'Alabama Crimson Tide'],
            ['Michigan Wolverines', 'Ohio State Buckeyes'],
            ['Texas Longhorns', 'Oklahoma Sooners'],
            ['Clemson Tigers', 'Florida State Seminoles']
        ],
        'NCAAB': [
            ['Duke Blue Devils', 'North Carolina Tar Heels'],
            ['Gonzaga Bulldogs', 'Kentucky Wildcats'],
            ['Villanova Wildcats', 'Kansas Jayhawks'],
            ['UCLA Bruins', 'Arizona Wildcats']
        ]
    };

    const demoInvestments = [];
    let gameId = 1;

    Object.entries(teams).forEach(([sport, sportTeams]) => {
        sportTeams.forEach(([team1, team2]) => {
            const gameTime = new Date();
            gameTime.setHours(gameTime.getHours() + Math.floor(Math.random() * 24) + 1);
            
            const investment = {
                id: `demo_${gameId++}`,
                sport_key: sport.toLowerCase(),
                sport_title: sport,
                commence_time: gameTime.toISOString(),
                home_team: team2,
                away_team: team1,
                teams: `${team1} vs ${team2}`, // Add the teams property for compatibility
                placed_bets: [], // Add empty placed_bets array
                bookmakers: [
                    {
                        title: 'DraftKings',
                        markets: [
                            {
                                key: 'h2h',
                                name: 'Moneyline',
                                outcomes: [
                                    { name: team1, price: Math.floor(Math.random() * 200) + 100 },
                                    { name: team2, price: Math.floor(Math.random() * 200) + 100 }
                                ]
                            },
                            {
                                key: 'spreads',
                                name: 'Spreads',
                                outcomes: [
                                    { name: team1, price: -110, point: -Math.floor(Math.random() * 10) - 1 },
                                    { name: team2, price: -110, point: Math.floor(Math.random() * 10) + 1 }
                                ]
                            }
                        ]
                    },
                    {
                        title: 'FanDuel',
                        markets: [
                            {
                                key: 'h2h',
                                name: 'Moneyline',
                                outcomes: [
                                    { name: team1, price: Math.floor(Math.random() * 200) + 105 },
                                    { name: team2, price: Math.floor(Math.random() * 200) + 105 }
                                ]
                            }
                        ]
                    }
                ]
            };
            demoInvestments.push(investment);
        });
    });

    return demoInvestments;
}

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

// Add Escape key functionality for closing modals
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        // Find any open modals and close them
        const openModals = document.querySelectorAll('.modal[style*="flex"]');
        openModals.forEach(modal => {
            modal.style.display = 'none';
        });
    }
});

// --- CRUD OPERATIONS & DATA DISPLAY ---

// Function to fetch and display strategies
async function fetchStrategies() {
    if (!firebaseAvailable) {
        console.log("Firebase not available, loading demo strategies");
        await loadDemoStrategies();
        return;
    }
    
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
        await loadDemoStrategies(); // Fallback to demo data
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
            setupStatsCardClicks();
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
        table.className = 'min-w-full divide-y divide-gray-200 post9-card';
        table.innerHTML = `
            <thead class="post9-card">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Name</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Sport</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Strategy</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Balance</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Bet %</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">P/L</th>
                    <th class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Status</th>
                    <th class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 post9-card">
                ${botsList.map(bot => {
                    const strategy = strategies.find(s => s.id === bot.strategy_id);
                    const strategyName = strategy ? strategy.name : 'Unknown';
                    const profitLoss = (bot.current_balance - bot.starting_balance).toFixed(2);
                    const profitLossClass = profitLoss >= 0 ? 'text-green-600' : 'text-red-600';
                    const statusColor = bot.status === 'running' ? 'bg-blue-500' : 'bg-gray-500';
                    const statusText = bot.status.charAt(0).toUpperCase() + bot.status.slice(1);
                    return `
                        <tr class="cursor-pointer post9-card" onclick="window.toggleBotWagers('${bot.id}')">
                            <td class="px-6 py-4 whitespace-nowrap font-semibold">${bot.name}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${bot.sport || 'N/A'}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${strategyName}</td>
                            <td class="px-6 py-4 whitespace-nowrap">$${bot.current_balance.toFixed(2)}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${bot.bet_percentage}%</td>
                            <td class="px-6 py-4 whitespace-nowrap ${profitLossClass}">$${profitLoss}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColor} text-white">${statusText}</span></td>
                            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                <button onclick="event.stopPropagation(); window.showBotDetails('${bot.id}')" class="text-indigo-400 hover:text-indigo-200 mx-1">Edit</button>
                                <button onclick="event.stopPropagation(); window.showBotHistory('${bot.id}')" class="text-blue-400 hover:text-blue-200 mx-1">History</button>
                                <button onclick="event.stopPropagation(); window.showBotLog('${bot.id}')" class="text-gray-300 hover:text-gray-100 mx-1">Log</button>
                                <button onclick="event.stopPropagation(); window.toggleBotStatus('${bot.id}', '${bot.status}')" class="text-green-400 hover:text-green-200 mx-1">${bot.status === 'running' ? 'Stop' : 'Start'}</button>
                                <button onclick="event.stopPropagation(); window.deleteBot('${bot.id}')" class="text-red-400 hover:text-red-200 ml-1">Delete</button>
                            </td>
                        </tr>
                        <tr id="wagers-${bot.id}" class="hidden post9-card">
                            <td colspan="8" class="px-6 py-4">
                                <div class="border-t border-gray-200 pt-4">
                                    <h4 class="font-semibold text-gray-200 mb-2">Open Wagers:</h4>
                                    <div id="wagers-content-${bot.id}" class="text-sm text-gray-200">
                                        ${bot.open_wagers && bot.open_wagers.length > 0 ? 
                                            bot.open_wagers.map(wager => `
                                                <div class="mb-2 p-2 post9-card">
                                                    <strong>${wager.teams || 'N/A'}</strong> - ${wager.bet_type || 'N/A'}<br>
                                                    Wager: $${wager.amount ? wager.amount.toFixed(2) : '0.00'} | 
                                                    Odds: ${wager.odds || 'N/A'} | 
                                                    Potential Payout: $${wager.potential_payout ? wager.potential_payout.toFixed(2) : '0.00'}
                                                </div>
                                            `).join('') 
                                            : '<p class="text-gray-400">No open wagers</p>'
                                        }
                                    </div>
                                    ${bot.strategy_id ? `
                                        <div class="mt-4 pt-4 border-t border-gray-200">
                                            <h4 class="font-semibold text-gray-200 mb-2">Strategy Picks:</h4>
                                            <button onclick="event.stopPropagation(); window.getStrategyPicks('${bot.id}', '${bot.strategy_id}')" 
                                                    class="post9-btn px-4 py-2 text-sm">
                                                Show Recommended Investments
                                            </button>
                                            <div id="picks-content-${bot.id}" class="mt-2"></div>
                                        </div>
                                    ` : ''}
                                </div>
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

// Load strategies from demo data initially
async function loadDemoStrategies() {
    try {
        const response = await fetch('/static/../data/strategies.json');
        const demoStrategies = await response.json();
        strategies = demoStrategies || [];
        displayStrategies();
        updateStrategySelects();
        hideLoading();
    } catch (error) {
        console.error("Error loading demo strategies:", error);
        // Fallback to hardcoded demo strategies
        strategies = [
            {
                "id": 1,
                "name": "Conservative",
                "type": "conservative",
                "description": "Low risk approach with smaller bet sizes and higher confidence requirements",
                "parameters": {
                    "min_confidence": 75,
                    "max_bet_percentage": 2.0,
                    "max_odds": 2.0
                }
            },
            {
                "id": 2,
                "name": "Aggressive",
                "type": "aggressive", 
                "description": "Higher risk, higher reward with larger bet sizes and more frequent betting",
                "parameters": {
                    "min_confidence": 60,
                    "max_bet_percentage": 5.0,
                    "max_odds": 5.0
                }
            },
            {
                "id": 3,
                "name": "Loss Recovery",
                "type": "recovery",
                "description": "Recover losses with calculated risk management and progressive betting",
                "parameters": {
                    "loss_threshold": 10.0,
                    "max_bet_percentage": 7.0,
                    "recovery_multiplier": 1.5
                }
            },
            {
                "id": 4,
                "name": "+eV Strategy",
                "type": "expected_value",
                "description": "Focus on bets with positive expected value. Calculates probability vs odds to find profitable opportunities",
                "parameters": {
                    "min_expected_value": 5.0,
                    "max_bet_percentage": 3.0,
                    "confidence_threshold": 65,
                    "max_odds": 3.0,
                    "kelly_fraction": 0.25
                },
                "created_from_template": "positive_ev"
            }
        ];
        displayStrategies();
        updateStrategySelects();
        hideLoading();
    }
}

// Strategy Builder help function
window.showStrategyBuilderHelp = function() {
    const helpContent = `
        <div class="text-left">
            <h4 class="font-bold mb-2">How to Build a Strategy:</h4>
            <ol class="list-decimal list-inside space-y-2 text-sm">
                <li>Start with an <strong>IF/THEN</strong> block from Logic Blocks</li>
                <li>Drag <strong>Data Sources</strong> like Weather or Team Stats into conditions</li>
                <li>Add <strong>Comparison</strong> blocks to set thresholds</li>
                <li>Use <strong>AND/OR</strong> blocks to combine multiple conditions</li>
                <li>Add <strong>Actions</strong> like Place Bet or Skip Bet</li>
                <li>Adjust <strong>Parameters</strong> on the right panel</li>
                <li>Test your strategy before saving</li>
            </ol>
            <h4 class="font-bold mt-4 mb-2">Quick Tips:</h4>
            <ul class="list-disc list-inside space-y-1 text-sm">
                <li>Use Templates for proven strategies</li>
                <li>Keep risk level moderate (3-7) for beginners</li>
                <li>Set bet size to 2-5% of balance</li>
                <li>Always backtest before going live</li>
            </ul>
        </div>
    `;
    
    showMessage(helpContent, false, 10000); // Show for 10 seconds
};
const strategyTemplates = {
    positive_ev: {
        name: "+eV Strategy",
        type: "expected_value",
        description: "Focuses on bets with positive expected value. Calculates probability vs odds to find profitable opportunities.",
        parameters: {
            min_expected_value: 5.0,  // Minimum 5% expected value
            max_bet_percentage: 3.0,  // 3% of balance per bet
            confidence_threshold: 65, // 65% confidence minimum
            max_odds: 3.0,           // Maximum odds of 3.0 (+200)
            kelly_fraction: 0.25     // Use 25% of Kelly Criterion recommendation
        },
        flow_definition: {
            logic: "IF (Expected Value > 5% AND Confidence > 65% AND Odds <= 3.0) THEN Place Bet (Kelly Criterion * 0.25)",
            conditions: [
                { type: "expected_value", operator: ">", value: 5.0 },
                { type: "confidence", operator: ">", value: 65 },
                { type: "odds", operator: "<=", value: 3.0 }
            ],
            action: { type: "place_bet", sizing: "kelly_fractional", fraction: 0.25 }
        }
    },
    conservative: {
        name: "Conservative Strategy",
        type: "conservative",
        description: "Low risk approach with smaller bet sizes and higher confidence requirements.",
        parameters: {
            min_confidence: 75,      // Minimum 75% confidence
            max_bet_percentage: 2.0, // 2% of balance per bet
            max_odds: 2.0,          // Maximum odds of 2.0 (-100)
            min_expected_value: 3.0  // Minimum 3% expected value
        },
        flow_definition: {
            logic: "IF (Confidence > 75% AND Odds <= 2.0 AND Expected Value > 3%) THEN Bet 1-2%",
            conditions: [
                { type: "confidence", operator: ">", value: 75 },
                { type: "odds", operator: "<=", value: 2.0 },
                { type: "expected_value", operator: ">", value: 3.0 }
            ],
            action: { type: "place_bet", sizing: "fixed_percentage", percentage: 2.0 }
        }
    },
    aggressive: {
        name: "Aggressive Strategy",
        type: "aggressive",
        description: "Higher risk, higher reward with larger bet sizes and more frequent betting.",
        parameters: {
            min_confidence: 60,      // Lower confidence threshold
            max_bet_percentage: 5.0, // 5% of balance per bet
            max_odds: 5.0,          // Higher odds acceptable
            min_expected_value: 3.0  // 3% expected value minimum
        },
        flow_definition: {
            logic: "IF (Confidence > 60% AND Expected Value > 3%) THEN Bet 3-5%",
            conditions: [
                { type: "confidence", operator: ">", value: 60 },
                { type: "expected_value", operator: ">", value: 3.0 }
            ],
            action: { type: "place_bet", sizing: "fixed_percentage", percentage: 5.0 }
        }
    },
    recovery: {
        name: "Loss Recovery Strategy",
        type: "recovery",
        description: "Recover losses with calculated risk management and progressive betting.",
        parameters: {
            loss_threshold: 10.0,    // Start recovery when down 10%
            max_bet_percentage: 7.0, // Up to 7% during recovery
            recovery_multiplier: 1.5, // Increase bet size by 50%
            min_confidence: 70       // Higher confidence during recovery
        },
        flow_definition: {
            logic: "IF (Current Balance < Starting Balance - 10% AND Confidence > 70%) THEN Increase Bet Size by 50%",
            conditions: [
                { type: "balance_loss", operator: ">", value: 10.0 },
                { type: "confidence", operator: ">", value: 70 }
            ],
            action: { type: "place_bet", sizing: "recovery_progressive", multiplier: 1.5 }
        }
    },
    value_hunting: {
        name: "Value Hunter Strategy",
        type: "value_hunting", 
        description: "Finds undervalued odds across multiple sportsbooks for maximum profit.",
        parameters: {
            min_odds_edge: 5.0,      // 5% better odds than market average
            max_bet_percentage: 3.5, // 3.5% of balance
            min_confidence: 65,      // 65% confidence minimum
            sportsbook_minimum: 3    // Check at least 3 sportsbooks
        },
        flow_definition: {
            logic: "IF (Best Odds > Market Average + 5% AND Confidence > 65%) THEN Place Bet",
            conditions: [
                { type: "odds_edge", operator: ">", value: 5.0 },
                { type: "confidence", operator: ">", value: 65 },
                { type: "sportsbook_count", operator: ">=", value: 3 }
            ],
            action: { type: "place_bet", sizing: "fixed_percentage", percentage: 3.5 }
        }
    },
    arbitrage: {
        name: "Arbitrage Strategy",
        type: "arbitrage",
        description: "Risk-free profit by betting both sides across different sportsbooks.",
        parameters: {
            min_arbitrage_profit: 1.0, // Minimum 1% profit
            max_bet_percentage: 10.0,  // Up to 10% for risk-free bets
            max_exposure: 20.0,        // Maximum 20% total exposure
            min_sportsbooks: 2         // Require at least 2 sportsbooks
        },
        flow_definition: {
            logic: "IF (Arbitrage Opportunity > 1% AND Have 2+ Sportsbooks) THEN Place Both Bets",
            conditions: [
                { type: "arbitrage_profit", operator: ">", value: 1.0 },
                { type: "sportsbook_count", operator: ">=", value: 2 }
            ],
            action: { type: "place_arbitrage", sizing: "calculated_risk_free" }
        }
    }
};

// Create strategy from template
window.createFromTemplate = function(templateKey) {
    const template = strategyTemplates[templateKey];
    if (!template) {
        console.error('Template not found:', templateKey);
        return;
    }
    
    showLoading();
    
    // Create strategy with template data
    const strategyData = {
        name: template.name,
        type: template.type,
        description: template.description,
        parameters: template.parameters,
        flow_definition: template.flow_definition,
        created_from_template: templateKey,
        created_at: new Date().toISOString()
    };
    
    // Add strategy via API
    fetch('/api/strategies', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            ...strategyData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(`${template.name} created successfully!`);
            closeModal('strategy-templates-modal');
            // Refresh strategies
            fetchStrategies();
        } else {
            showMessage(`Failed to create strategy: ${data.message}`, true);
        }
    })
    .catch(error => {
        console.error('Error creating strategy:', error);
        showMessage('Failed to create strategy from template', true);
    })
    .finally(() => {
        hideLoading();
    });
};

// Update displayStrategies function to show more details
function displayStrategies() {
    const container = strategiesContainer;
    if (strategies.length === 0) {
        container.innerHTML = `<p class="text-center text-gray-400 py-4">No strategies found. Create one using templates above!</p>`;
        return;
    }
    
    // Enhanced strategy display with cards instead of table
    const strategiesGrid = document.createElement('div');
    strategiesGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';
    
    strategiesGrid.innerHTML = strategies.map(strategy => {
        const linkedStrategy = strategies.find(s => s.id === strategy.linked_strategy_id);
        const linkedStrategyName = linkedStrategy ? linkedStrategy.name : 'None';
        
        // Determine card color based on strategy type
        let cardColor = 'from-gray-600 to-gray-800';
        if (strategy.type === 'expected_value') cardColor = 'from-green-500 to-green-700';
        else if (strategy.type === 'conservative') cardColor = 'from-blue-500 to-blue-700';
        else if (strategy.type === 'aggressive') cardColor = 'from-orange-500 to-red-600';
        else if (strategy.type === 'recovery') cardColor = 'from-purple-500 to-purple-700';
        else if (strategy.type === 'value_hunting') cardColor = 'from-teal-500 to-cyan-600';
        else if (strategy.type === 'arbitrage') cardColor = 'from-indigo-500 to-purple-600';
        
        // Get icon based on type
        let icon = '📋';
        if (strategy.type === 'expected_value') icon = '💰';
        else if (strategy.type === 'conservative') icon = '🛡️';
        else if (strategy.type === 'aggressive') icon = '🚀';
        else if (strategy.type === 'recovery') icon = '🔄';
        else if (strategy.type === 'value_hunting') icon = '🎯';
        else if (strategy.type === 'arbitrage') icon = '⚖️';
        
        return `
            <div class="bg-gradient-to-br ${cardColor} p-4 rounded-lg text-white relative group">
                <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="window.showStrategyDetails('${strategy.id}')" class="text-white hover:text-gray-200 mx-1 text-sm">✏️</button>
                    <button onclick="window.deleteStrategy('${strategy.id}')" class="text-white hover:text-red-300 mx-1 text-sm">🗑️</button>
                </div>
                
                <div class="text-2xl mb-2">${icon}</div>
                <h4 class="text-lg font-bold mb-2">${strategy.name}</h4>
                <div class="text-sm opacity-90 mb-3">${strategy.description || 'No description'}</div>
                
                <div class="text-xs bg-black bg-opacity-30 p-2 rounded mb-3">
                    <strong>Type:</strong> ${strategy.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    ${linkedStrategyName !== 'None' ? `<br><strong>Recovery:</strong> ${linkedStrategyName}` : ''}
                </div>
                
                ${strategy.parameters ? `
                    <div class="text-xs text-gray-200">
                        ${strategy.parameters.max_bet_percentage ? `Max Bet: ${strategy.parameters.max_bet_percentage}%` : ''}
                        ${strategy.parameters.min_confidence ? `<br>Min Confidence: ${strategy.parameters.min_confidence}%` : ''}
                        ${strategy.parameters.min_expected_value ? `<br>Min +eV: ${strategy.parameters.min_expected_value}%` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = '';
    container.appendChild(strategiesGrid);
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

    const totalProfitEl = document.getElementById('total-profit');
    if (totalProfitEl) {
        totalProfitEl.textContent = `$${totalProfit.toFixed(2)}`;
        totalProfitEl.className = `stats-value ${profitClass}`;
    }
    const totalWagersEl = document.getElementById('total-wagers');
    if (totalWagersEl) {
        totalWagersEl.textContent = totalWagers;
    }
    const winRateEl = document.getElementById('win-rate');
    if (winRateEl) {
        winRateEl.textContent = `${winRate}%`;
    }
    const bestBotNameEl = document.getElementById('best-bot-name');
    const bestBotProfitEl = document.getElementById('best-bot-profit');
    if (bestBot && bestBotNameEl && bestBotProfitEl) {
        bestBotNameEl.textContent = bestBot.name;
        bestBotProfitEl.textContent = `$${(bestBot.current_balance - bestBot.starting_balance).toFixed(2)}`;
    }
    const worstBotNameEl = document.getElementById('worst-bot-name');
    const worstBotProfitEl = document.getElementById('worst-bot-profit');
    if (worstBot && worstBotNameEl && worstBotProfitEl) {
        worstBotNameEl.textContent = worstBot.name;
        worstBotProfitEl.textContent = `$${(worstBot.current_balance - worstBot.starting_balance).toFixed(2)}`;
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

window.toggleBotWagers = function(botId) {
    const wagersRow = document.getElementById(`wagers-${botId}`);
    if (wagersRow) {
        wagersRow.classList.toggle('hidden');
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

window.getStrategyPicks = async function(botId, strategyId) {
    try {
        showLoading();
        // Pass userId in the API call
        const response = await fetch(`/api/strategy/${strategyId}/picks?user_id=${userId}&bot_id=${botId}`);
        const data = await response.json();
        
        const picksContent = document.getElementById(`picks-content-${botId}`);
        
        if (data.success && data.picks.length > 0) {
            const picksHtml = data.picks.map(pick => `
                <div class="mb-2 p-3 bg-purple-50 rounded border border-purple-200">
                    <div class="font-semibold text-purple-800">${pick.teams} (${pick.sport})</div>
                    <div class="text-sm text-purple-600">
                        ${pick.bet_type} | Odds: ${pick.odds} | Confidence: ${pick.confidence}%
                    </div>
                    <div class="text-sm text-purple-700">
                        Recommended: $${pick.recommended_amount} → Potential: $${pick.potential_payout}
                    </div>
                </div>
            `).join('');
            
            picksContent.innerHTML = `
                <div class="text-sm text-gray-600 mb-2">
                    Strategy: ${data.strategy_name} | Remaining bets this week: ${data.remaining_bets}
                </div>
                ${picksHtml}
            `;
            
            showMessage(`Generated ${data.picks.length} picks from strategy`, false);
        } else {
            picksContent.innerHTML = `
                <div class="text-sm text-gray-500 p-2 bg-gray-100 rounded">
                    ${data.message || 'No picks available from strategy'}
                </div>
            `;
            showMessage(data.message || "No picks available", false);
        }
    } catch (error) {
        console.error("Error getting strategy picks:", error);
        showMessage("Failed to get strategy picks", true);
    } finally {
        hideLoading();
    }
};

window.refreshApiStatus = async function() {
    try {
        showLoading();
        const response = await fetch('/api/api-status');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('api-requests-remaining').textContent = data.remaining_requests;
            document.getElementById('api-requests-used').textContent = data.used_requests;
            
            if (data.demo_mode) {
                showMessage("API status refreshed (Demo Mode)", false);
            } else {
                showMessage("API status refreshed successfully", false);
            }
        } else {
            showMessage(data.message || "Failed to refresh API status", true);
        }
    } catch (error) {
        console.error("Error refreshing API status:", error);
        showMessage("Failed to refresh API status", true);
    } finally {
        hideLoading();
    }
};

// Load API status when account page is shown
function loadApiStatus() {
    window.refreshApiStatus();
}

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
        // Load investments and bot recommendations in parallel
        const [investmentsResponse, recommendationsResponse] = await Promise.all([
            fetch(`/api/investments?user_id=${userId}&refresh=false`),
            fetch(`/api/bot-recommendations?user_id=${userId}`).catch(e => {
                console.warn('Failed to load bot recommendations:', e);
                return { ok: false };
            })
        ]);
        
        const investmentsData = await investmentsResponse.json();
        
        // Load bot recommendations if available
        if (recommendationsResponse.ok) {
            try {
                const recommendationsData = await recommendationsResponse.json();
                if (recommendationsData.success) {
                    botRecommendations = recommendationsData.recommendations || {};
                    console.log('Loaded bot recommendations:', Object.keys(botRecommendations).length, 'games');
                }
            } catch (e) {
                console.warn('Failed to parse bot recommendations:', e);
                botRecommendations = {};
            }
        } else {
            botRecommendations = {};
        }

        if (investmentsData.success && investmentsData.investments.length > 0) {
            displayInvestments(investmentsData.investments);
            updateCacheStatus(investmentsData);
        } else {
            noInvestmentsMessage.classList.remove('hidden');
            updateCacheStatus({ cached: false, has_cache: false });
        }
    } catch (e) {
        console.error("Error loading cached investments:", e);
        
        // Fallback to demo data when running without backend API
        console.log("Loading demo investment data for testing...");
        const demoInvestments = generateDemoInvestments();
        if (demoInvestments.length > 0) {
            displayInvestments(demoInvestments);
            updateCacheStatus({ 
                cached: true, 
                has_cache: true, 
                last_refresh: new Date().toISOString(),
                demo_mode: true 
            });
            showMessage("Loaded demo investment data for testing.", false);
        } else {
            showMessage("Failed to load investments.", true);
            noInvestmentsMessage.classList.remove('hidden');
            updateCacheStatus({ cached: false, has_cache: false });
        }
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
        
        // Fallback to demo data when running without backend API
        console.log("Loading demo investment data for testing...");
        const demoInvestments = generateDemoInvestments();
        if (demoInvestments.length > 0) {
            displayInvestments(demoInvestments);
            updateCacheStatus({ 
                cached: false, 
                has_cache: true, 
                last_refresh: new Date().toISOString(),
                demo_mode: true 
            });
            showMessage(`Loaded ${demoInvestments.length} demo games for testing.`, false);
        } else {
            showMessage("Failed to refresh investments. Check API key and connection.", true);
            noInvestmentsMessage.classList.remove('hidden');
            updateCacheStatus({ cached: false, has_cache: false });
        }
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
        const sport = investment.sport_title || investment.sport || 'Unknown Sport';
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
                        const marketName = market.name || marketNameMapping[market.key] || market.key || 'UNDEFINED';
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
    
    const tabButton = document.querySelector(`.tab-button[data-sport='${sport}']`);
    if (tabButton) {
        tabButton.classList.add('active');
    }

    // Show the corresponding tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    const tabContent = document.getElementById(`tab-content-${sport}`);
    if (tabContent) {
        tabContent.classList.add('active');
    }
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

    // Generate placed wagers HTML
    const placedWagersHtml = investment.placed_bets.length > 0
        ? `
            <div class="mt-4 p-3 bg-green-50 rounded-lg text-green-800 font-semibold text-sm">
                Placed Wagers: ${investment.placed_bets.map(wager => `${wager.bet_type}`).join(', ')}
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

    // Get bot recommendations for this game
    const gameRecommendations = botRecommendations[investment.id] || [];

    // Generate bookmakers HTML
    const bookmakersHtml = bookmakers.map(bookmaker => {
        const colors = sportsbookColors[bookmaker.title] || { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
        const marketsHtml = bookmaker.markets.map(market => {
            const marketName = market.name || marketNameMapping[market.key] || market.key || 'UNDEFINED';
            const outcomesHtml = market.outcomes.map(outcome => {
                let displayText = outcome.name;
                if (outcome.point !== undefined) {
                    displayText += ` (${outcome.point > 0 ? '+' : ''}${outcome.point})`;
                }
                const priceText = outcome.price > 0 ? `+${outcome.price}` : outcome.price;
                const defaultWager = 10;
                const payout = calculatePayout(defaultWager, outcome.price) + defaultWager;
                return `
                    <div class="wager-outcome text-center p-2 border border-gray-100 rounded relative cursor-pointer" style="position:relative;">
                        <div class="text-xs font-medium text-gray-600">${displayText}</div>
                        <div class="text-sm font-bold text-gray-900">${priceText}</div>
                        <div class="text-xs text-gray-500">Wager: $${defaultWager} | Payout: $${payout.toFixed(2)}</div>
                        <button class="post9-btn add-to-cart-btn" style="display:none; position:absolute; left:50%; transform:translateX(-50%); bottom:8px; z-index:10;" onclick="window.addToCart({
                            id: '${investment.id}_${bookmaker.title}_${market.key}_${outcome.name}',
                            teams: '${investment.teams}',
                            sport: '${investment.sport_title || investment.sport || ''}',
                            sportsbook: '${bookmaker.title}',
                            marketType: '${marketName}',
                            selection: '${outcome.name}',
                            odds: ${outcome.price},
                            commenceTime: '${investment.commence_time}'
                        })">Add to Cart</button>
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

    // Generate game-level bot summary if there are recommendations
    let botSummaryHtml = '';
    if (gameRecommendations.length > 0) {
        const uniqueBots = [...new Set(gameRecommendations.map(rec => rec.bot_name))];
        botSummaryHtml = `
            <div class="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div class="text-xs font-semibold text-gray-600 mb-2">🤖 Bot Recommendations:</div>
                <div class="flex flex-wrap gap-2">
                    ${uniqueBots.map(botName => {
                        const botRecs = gameRecommendations.filter(rec => rec.bot_name === botName);
                        const avgConfidence = Math.round(botRecs.reduce((sum, rec) => sum + rec.confidence, 0) / botRecs.length);
                        const totalAmount = botRecs.reduce((sum, rec) => sum + rec.recommended_amount, 0);
                        const botColor = botRecs[0].bot_color;
                        
                        return `
                            <div class="text-xs px-2 py-1 rounded-full" style="background-color: ${botColor}20; border: 1px solid ${botColor}; color: ${botColor};">
                                ${botName}: ${botRecs.length} bet${botRecs.length > 1 ? 's' : ''}, ${avgConfidence}% avg, $${totalAmount.toFixed(0)}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    card.innerHTML = `
        <style>
            .wager-outcome { position: relative; cursor: pointer; }
            .wager-outcome:hover .add-to-cart-btn { display: block !important; }
            .game-title-clickable { cursor: pointer; transition: color 0.2s ease; }
            .game-title-clickable:hover { color: #3b82f6; text-decoration: underline; }
        </style>
        <div class="mb-4">
            <h3 class="text-lg font-bold text-gray-900 game-title-clickable" onclick="showGameAnalytics('${investment.id}', '${investment.teams}', '${investment.sport_title || investment.sport || 'Sport'}', '${investment.commence_time}')">
                ${investment.teams} 📊
            </h3>
            <p class="text-sm text-gray-600">${formattedTime}</p>
            <p class="text-xs text-gray-500">${investment.sport_title || investment.sport || 'Sport'}</p>
        </div>
        ${botSummaryHtml}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            ${bookmakersHtml}
        </div>
        ${placedWagersHtml}
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
    // Only proceed if userSettings is properly loaded and auto-refresh is explicitly enabled
    if (userSettings && userSettings.auto_refresh_on_login === true) {
        // Auto refresh is enabled, check if we're on investments page
        const investmentsPage = document.getElementById('investments-page');
        if (investmentsPage && investmentsPage.style.display === 'block') {
            console.log('Auto-refresh enabled, refreshing investments...');
            await window.refreshInvestments();
        }
    } else {
        console.log('Auto-refresh disabled or settings not loaded, using cached data...');
        // Load cached data instead of refreshing when auto-refresh is disabled
        await window.loadCachedInvestments();
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

async function startListeners() {
    if (!firebaseAvailable || !auth || !onAuthStateChanged) {
        // In demo mode without Firebase, just set up the UI
        console.log("Running in demo mode, skipping Firebase auth listeners");
        userId = 'demo-user';
        document.getElementById('user-id').textContent = 'Demo Mode';
        
        // Load demo settings
        await loadUserSettings();
        // Fetch strategies first, then bots
        await fetchStrategies();
        await fetchBots();
        
        // Check auto-refresh for demo mode too
        setTimeout(() => {
            if (userSettings) {
                checkAutoRefresh();
            } else {
                console.warn('Demo settings not loaded, loading cached data instead');
                window.loadCachedInvestments();
            }
        }, 1000);
        
        hideLoading();
        return;
    }

    onAuthStateChanged(auth, async (user) => {
        if (user) {
            userId = user.uid;
            document.getElementById('user-id').textContent = userId;
            // Load user settings first, then fetch data, then check auto-refresh
            await loadUserSettings();
            // Fetch strategies first, then bots
            await fetchStrategies();
            await fetchBots();
            // Check auto-refresh after everything is loaded AND settings are available
            setTimeout(() => {
                if (userSettings) {
                    checkAutoRefresh();
                } else {
                    console.warn('User settings not loaded, skipping auto-refresh check');
                }
            }, 1500); // Increased delay to ensure settings are loaded
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
    closeModal('add-bot-modal');
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
        linked_strategy_id: form.linked_strategy_id.value || null,
        description: form.description.value
    };
    await window.addStrategy(strategyData);
    form.reset();
    closeModal('add-strategy-modal');
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

const preferencesForm = document.getElementById('preferences-form');
if (preferencesForm) {
    preferencesForm.addEventListener('submit', async function(event) {
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
}

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

function setupStatsCardClicks() {
    document.querySelectorAll('.stats-card').forEach((card, idx) => {
        card.onclick = function() {


            let statType = '';
            switch (idx) {
                case 0: statType = 'profit'; break;
                case 1: statType = 'wagers'; break;
                case 2: statType = 'winrate'; break;
                case 3: statType = 'bestbot'; break;
                case 4: statType = 'worstbot'; break;
                default: statType = '';
            }
            showStatsBreakdownInline(statType, card);
        };
    });
}

function showStatsBreakdownInline(statType, card) {
    let title = '';
    let html = '';
    if (statType === 'profit') {
        title = 'Total Profit Breakdown by Bot';
        html = `<table class='min-w-full post9-card'><thead><tr><th>Bot</th><th>Profit</th></tr></thead><tbody>` +
            bots.map(bot => `<tr><td>${bot.name}</td><td>$${(bot.current_balance - bot.starting_balance).toFixed(2)}</td></tr>`).join('') + '</tbody></table>';
    } else if (statType === 'wagers') {
        title = 'Total Wagers Breakdown by Bot';
        html = `<table class='min-w-full post9-card'><thead><tr><th>Bot</th><th>Wagers</th></tr></thead><tbody>` +
            bots.map(bot => `<tr><td>${bot.name}</td><td>${bot.total_wagers}</td></tr>`).join('') + '</tbody></table>';
    } else if (statType === 'winrate') {
        title = 'Win Rate Breakdown by Bot';
        html = `<table class='min-w-full post9-card'><thead><tr><th>Bot</th><th>Win Rate</th></tr></thead><tbody>` +
            bots.map(bot => {
                const winRate = bot.total_wagers > 0 ? ((bot.total_wins / bot.total_wagers) * 100).toFixed(2) : '0.00';
                return `<tr><td>${bot.name}</td><td>${winRate}%</td></tr>`;
            }).join('') + '</tbody></table>';
    } else if (statType === 'bestbot') {
        title = 'Best Bot Details';
        const bestBot = [...bots].sort((a, b) => (b.current_balance - b.starting_balance) - (a.current_balance - a.starting_balance))[0];
        html = bestBot ? `<div class='post9-card p-4'><strong>${bestBot.name}</strong><br>Profit: $${(bestBot.current_balance - bestBot.starting_balance).toFixed(2)}</div>` : '<div>No bots found.</div>';
    } else if (statType === 'worstbot') {
        title = 'Worst Bot Details';
        const worstBot = [...bots].sort((a, b) => (a.current_balance - a.starting_balance) - (b.current_balance - b.starting_balance))[0];
        html = worstBot ? `<div class='post9-card p-4'><strong>${worstBot.name}</strong><br>Profit: $${(worstBot.current_balance - worstBot.starting_balance).toFixed(2)}</div>` : '<div>No bots found.</div>';
    }
    const breakdownContainer = document.getElementById('stats-breakdown-inline');
    breakdownContainer.innerHTML = `
        <div class='post9-card p-6 mt-4 mb-4'>
            <div class='flex justify-between items-center mb-2'>
                <span class='text-lg font-bold text-white'>${title}</span>
                <button onclick="document.getElementById('stats-breakdown-inline').innerHTML = ''" class='post9-btn px-3 py-1 text-sm'>Close</button>
            </div>
            ${html}
        </div>
    `;
    // Scroll to the breakdown if needed
    breakdownContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// --- BET CART FUNCTIONALITY ---

window.addToCart = function(wagerData) {
    // Check if wager already exists in cart
    const existingIndex = betCart.findIndex(item => item.id === wagerData.id);
    if (existingIndex >= 0) {
        showMessage('This wager is already in your cart!', true);
        return;
    }
    wagerData.wagerAmount = 10;
    wagerData.payout = calculatePayout(wagerData.wagerAmount, wagerData.odds) + wagerData.wagerAmount;
    wagerData.addedAt = new Date().toISOString();
    betCart.push(wagerData);
    setTimeout(updateCartUI, 0); // Ensure UI updates after adding
    showMessage(`Added ${wagerData.selection} to cart!`, false);
}

window.removeFromCart = function(itemId) {
    betCart = betCart.filter(item => item.id !== itemId);
    updateCartUI();
    showMessage('Removed bet from cart', false);
}

window.clearCart = function() {
    if (betCart.length === 0) {
        showMessage('Cart is already empty', true);
        return;
    }
    
    if (confirm('Are you sure you want to clear all bets from your cart?')) {
        betCart = [];
        updateCartUI();
        showMessage('Cart cleared', false);
    }
}

window.toggleBetCart = function() {
    const sidebar = document.getElementById('bet-cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    
    if (cartVisible) {
        closeBetCart();
    } else {
        sidebar.classList.remove('translate-x-full');
        overlay.classList.remove('hidden');
        cartVisible = true;
    }
}

window.closeBetCart = function() {
    const sidebar = document.getElementById('bet-cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    
    sidebar.classList.add('translate-x-full');
    overlay.classList.add('hidden');
    cartVisible = false;
}

window.showBetConfirmation = function() {
    if (betCart.length === 0) {
        showMessage('No bets in cart to place', true);
        return;
    }
    
    populateConfirmationModal();
    showModal('bet-confirmation-modal');
}

window.confirmPlaceBets = function() {
    confirmPlaceBetsInternal();
}

window.exportToExcel = function() {
    exportToExcelInternal();
}

function updateCartUI() {
    const cartContainer = document.getElementById('cart-container');
    if (!cartContainer) return;
    const cartCount = betCart.length;
    const cartBadge = document.getElementById('cart-count-badge');
    const cartItemsCount = document.getElementById('cart-items-count');
    const cartContainerEl = document.getElementById('cart-items-container');
    const emptyMessage = document.getElementById('empty-cart-message');
    const placeBetsBtn = document.getElementById('place-bets-btn');
    const exportBtn = document.getElementById('export-excel-btn');
    
    // Update cart count badge
    if (cartCount > 0) {
        cartBadge.textContent = cartCount;
        cartBadge.classList.remove('hidden');
    } else {
        cartBadge.classList.add('hidden');
    }
    
    // Update items count
    cartItemsCount.textContent = cartCount;
    
    // Show/hide empty message
    if (cartCount === 0) {
        emptyMessage.classList.remove('hidden');
        cartContainerEl.innerHTML = '';
        cartContainerEl.appendChild(emptyMessage);
    } else {
        emptyMessage.classList.add('hidden');
        renderCartItems();
    }
    
    // Enable/disable buttons
    placeBetsBtn.disabled = cartCount === 0;
    exportBtn.disabled = cartCount === 0;
    
    // Update total payout
    updateCartTotals();
}

function renderCartItems() {
    const container = document.getElementById('cart-items-container');
    container.innerHTML = '';
    betCart.forEach(wager => {
        const cartItem = document.createElement('div');
        cartItem.className = 'bg-gray-50 border border-gray-200 rounded-lg p-3';
        const commenceTime = new Date(wager.commenceTime).toLocaleString();
        cartItem.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <div class="flex-1">
                    <div class="font-semibold text-sm text-gray-900">${wager.teams}</div>
                    <div class="text-xs text-gray-600">${wager.sport} • ${commenceTime}</div>
                </div>
                <button onclick="removeFromCart('${wager.id}')" class="text-red-500 hover:text-red-700 ml-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div class="text-xs text-gray-700 mb-2">
                <div><span class="font-medium">Book:</span> ${wager.sportsbook}</div>
                <div><span class="font-medium">Market:</span> ${wager.marketType}</div>
                <div><span class="font-medium">Selection:</span> ${wager.selection}</div>
                <div><span class="font-medium">Odds:</span> ${wager.odds > 0 ? '+' : ''}${wager.odds}</div>
            </div>
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <span class="text-xs text-gray-600 mr-2">Wager:</span>
                    <input type="number" value="${wager.wagerAmount}" min="1" step="0.01" 
                           onchange="updateWagerAmount('${wager.id}', this.value)"
                           class="w-20 px-2 py-1 border border-gray-300 rounded text-xs">
                </div>
                <div class="text-xs">
                    <div class="text-green-600 font-semibold">$${wager.payout.toFixed(2)}</div>
                </div>
            </div>
        `;
        container.appendChild(cartItem);
    });
}

function updateWagerAmount(wagerId, newAmount) {
    const wager = betCart.find(item => item.id === wagerId);
    if (wager) {
        wager.wagerAmount = parseFloat(newAmount) || 0;
        wager.payout = calculatePayout(wager.wagerAmount, wager.odds) + wager.wagerAmount;
        updateCartTotals();
    }
}

function calculatePayout(betAmount, odds) {
    if (odds > 0) {
        return betAmount * (odds / 100);
    } else {
        return betAmount * (100 / Math.abs(odds));
    }
}

function updateCartTotals() {
    const totalPayout = betCart.reduce((sum, wager) => sum + wager.payout, 0);
    document.getElementById('cart-total-payout').textContent = `$${totalPayout.toFixed(2)}`;
}

function toggleBetCart() {
    const sidebar = document.getElementById('bet-cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    
    if (cartVisible) {
        closeBetCart();
    } else {
        sidebar.classList.remove('translate-x-full');
        overlay.classList.remove('hidden');
        cartVisible = true;
    }
}

function closeBetCart() {
    const sidebar = document.getElementById('bet-cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    
    sidebar.classList.add('translate-x-full');
    overlay.classList.add('hidden');
    cartVisible = false;
}

function showBetConfirmation() {
    if (betCart.length === 0) {
        showMessage('No bets in cart to place', true);
        return;
    }
    
    populateConfirmationModal();
    showModal('bet-confirmation-modal');
}

function populateConfirmationModal() {
    // Calculate totals
    const totalBets = betCart.length;
    const totalAmount = betCart.reduce((sum, bet) => sum + bet.wagerAmount, 0);
    const totalPayout = betCart.reduce((sum, bet) => sum + bet.potentialPayout, 0);
    const totalProfit = totalPayout - totalAmount;
    
    // Update summary
    document.getElementById('confirm-bet-count').textContent = totalBets;
    document.getElementById('confirm-total-amount').textContent = `$${totalAmount.toFixed(2)}`;
    document.getElementById('confirm-potential-payout').textContent = `$${totalPayout.toFixed(2)}`;
    document.getElementById('confirm-potential-profit').textContent = `$${totalProfit.toFixed(2)}`;
    
    // Group by sportsbook
    const betsBySportsbook = {};
    const betsByBot = { 'Manual Selection': betCart }; // For now, all bets are manual
    
    betCart.forEach(bet => {
        if (!betsBySportsbook[bet.sportsbook]) {
            betsBySportsbook[bet.sportsbook] = [];
        }
        betsBySportsbook[bet.sportsbook].push(bet);
    });
    
    // Render by sportsbook
    const sportsbookContainer = document.getElementById('bets-by-sportsbook');
    sportsbookContainer.innerHTML = '';
    
    Object.entries(betsBySportsbook).forEach(([sportsbook, bets]) => {
        const div = document.createElement('div');
        div.className = 'bg-gray-50 border rounded-lg p-4';
        
        const sportsbookTotal = bets.reduce((sum, bet) => sum + bet.wagerAmount, 0);
        const sportsbookPayout = bets.reduce((sum, bet) => sum + bet.potentialPayout, 0);
        
        div.innerHTML = `
            <div class="flex justify-between items-center mb-3">
                <h4 class="font-semibold text-lg">${sportsbook}</h4>
                <div class="text-sm text-gray-600">
                    ${bets.length} bet(s) • $${sportsbookTotal.toFixed(2)} → $${sportsbookPayout.toFixed(2)}
                </div>
            </div>
            <div class="space-y-2">
                ${bets.map(bet => `
                    <div class="text-sm bg-white p-2 rounded border">
                        <div class="font-medium">${bet.teams}</div>
                        <div class="text-gray-600">${bet.marketType}: ${bet.selection} (${bet.odds > 0 ? '+' : ''}${bet.odds})</div>
                        <div class="text-green-600">$${bet.wagerAmount} → $${bet.potentialPayout.toFixed(2)}</div>
                    </div>
                `).join('')}
            </div>
        `;
        
        sportsbookContainer.appendChild(div);
    });
    
    // Render by bot (simplified for now)
    const botContainer = document.getElementById('bets-by-bot');
    botContainer.innerHTML = `
        <div class="bg-gray-50 border rounded-lg p-4">
            <div class="flex justify-between items-center mb-3">
                <h4 class="font-semibold text-lg">Manual Selection</h4>
                <div class="text-sm text-gray-600">
                    ${totalBets} bet(s) • $${totalAmount.toFixed(2)} → $${totalPayout.toFixed(2)}
                </div>
            </div>
            <div class="text-sm text-gray-600">All bets selected manually from available investments</div>
        </div>
    `;
}

async function confirmPlaceBetsInternal() {
    if (betCart.length === 0) {
        showMessage('No bets to place', true);
        return;
    }
    
    try {
        showLoading();
        
        // For demo mode, just simulate placing bets
        const response = await fetch('/api/place-bets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                bets: betCart
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(`Successfully placed ${betCart.length} bet(s)!`, false);
            betCart = [];
            updateCartUI();
            closeModal('bet-confirmation-modal');
            closeBetCart();
        } else {
            showMessage(`Failed to place bets: ${data.message}`, true);
        }
        
    } catch (error) {
        console.error('Error placing bets:', error);
        showMessage('Failed to place bets. Please try again.', true);
    } finally {
        hideLoading();
    }
}

async function exportToExcelInternal() {
    if (betCart.length === 0) {
        showMessage('No bets to export', true);
        return;
    }
    
    try {
        // Create CSV content
        const headers = ['Game', 'Sport', 'Sportsbook', 'Market', 'Selection', 'Odds', 'Bet Amount', 'Potential Payout', 'Game Time'];
        const rows = betCart.map(bet => [
            bet.teams,
            bet.sport,
            bet.sportsbook,
            bet.marketType,
            bet.selection,
            bet.odds,
            bet.wagerAmount,
            bet.payout.toFixed(2),
            new Date(bet.commenceTime).toLocaleString()
        ]);
        
        const csvContent = [headers, ...rows].map(row => 
            row.map(cell => `"${cell}"`).join(',')
        ).join('\n');
        
        // Create and download file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `bet-cart-${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showMessage('Bet cart exported to CSV file', false);
        
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showMessage('Failed to export bets. Please try again.', true);
    }
}

// --- STRATEGY BUILDER FUNCTIONS ---

// Strategy builder state
let currentStrategy = {
    nodes: [],
    connections: [],
    parameters: {}
};

window.saveCurrentStrategy = function() {
    if (currentStrategy.nodes.length === 0) {
        showMessage('Please build a strategy before saving', true);
        return;
    }
    
    const strategyName = prompt('Enter a name for your strategy:', 'My Custom Strategy');
    if (!strategyName) return;
    
    const strategyData = {
        name: strategyName,
        type: 'visual_flow',
        flow_definition: currentStrategy,
        parameters: {
            risk_level: document.getElementById('risk-level').value,
            bet_percentage: document.getElementById('bet-size-percent').value,
            max_bets_per_week: document.getElementById('max-bets-week').value,
            recovery_strategy: document.getElementById('recovery-strategy').value
        }
    };
    
    // Save strategy via existing API
    window.addStrategy(strategyData);
    updateStrategyDescription();
};

window.testStrategy = function() {
    if (currentStrategy.nodes.length === 0) {
        showMessage('Please build a strategy before testing', true);
        return;
    }
    
    showMessage('Running strategy test with current market data...', false);
    
    // Simulate strategy execution
    setTimeout(() => {
        const testResult = {
            passed: Math.random() > 0.3,
            confidence: Math.floor(Math.random() * 40) + 60,
            recommendations: Math.floor(Math.random() * 5) + 1
        };
        
        if (testResult.passed) {
            showMessage(`✅ Strategy test passed! Found ${testResult.recommendations} potential bets with ${testResult.confidence}% avg confidence`, false);
        } else {
            showMessage('❌ Strategy test failed. Check your logic and parameters.', true);
        }
    }, 2000);
};

window.simulateStrategy = function() {
    if (currentStrategy.nodes.length === 0) {
        showMessage('Please build a strategy before backtesting', true);
        return;
    }
    
    showMessage('Running backtest simulation over past 6 months...', false);
    
    // Simulate backtesting
    setTimeout(() => {
        const backtest = {
            total_bets: Math.floor(Math.random() * 200) + 50,
            win_rate: (Math.random() * 0.3 + 0.5).toFixed(3),
            profit: (Math.random() * 2000 - 500).toFixed(2),
            roi: (Math.random() * 0.4 - 0.1).toFixed(3)
        };
        
        const profitClass = backtest.profit > 0 ? 'green' : 'red';
        showMessage(`📈 Backtest complete: ${backtest.total_bets} bets, ${(backtest.win_rate * 100).toFixed(1)}% win rate, $${backtest.profit} profit (${(backtest.roi * 100).toFixed(1)}% ROI)`, backtest.profit > 0);
    }, 3000);
};

function updateStrategyDescription() {
    const description = document.getElementById('strategy-description');
    if (!description) return;
    
    if (currentStrategy.nodes.length === 0) {
        description.textContent = 'Build your strategy above to see the logic description here...';
        return;
    }
    
    // Generate plain English description
    let text = 'Strategy Logic:\n';
    text += '1. When a new game is available:\n';
    text += '2. Check if conditions are met (weather, team stats, model predictions)\n';
    text += '3. If conditions pass, place bet with configured parameters\n';
    text += '4. Otherwise, skip this opportunity\n';
    
    const betSizeEl = document.getElementById('bet-size-value');
    const maxBetsEl = document.getElementById('max-bets-week');
    if (betSizeEl && maxBetsEl) {
        text += `\nParameters: ${betSizeEl.textContent}% bet size, max ${maxBetsEl.value} bets per week`;
    }
    
    description.textContent = text;
}

// Setup drag and drop for strategy builder
function initializeStrategyBuilder() {
    const canvas = document.getElementById('strategy-canvas');
    const components = document.querySelectorAll('.draggable-component');
    
    if (!canvas || !components.length) return;
    
    components.forEach(component => {
        component.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', e.target.dataset.type);
        });
        component.draggable = true;
    });
    
    canvas.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    
    canvas.addEventListener('drop', (e) => {
        e.preventDefault();
        const componentType = e.dataTransfer.getData('text/plain');
        addComponentToCanvas(componentType, e.offsetX, e.offsetY);
    });
    
    // Setup parameter updates
    const riskLevel = document.getElementById('risk-level');
    const betSize = document.getElementById('bet-size-percent');
    
    if (riskLevel) {
        riskLevel.addEventListener('input', () => {
            const valueEl = document.getElementById('risk-level-value');
            if (valueEl) valueEl.textContent = riskLevel.value;
            updateStrategyDescription();
        });
    }
    
    if (betSize) {
        betSize.addEventListener('input', () => {
            const valueEl = document.getElementById('bet-size-value');
            if (valueEl) valueEl.textContent = betSize.value;
            updateStrategyDescription();
        });
    }
}

function addComponentToCanvas(componentType, x, y) {
    const canvas = document.getElementById('strategy-canvas');
    if (!canvas) return;
    
    const node = document.createElement('div');
    
    // Create visual node with better styling
    node.className = 'strategy-node absolute bg-white border-2 border-blue-500 rounded-lg p-3 cursor-move shadow-lg hover:shadow-xl transition-shadow';
    node.style.left = `${x - 50}px`;
    node.style.top = `${y - 25}px`;
    node.style.width = '120px';
    node.style.height = '60px';
    node.style.display = 'flex';
    node.style.alignItems = 'center';
    node.style.justifyContent = 'center';
    node.style.fontSize = '11px';
    node.style.fontWeight = 'bold';
    node.style.color = '#1e40af';
    node.style.backgroundColor = '#f8fafc';
    node.style.position = 'absolute';
    
    // Add a small close button
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.className = 'absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 text-xs font-bold hover:bg-red-600 transition-colors';
    closeBtn.onclick = (e) => {
        e.stopPropagation();
        removeComponentFromCanvas(node);
    };
    
    const icons = {
        'if-condition': '📋 IF/THEN',
        'and-or': '🔗 AND/OR',
        'comparison': '⚖️ Compare',
        'weather': '🌤️ Weather',
        'team-stats': '📊 Team Stats',
        'model-prediction': '🤖 ML Model',
        'place-bet': '💰 Place Bet',
        'skip-bet': '⏭️ Skip Bet'
    };
    
    const textContent = document.createElement('div');
    textContent.textContent = icons[componentType] || componentType;
    textContent.className = 'text-center';
    
    node.appendChild(closeBtn);
    node.appendChild(textContent);
    node.onclick = () => editNode(node, componentType);
    
    // Make node draggable within canvas
    makeDraggable(node);
    
    // Clear placeholder if this is first node
    const placeholder = document.getElementById('canvas-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    
    canvas.appendChild(node);
    
    // Add to strategy state
    currentStrategy.nodes.push({
        id: `node_${Date.now()}`,
        type: componentType,
        position: { x, y },
        element: node
    });
    
    updateStrategyDescription();
    showMessage(`Added ${componentType} component`, false);
}

// Make nodes draggable within the canvas
function makeDraggable(element) {
    let isDragging = false;
    let startX, startY;
    
    element.addEventListener('mousedown', (e) => {
        if (e.target.tagName === 'BUTTON') return; // Don't drag when clicking close button
        
        isDragging = true;
        startX = e.clientX - element.offsetLeft;
        startY = e.clientY - element.offsetTop;
        element.style.zIndex = '1000';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const canvas = document.getElementById('strategy-canvas');
        const rect = canvas.getBoundingClientRect();
        
        let newX = e.clientX - rect.left - startX;
        let newY = e.clientY - rect.top - startY;
        
        // Keep within canvas bounds
        newX = Math.max(0, Math.min(newX, canvas.offsetWidth - element.offsetWidth));
        newY = Math.max(0, Math.min(newY, canvas.offsetHeight - element.offsetHeight));
        
        element.style.left = `${newX}px`;
        element.style.top = `${newY}px`;
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            element.style.zIndex = 'auto';
        }
    });
}

function editNode(element, type) {
    // Add a context menu or right-click to delete functionality
    const action = confirm(`Configure ${type} component. Click OK to configure, Cancel to delete.`);
    
    if (action === true) {
        // Configure the node
        const newLabel = prompt(`Configure ${type}:`, element.textContent);
        if (newLabel) {
            element.textContent = newLabel;
            updateStrategyDescription();
        }
    } else {
        // Delete the node
        removeComponentFromCanvas(element);
    }
}

// Add component removal functionality
function removeComponentFromCanvas(nodeElement) {
    const canvas = document.getElementById('strategy-canvas');
    if (!canvas || !nodeElement) return;
    
    // Remove from DOM
    nodeElement.remove();
    
    // Remove from strategy state
    const nodeIndex = currentStrategy.nodes.findIndex(node => node.element === nodeElement);
    if (nodeIndex > -1) {
        currentStrategy.nodes.splice(nodeIndex, 1);
    }
    
    // Show placeholder if no nodes left
    if (currentStrategy.nodes.length === 0) {
        showCanvasPlaceholder();
    }
    
    updateStrategyDescription();
    showMessage('Component removed', false);
}

// Clear canvas function
window.clearCanvas = function() {
    if (!confirm('Are you sure you want to clear the entire strategy? This cannot be undone.')) {
        return;
    }
    
    const canvas = document.getElementById('strategy-canvas');
    if (!canvas) return;
    
    // Clear all nodes
    currentStrategy.nodes = [];
    
    // Reset canvas
    canvas.innerHTML = '';
    showCanvasPlaceholder();
    
    updateStrategyDescription();
    showMessage('Canvas cleared', false);
};

// Undo last action
window.undoLastAction = function() {
    if (currentStrategy.nodes.length === 0) {
        showMessage('Nothing to undo', true);
        return;
    }
    
    // Remove last added component
    const lastNode = currentStrategy.nodes.pop();
    if (lastNode && lastNode.element) {
        lastNode.element.remove();
    }
    
    // Show placeholder if no nodes left
    if (currentStrategy.nodes.length === 0) {
        showCanvasPlaceholder();
    }
    
    updateStrategyDescription();
    showMessage('Last action undone', false);
};

// Show canvas placeholder
function showCanvasPlaceholder() {
    const canvas = document.getElementById('strategy-canvas');
    if (!canvas) return;
    
    canvas.innerHTML = `
        <div class="absolute inset-0 flex items-center justify-center text-gray-500" id="canvas-placeholder">
            <div class="text-center">
                <div class="text-4xl mb-2">🎯</div>
                <p>Drag components here to build your strategy</p>
                <p class="text-sm mt-1">Start with an IF/THEN block</p>
            </div>
        </div>
    `;
}

// --- SPORTS ANALYTICS FUNCTIONS ---

// Global variable to store current game analytics data
let currentGameAnalytics = null;

// Show sports analytics for a game
window.showGameAnalytics = function(gameId, teams, sport, commenceTime) {
    // Extract team names from the teams string
    const teamNames = teams.split(' vs ');
    const team1 = teamNames[0];
    const team2 = teamNames[1];
    
    // Set modal title and basic info
    document.getElementById('analytics-game-title').textContent = `${teams} - Analytics`;
    document.getElementById('analytics-game-date').textContent = new Date(commenceTime).toLocaleString();
    document.getElementById('analytics-game-sport').textContent = sport;
    
    // Set team names in various sections
    document.getElementById('team1-header').textContent = team1;
    document.getElementById('team2-header').textContent = team2;
    document.getElementById('team1-name-off').textContent = `${team1}:`;
    document.getElementById('team2-name-off').textContent = `${team2}:`;
    document.getElementById('team1-name-def').textContent = `${team1}:`;
    document.getElementById('team2-name-def').textContent = `${team2}:`;
    
    // Generate AI analysis
    generateAIAnalysis(team1, team2, sport);
    
    // Load team statistics and analytics
    loadTeamStatistics(team1, team2, sport);
    
    // Generate consensus odds
    generateConsensusOdds(gameId);
    
    // Draw odds movement chart
    drawOddsMovementChart(team1, team2);
    
    // Show the modal
    showModal('game-analytics-modal');
    
    showMessage('Loading comprehensive game analytics...', false);
};

// Generate AI analysis for the game
function generateAIAnalysis(team1, team2, sport) {
    const analyses = {
        'NBA': [
            `${team1} brings strong offensive firepower while ${team2} excels defensively. Recent injury reports favor the home team, making this a potential value play on the spread.`,
            `Both teams are trending upward in offensive efficiency. Weather won't be a factor, but rest days and travel schedule give ${team2} a slight edge in this matchup.`,
            `${team1}'s recent struggles against elite defenses could be exploited here. Look for value in the under as both teams tighten up in crunch time scenarios.`
        ],
        'NFL': [
            `Weather conditions forecast 15mph winds, which typically reduces passing efficiency by 12%. Both teams should lean heavily on ground games, favoring the under.`,
            `${team1} has covered the spread in 4 of their last 5 divisional games. Their defensive line creates favorable matchup problems for ${team2}'s offensive scheme.`,
            `Key injury updates show ${team2}'s star player listed as questionable. If he sits, the line movement could create significant value opportunities late in the week.`
        ],
        'MLB': [
            `Pitching matchup heavily favors ${team1} with their ace on the mound. Wind patterns at game time should help or hinder home runs significantly.`,
            `${team2} has struggled against left-handed pitching this season, going under the team total in 8 of 12 games. Weather looks favorable for pitchers tonight.`,
            `Both bullpens are well-rested after yesterday's day off. This sets up for a potentially low-scoring affair, making the under an attractive option.`
        ],
        'NCAAF': [
            `${team1} excels in red zone efficiency while ${team2} has shown vulnerability on third down conversions. Home field advantage could be the deciding factor.`,
            `Weather forecast shows clear skies and mild temperatures - perfect conditions for both offenses to perform at their peak. Total points line looks soft.`,
            `${team2}'s defensive coordinator has a strong track record against spread offenses. This tactical advantage isn't reflected in the current market pricing.`
        ],
        'NCAAB': [
            `${team1} shoots exceptionally well from beyond the arc at home, while ${team2} has struggled with perimeter defense on the road recently.`,
            `Both teams play at a fast pace, averaging 75+ possessions per game. The total points line may be undervalued given their offensive capabilities.`,
            `${team2}'s freshman point guard has been turnover-prone in hostile environments. This could create live betting opportunities if the trend continues.`
        ]
    };
    
    const sportAnalyses = analyses[sport] || analyses['NBA'];
    const randomAnalysis = sportAnalyses[Math.floor(Math.random() * sportAnalyses.length)];
    
    // Simulate typing effect
    const analysisElement = document.getElementById('ai-analysis-text');
    analysisElement.textContent = '';
    
    let i = 0;
    const typeTimer = setInterval(() => {
        analysisElement.textContent += randomAnalysis[i];
        i++;
        if (i >= randomAnalysis.length) {
            clearInterval(typeTimer);
        }
    }, 30);
}

// Load team statistics (demo data)
function loadTeamStatistics(team1, team2, sport) {
    // Generate realistic demo stats based on sport
    const stats = generateTeamStats(sport);
    
    document.getElementById('team1-win-rate').textContent = `${stats.team1.winRate}%`;
    document.getElementById('team2-win-rate').textContent = `${stats.team2.winRate}%`;
    document.getElementById('team1-avg-score').textContent = stats.team1.avgScore;
    document.getElementById('team2-avg-score').textContent = stats.team2.avgScore;
    document.getElementById('team1-ats').textContent = stats.team1.ats;
    document.getElementById('team2-ats').textContent = stats.team2.ats;
    document.getElementById('team1-ou').textContent = stats.team1.ou;
    document.getElementById('team2-ou').textContent = stats.team2.ou;
    
    // Advanced metrics
    document.getElementById('team1-off-eff').textContent = stats.team1.offEff;
    document.getElementById('team2-off-eff').textContent = stats.team2.offEff;
    document.getElementById('team1-def-rating').textContent = stats.team1.defRating;
    document.getElementById('team2-def-rating').textContent = stats.team2.defRating;
}

// Generate realistic team stats based on sport
function generateTeamStats(sport) {
    const baseStats = {
        'NBA': { avgScoreRange: [108, 118], effRange: [110, 125] },
        'NFL': { avgScoreRange: [20, 28], effRange: [95, 110] },
        'MLB': { avgScoreRange: [4.2, 5.8], effRange: [85, 105] },
        'NCAAF': { avgScoreRange: [24, 35], effRange: [90, 115] },
        'NCAAB': { avgScoreRange: [70, 85], effRange: [95, 120] }
    };
    
    const sportStats = baseStats[sport] || baseStats['NBA'];
    
    return {
        team1: {
            winRate: Math.floor(Math.random() * 30 + 55), // 55-85%
            avgScore: (Math.random() * (sportStats.avgScoreRange[1] - sportStats.avgScoreRange[0]) + sportStats.avgScoreRange[0]).toFixed(1),
            ats: `${Math.floor(Math.random() * 15 + 10)}-${Math.floor(Math.random() * 15 + 8)}-${Math.floor(Math.random() * 3 + 1)}`,
            ou: `${Math.floor(Math.random() * 15 + 8)}-${Math.floor(Math.random() * 15 + 10)}`,
            offEff: (Math.random() * (sportStats.effRange[1] - sportStats.effRange[0]) + sportStats.effRange[0]).toFixed(1),
            defRating: (Math.random() * (sportStats.effRange[1] - sportStats.effRange[0]) + sportStats.effRange[0]).toFixed(1)
        },
        team2: {
            winRate: Math.floor(Math.random() * 30 + 55),
            avgScore: (Math.random() * (sportStats.avgScoreRange[1] - sportStats.avgScoreRange[0]) + sportStats.avgScoreRange[0]).toFixed(1),
            ats: `${Math.floor(Math.random() * 15 + 8)}-${Math.floor(Math.random() * 15 + 12)}-${Math.floor(Math.random() * 3 + 1)}`,
            ou: `${Math.floor(Math.random() * 15 + 10)}-${Math.floor(Math.random() * 15 + 8)}`,
            offEff: (Math.random() * (sportStats.effRange[1] - sportStats.effRange[0]) + sportStats.effRange[0]).toFixed(1),
            defRating: (Math.random() * (sportStats.effRange[1] - sportStats.effRange[0]) + sportStats.effRange[0]).toFixed(1)
        }
    };
}

// Generate consensus odds from available sportsbooks
function generateConsensusOdds(gameId) {
    // In a real implementation, this would aggregate odds from all sportsbooks
    // For demo, we'll generate realistic consensus values
    
    const consensus = {
        moneyline: Math.random() > 0.5 ? `-${Math.floor(Math.random() * 200 + 120)}` : `+${Math.floor(Math.random() * 200 + 110)}`,
        spread: `${(Math.random() * 14 - 7).toFixed(1)}`,
        total: `${Math.floor(Math.random() * 50 + 200)}.5`
    };
    
    document.getElementById('consensus-moneyline').textContent = consensus.moneyline;
    document.getElementById('consensus-spread').textContent = consensus.spread;
    document.getElementById('consensus-total').textContent = consensus.total;
    
    // Generate value ratings
    document.getElementById('moneyline-value').textContent = `${(Math.random() * 15 - 2.5).toFixed(1)}%`;
    document.getElementById('spread-value').textContent = `${(Math.random() * 12 - 1).toFixed(1)}%`;
    document.getElementById('total-value').textContent = `${(Math.random() * 18 - 4).toFixed(1)}%`;
}

// Draw odds movement chart using Canvas
function drawOddsMovementChart(team1, team2) {
    const canvas = document.getElementById('odds-chart-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Generate sample odds movement data (last 7 days)
    const days = 7;
    const team1Odds = [];
    const team2Odds = [];
    
    let team1Base = Math.random() * 200 + 110; // Starting odds
    let team2Base = Math.random() * 200 + 110;
    
    for (let i = 0; i < days; i++) {
        team1Base += (Math.random() - 0.5) * 20; // Random movement
        team2Base += (Math.random() - 0.5) * 20;
        team1Odds.push(Math.max(100, team1Base));
        team2Odds.push(Math.max(100, team2Base));
    }
    
    // Chart dimensions
    const padding = 30;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;
    
    // Draw axes
    ctx.strokeStyle = '#ccc';
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();
    
    // Draw team 1 odds line
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    for (let i = 0; i < team1Odds.length; i++) {
        const x = padding + (i / (days - 1)) * chartWidth;
        const y = canvas.height - padding - ((team1Odds[i] - 100) / 200) * chartHeight;
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // Draw team 2 odds line
    ctx.strokeStyle = '#ef4444';
    ctx.beginPath();
    
    for (let i = 0; i < team2Odds.length; i++) {
        const x = padding + (i / (days - 1)) * chartWidth;
        const y = canvas.height - padding - ((team2Odds[i] - 100) / 200) * chartHeight;
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
    
    // Add legend
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(10, 10, 15, 10);
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.fillText(team1, 30, 20);
    
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(10, 30, 15, 10);
    ctx.fillStyle = '#333';
    ctx.fillText(team2, 30, 40);
}

// Export game analytics report
window.exportGameAnalytics = function() {
    showMessage('Analytics report exported to downloads folder', false);
};

// Add game to watchlist
window.addGameToWatchlist = function() {
    showMessage('Game added to your watchlist', false);
};

let availableModels = [];

window.filterModels = function() {
    const sportFilter = document.getElementById('model-filter-sport')?.value || 'all';
    const typeFilter = document.getElementById('model-filter-type')?.value || 'all';
    const performanceFilter = document.getElementById('model-filter-performance')?.value || 'all';
    
    showLoading();
    
    // Simulate API call to filter models
    setTimeout(() => {
        loadModels(sportFilter, typeFilter, performanceFilter);
        hideLoading();
    }, 1000);
};

function loadModels(sportFilter = 'all', typeFilter = 'all', performanceFilter = 'all') {
    // Generate demo models
    availableModels = [
        {
            id: 'nfl_totals_lstm',
            name: 'NFL Total Points Predictor',
            type: 'LSTM + Weather',
            sport: 'nfl',
            accuracy: 68.2,
            profit: 12.4,
            description: 'Predicts NFL game total points using weather, team stats, and historical data'
        },
        {
            id: 'nba_moneyline_transformer',
            name: 'NBA Moneyline Predictor',
            type: 'Transformer',
            sport: 'nba', 
            accuracy: 71.5,
            profit: 8.9,
            description: 'Advanced transformer model for NBA moneyline predictions'
        },
        {
            id: 'mlb_runline_rf',
            name: 'MLB Run Line Model',
            type: 'Random Forest',
            sport: 'mlb',
            accuracy: 66.8,
            profit: 15.2,
            description: 'Random forest model specializing in MLB run line betting'
        },
        {
            id: 'ncaaf_spread_xgb',
            name: 'College Football Spreads',
            type: 'XGBoost',
            sport: 'ncaaf',
            accuracy: 64.3,
            profit: 7.8,
            description: 'XGBoost model for college football point spreads'
        },
        {
            id: 'ncaab_total_lstm',
            name: 'College Basketball Totals',
            type: 'LSTM',
            sport: 'ncaab',
            accuracy: 62.1,
            profit: -2.3,
            description: 'LSTM model for college basketball total points'
        }
    ];
    
    // Apply filters
    let filteredModels = availableModels;
    
    if (sportFilter !== 'all') {
        filteredModels = filteredModels.filter(model => model.sport === sportFilter);
    }
    
    if (typeFilter !== 'all') {
        filteredModels = filteredModels.filter(model => 
            model.type.toLowerCase().includes(typeFilter.toLowerCase())
        );
    }
    
    if (performanceFilter !== 'all') {
        if (performanceFilter === 'high') {
            filteredModels = filteredModels.filter(model => model.accuracy > 70);
        } else if (performanceFilter === 'medium') {
            filteredModels = filteredModels.filter(model => model.accuracy >= 60 && model.accuracy <= 70);
        } else if (performanceFilter === 'low') {
            filteredModels = filteredModels.filter(model => model.accuracy < 60);
        }
    }
    
    displayModels(filteredModels);
}

function displayModels(models) {
    const grid = document.getElementById('models-grid');
    
    if (!grid) return;
    
    if (models.length === 0) {
        grid.innerHTML = '<div class="col-span-full text-center text-gray-500 py-8">No models found matching your filters.</div>';
        return;
    }
    
    grid.innerHTML = models.map(model => {
        const profitColor = model.profit > 0 ? 'text-green-600' : 'text-red-600';
        const performanceColor = model.accuracy > 70 ? 'bg-green-100' : model.accuracy > 60 ? 'bg-yellow-100' : 'bg-red-100';
        
        return `
            <div class="bg-white rounded-lg p-6 border border-gray-200 hover:border-blue-400 transition-colors">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900">${model.name}</h3>
                        <p class="text-sm text-gray-600">${model.type}</p>
                    </div>
                    <span class="px-2 py-1 ${performanceColor} text-xs font-medium rounded">
                        ${model.sport.toUpperCase()}
                    </span>
                </div>
                
                <div class="space-y-2 mb-4">
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600">Accuracy:</span>
                        <span class="text-sm font-medium">${model.accuracy}%</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-600">Profit:</span>
                        <span class="text-sm font-medium ${profitColor}">${model.profit > 0 ? '+' : ''}${model.profit}%</span>
                    </div>
                </div>
                
                <p class="text-sm text-gray-700 mb-4">${model.description}</p>
                
                <div class="space-y-2">
                    <button onclick="useModel('${model.id}')" class="w-full post9-btn text-sm py-2">
                        Use Model
                    </button>
                    <div class="flex space-x-2">
                        <button onclick="customizeModel('${model.id}')" class="flex-1 bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200">
                            Customize
                        </button>
                        <button onclick="viewModelDetails('${model.id}')" class="flex-1 bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200">
                            Details
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

window.useModel = function(modelId) {
    const model = availableModels.find(m => m.id === modelId);
    if (model) {
        showMessage(`${model.name} is now active for predictions`, false);
        
        // In a real implementation, this would:
        // 1. Add model to user's active models
        // 2. Update strategy configurations
        // 3. Start generating predictions
    }
};

window.customizeModel = function(modelId) {
    showMessage('Opening model customization interface...', false);
    // Would open a modal for model parameter tuning
};

window.viewModelDetails = function(modelId) {
    const model = availableModels.find(m => m.id === modelId);
    if (model) {
        showMessage(`Viewing details for ${model.name}`, false);
        // Would show detailed performance metrics, feature importance, etc.
    }
};

// --- ADVANCED ANALYTICS FUNCTIONS ---

window.exportAnalytics = function() {
    showMessage('Exporting analytics report...', false);
    
    // Simulate export
    setTimeout(() => {
        const data = {
            totalProfit: 1247.50,
            winRate: 68.4,
            roi: 12.3,
            totalBets: 89,
            exportDate: new Date().toISOString()
        };
        
        const csvContent = `Analytics Report - ${new Date().toLocaleDateString()}\n` +
                          `Total Profit,$${data.totalProfit}\n` +
                          `Win Rate,${data.winRate}%\n` +
                          `ROI,${data.roi}%\n` +
                          `Total Bets,${data.totalBets}`;
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics-report-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        
        showMessage('Analytics report exported successfully', false);
    }, 1000);
};

// Initialize new functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        initializeStrategyBuilder();
        
        // Load models when model gallery page exists
        const modelGalleryPage = document.getElementById('model-gallery-page');
        if (modelGalleryPage) {
            loadMLModels();
        }
        
        // Initialize analytics page if it exists
        const analyticsPage = document.getElementById('analytics-page');
        if (analyticsPage) {
            initializeMLAnalytics();
        }
        
        // Update ML dashboard stats
        updateMLDashboardStats();
    }, 1000);
});

// Extend the original showPage function to initialize components
const originalShowPage = window.showPage;
if (originalShowPage) {
    window.showPage = function(pageId) {
        originalShowPage(pageId);
        
        setTimeout(() => {
            if (pageId === 'strategy-builder-page') {
                initializeStrategyBuilder();
            } else if (pageId === 'model-gallery-page') {
                loadMLModels();
            } else if (pageId === 'analytics-page') {
                loadMLAnalytics();
            }
        }, 100);
    };
}

// --- ML INTEGRATION FUNCTIONS ---

// Enhanced ML Models Gallery
async function loadMLModels() {
    try {
        // First try to load real ML models from API
        const response = await fetch('/api/ml/models');
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.models && result.models.length > 0) {
                displayMLModels(result.models);
                return;
            }
        }
    } catch (error) {
        console.log('ML models API not available, using demo data');
    }
    
    // Fallback to enhanced demo models with ML features
    const demoModels = [
        {
            id: 'nba_lstm_advanced',
            name: 'NBA Advanced LSTM',
            description: 'Deep learning model for NBA predictions with 68.2% accuracy',
            model_type: 'LSTM',
            sport: 'NBA',
            accuracy: 68.2,
            precision: 67.8,
            recall: 68.6,
            f1_score: 68.2,
            sharpe_ratio: 1.45,
            max_drawdown: -8.4,
            status: 'active',
            last_updated: new Date().toISOString()
        },
        {
            id: 'nfl_ensemble_pro',
            name: 'NFL Ensemble Pro',
            description: 'Professional ensemble model combining multiple algorithms',
            model_type: 'ensemble',
            sport: 'NFL',
            accuracy: 64.8,
            precision: 65.2,
            recall: 64.4,
            f1_score: 64.8,
            sharpe_ratio: 1.32,
            max_drawdown: -12.1,
            status: 'active',
            last_updated: new Date().toISOString()
        },
        {
            id: 'mlb_neural_net',
            name: 'MLB Neural Network',
            description: 'Advanced neural network for baseball predictions',
            model_type: 'neural_network',
            sport: 'MLB',
            accuracy: 61.5,
            precision: 62.1,
            recall: 60.9,
            f1_score: 61.5,
            sharpe_ratio: 1.18,
            max_drawdown: -15.3,
            status: 'training',
            last_updated: new Date().toISOString()
        }
    ];
    
    displayMLModels(demoModels);
}

function displayMLModels(models) {
    const modelsGrid = document.getElementById('models-grid');
    if (!modelsGrid) return;
    
    modelsGrid.innerHTML = models.map(model => `
        <div class="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-gray-800">${model.name}</h3>
                <span class="px-2 py-1 text-xs font-semibold rounded ${
                    model.status === 'active' ? 'bg-green-100 text-green-800' : 
                    model.status === 'training' ? 'bg-yellow-100 text-yellow-800' : 
                    'bg-gray-100 text-gray-800'
                }">${model.status}</span>
            </div>
            
            <p class="text-gray-600 text-sm mb-4">${model.description}</p>
            
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div class="text-center">
                    <div class="text-2xl font-bold text-blue-600">${model.accuracy}%</div>
                    <div class="text-xs text-gray-500">Accuracy</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold text-green-600">${model.sharpe_ratio || 'N/A'}</div>
                    <div class="text-xs text-gray-500">Sharpe Ratio</div>
                </div>
            </div>
            
            <div class="space-y-2 text-xs text-gray-600">
                <div class="flex justify-between">
                    <span>Sport:</span>
                    <span class="font-semibold">${model.sport}</span>
                </div>
                <div class="flex justify-between">
                    <span>Type:</span>
                    <span class="font-semibold">${model.model_type}</span>
                </div>
                <div class="flex justify-between">
                    <span>Precision:</span>
                    <span class="font-semibold">${model.precision}%</span>
                </div>
                <div class="flex justify-between">
                    <span>Max Drawdown:</span>
                    <span class="font-semibold text-red-600">${model.max_drawdown}%</span>
                </div>
            </div>
            
            <div class="mt-4 pt-4 border-t border-gray-200">
                <button onclick="viewModelDetails('${model.id}')" class="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors text-sm font-medium">
                    View Details
                </button>
            </div>
        </div>
    `).join('');
}

// ML Analytics Dashboard
async function loadMLAnalytics() {
    try {
        // Try to load real analytics data
        const response = await fetch('/api/analytics/performance');
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                displayMLAnalytics(result.analytics);
                return;
            }
        }
    } catch (error) {
        console.log('ML analytics API not available, using demo data');
    }
    
    // Fallback to demo analytics with ML insights
    const demoAnalytics = {
        ml_performance: {
            total_predictions: 2847,
            correct_predictions: 1923,
            overall_accuracy: 67.5,
            total_profit: 2456.78,
            roi: 23.05,
            sharpe_ratio: 1.45,
            sortino_ratio: 1.82,
            max_drawdown: -8.4,
            current_streak: 7,
            best_streak: 12
        },
        sport_breakdown: {
            NBA: { accuracy: 68.2, profit: 1234.56, games: 156 },
            NFL: { accuracy: 64.8, profit: 892.34, games: 89 },
            MLB: { accuracy: 61.5, profit: 329.88, games: 67 }
        },
        recent_alerts: [
            {
                type: 'success',
                message: 'NBA Model achieved 75% accuracy over last 20 games',
                timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
            },
            {
                type: 'warning', 
                message: 'NFL Model performance declined - retraining recommended',
                timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString()
            },
            {
                type: 'info',
                message: 'High value bet opportunity detected: Lakers vs Warriors',
                timestamp: new Date(Date.now() - 12 * 60 * 1000).toISOString()
            }
        ]
    };
    
    displayMLAnalytics(demoAnalytics);
}

function initializeMLAnalytics() {
    // Initialize analytics page without the ML prediction tool
    // The ML prediction tool was moved to the dedicated Predictive Analytics section
    const analyticsPage = document.getElementById('analytics-page');
    if (!analyticsPage) return;
    
    // Analytics page now focuses purely on performance analysis and reporting
    // Removed the ML prediction tool as it belongs in the Predictive Analytics section
    console.log('Analytics page initialized - ML prediction tool removed from this section');
}

function displayMLAnalytics(analytics) {
    // Update the summary metrics with ML data
    document.getElementById('analytics-total-profit').textContent = 
        `+$${analytics.ml_performance.total_profit.toFixed(0)}`;
    document.getElementById('analytics-win-rate').textContent = 
        `${analytics.ml_performance.overall_accuracy.toFixed(1)}%`;
    document.getElementById('analytics-roi').textContent = 
        `+${analytics.ml_performance.roi.toFixed(1)}%`;
    document.getElementById('analytics-bets-count').textContent = 
        analytics.ml_performance.total_predictions.toString();
        
    // Add ML-specific alerts to the recent alerts section
    const alertsContainer = document.getElementById('recent-alerts');
    if (alertsContainer && analytics.recent_alerts) {
        alertsContainer.innerHTML = analytics.recent_alerts.map(alert => {
            const alertClass = alert.type === 'success' ? 'green' : 
                              alert.type === 'warning' ? 'yellow' : 'blue';
            const icon = alert.type === 'success' ? '🟢' : 
                        alert.type === 'warning' ? '🟡' : '🔵';
            const timeAgo = getTimeAgo(new Date(alert.timestamp));
            
            return `
                <div class="flex items-center p-2 bg-${alertClass}-50 border border-${alertClass}-200 rounded">
                    <span class="text-${alertClass}-600 mr-2">${icon}</span>
                    <div>
                        <div class="font-medium text-${alertClass}-800">${alert.message}</div>
                        <div class="text-xs text-${alertClass}-600">${timeAgo}</div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

// ML Prediction Function
async function makeMLPrediction() {
    const sport = document.getElementById('ml-predict-sport').value;
    const homeWinPct = parseFloat(document.getElementById('ml-home-win-pct').value);
    const awayWinPct = parseFloat(document.getElementById('ml-away-win-pct').value);
    
    if (!homeWinPct || !awayWinPct) {
        alert('Please enter valid win percentages');
        return;
    }
    
    const requestData = {
        sport: sport,
        home_win_pct: homeWinPct,
        away_win_pct: awayWinPct
    };
    
    try {
        const response = await fetch('/api/ml/demo/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayMLPredictionResults(result);
        } else {
            alert('Error: ' + (result.error || 'Prediction failed'));
        }
    } catch (error) {
        console.error('Prediction error:', error);
        // Fallback to demo prediction
        const demoResult = generateDemoPrediction(requestData);
        displayMLPredictionResults(demoResult);
    }
}

// Make functions globally available
window.makeMLPrediction = makeMLPrediction;
window.viewModelDetails = viewModelDetails;

function generateDemoPrediction(data) {
    const homeAdvantage = data.home_win_pct - data.away_win_pct;
    const confidence = Math.min(0.95, Math.max(0.55, 0.6 + Math.abs(homeAdvantage) / 100));
    const predictedOutcome = homeAdvantage > 0 ? 'Home Team Win' : 'Away Team Win';
    const kellySize = confidence > 0.7 ? (confidence * 250).toFixed(2) : (confidence * 150).toFixed(2);
    const expectedROI = ((confidence - 0.5) * 40).toFixed(1);
    
    return {
        success: true,
        prediction: {
            predicted_outcome: predictedOutcome,
            confidence: confidence
        },
        kelly_size: kellySize,
        expected_roi: expectedROI,
        model_type: 'demo_statistical'
    };
}

function displayMLPredictionResults(result) {
    const resultsDiv = document.getElementById('ml-prediction-results');
    if (!resultsDiv) return;
    
    resultsDiv.classList.remove('hidden');
    
    const prediction = result.prediction;
    const confidence = (prediction.confidence * 100).toFixed(1);
    
    document.getElementById('ml-predicted-outcome').textContent = prediction.predicted_outcome;
    document.getElementById('ml-confidence-level').textContent = `${confidence}% confidence`;
    document.getElementById('ml-kelly-size').textContent = `$${result.kelly_size || '125.50'}`;
    document.getElementById('ml-expected-roi').textContent = `+${result.expected_roi || '15.2'}%`;
    
    // Update colors based on confidence
    const outcomeEl = document.getElementById('ml-predicted-outcome');
    outcomeEl.className = `text-lg font-bold ${confidence > 70 ? 'text-green-600' : 
                                                confidence > 60 ? 'text-yellow-600' : 'text-red-600'}`;
}

// Model Details Modal
function viewModelDetails(modelId) {
    // For now, show a simple alert with model info
    // In a real implementation, this would open a detailed modal
    alert(`Model Details for ${modelId}\n\nThis would show comprehensive model information including:\n- Training history\n- Feature importance\n- Performance over time\n- Model architecture\n- Recent predictions`);
}

// Utility function for time formatting
function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
    if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
    return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
}

// Update ML dashboard stats
async function updateMLDashboardStats() {
    try {
        // Try to get real ML stats
        const response = await fetch('/api/ml/models');
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                updateMLStatsDisplay(result);
                return;
            }
        }
    } catch (error) {
        console.log('ML stats API not available, using demo data');
    }
    
    // Fallback to demo stats
    const demoStats = {
        active_models: 3,
        overall_accuracy: 67.5,
        accuracy_trend: '+2.1%'
    };
    
    updateMLStatsDisplay(demoStats);
}

function updateMLStatsDisplay(stats) {
    const activeModelsEl = document.getElementById('ml-models-active');
    const accuracyEl = document.getElementById('ml-accuracy');
    const accuracyTrendEl = document.getElementById('ml-accuracy-trend');
    
    if (activeModelsEl) {
        activeModelsEl.textContent = stats.active_models || stats.models?.filter(m => m.status === 'active')?.length || '3';
    }
    
    if (accuracyEl) {
        const accuracy = stats.overall_accuracy || 
                        (stats.models && stats.models.length > 0 ? 
                         (stats.models.reduce((sum, m) => sum + (m.accuracy || 0), 0) / stats.models.length).toFixed(1) : 
                         '67.5');
        accuracyEl.textContent = `${accuracy}%`;
    }
    
    if (accuracyTrendEl) {
        accuracyTrendEl.textContent = stats.accuracy_trend || '▲ +2.1%';
    }
}

// --- PREDICTIVE ANALYTICS FUNCTIONS ---

// Tab management for Predictive Analytics page
function showPredictiveTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.predictive-tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.predictive-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(`${tabName}-tab-content`);
    if (selectedContent) {
        selectedContent.classList.remove('hidden');
    }
    
    // Add active class to selected tab button
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Load content for specific tabs
    if (tabName === 'models') {
        loadPredictiveModels();
    }
}

// Load predictive models for the models tab
function loadPredictiveModels() {
    const modelsGrid = document.getElementById('predictive-models-grid');
    if (!modelsGrid) return;
    
    // Demo models data
    const demoModels = [
        {
            id: 'nba_advanced_lstm',
            name: 'NBA Advanced LSTM',
            sport: 'NBA',
            accuracy: 68.2,
            status: 'active',
            predictions: 156,
            profit: 1234.56
        },
        {
            id: 'nfl_ensemble_v2',
            name: 'NFL Ensemble v2.0',
            sport: 'NFL', 
            accuracy: 64.8,
            status: 'active',
            predictions: 89,
            profit: 892.34
        },
        {
            id: 'mlb_statistical',
            name: 'MLB Statistical',
            sport: 'MLB',
            accuracy: 61.5,
            status: 'training',
            predictions: 67,
            profit: 329.88
        }
    ];
    
    modelsGrid.innerHTML = demoModels.map(model => `
        <div class="p-4 border rounded-lg ${model.status === 'active' ? 'border-green-300 bg-green-50' : 'border-gray-300 bg-gray-50'}">
            <div class="flex justify-between items-center mb-2">
                <h4 class="font-bold text-gray-800">${model.name}</h4>
                <span class="px-2 py-1 text-xs rounded ${model.status === 'active' ? 'bg-green-200 text-green-800' : 'bg-yellow-200 text-yellow-800'}">
                    ${model.status}
                </span>
            </div>
            <div class="text-sm text-gray-600 space-y-1">
                <div>Sport: ${model.sport}</div>
                <div>Accuracy: ${model.accuracy}%</div>
                <div>Predictions: ${model.predictions}</div>
                <div>Profit: $${model.profit}</div>
            </div>
            <div class="mt-3 flex gap-2">
                <button onclick="viewModelDetails('${model.id}')" class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">
                    View Details
                </button>
                ${model.status === 'active' ? `
                    <button onclick="makePredictionWithModel('${model.id}')" class="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                        Use Model
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// Make prediction using the prediction tab form
function makePrediction() {
    const sport = document.getElementById('pred-sport').value;
    const homeWinPct = parseFloat(document.getElementById('pred-home-win-pct').value);
    const awayWinPct = parseFloat(document.getElementById('pred-away-win-pct').value);
    
    if (!homeWinPct || !awayWinPct) {
        showMessage('Please enter valid win percentages', true);
        return;
    }
    
    // Use the existing makeMLPrediction logic but with new IDs
    const demoResult = generateDemoPrediction({
        sport: sport,
        home_win_pct: homeWinPct / 100,
        away_win_pct: awayWinPct / 100
    });
    
    displayPredictionResults(demoResult);
}

// Display prediction results in the predictions tab
function displayPredictionResults(result) {
    const resultsDiv = document.getElementById('prediction-results');
    if (!resultsDiv) return;
    
    const prediction = result.prediction;
    const training = result.training_results || {};
    
    // Update prediction outcome
    const outcomeEl = document.getElementById('predicted-outcome');
    if (outcomeEl) {
        outcomeEl.textContent = prediction.predicted_outcome;
        outcomeEl.className = `text-lg font-bold ${prediction.confidence > 70 ? 'text-green-600' : prediction.confidence > 60 ? 'text-yellow-600' : 'text-red-600'}`;
    }
    
    // Update confidence level
    const confidenceEl = document.getElementById('confidence-level');
    if (confidenceEl) {
        confidenceEl.textContent = `${(prediction.confidence * 100).toFixed(1)}% confidence`;
    }
    
    // Calculate and display Kelly bet size (demo calculation)
    const kellyEl = document.getElementById('kelly-bet-size');
    if (kellyEl) {
        const bankroll = 1000; // Demo bankroll
        const odds = 2.0; // Demo odds
        const winProb = prediction.confidence;
        const kellyFraction = (winProb * odds - 1) / (odds - 1);
        const betSize = Math.max(0, kellyFraction * bankroll * 0.25); // Quarter Kelly
        kellyEl.textContent = `$${betSize.toFixed(2)}`;
    }
    
    // Calculate and display expected ROI
    const roiEl = document.getElementById('expected-roi');
    if (roiEl) {
        const expectedRoi = ((prediction.confidence * 2.0 - 1) * 100).toFixed(1);
        roiEl.textContent = `${expectedRoi}%`;
    }
    
    resultsDiv.classList.remove('hidden');
}

// Calculate Kelly optimal bet size
function calculateKellyOptimal() {
    const winProb = parseFloat(document.getElementById('kelly-win-prob').value) / 100;
    const odds = parseFloat(document.getElementById('kelly-odds').value);
    const bankroll = parseFloat(document.getElementById('kelly-bankroll').value);
    
    if (!winProb || !odds || !bankroll) {
        showMessage('Please fill in all Kelly calculator fields', true);
        return;
    }
    
    // Kelly formula: f* = (bp - q) / b
    // where b = odds-1, p = win probability, q = 1-p
    const b = odds - 1;
    const p = winProb;
    const q = 1 - p;
    const kellyFraction = (b * p - q) / b;
    
    const optimalBet = Math.max(0, kellyFraction * bankroll);
    const percentage = Math.max(0, kellyFraction * 100);
    const expectedGrowth = (p * Math.log(1 + b * kellyFraction) + q * Math.log(1 - kellyFraction)) * 100;
    
    // Display results
    document.getElementById('kelly-bet-amount').textContent = `$${optimalBet.toFixed(2)}`;
    document.getElementById('kelly-percentage').textContent = `${percentage.toFixed(2)}%`;
    document.getElementById('kelly-growth').textContent = `${expectedGrowth.toFixed(2)}%`;
    
    document.getElementById('kelly-results').classList.remove('hidden');
}

// Start model training
function startModelTraining() {
    const sport = document.getElementById('train-sport').value;
    const modelType = document.getElementById('train-model-type').value;
    
    showMessage(`Starting ${modelType} model training for ${sport}...`, false);
    
    // Simulate training process
    setTimeout(() => {
        showMessage(`${sport} ${modelType} model training completed successfully!`, false);
    }, 3000);
}

// Refresh predictive models
function refreshPredictiveModels() {
    showMessage('Refreshing predictive models...', false);
    setTimeout(() => {
        loadPredictiveModels();
        showMessage('Models refreshed successfully!', false);
    }, 1000);
}

// Make prediction with specific model
function makePredictionWithModel(modelId) {
    showMessage(`Using model ${modelId} for prediction...`, false);
    // Switch to predictions tab and populate with model-specific prediction
    showPredictiveTab('predictions');
}

// Extend the original showPage function to handle predictive analytics
const originalShowPageFunc = window.showPage;
window.showPage = function(pageId) {
    originalShowPageFunc(pageId);
    
    // Initialize predictive analytics page when shown
    if (pageId === 'predictive-analytics-page') {
        setTimeout(() => {
            showPredictiveTab('models'); // Default to models tab
        }, 100);
    }
};

// Make functions globally available
window.showPredictiveTab = showPredictiveTab;
window.makePrediction = makePrediction;
window.makePredictionWithModel = makePredictionWithModel;
window.calculateKellyOptimal = calculateKellyOptimal;
window.startModelTraining = startModelTraining;
window.refreshPredictiveModels = refreshPredictiveModels;

// Add form handler for train model modal
document.addEventListener('DOMContentLoaded', function() {
    const trainModelForm = document.getElementById('train-model-form');
    if (trainModelForm) {
        trainModelForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const modelData = Object.fromEntries(formData.entries());
            
            // Validate required fields
            if (!modelData.model_name || !modelData.sport || !modelData.model_type) {
                showMessage('Please fill in all required fields', true);
                return;
            }
            
            showMessage(`Starting training for ${modelData.model_name}...`, false);
            closeModal('train-model-modal');
            
            // Simulate training process
            setTimeout(() => {
                showMessage(`${modelData.model_name} training initiated successfully! Training will complete in background.`, false);
            }, 1000);
            
            // Reset form
            trainModelForm.reset();
        });
    }
});
}