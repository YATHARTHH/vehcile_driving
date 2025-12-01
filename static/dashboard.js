// Extract data from tripsData
const tripDates = tripsData.map(trip => trip['trip_date']);
const distances = tripsData.map(trip => trip['distance_km']);
const avgSpeeds = tripsData.map(trip => trip['avg_speed_kmph']);
const maxSpeeds = tripsData.map(trip => trip['max_speed']);
const fuelConsumed = tripsData.map(trip => trip['fuel_consumed']);
const maxRPMs = tripsData.map(trip => trip['max_rpm']);
const steeringAngles = tripsData.map(trip => trip['steering_angle']);

// New metrics extraction
const brakeEvents = tripsData.map(trip => trip['brake_events']);
const angularVelocities = tripsData.map(trip => trip['angular_velocity']);
const accelerations = tripsData.map(trip => trip['acceleration']);
const gearPositions = tripsData.map(trip => trip['gear_position']);
const tirePressures = tripsData.map(trip => trip['tire_pressure']);
const engineLoads = tripsData.map(trip => trip['engine_load']);
const throttlePositions = tripsData.map(trip => trip['throttle_position']);
const brakePressures = tripsData.map(trip => trip['brake_pressure']);
const tripDurations = tripsData.map(trip => trip['trip_duration']);

// Calculate fuel efficiency (km/L) for each trip
const fuelEfficiencies = tripsData.map(trip => 
    trip['fuel_consumed'] > 0 ? (trip['distance_km'] / trip['fuel_consumed']).toFixed(2) : 0
);

// Create reusable gradient function
const createGradient = (ctx, colorStart, colorEnd) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
};

// Chart configuration object for consistent settings
const chartConfig = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top',
            labels: {
                boxWidth: 12,
                usePointStyle: true,
                padding: 20
            }
        }
    },
    scales: {
        y: {
            beginAtZero: true,
            grid: {
                display: true,
                color: 'rgba(0, 0, 0, 0.05)'
            }
        },
        x: {
            grid: {
                display: false
            }
        }
    }
};

// Distance Chart
new Chart(document.getElementById('distanceChart'), {
    type: 'bar',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Distance (km)',
            data: distances,
            backgroundColor: 'rgba(37, 99, 235, 0.7)',
            borderColor: '#2563eb',
            borderWidth: 2,
            borderRadius: 6,
            hoverBackgroundColor: '#3b82f6'
        }]
    },
    options: {...chartConfig}
});

// Average Speed Chart
new Chart(document.getElementById('avgSpeedChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Avg Speed (km/h)',
            data: avgSpeeds,
            borderColor: '#10b981',
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(16, 185, 129, 0.8)', 'rgba(16, 185, 129, 0.1)');
            },
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#10b981',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 6
        }]
    },
    options: {...chartConfig}
});

// Max Speed Chart
new Chart(document.getElementById('maxSpeedChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Max Speed (km/h)',
            data: maxSpeeds,
            borderColor: '#f43f5e',
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(244, 63, 94, 0.6)', 'rgba(244, 63, 94, 0.05)');
            },
            fill: true,
            tension: 0.3,
            pointRadius: 4,
            pointBackgroundColor: '#f43f5e',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 6
        }]
    },
    options: {...chartConfig}
});

// Fuel Consumed Pie Chart
new Chart(document.getElementById('fuelChart'), {
    type: 'doughnut',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Fuel Consumed (L)',
            data: fuelConsumed,
            backgroundColor: [
                '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
                '#ec4899', '#14b8a6', '#6366f1', '#ef4444',
                '#0ea5e9', '#a855f7'
            ],
            borderColor: '#ffffff',
            borderWidth: 2,
            hoverOffset: 15
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 15,
                    font: {
                        size: 11
                    }
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const value = context.raw || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = Math.round((value / total) * 100) + '%';
                        return `${context.label}: ${value}L (${percentage})`;
                    }
                }
            }
        },
        cutout: '60%',
        radius: '90%'
    }
});

// Max RPM Chart
new Chart(document.getElementById('rpmChart'), {
    type: 'bar',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Max RPM',
            data: maxRPMs,
            backgroundColor: 'rgba(139, 92, 246, 0.7)',
            borderColor: '#8b5cf6',
            borderWidth: 2,
            borderRadius: 6,
            hoverBackgroundColor: '#a78bfa'
        }]
    },
    options: {...chartConfig}
});

