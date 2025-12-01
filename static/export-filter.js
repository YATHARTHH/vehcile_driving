// Export and Filter Functionality
(function() {
    'use strict';

    // Modal elements
    const exportModal = document.getElementById('exportModal');
    const filterModal = document.getElementById('filterModal');
    const exportBtn = document.getElementById('exportBtn');
    const filterBtn = document.getElementById('filterBtn');
    const closeExport = document.getElementById('closeExport');
    const closeFilter = document.getElementById('closeFilter');
    const cancelExport = document.getElementById('cancelExport');
    const confirmExport = document.getElementById('confirmExport');
    const applyFilter = document.getElementById('applyFilter');
    const resetFilter = document.getElementById('resetFilter');

    // Filter state
    let activeFilters = {
        dateFrom: null,
        dateTo: null,
        minDistance: null,
        maxDistance: null,
        minSpeed: null,
        maxSpeed: null
    };

    // ========== EXPORT FUNCTIONALITY ==========

    // Open export modal
    exportBtn.addEventListener('click', () => {
        exportModal.style.display = 'block';
    });

    // Close export modal
    closeExport.addEventListener('click', () => {
        exportModal.style.display = 'none';
    });

    cancelExport.addEventListener('click', () => {
        exportModal.style.display = 'none';
    });

    // Confirm export
    confirmExport.addEventListener('click', () => {
        const format = document.querySelector('input[name="exportFormat"]:checked').value;
        exportData(format);
        exportModal.style.display = 'none';
    });

    // Export functions
    function exportData(format) {
        const dataToExport = filteredTrips.length > 0 ? filteredTrips : allTrips;
        
        switch(format) {
            case 'csv':
                exportToCSV(dataToExport);
                break;
            case 'json':
                exportToJSON(dataToExport);
                break;
            case 'excel':
                exportToExcel(dataToExport);
                break;
        }
    }

    function exportToCSV(data) {
        const headers = [
            'Trip Date', 'Distance (km)', 'Avg Speed (km/h)', 'Max Speed (km/h)', 
            'Max RPM', 'Fuel Consumed (L)', 'Brake Events', 'Steering Angle',
            'Angular Velocity', 'Acceleration', 'Gear', 'Tire Pressure',
            'Engine Load', 'Throttle Position', 'Brake Pressure', 'Trip Duration',
            'Start Location', 'End Location'
        ];

        let csv = headers.join(',') + '\n';

        data.forEach(trip => {
            const row = [
                trip.trip_date,
                trip.distance_km,
                trip.avg_speed_kmph,
                trip.max_speed,
                trip.max_rpm,
                trip.fuel_consumed,
                trip.brake_events,
                trip.steering_angle,
                trip.angular_velocity,
                trip.acceleration,
                trip.gear_position,
                trip.tire_pressure,
                trip.engine_load,
                trip.throttle_position,
                trip.brake_pressure,
                trip.trip_duration,
                `"${trip.start_location}"`,
                `"${trip.end_location}"`
            ];
            csv += row.join(',') + '\n';
        });

        downloadFile(csv, 'trip-data.csv', 'text/csv');
    }

    function exportToJSON(data) {
        const json = JSON.stringify(data, null, 2);
        downloadFile(json, 'trip-data.json', 'application/json');
    }

    function exportToExcel(data) {
        // Create HTML table for Excel
        let html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">';
        html += '<head><meta charset="UTF-8"><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>';
        html += '<x:Name>Trip Data</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet>';
        html += '</x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head><body>';
        html += '<table border="1">';
        
        // Headers
        html += '<tr style="background-color: #4472c4; color: white; font-weight: bold;">';
        html += '<th>Trip Date</th><th>Distance (km)</th><th>Avg Speed (km/h)</th><th>Max Speed (km/h)</th>';
        html += '<th>Max RPM</th><th>Fuel Consumed (L)</th><th>Brake Events</th><th>Steering Angle</th>';
        html += '<th>Angular Velocity</th><th>Acceleration</th><th>Gear</th><th>Tire Pressure</th>';
        html += '<th>Engine Load</th><th>Throttle Position</th><th>Brake Pressure</th><th>Trip Duration</th>';
        html += '<th>Start Location</th><th>End Location</th></tr>';

        // Data rows
        data.forEach(trip => {
            html += '<tr>';
            html += `<td>${trip.trip_date}</td>`;
            html += `<td>${trip.distance_km}</td>`;
            html += `<td>${trip.avg_speed_kmph}</td>`;
            html += `<td>${trip.max_speed}</td>`;
            html += `<td>${trip.max_rpm}</td>`;
            html += `<td>${trip.fuel_consumed}</td>`;
            html += `<td>${trip.brake_events}</td>`;
            html += `<td>${trip.steering_angle}</td>`;
            html += `<td>${trip.angular_velocity}</td>`;
            html += `<td>${trip.acceleration}</td>`;
            html += `<td>${trip.gear_position}</td>`;
            html += `<td>${trip.tire_pressure}</td>`;
            html += `<td>${trip.engine_load}</td>`;
            html += `<td>${trip.throttle_position}</td>`;
            html += `<td>${trip.brake_pressure}</td>`;
            html += `<td>${trip.trip_duration}</td>`;
            html += `<td>${trip.start_location}</td>`;
            html += `<td>${trip.end_location}</td>`;
            html += '</tr>';
        });

        html += '</table></body></html>';

        downloadFile(html, 'trip-data.xls', 'application/vnd.ms-excel');
    }

    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification(`File "${filename}" downloaded successfully!`, 'success');
    }

    // ========== FILTER FUNCTIONALITY ==========

    // Open filter modal
    filterBtn.addEventListener('click', () => {
        filterModal.style.display = 'block';
        loadSavedFilters();
    });

    // Close filter modal
    closeFilter.addEventListener('click', () => {
        filterModal.style.display = 'none';
    });

    // Apply filters
    applyFilter.addEventListener('click', () => {
        saveFilters();
        applyFiltersToTable();
        filterModal.style.display = 'none';
        updateFilterButton();
    });

    // Reset filters
    resetFilter.addEventListener('click', () => {
        clearFilters();
        applyFiltersToTable();
        filterModal.style.display = 'none';
        updateFilterButton();
    });

    function saveFilters() {
        activeFilters = {
            dateFrom: document.getElementById('filterDateFrom').value,
            dateTo: document.getElementById('filterDateTo').value,
            minDistance: parseFloat(document.getElementById('filterMinDistance').value) || null,
            maxDistance: parseFloat(document.getElementById('filterMaxDistance').value) || null,
            minSpeed: parseFloat(document.getElementById('filterMinSpeed').value) || null,
            maxSpeed: parseFloat(document.getElementById('filterMaxSpeed').value) || null
        };
    }

    function loadSavedFilters() {
        document.getElementById('filterDateFrom').value = activeFilters.dateFrom || '';
        document.getElementById('filterDateTo').value = activeFilters.dateTo || '';
        document.getElementById('filterMinDistance').value = activeFilters.minDistance || '';
        document.getElementById('filterMaxDistance').value = activeFilters.maxDistance || '';
        document.getElementById('filterMinSpeed').value = activeFilters.minSpeed || '';
        document.getElementById('filterMaxSpeed').value = activeFilters.maxSpeed || '';
    }

    function clearFilters() {
        activeFilters = {
            dateFrom: null,
            dateTo: null,
            minDistance: null,
            maxDistance: null,
            minSpeed: null,
            maxSpeed: null
        };
        document.getElementById('filterDateFrom').value = '';
        document.getElementById('filterDateTo').value = '';
        document.getElementById('filterMinDistance').value = '';
        document.getElementById('filterMaxDistance').value = '';
        document.getElementById('filterMinSpeed').value = '';
        document.getElementById('filterMaxSpeed').value = '';
    }

    function applyFiltersToTable() {
        filteredTrips = allTrips.filter(trip => {
            // Date filters
            if (activeFilters.dateFrom) {
                const tripDate = new Date(trip.trip_date);
                const fromDate = new Date(activeFilters.dateFrom);
                if (tripDate < fromDate) return false;
            }

            if (activeFilters.dateTo) {
                const tripDate = new Date(trip.trip_date);
                const toDate = new Date(activeFilters.dateTo);
                toDate.setHours(23, 59, 59, 999); // End of day
                if (tripDate > toDate) return false;
            }

            // Distance filters
            if (activeFilters.minDistance !== null && trip.distance_km < activeFilters.minDistance) {
                return false;
            }

            if (activeFilters.maxDistance !== null && trip.distance_km > activeFilters.maxDistance) {
                return false;
            }

            // Speed filters
            if (activeFilters.minSpeed !== null && trip.avg_speed_kmph < activeFilters.minSpeed) {
                return false;
            }

            if (activeFilters.maxSpeed !== null && trip.avg_speed_kmph > activeFilters.maxSpeed) {
                return false;
            }

            return true;
        });

        updateTableDisplay();
        updateStatistics();
        showNotification(`Showing ${filteredTrips.length} of ${allTrips.length} trips`, 'info');
    }

    function updateTableDisplay() {
        const tbody = document.getElementById('tripsTableBody');
        tbody.innerHTML = '';

        if (filteredTrips.length === 0) {
            tbody.innerHTML = '<tr><td colspan="19" style="text-align: center; padding: 40px; color: #6b7280;">No trips match the selected filters</td></tr>';
            return;
        }

        filteredTrips.forEach(trip => {
            const row = document.createElement('tr');
            row.setAttribute('data-trip', JSON.stringify(trip));
            row.innerHTML = `
                <td>${trip.trip_date}</td>
                <td>${trip.distance_km}</td>
                <td>${trip.avg_speed_kmph}</td>
                <td>${trip.max_speed}</td>
                <td>${trip.max_rpm}</td>
                <td>${trip.fuel_consumed}</td>
                <td>${trip.brake_events}</td>
                <td>${trip.steering_angle}</td>
                <td>${trip.angular_velocity}</td>
                <td>${trip.acceleration}</td>
                <td>${trip.gear_position}</td>
                <td>${trip.tire_pressure}</td>
                <td>${trip.engine_load}</td>
                <td>${trip.throttle_position}</td>
                <td>${trip.brake_pressure}</td>
                <td>${trip.trip_duration}</td>
                <td>${trip.start_location}</td>
                <td>${trip.end_location}</td>
                <td><a href="/trip/${trip.id}">View</a></td>
            `;
            tbody.appendChild(row);
        });
    }

    function updateStatistics() {
        if (filteredTrips.length === 0) {
            document.getElementById('totalDistance').textContent = '0 km';
            document.getElementById('avgSpeed').textContent = '0 km/h';
            document.getElementById('totalFuel').textContent = '0 L';
            document.getElementById('totalTrips').textContent = '0';
            return;
        }

        const totalDistance = filteredTrips.reduce((sum, trip) => sum + parseFloat(trip.distance_km || 0), 0);
        const avgSpeed = filteredTrips.reduce((sum, trip) => sum + parseFloat(trip.avg_speed_kmph || 0), 0) / filteredTrips.length;
        const totalFuel = filteredTrips.reduce((sum, trip) => sum + parseFloat(trip.fuel_consumed || 0), 0);

        document.getElementById('totalDistance').textContent = totalDistance.toFixed(1) + ' km';
        document.getElementById('avgSpeed').textContent = avgSpeed.toFixed(1) + ' km/h';
        document.getElementById('totalFuel').textContent = totalFuel.toFixed(1) + ' L';
        document.getElementById('totalTrips').textContent = filteredTrips.length;
    }

    function updateFilterButton() {
        const activeFilterCount = Object.values(activeFilters).filter(v => v !== null && v !== '').length;
        
        if (activeFilterCount > 0) {
            filterBtn.classList.add('filter-active');
            
            // Add badge if it doesn't exist
            let badge = filterBtn.querySelector('.filter-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'filter-badge';
                filterBtn.appendChild(badge);
            }
            badge.textContent = activeFilterCount;
        } else {
            filterBtn.classList.remove('filter-active');
            const badge = filterBtn.querySelector('.filter-badge');
            if (badge) badge.remove();
        }
    }

    // ========== NOTIFICATION SYSTEM ==========

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background-color: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            font-weight: 500;
            animation: slideInRight 0.3s ease-out;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // Close modals when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === exportModal) {
            exportModal.style.display = 'none';
        }
        if (event.target === filterModal) {
            filterModal.style.display = 'none';
        }
    });

    // Initialize
    updateFilterButton();

})();