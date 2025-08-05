// Lazy Loading JavaScript for Admin Dashboard
// This file handles AJAX loading of detailed statistics

class DashboardLazyLoader {
    constructor() {
        this.loadedStats = new Set();
        this.loadingPromises = new Map();
        this.init();
    }

    init() {
        // Initialize lazy loading for dashboard elements
        this.setupLazyLoading();
        this.setupScrollTriggers();
        this.setupTabTriggers();
    }

    setupLazyLoading() {
        // Find elements that need lazy loading
        const lazyElements = document.querySelectorAll('[data-lazy-load]');
        
        lazyElements.forEach(element => {
            const loadType = element.dataset.lazyLoad;
            const loadTrigger = element.dataset.loadTrigger || 'scroll';
            
            if (loadTrigger === 'scroll') {
                this.setupScrollObserver(element, loadType);
            } else if (loadTrigger === 'click') {
                this.setupClickTrigger(element, loadType);
            } else if (loadTrigger === 'tab') {
                this.setupTabTrigger(element, loadType);
            }
        });
    }

    setupScrollObserver(element, loadType) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !this.loadedStats.has(loadType)) {
                    this.loadStatistics(loadType, element);
                }
            });
        }, {
            rootMargin: '50px'
        });
        
        observer.observe(element);
    }

    setupClickTrigger(element, loadType) {
        element.addEventListener('click', (e) => {
            if (!this.loadedStats.has(loadType)) {
                e.preventDefault();
                this.loadStatistics(loadType, element);
            }
        });
    }

    setupTabTrigger(element, loadType) {
        // For tab-based loading, we'll use a custom event
        document.addEventListener('tabChanged', (e) => {
            if (e.detail.tabId === element.dataset.tabId && !this.loadedStats.has(loadType)) {
                this.loadStatistics(loadType, element);
            }
        });
    }

    setupScrollTriggers() {
        // Setup scroll-based loading for dashboard sections
        const sections = document.querySelectorAll('.dashboard-section[data-lazy-load]');
        
        sections.forEach(section => {
            const loadType = section.dataset.lazyLoad;
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !this.loadedStats.has(loadType)) {
                        this.loadStatistics(loadType, section);
                    }
                });
            }, {
                threshold: 0.1
            });
            
            observer.observe(section);
        });
    }

    setupTabTriggers() {
        // Setup tab-based loading
        const tabs = document.querySelectorAll('[data-tab-trigger]');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = tab.dataset.tabTrigger;
                document.dispatchEvent(new CustomEvent('tabChanged', {
                    detail: { tabId: tabId }
                }));
            });
        });
    }

    async loadStatistics(loadType, element) {
        // Prevent duplicate loading
        if (this.loadedStats.has(loadType) || this.loadingPromises.has(loadType)) {
            return;
        }

        // Show loading state
        this.showLoadingState(element);

        try {
            // Check if we already have a loading promise for this type
            if (this.loadingPromises.has(loadType)) {
                await this.loadingPromises.get(loadType);
                return;
            }

            // Create loading promise
            const loadPromise = this.fetchStatistics(loadType);
            this.loadingPromises.set(loadType, loadPromise);

            const data = await loadPromise;
            this.renderStatistics(loadType, element, data);
            this.loadedStats.add(loadType);

        } catch (error) {
            console.error(`Failed to load ${loadType} statistics:`, error);
            this.showErrorState(element, error);
        } finally {
            this.loadingPromises.delete(loadType);
            this.hideLoadingState(element);
        }
    }

    async fetchStatistics(loadType) {
        const url = `/admin/dashboard/stats-ajax/?type=${loadType}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    renderStatistics(loadType, element, data) {
        switch (loadType) {
            case 'detailed':
                this.renderDetailedStats(element, data);
                break;
            case 'recent_activities':
                this.renderRecentActivities(element, data);
                break;
            case 'user_trends':
                this.renderUserTrends(element, data);
                break;
            case 'security_events':
                this.renderSecurityEvents(element, data);
                break;
            default:
                this.renderGenericStats(element, data);
        }
    }

    renderDetailedStats(element, data) {
        const template = `
            <div class="detailed-stats">
                <h4>Recent Activities</h4>
                <div class="activity-list">
                    ${data.recent_activities.map(activity => `
                        <div class="activity-item">
                            <span class="user">${activity.user__username}</span>
                            <span class="action">${activity.action}</span>
                            <span class="time">${new Date(activity.timestamp).toLocaleString()}</span>
                        </div>
                    `).join('')}
                </div>
                
                <h4>User Registration Trend</h4>
                <div class="trend-chart">
                    ${data.user_registration_trend.map(day => `
                        <div class="trend-day">
                            <span class="date">${day.day}</span>
                            <span class="count">${day.count}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        element.innerHTML = template;
    }

    renderRecentActivities(element, data) {
        const template = `
            <div class="recent-activities">
                ${data.map(activity => `
                    <div class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-user"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-user">${activity.user__username}</div>
                            <div class="activity-action">${activity.action}</div>
                            <div class="activity-time">${new Date(activity.timestamp).toLocaleString()}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        element.innerHTML = template;
    }

    renderUserTrends(element, data) {
        // Create a simple chart using CSS or integrate with Chart.js
        const template = `
            <div class="user-trends">
                <canvas id="userTrendChart"></canvas>
            </div>
        `;
        
        element.innerHTML = template;
        
        // Initialize chart if Chart.js is available
        if (typeof Chart !== 'undefined') {
            this.createUserTrendChart(data);
        }
    }

    renderSecurityEvents(element, data) {
        const template = `
            <div class="security-events">
                ${data.map(event => `
                    <div class="security-event ${event.action.toLowerCase()}">
                        <div class="event-type">${event.action}</div>
                        <div class="event-time">${new Date(event.timestamp).toLocaleString()}</div>
                        <div class="event-ip">${event.ip_address || 'N/A'}</div>
                    </div>
                `).join('')}
            </div>
        `;
        
        element.innerHTML = template;
    }

    renderGenericStats(element, data) {
        const template = `
            <div class="generic-stats">
                ${Object.entries(data).map(([key, value]) => `
                    <div class="stat-item">
                        <span class="stat-label">${key.replace(/_/g, ' ').toUpperCase()}</span>
                        <span class="stat-value">${value}</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        element.innerHTML = template;
    }

    createUserTrendChart(data) {
        const ctx = document.getElementById('userTrendChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(item => item.day),
                datasets: [{
                    label: 'User Registrations',
                    data: data.map(item => item.count),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    showLoadingState(element) {
        element.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading statistics...</p>
            </div>
        `;
    }

    hideLoadingState(element) {
        // Loading state will be replaced by actual content
    }

    showErrorState(element, error) {
        element.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Failed to load statistics</p>
                <small>${error.message}</small>
            </div>
        `;
    }

    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize lazy loading when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardLazyLoader();
});

// Export for use in other modules
window.DashboardLazyLoader = DashboardLazyLoader; 