// Steering Angle Chart
new Chart(document.getElementById('steeringChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Steering Angle',
            data: steeringAngles,
            borderColor: '#f59e0b',
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(245, 158, 11, 0.6)', 'rgba(245, 158, 11, 0.05)');
            },
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#f59e0b',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 6
        }]
    },
    options: {...chartConfig}
});

// Brake Events Chart - Bubble Chart
new Chart(document.getElementById('brakeEventsChart'), {
    type: 'bubble',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Brake Events',
            data: brakeEvents.map((value, index) => ({
                x: index,
                y: value,
                r: Math.max(value * 2, 5)  // Radius based on value, with minimum size
            })),
            backgroundColor: 'rgba(244, 63, 94, 0.7)',
            borderColor: '#f43f5e',
            borderWidth: 1,
            hoverBackgroundColor: 'rgba(244, 63, 94, 0.9)',
            hoverBorderColor: '#e11d48'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return `${tripDates[context.raw.x]}: ${context.raw.y} brake events`;
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Number of Events'
                },
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            x: {
                type: 'linear',
                position: 'bottom',
                ticks: {
                    callback: function(value) {
                        return tripDates[value] || '';
                    },
                    stepSize: 1
                },
                grid: {
                    display: false
                }
            }
        }
    }
});

// Angular Velocity Chart - Polar Area Chart (replacing radar chart)
new Chart(document.getElementById('angularVelocityChart'), {
    type: 'polarArea',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Angular Velocity',
            data: angularVelocities,
            backgroundColor: [
                'rgba(99, 102, 241, 0.7)',
                'rgba(16, 185, 129, 0.7)', 
                'rgba(245, 158, 11, 0.7)',
                'rgba(139, 92, 246, 0.7)',
                'rgba(236, 72, 153, 0.7)',
                'rgba(14, 165, 233, 0.7)',
                'rgba(239, 68, 68, 0.7)',
                'rgba(20, 184, 166, 0.7)',
                'rgba(168, 85, 247, 0.7)',
                'rgba(249, 115, 22, 0.7)'
            ],
            borderColor: '#ffffff',
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 15,
                    font: {
                        size: 11
                    }
                }
            }
        },
        scales: {
            r: {
                beginAtZero: true,
                ticks: {
                    backdropColor: 'rgba(255, 255, 255, 0.8)'
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.1)'
                },
                angleLines: {
                    color: 'rgba(0, 0, 0, 0.1)'
                }
            }
        }
    }
});

// Acceleration Chart - Area Chart
new Chart(document.getElementById('accelerationChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Acceleration',
            data: accelerations,
            borderColor: '#0ea5e9',
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(14, 165, 233, 0.6)', 'rgba(14, 165, 233, 0.05)');
            },
            fill: true,
            tension: 0.2,
            pointRadius: 5,
            pointBackgroundColor: '#0ea5e9',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 7
        }]
    },
    options: {...chartConfig}
});

// Gear Position Chart - Scatter Chart
new Chart(document.getElementById('gearChart'), {
    type: 'scatter',
    data: {
        datasets: [{
            label: 'Gear Position',
            data: gearPositions.map((value, index) => ({
                x: index,
                y: value
            })),
            backgroundColor: 'rgba(20, 184, 166, 0.7)',
            borderColor: '#14b8a6',
            pointRadius: 8,
            pointHoverRadius: 10
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return `${tripDates[context.raw.x]}: Gear ${context.raw.y}`;
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Gear Number'
                },
                ticks: {
                    stepSize: 1
                },
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            x: {
                type: 'linear',
                position: 'bottom',
                ticks: {
                    callback: function(value) {
                        return tripDates[value] || '';
                    },
                    stepSize: 1
                },
                grid: {
                    display: false
                }
            }
        }
    }
});

