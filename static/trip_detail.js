/**
 * FleetTrack Analytics Trip Detail JavaScript
 * Optimized visualization script for trip data analysis
 */

document.addEventListener("DOMContentLoaded", function () {
    // Ensure tripData exists
    if (typeof tripData === 'undefined') {
        console.error('Trip data not available');
        return;
    }

    // Extract trip data from the global tripData object
    const { 
        speed, 
        maxSpeed, 
        rpm, 
        brakeEvents, 
        brakePressure, 
        fuelConsumed, 
        fuelEfficiency, 
        steeringAngle, 
        angularVelocity, 
        acceleration, 
        engineLoad, 
        throttlePosition, 
        tripDuration,
        distance,
        // Score and behavior data
        logicScore,
        logicBehavior,
        mlBehavior
    } = tripData;

    // Chart.js global configuration for consistent styling
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = "#64748b";
    Chart.defaults.borderColor = "#e2e8f0";
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.titleFont = { size: 14 };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 13 };
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15, 23, 42, 0.9)";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.elements.point.radius = 4;
    Chart.defaults.elements.point.hoverRadius = 6;

    // Helper function to create gradient backgrounds
    const createGradient = (ctx, color1, color2) => {
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    };

    // Helper function to generate realistic trip data with fluctuations
    const generateTripData = (baseValue, labels, factor = 1, maxChange = 8) => {
        let currentValue = baseValue;
        return labels.map(() => {
            const change = Math.random() * maxChange - (maxChange / 2);
            currentValue = Math.max(0, currentValue + change * factor);
            return parseFloat(currentValue.toFixed(1));
        });
    };

    // Time labels for charts - 10 time intervals
    const timeLabels = Array.from({ length: 10 }, (_, i) => `T${i + 1}`);

    // Generate data for all chart types based on summary values
    const speedData = generateTripData(speed, timeLabels);
    const rpmData = generateTripData(rpm / 10, timeLabels, 0.5);
    const brakeEventsData = generateTripData(brakeEvents / 10, timeLabels, 1.2);
    const brakePressureData = generateTripData(brakePressure, timeLabels, 0.8);
    const accelerationData = generateTripData(acceleration, timeLabels, 0.9);
    const engineLoadData = generateTripData(engineLoad, timeLabels, 0.7);
    const throttlePositionData = generateTripData(throttlePosition, timeLabels, 0.6);
    const steeringAngleData = generateTripData(steeringAngle, timeLabels, 1.5);
    const angularVelocityData = generateTripData(angularVelocity, timeLabels, 1.2);
    const fuelConsumptionData = Array.from({ length: 10 }, (_, i) => {
        return (fuelConsumed / 10) * (i + 1);
    });

    // Function to create charts with standardized configuration
    const createChart = (ctx, type, data, options) => {
        if (!ctx) return null; // Safety check
        return new Chart(ctx, {
            type: type,
            data: data,
            options: options
        });
    };

    // Default animation delay for each chart
    let animationDelay = 200;

    // 1. Speed & RPM Chart
    const speedRpmCtx = document.getElementById('speedRpmChart')?.getContext('2d');
    let speedRpmChart;
    
    if (speedRpmCtx) {
        const speedRpmChartData = {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Speed (km/h)',
                    data: speedData,
                    borderColor: '#3b82f6',
                    backgroundColor: createGradient(speedRpmCtx, 'rgba(59, 130, 246, 0.7)', 'rgba(59, 130, 246, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#3b82f6'
                },
                {
                    label: 'RPM',
                    data: rpmData.map(val => val * 10), // Scale up to realistic RPM values
                    borderColor: '#ef4444',
                    backgroundColor: createGradient(speedRpmCtx, 'rgba(239, 68, 68, 0.7)', 'rgba(239, 68, 68, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#ef4444',
                    yAxisID: 'y1'
                }
            ]
        };
        
        const speedRpmChartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: { 
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(1)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Speed (km/h)',
                        color: '#3b82f6',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'RPM',
                        color: '#ef4444',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        };
        
        speedRpmChart = createChart(speedRpmCtx, 'line', speedRpmChartData, speedRpmChartOptions);
        
        const chartControlBtns = document.querySelectorAll('.speed-rpm-chart .chart-control-btn');
        chartControlBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                chartControlBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                const view = this.getAttribute('data-view');
                
                speedRpmChart.destroy();
                speedRpmChart = createChart(speedRpmCtx, view, speedRpmChartData, speedRpmChartOptions);
            });
        });
        
        animationDelay += 100;
    }

    // 2. Brake Analysis Chart
    const brakeCtx = document.getElementById('brakeChart')?.getContext('2d');
    if (brakeCtx) {
        createChart(brakeCtx, 'line', {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Brake Events',
                    data: brakeEventsData,
                    borderColor: '#f59e0b',
                    backgroundColor: createGradient(brakeCtx, 'rgba(245, 158, 11, 0.7)', 'rgba(245, 158, 11, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#f59e0b'
                },
                {
                    label: 'Brake Pressure (bar)',
                    data: brakePressureData,
                    borderColor: '#8b5cf6',
                    backgroundColor: createGradient(brakeCtx, 'rgba(139, 92, 246, 0.7)', 'rgba(139, 92, 246, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#8b5cf6',
                    yAxisID: 'y1'
                }
            ]
        }, {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: { 
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(1)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Brake Events',
                        color: '#f59e0b',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Brake Pressure (bar)',
                        color: '#8b5cf6',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        });
        
        animationDelay += 100;
    }

    // 3. Engine Performance Chart
    const accelerationCtx = document.getElementById('accelerationChart')?.getContext('2d');
    if (accelerationCtx) {
        createChart(accelerationCtx, 'line', {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Acceleration (m/s²)',
                    data: accelerationData,
                    borderColor: '#2563eb',
                    backgroundColor: createGradient(accelerationCtx, 'rgba(37, 99, 235, 0.7)', 'rgba(37, 99, 235, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#2563eb'
                },
                {
                    label: 'Engine Load (%)',
                    data: engineLoadData,
                    borderColor: '#f59e0b',
                    backgroundColor: createGradient(accelerationCtx, 'rgba(245, 158, 11, 0.7)', 'rgba(245, 158, 11, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#f59e0b',
                    yAxisID: 'y1'
                },
                {
                    label: 'Throttle Position (%)',
                    data: throttlePositionData,
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    fill: false,
                    tension: 0.4,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointBackgroundColor: '#10b981',
                    yAxisID: 'y1'
                }
            ]
        }, {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: { 
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(1)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Acceleration (m/s²)',
                        color: '#2563eb',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                },
                y1: {
                    beginAtZero: true,
                    max: 100,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Engine Load & Throttle (%)',
                        color: '#f59e0b',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        });
        
        animationDelay += 100;
    }

    // 4. Steering Dynamics Chart
    const steeringCtx = document.getElementById('steeringChart')?.getContext('2d');
    if (steeringCtx) {
        createChart(steeringCtx, 'line', {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Steering Angle (°)',
                    data: steeringAngleData,
                    borderColor: '#6366f1',
                    backgroundColor: createGradient(steeringCtx, 'rgba(99, 102, 241, 0.7)', 'rgba(99, 102, 241, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#6366f1'
                },
                {
                    label: 'Angular Velocity (rad/s)',
                    data: angularVelocityData,
                    borderColor: '#0891b2',
                    backgroundColor: createGradient(steeringCtx, 'rgba(8, 145, 178, 0.7)', 'rgba(8, 145, 178, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#0891b2',
                    yAxisID: 'y1'
                }
            ]
        }, {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: { 
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => {
                            const unit = tooltipItem.dataset.label.includes('Angle') ? '°' : 
                                        tooltipItem.dataset.label.includes('Velocity') ? ' rad/s' : '';
                            return `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(1)}${unit}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Steering Angle (°)',
                        color: '#6366f1',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Angular Velocity (rad/s)',
                        color: '#0891b2',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        });
        
        animationDelay += 100;
    }

    // 5. Fuel Consumption & Efficiency Chart
    const fuelCtx = document.getElementById('fuelChart')?.getContext('2d');
    if (fuelCtx) {
        createChart(fuelCtx, 'line', {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Fuel Consumption (L)',
                    data: fuelConsumptionData,
                    borderColor: '#10b981',
                    backgroundColor: createGradient(fuelCtx, 'rgba(16, 185, 129, 0.7)', 'rgba(16, 185, 129, 0.1)'),
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#10b981'
                }
            ]
        }, {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { 
                    position: 'top',
                    labels: { 
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(2)} L`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Fuel Consumption (L)',
                        color: '#10b981',
                        font: { weight: 'bold' }
                    },
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        });
        
        animationDelay += 100;
    }

    // 6. Driving Score Chart with radar visualization
    const drivingScoreCtx = document.getElementById('drivingScoreChart')?.getContext('2d');
    if (drivingScoreCtx) {
        const scoreValue = logicScore / 100;
        const behaviorValue = mlBehavior === 'Safe' ? 0.9 : 
                              mlBehavior === 'Moderate' ? 0.6 : 0.3;
        
        createChart(drivingScoreCtx, 'radar', {
            labels: [
                'Acceleration Control',
                'Braking Smoothness',
                'Cornering Technique',
                'Speed Management',
                'Fuel Efficiency',
                'Overall Safety'
            ],
            datasets: [
                {
                    label: 'Driver Performance',
                    data: [
                        scoreValue * 100 * (0.8 + Math.random() * 0.4),
                        scoreValue * 100 * (0.75 + Math.random() * 0.5),
                        behaviorValue * 100 * (0.85 + Math.random() * 0.3),
                        scoreValue * 100 * (0.9 + Math.random() * 0.2),
                        (fuelEfficiency / 20) * 100,
                        behaviorValue * 100 * (0.95 + Math.random() * 0.1)
                    ],
                    fill: true,
                    backgroundColor: createGradient(drivingScoreCtx, 'rgba(91, 33, 182, 0.7)', 'rgba(91, 33, 182, 0.2)'),
                    borderColor: '#8b5cf6',
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#8b5cf6'
                },
                {
                    label: 'Ideal Performance',
                    data: [100, 100, 100, 100, 100, 100],
                    fill: true,
                    backgroundColor: 'rgba(203, 213, 225, 0.2)',
                    borderColor: 'rgba(203, 213, 225, 0.8)',
                    borderDash: [5, 5],
                    pointBackgroundColor: 'rgba(203, 213, 225, 0.8)',
                    pointBorderColor: 'rgba(203, 213, 225, 0.8)',
                    pointRadius: 0
                }
            ]
        }, {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                r: {
                    angleLines: {
                        display: true,
                        color: 'rgba(226, 232, 240, 0.5)'
                    },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    ticks: {
                        stepSize: 20,
                        backdropColor: 'transparent'
                    },
                    grid: {
                        color: 'rgba(226, 232, 240, 0.5)'
                    },
                    pointLabels: {
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        color: '#64748b'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 20,
                        boxWidth: 12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (tooltipItem) => {
                            return `${tooltipItem.dataset.label}: ${Math.round(tooltipItem.raw)}%`;
                        }
                    }
                }
            },
            animation: {
                delay: animationDelay
            }
        });
    }

    // Chart container animation
    const animateCharts = () => {
        const chartContainers = document.querySelectorAll('.chart-container');
        
        chartContainers.forEach((container, index) => {
            container.style.opacity = '0';
            container.style.transform = 'translateY(20px)';
            container.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            
            setTimeout(() => {
                container.style.opacity = '1';
                container.style.transform = 'translateY(0)';
            }, index * 100);
        });
    };

    // EXPORT PDF – key changes to avoid blank area[web:10]
  // Add export functionality
const exportBtn = document.getElementById('exportReport');
if (exportBtn && typeof html2pdf !== 'undefined') {
    exportBtn.addEventListener('click', function (e) {
        e.preventDefault();

        // Use your existing HTML wrapper element (adjust selector if needed)
        // If you already have <div id="reportContainer"> wrap, this will hit it.
        const element = document.getElementById('reportContainer') || document.body;

        // Make sure page is at top so html2canvas doesn't add scroll offset
        window.scrollTo(0, 0);

        // Small delay to let layout/charts finish
        setTimeout(() => {
            const opt = {
                margin: 0,                            // no extra margins
                filename: 'trip_report.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: {
                    scale: 1,                         // critical to avoid top blank band[web:4]
                    scrollX: 0,
                    scrollY: 0,
                    useCORS: true,
                    backgroundColor: '#ffffff'
                },
                jsPDF: {
                    unit: 'mm',
                    format: 'a4',                     // standard A4, let library handle height[web:44]
                    orientation: 'portrait'
                },
                pagebreak: { mode: ['css', 'legacy'] }
            };

            html2pdf()
                .set(opt)
                .from(element)
                .save();

            // Notification
            const notification = document.createElement('div');
            notification.className = 'export-notification';
            notification.innerHTML = '<i class="fas fa-file-export"></i> Exporting trip report as PDF...';

            Object.assign(notification.style, {
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                backgroundColor: '#3b82f6',
                color: 'white',
                padding: '12px 20px',
                borderRadius: '8px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                zIndex: '9999',
                opacity: '0',
                transition: 'opacity 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
            });

            document.body.appendChild(notification);
            setTimeout(() => notification.style.opacity = '1', 10);
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }, 300);
    });
}


    // Smooth scrolling back button
    const backButton = document.querySelector('.back-button');
    if (backButton) {
        backButton.addEventListener('click', function(e) {
            if (this.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const href = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(href);
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    }
    
    // Start animations after a short delay
    setTimeout(animateCharts, 300);
    
    // Add CSS for animations and report container
    const style = document.createElement('style');
    style.textContent = `
        .chart-container {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }
        
        .metric-card, .tile, .health-card, .maintenance-alerts, .alert-item {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .metric-card:hover, .tile:hover, .health-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
        }
        
        .export-button, .back-button {
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        
        .export-button:hover, .back-button:hover {
            transform: translateY(-2px);
        }
        
        .export-button:active, .back-button:active {
            transform: translateY(0);
        }

        /* Critical: ensure report container is tight, no extra margins/padding */
        #reportContainer {
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff;
            box-sizing: border-box;
        }

        @media print {
            #reportContainer {
                page-break-inside: avoid;
            }
        }
    `;
    document.head.appendChild(style);
});
