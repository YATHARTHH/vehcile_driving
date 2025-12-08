// AI Features JavaScript

// Demo functions for each AI feature
function showSentimentDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-heart"></i> Trip Sentiment Analysis Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="sentiment-analysis">
                <h4>Recent Trip Analysis</h4>
                <div class="sentiment-result">
                    <div class="sentiment-card positive">
                        <div class="sentiment-icon"><i class="fas fa-smile"></i></div>
                        <div class="sentiment-info">
                            <h5>Positive Driving Experience</h5>
                            <p>Confidence: 87.3%</p>
                            <div class="sentiment-details">
                                <span class="tag">Smooth acceleration</span>
                                <span class="tag">Consistent speed</span>
                                <span class="tag">Minimal braking</span>
                            </div>
                        </div>
                    </div>
                    <div class="analysis-insights">
                        <h5>AI Insights:</h5>
                        <ul>
                            <li>Your driving pattern shows excellent emotional control</li>
                            <li>Consistent speed maintenance indicates relaxed state</li>
                            <li>Low brake frequency suggests anticipatory driving</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .sentiment-analysis { margin-bottom: 1.5rem; }
            .sentiment-card { 
                background: linear-gradient(135deg, #d4edda, #c3e6cb);
                border-radius: 12px;
                padding: 1.5rem;
                display: flex;
                align-items: center;
                margin-bottom: 1rem;
            }
            .sentiment-icon { 
                font-size: 2rem;
                color: #28a745;
                margin-right: 1rem;
            }
            .sentiment-info h5 { 
                color: #155724;
                margin-bottom: 0.5rem;
            }
            .sentiment-details { 
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
                margin-top: 0.5rem;
            }
            .tag { 
                background: #28a745;
                color: white;
                padding: 0.2rem 0.5rem;
                border-radius: 15px;
                font-size: 0.8rem;
            }
            .analysis-insights ul { 
                list-style: none;
                padding-left: 0;
            }
            .analysis-insights li { 
                padding: 0.3rem 0;
                color: #555;
            }
            .analysis-insights li::before { 
                content: '🧠';
                margin-right: 0.5rem;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showInsightsDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-lightbulb"></i> Smart Trip Insights Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="insights-grid">
                <div class="insight-card excellent">
                    <div class="insight-header">
                        <i class="fas fa-leaf"></i>
                        <h5>Fuel Efficiency</h5>
                        <span class="score">92/100</span>
                    </div>
                    <p>Excellent fuel management with smooth acceleration patterns</p>
                    <div class="recommendation">💡 Maintain current driving style for optimal efficiency</div>
                </div>
                
                <div class="insight-card good">
                    <div class="insight-header">
                        <i class="fas fa-tachometer-alt"></i>
                        <h5>Speed Control</h5>
                        <span class="score">78/100</span>
                    </div>
                    <p>Good speed consistency with minor variations</p>
                    <div class="recommendation">💡 Use cruise control on highways for better consistency</div>
                </div>
                
                <div class="insight-card warning">
                    <div class="insight-header">
                        <i class="fas fa-car-burst"></i>
                        <h5>Braking Smoothness</h5>
                        <span class="score">65/100</span>
                    </div>
                    <p>Frequent hard braking detected</p>
                    <div class="recommendation">⚠️ Increase following distance and anticipate stops</div>
                </div>
            </div>
        </div>
        <style>
            .insights-grid { display: grid; gap: 1rem; }
            .insight-card { 
                border-radius: 10px;
                padding: 1.2rem;
                border-left: 4px solid;
            }
            .insight-card.excellent { 
                background: #d4edda;
                border-color: #28a745;
            }
            .insight-card.good { 
                background: #fff3cd;
                border-color: #ffc107;
            }
            .insight-card.warning { 
                background: #f8d7da;
                border-color: #dc3545;
            }
            .insight-header { 
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.8rem;
            }
            .insight-header i { 
                margin-right: 0.5rem;
            }
            .score { 
                font-weight: bold;
                padding: 0.2rem 0.5rem;
                border-radius: 15px;
                background: rgba(0,0,0,0.1);
            }
            .recommendation { 
                margin-top: 0.8rem;
                font-size: 0.9rem;
                font-style: italic;
                color: #666;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showTipsDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-user-cog"></i> Personalized AI Tips Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="tips-container">
                <div class="tip-card easy">
                    <div class="tip-header">
                        <span class="difficulty easy">Easy</span>
                        <span class="impact">+5% efficiency</span>
                    </div>
                    <h5>Gentle Acceleration</h5>
                    <p>Gradually increase speed instead of rapid acceleration to improve fuel economy.</p>
                    <div class="tip-action">
                        <button class="apply-tip">Apply This Tip</button>
                    </div>
                </div>
                
                <div class="tip-card medium">
                    <div class="tip-header">
                        <span class="difficulty medium">Medium</span>
                        <span class="impact">+12% efficiency</span>
                    </div>
                    <h5>Optimal Speed Maintenance</h5>
                    <p>Maintain speeds between 50-80 km/h for maximum fuel efficiency on highways.</p>
                    <div class="tip-action">
                        <button class="apply-tip">Apply This Tip</button>
                    </div>
                </div>
                
                <div class="tip-card hard">
                    <div class="tip-header">
                        <span class="difficulty hard">Hard</span>
                        <span class="impact">+20% efficiency</span>
                    </div>
                    <h5>Predictive Driving</h5>
                    <p>Anticipate traffic patterns and adjust speed proactively to minimize braking.</p>
                    <div class="tip-action">
                        <button class="apply-tip">Apply This Tip</button>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .tips-container { display: grid; gap: 1rem; }
            .tip-card { 
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                border-top: 4px solid;
            }
            .tip-card.easy { border-color: #28a745; }
            .tip-card.medium { border-color: #ffc107; }
            .tip-card.hard { border-color: #dc3545; }
            .tip-header { 
                display: flex;
                justify-content: space-between;
                margin-bottom: 1rem;
            }
            .difficulty { 
                padding: 0.3rem 0.8rem;
                border-radius: 15px;
                font-size: 0.8rem;
                font-weight: bold;
                color: white;
            }
            .difficulty.easy { background: #28a745; }
            .difficulty.medium { background: #ffc107; }
            .difficulty.hard { background: #dc3545; }
            .impact { 
                color: #28a745;
                font-weight: bold;
            }
            .apply-tip { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                cursor: pointer;
                margin-top: 1rem;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showAnomalyDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Anomaly Detection Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="anomaly-detection">
                <h4>Detected Anomalies</h4>
                <div class="anomaly-list">
                    <div class="anomaly-item high">
                        <div class="anomaly-icon"><i class="fas fa-exclamation-circle"></i></div>
                        <div class="anomaly-info">
                            <h5>Sudden Speed Variations</h5>
                            <p>Severity: High | Detected: 3 times in last trip</p>
                            <div class="anomaly-recommendation">
                                <strong>Recommendation:</strong> Check for traffic conditions or consider route optimization
                            </div>
                        </div>
                    </div>
                    
                    <div class="anomaly-item medium">
                        <div class="anomaly-icon"><i class="fas fa-exclamation-triangle"></i></div>
                        <div class="anomaly-info">
                            <h5>Unusual RPM Patterns</h5>
                            <p>Severity: Medium | Engine stress detected</p>
                            <div class="anomaly-recommendation">
                                <strong>Recommendation:</strong> Schedule engine diagnostic check
                            </div>
                        </div>
                    </div>
                    
                    <div class="anomaly-item low">
                        <div class="anomaly-icon"><i class="fas fa-info-circle"></i></div>
                        <div class="anomaly-info">
                            <h5>Minor Steering Adjustments</h5>
                            <p>Severity: Low | Slight deviation from normal</p>
                            <div class="anomaly-recommendation">
                                <strong>Recommendation:</strong> Monitor tire pressure and alignment
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .anomaly-list { display: grid; gap: 1rem; }
            .anomaly-item { 
                display: flex;
                align-items: flex-start;
                padding: 1.2rem;
                border-radius: 10px;
                border-left: 4px solid;
            }
            .anomaly-item.high { 
                background: #f8d7da;
                border-color: #dc3545;
            }
            .anomaly-item.medium { 
                background: #fff3cd;
                border-color: #ffc107;
            }
            .anomaly-item.low { 
                background: #d1ecf1;
                border-color: #17a2b8;
            }
            .anomaly-icon { 
                margin-right: 1rem;
                font-size: 1.5rem;
            }
            .anomaly-item.high .anomaly-icon { color: #dc3545; }
            .anomaly-item.medium .anomaly-icon { color: #ffc107; }
            .anomaly-item.low .anomaly-icon { color: #17a2b8; }
            .anomaly-recommendation { 
                margin-top: 0.8rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showMaintenanceDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-wrench"></i> Predictive Maintenance Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="maintenance-dashboard">
                <h4>Maintenance Predictions</h4>
                <div class="maintenance-timeline">
                    <div class="maintenance-item urgent">
                        <div class="maintenance-date">Next 500 km</div>
                        <div class="maintenance-details">
                            <h5><i class="fas fa-car-burst"></i> Brake Pads</h5>
                            <p>Predicted wear: 85% | Risk Level: High</p>
                            <button class="schedule-btn urgent">Schedule Now</button>
                        </div>
                    </div>
                    
                    <div class="maintenance-item warning">
                        <div class="maintenance-date">Next 2,000 km</div>
                        <div class="maintenance-details">
                            <h5><i class="fas fa-cog"></i> Engine Oil</h5>
                            <p>Predicted degradation: 60% | Risk Level: Medium</p>
                            <button class="schedule-btn warning">Schedule Soon</button>
                        </div>
                    </div>
                    
                    <div class="maintenance-item normal">
                        <div class="maintenance-date">Next 8,000 km</div>
                        <div class="maintenance-details">
                            <h5><i class="fas fa-circle-dot"></i> Tire Rotation</h5>
                            <p>Predicted wear: 25% | Risk Level: Low</p>
                            <button class="schedule-btn normal">Plan Ahead</button>
                        </div>
                    </div>
                </div>
                
                <div class="maintenance-insights">
                    <h5>AI Insights:</h5>
                    <ul>
                        <li>Your braking patterns suggest accelerated brake pad wear</li>
                        <li>Engine load analysis indicates oil change needed sooner than standard interval</li>
                        <li>Tire pressure monitoring shows even wear distribution</li>
                    </ul>
                </div>
            </div>
        </div>
        <style>
            .maintenance-timeline { margin-bottom: 2rem; }
            .maintenance-item { 
                display: flex;
                margin-bottom: 1.5rem;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .maintenance-date { 
                padding: 1.5rem;
                font-weight: bold;
                color: white;
                min-width: 150px;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
            }
            .maintenance-item.urgent .maintenance-date { background: #dc3545; }
            .maintenance-item.warning .maintenance-date { background: #ffc107; color: #333; }
            .maintenance-item.normal .maintenance-date { background: #28a745; }
            .maintenance-details { 
                flex: 1;
                padding: 1.5rem;
                background: white;
            }
            .schedule-btn { 
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                margin-top: 0.8rem;
            }
            .schedule-btn.urgent { background: #dc3545; color: white; }
            .schedule-btn.warning { background: #ffc107; color: #333; }
            .schedule-btn.normal { background: #28a745; color: white; }
            .maintenance-insights ul { 
                list-style: none;
                padding-left: 0;
            }
            .maintenance-insights li { 
                padding: 0.3rem 0;
                color: #555;
            }
            .maintenance-insights li::before { 
                content: '🔧';
                margin-right: 0.5rem;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showRecommendationsDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-robot"></i> Smart Recommendations Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="recommendations-engine">
                <h4>Contextual Recommendations</h4>
                <div class="context-info">
                    <div class="context-item">
                        <i class="fas fa-cloud-rain"></i>
                        <span>Weather: Rainy</span>
                    </div>
                    <div class="context-item">
                        <i class="fas fa-clock"></i>
                        <span>Time: Rush Hour</span>
                    </div>
                    <div class="context-item">
                        <i class="fas fa-user"></i>
                        <span>Driver: Experienced</span>
                    </div>
                </div>
                
                <div class="recommendations-list">
                    <div class="recommendation-card priority-high">
                        <div class="priority-badge">High Priority</div>
                        <h5><i class="fas fa-shield-alt"></i> Safety First</h5>
                        <p>Reduce speed by 20% due to wet road conditions. Increase following distance to 4+ seconds.</p>
                        <div class="recommendation-impact">Expected: 15% safer journey</div>
                    </div>
                    
                    <div class="recommendation-card priority-medium">
                        <div class="priority-badge">Medium Priority</div>
                        <h5><i class="fas fa-route"></i> Route Optimization</h5>
                        <p>Alternative route available with 12% less traffic. ETA: +5 minutes, Fuel savings: 8%</p>
                        <div class="recommendation-impact">Expected: $2.50 fuel savings</div>
                    </div>
                    
                    <div class="recommendation-card priority-low">
                        <div class="priority-badge">Low Priority</div>
                        <h5><i class="fas fa-music"></i> Comfort Enhancement</h5>
                        <p>Play calming music to reduce stress during heavy traffic conditions.</p>
                        <div class="recommendation-impact">Expected: Better driving experience</div>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .context-info { 
                display: flex;
                gap: 1rem;
                margin-bottom: 2rem;
                flex-wrap: wrap;
            }
            .context-item { 
                background: #f8f9fa;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
            }
            .recommendations-list { display: grid; gap: 1rem; }
            .recommendation-card { 
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                position: relative;
                border-left: 4px solid;
            }
            .recommendation-card.priority-high { border-color: #dc3545; }
            .recommendation-card.priority-medium { border-color: #ffc107; }
            .recommendation-card.priority-low { border-color: #28a745; }
            .priority-badge { 
                position: absolute;
                top: -8px;
                right: 1rem;
                padding: 0.3rem 0.8rem;
                border-radius: 15px;
                font-size: 0.8rem;
                font-weight: bold;
                color: white;
            }
            .priority-high .priority-badge { background: #dc3545; }
            .priority-medium .priority-badge { background: #ffc107; color: #333; }
            .priority-low .priority-badge { background: #28a745; }
            .recommendation-impact { 
                margin-top: 1rem;
                font-weight: bold;
                color: #28a745;
                font-size: 0.9rem;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showCoachDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-graduation-cap"></i> Real-Time AI Coach Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="coach-dashboard">
                <div class="live-score">
                    <h4>Live Driving Score</h4>
                    <div class="score-display">
                        <div class="score-circle">
                            <span class="score-number" id="liveScore">85</span>
                            <span class="score-label">/ 100</span>
                        </div>
                        <div class="score-trend">
                            <i class="fas fa-arrow-up trend-up"></i>
                            <span>+3 from last minute</span>
                        </div>
                    </div>
                </div>
                
                <div class="live-metrics">
                    <div class="metric-item">
                        <div class="metric-label">Speed</div>
                        <div class="metric-value" id="liveSpeed">65 km/h</div>
                        <div class="metric-status good">Optimal</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">RPM</div>
                        <div class="metric-value" id="liveRPM">2,200</div>
                        <div class="metric-status warning">High</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Fuel Rate</div>
                        <div class="metric-value" id="liveFuel">8.5 L/h</div>
                        <div class="metric-status good">Efficient</div>
                    </div>
                </div>
                
                <div class="live-coaching">
                    <h5>Live Coaching Tips</h5>
                    <div class="coaching-tip active">
                        <i class="fas fa-lightbulb"></i>
                        <span>Ease off the accelerator to reduce RPM and improve efficiency</span>
                    </div>
                    <div class="coaching-tip">
                        <i class="fas fa-thumbs-up"></i>
                        <span>Great job maintaining steady speed!</span>
                    </div>
                </div>
                
                <button class="start-coaching" onclick="startLiveDemo()">
                    <i class="fas fa-play"></i> Start Live Demo
                </button>
            </div>
        </div>
        <style>
            .coach-dashboard { text-align: center; }
            .live-score { margin-bottom: 2rem; }
            .score-display { 
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 2rem;
                margin: 1rem 0;
            }
            .score-circle { 
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: conic-gradient(#28a745 0deg 306deg, #e9ecef 306deg 360deg);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;
                position: relative;
            }
            .score-circle::before { 
                content: '';
                position: absolute;
                width: 90px;
                height: 90px;
                background: white;
                border-radius: 50%;
            }
            .score-number { 
                font-size: 2rem;
                font-weight: bold;
                color: #28a745;
                z-index: 1;
            }
            .score-label { 
                font-size: 0.9rem;
                color: #666;
                z-index: 1;
            }
            .score-trend { 
                color: #28a745;
                font-size: 0.9rem;
            }
            .trend-up { margin-right: 0.5rem; }
            .live-metrics { 
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1rem;
                margin-bottom: 2rem;
            }
            .metric-item { 
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
            }
            .metric-label { 
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 0.5rem;
            }
            .metric-value { 
                font-size: 1.2rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            .metric-status { 
                font-size: 0.8rem;
                padding: 0.2rem 0.5rem;
                border-radius: 10px;
                display: inline-block;
            }
            .metric-status.good { 
                background: #d4edda;
                color: #155724;
            }
            .metric-status.warning { 
                background: #fff3cd;
                color: #856404;
            }
            .live-coaching { 
                text-align: left;
                margin-bottom: 2rem;
            }
            .coaching-tip { 
                display: flex;
                align-items: center;
                gap: 0.8rem;
                padding: 0.8rem;
                margin-bottom: 0.5rem;
                border-radius: 8px;
                background: #f8f9fa;
            }
            .coaching-tip.active { 
                background: #fff3cd;
                border-left: 4px solid #ffc107;
            }
            .start-coaching { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 1rem 2rem;
                border-radius: 10px;
                font-weight: bold;
                cursor: pointer;
                font-size: 1.1rem;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

function showFuelDemo() {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = '<i class="fas fa-gas-pump"></i> Fuel Consumption Prediction Demo';
    modalBody.innerHTML = `
        <div class="demo-content">
            <div class="fuel-prediction">
                <h4>Route Fuel Prediction</h4>
                <div class="route-info">
                    <div class="route-detail">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>From: Downtown Office</span>
                    </div>
                    <div class="route-detail">
                        <i class="fas fa-map-marker"></i>
                        <span>To: Airport Terminal</span>
                    </div>
                    <div class="route-detail">
                        <i class="fas fa-road"></i>
                        <span>Distance: 45.2 km</span>
                    </div>
                </div>
                
                <div class="driving-scenarios">
                    <h5>Fuel Predictions by Driving Style</h5>
                    <div class="scenario-grid">
                        <div class="scenario-card eco">
                            <div class="scenario-header">
                                <i class="fas fa-leaf"></i>
                                <h6>Eco Driving</h6>
                            </div>
                            <div class="fuel-amount">3.2 L</div>
                            <div class="fuel-cost">$4.80</div>
                            <div class="scenario-details">
                                <div class="detail-item">
                                    <span>Avg Speed: 55 km/h</span>
                                </div>
                                <div class="detail-item">
                                    <span>ETA: +8 minutes</span>
                                </div>
                                <div class="detail-item savings">
                                    <span>Savings: $1.20</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="scenario-card normal">
                            <div class="scenario-header">
                                <i class="fas fa-car"></i>
                                <h6>Normal Driving</h6>
                            </div>
                            <div class="fuel-amount">4.0 L</div>
                            <div class="fuel-cost">$6.00</div>
                            <div class="scenario-details">
                                <div class="detail-item">
                                    <span>Avg Speed: 65 km/h</span>
                                </div>
                                <div class="detail-item">
                                    <span>ETA: Standard</span>
                                </div>
                                <div class="detail-item baseline">
                                    <span>Baseline</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="scenario-card aggressive">
                            <div class="scenario-header">
                                <i class="fas fa-tachometer-alt"></i>
                                <h6>Aggressive Driving</h6>
                            </div>
                            <div class="fuel-amount">5.1 L</div>
                            <div class="fuel-cost">$7.65</div>
                            <div class="scenario-details">
                                <div class="detail-item">
                                    <span>Avg Speed: 75 km/h</span>
                                </div>
                                <div class="detail-item">
                                    <span>ETA: -5 minutes</span>
                                </div>
                                <div class="detail-item cost">
                                    <span>Extra Cost: $1.65</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="prediction-insights">
                    <h5>AI Recommendations:</h5>
                    <div class="insight-item">
                        <i class="fas fa-lightbulb"></i>
                        <span>Choose eco driving to save $1.20 on this trip</span>
                    </div>
                    <div class="insight-item">
                        <i class="fas fa-clock"></i>
                        <span>Leave 8 minutes earlier for maximum savings</span>
                    </div>
                    <div class="insight-item">
                        <i class="fas fa-route"></i>
                        <span>Highway route recommended for fuel efficiency</span>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .route-info { 
                display: flex;
                justify-content: space-around;
                margin-bottom: 2rem;
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
            }
            .route-detail { 
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
            }
            .scenario-grid { 
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 1rem;
                margin-bottom: 2rem;
            }
            .scenario-card { 
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
                border-top: 4px solid;
            }
            .scenario-card.eco { border-color: #28a745; }
            .scenario-card.normal { border-color: #17a2b8; }
            .scenario-card.aggressive { border-color: #dc3545; }
            .scenario-header { 
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }
            .fuel-amount { 
                font-size: 2rem;
                font-weight: bold;
                color: #333;
                margin-bottom: 0.5rem;
            }
            .fuel-cost { 
                font-size: 1.2rem;
                color: #666;
                margin-bottom: 1rem;
            }
            .scenario-details { 
                text-align: left;
            }
            .detail-item { 
                padding: 0.3rem 0;
                font-size: 0.9rem;
            }
            .detail-item.savings { color: #28a745; font-weight: bold; }
            .detail-item.cost { color: #dc3545; font-weight: bold; }
            .detail-item.baseline { color: #17a2b8; font-weight: bold; }
            .prediction-insights { 
                background: #e8f4fd;
                padding: 1.5rem;
                border-radius: 10px;
            }
            .insight-item { 
                display: flex;
                align-items: center;
                gap: 0.8rem;
                margin-bottom: 0.8rem;
                color: #0c5460;
            }
        </style>
    `;
    
    document.getElementById('demoModal').style.display = 'block';
}

// Live demo simulation
function startLiveDemo() {
    let score = 85;
    let speed = 65;
    let rpm = 2200;
    let fuel = 8.5;
    
    const interval = setInterval(() => {
        // Simulate changing values
        score += Math.random() * 6 - 3; // ±3 variation
        speed += Math.random() * 10 - 5; // ±5 variation
        rpm += Math.random() * 400 - 200; // ±200 variation
        fuel += Math.random() * 2 - 1; // ±1 variation
        
        // Keep values in realistic ranges
        score = Math.max(60, Math.min(100, score));
        speed = Math.max(40, Math.min(80, speed));
        rpm = Math.max(1500, Math.min(3000, rpm));
        fuel = Math.max(6, Math.min(12, fuel));
        
        // Update display
        document.getElementById('liveScore').textContent = Math.round(score);
        document.getElementById('liveSpeed').textContent = Math.round(speed) + ' km/h';
        document.getElementById('liveRPM').textContent = Math.round(rpm).toLocaleString();
        document.getElementById('liveFuel').textContent = fuel.toFixed(1) + ' L/h';
        
        // Update score circle
        const scoreCircle = document.querySelector('.score-circle');
        const percentage = score / 100 * 360;
        scoreCircle.style.background = `conic-gradient(#28a745 0deg ${percentage}deg, #e9ecef ${percentage}deg 360deg)`;
    }, 2000);
    
    // Stop demo after 30 seconds
    setTimeout(() => {
        clearInterval(interval);
    }, 30000);
}

// Modal functions
function closeModal() {
    document.getElementById('demoModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('demoModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Add animation to feature cards
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.feature-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
});