// Tire Pressure Chart - Horizontal Bar Chart
new Chart(document.getElementById('tirePressureChart'), {
    type: 'bar',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Tire Pressure (PSI)',
            data: tirePressures,
            backgroundColor: 'rgba(168, 85, 247, 0.7)',
            borderColor: '#a855f7',
            borderWidth: 2,
            borderRadius: 4,
            barPercentage: 0.6,
            categoryPercentage: 0.8
        }]
    },
    options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 20
                }
            }
        },
        scales: {
            x: {
                beginAtZero: false,
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            y: {
                grid: {
                    display: false
                }
            }
        }
    }
});

// Engine Load Chart - Gauge-like Chart
new Chart(document.getElementById('engineLoadChart'), {
    type: 'doughnut',
    data: {
        labels: ['Engine Load', 'Remaining Capacity'],
        datasets: [{
            data: [
                Math.max(...engineLoads), // Showing the maximum engine load
                100 - Math.max(...engineLoads)
            ],
            backgroundColor: [
                '#f97316',
                'rgba(229, 231, 235, 0.5)'
            ],
            borderColor: ['#f97316', '#e5e7eb'],
            borderWidth: 1,
            circumference: 180,
            rotation: 270
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '80%',
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        if (context.dataIndex === 0) {
                            return `Maximum Engine Load: ${context.raw}%`;
                        }
                        return '';
                    }
                }
            }
        }
    },
    plugins: [{
        id: 'engineLoadText',
        afterDraw: function(chart) {
            const width = chart.width;
            const height = chart.height;
            const ctx = chart.ctx;
            
            ctx.restore();
            const fontSize = (height / 114).toFixed(2);
            ctx.font = `${fontSize}em sans-serif`;
            ctx.textBaseline = 'middle';
            
            const text = `${Math.max(...engineLoads)}%`;
            const textX = Math.round((width - ctx.measureText(text).width) / 2);
            const textY = height / 1.35;
            
            ctx.fillStyle = '#111827';
            ctx.fillText(text, textX, textY);
            
            ctx.fillStyle = '#6b7280';
            ctx.font = `${fontSize / 2}em sans-serif`;
            const label = 'Max Engine Load';
            const labelX = Math.round((width - ctx.measureText(label).width) / 2);
            const labelY = height / 1.1;
            ctx.fillText(label, labelX, labelY);
            
            ctx.save();
        }
    }]
});

// Throttle Position Chart - Line Chart with Stepped Line
new Chart(document.getElementById('throttleChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Throttle Position (%)',
            data: throttlePositions,
            borderColor: '#ec4899',
            borderWidth: 3,
            pointBackgroundColor: '#ec4899',
            pointBorderColor: '#fff',
            pointRadius: 5,
            pointHoverRadius: 7,
            stepped: 'before'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 20
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            x: {
                grid: {
                    display: false
                }
            }
        }
    }
});

// Brake Pressure Chart - Line Chart with Points Focus
new Chart(document.getElementById('brakePressureChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Brake Pressure (PSI)',
            data: brakePressures,
            borderColor: '#ef4444',
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(239, 68, 68, 0.6)', 'rgba(239, 68, 68, 0.05)');
            },
            borderWidth: 2,
            fill: true,
            tension: 0.1,
            pointRadius: 6,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 8
        }]
    },
    options: {...chartConfig}
});

// Trip Duration Chart - Bar Chart with Gradient
new Chart(document.getElementById('tripDurationChart'), {
    type: 'bar',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Trip Duration (min)',
            data: tripDurations,
            backgroundColor: function(context) {
                return createGradient(context.chart.ctx, 'rgba(20, 184, 166, 0.8)', 'rgba(20, 184, 166, 0.2)');
            },
            borderColor: '#14b8a6',
            borderWidth: 1,
            borderRadius: 4,
            hoverBackgroundColor: '#14b8a6'
        }]
    },
    options: {...chartConfig}
});

// Fuel Efficiency Chart - Showing only fuel efficiency (removed combined chart)
new Chart(document.getElementById('fuelEfficiencyChart'), {
    type: 'line',
    data: {
        labels: tripDates,
        datasets: [{
            label: 'Fuel Efficiency (km/L)',
            data: fuelEfficiencies,
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            borderColor: '#10b981',
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#10b981',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth: 12,
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return `${context.raw} km/L`;
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                },
                title: {
                    display: true,
                    text: 'Kilometers per Liter'
                }
            },
            x: {
                grid: {
                    display: false
                }
            }
        }
    }
});