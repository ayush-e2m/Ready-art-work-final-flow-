let currentSessionId = null;
let statusCheckInterval = null;
let competitorCounter = 3;
const maxCompetitors = 10;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    initializeForm();
});

function initializeForm() {
    // Focus on primary URL input
    const primaryInput = document.getElementById('primaryUrl');
    if (primaryInput) {
        primaryInput.focus();
    }
}

function setupEventListeners() {
    // Form submission
    const form = document.getElementById('competitorForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Add competitor button
    const addBtn = document.getElementById('addCompetitorBtn');
    if (addBtn) {
        addBtn.addEventListener('click', addCompetitorInput);
    }
}

function addCompetitorInput() {
    if (competitorCounter >= maxCompetitors) {
        showNotification(`Maximum of ${maxCompetitors} websites allowed for analysis.`, 'warning');
        return;
    }
    
    competitorCounter++;
    const grid = document.getElementById('competitorsGrid');
    
    // Create new competitor input
    const competitorDiv = document.createElement('div');
    competitorDiv.className = 'competitor-input';
    competitorDiv.setAttribute('data-competitor', competitorCounter);
    
    competitorDiv.innerHTML = `
        <div class="competitor-number">${competitorCounter}</div>
        <label>Competitor #${competitorCounter}</label>
        <input type="url" name="url${competitorCounter + 1}" placeholder="https://competitor${competitorCounter}.com">
        <button type="button" class="remove-competitor-btn" onclick="removeCompetitorInput(${competitorCounter})">
            <span class="remove-icon">×</span>
        </button>
    `;
    
    grid.appendChild(competitorDiv);
    
    // Update add button visibility
    updateAddButtonState();
    
    // Focus on new input
    const newInput = competitorDiv.querySelector('input');
    if (newInput) {
        newInput.focus();
    }
    
    // Add entrance animation
    competitorDiv.style.opacity = '0';
    competitorDiv.style.transform = 'translateY(10px)';
    setTimeout(() => {
        competitorDiv.style.transition = 'all 0.3s ease';
        competitorDiv.style.opacity = '1';
        competitorDiv.style.transform = 'translateY(0)';
    }, 50);
}

function removeCompetitorInput(competitorNumber) {
    const competitorDiv = document.querySelector(`[data-competitor="${competitorNumber}"]`);
    if (competitorDiv) {
        // Add exit animation
        competitorDiv.style.transition = 'all 0.3s ease';
        competitorDiv.style.opacity = '0';
        competitorDiv.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            competitorDiv.remove();
            renumberCompetitors();
            updateAddButtonState();
        }, 300);
    }
}

function renumberCompetitors() {
    const competitorInputs = document.querySelectorAll('.competitor-input');
    competitorCounter = 3; // Reset to base count
    
    competitorInputs.forEach((div, index) => {
        const actualNumber = index + 1;
        if (actualNumber > 3) {
            competitorCounter = actualNumber;
            div.setAttribute('data-competitor', actualNumber);
            
            // Update number display
            const numberDiv = div.querySelector('.competitor-number');
            if (numberDiv) {
                numberDiv.textContent = actualNumber;
            }
            
            // Update label
            const label = div.querySelector('label');
            if (label) {
                label.textContent = `Competitor #${actualNumber}`;
            }
            
            // Update input name and placeholder
            const input = div.querySelector('input');
            if (input) {
                input.name = `url${actualNumber + 1}`;
                input.placeholder = `https://competitor${actualNumber}.com`;
            }
            
            // Update remove button
            const removeBtn = div.querySelector('.remove-competitor-btn');
            if (removeBtn) {
                removeBtn.setAttribute('onclick', `removeCompetitorInput(${actualNumber})`);
            }
        }
    });
}

function updateAddButtonState() {
    const addBtn = document.getElementById('addCompetitorBtn');
    const limitText = document.querySelector('.limit-text');
    
    if (competitorCounter >= maxCompetitors) {
        addBtn.style.display = 'none';
        limitText.textContent = `Maximum of ${maxCompetitors} websites reached`;
        limitText.style.color = 'var(--warning-orange)';
    } else {
        addBtn.style.display = 'inline-flex';
        limitText.textContent = `You can analyze up to ${maxCompetitors} websites at once`;
        limitText.style.color = 'var(--gray-400)';
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {};
    
    // Collect all URL inputs
    let urlIndex = 1;
    for (const [key, value] of formData.entries()) {
        if (key.startsWith('url') && value.trim()) {
            data[`url${urlIndex}`] = value.trim();
            urlIndex++;
        }
    }
    
    // Validate primary URL
    if (!data.url1) {
        showNotification('Please enter your primary website URL', 'error');
        return;
    }
    
    // Show analysis in progress
    showAnalysisProgress();
    disableForm();
    
    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Failed to start competitive analysis');
        }
        
        currentSessionId = result.session_id;
        updateProgress(0, result.total_urls, 'Initializing competitive analysis...');
        startStatusChecking();
        
    } catch (error) {
        showError(error.message);
        enableForm();
    }
}

function showAnalysisProgress() {
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('errorSection').style.display = 'none';
    
    // Scroll to progress section
    document.getElementById('progressSection').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
    });
}

function showError(message) {
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('progressSection').style.display = 'none';
    
    // Scroll to error section
    document.getElementById('errorSection').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
    });
    
    showNotification(message, 'error');
}

function disableForm() {
    const startBtn = document.getElementById('startAnalysisBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    
    startBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline-block';
    
    // Disable all inputs
    const inputs = document.querySelectorAll('input, button:not(#startAnalysisBtn)');
    inputs.forEach(input => input.disabled = true);
}

function enableForm() {
    const startBtn = document.getElementById('startAnalysisBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    
    startBtn.disabled = false;
    btnText.style.display = 'inline';
    btnSpinner.style.display = 'none';
    
    // Enable all inputs
    const inputs = document.querySelectorAll('input, button');
    inputs.forEach(input => input.disabled = false);
}

function startStatusChecking() {
    statusCheckInterval = setInterval(checkAnalysisStatus, 2000);
}

function stopStatusChecking() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

async function checkAnalysisStatus() {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`/status/${currentSessionId}`);
        const status = await response.json();
        
        if (!response.ok) {
            throw new Error('Failed to get analysis status');
        }
        
        updateProgress(status.completed, status.total, status.current_url || 'Processing...');
        
        if (status.status === 'completed') {
            stopStatusChecking();
            showNotification('Competitive analysis completed successfully!', 'success');
            
            // Redirect to results with a brief delay
            setTimeout(() => {
                window.location.href = `/results/${currentSessionId}`;
            }, 1500);
            
        } else if (status.status === 'error') {
            stopStatusChecking();
            showError(status.error || 'An error occurred during competitive analysis');
            enableForm();
        }
        
    } catch (error) {
        console.warn('Status check failed:', error);
        // Continue checking - might be temporary network issue
    }
}

function updateProgress(completed, total, currentUrl) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressStatus = document.getElementById('progressStatus');
    const currentUrlElement = document.getElementById('currentUrl');
    
    const percentage = total > 0 ? (completed / total) * 100 : 0;
    
    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }
    
    if (progressText) {
        progressText.textContent = `${completed} of ${total} websites analyzed`;
    }
    
    if (currentUrl && currentUrlElement) {
        if (currentUrl.startsWith('Completed') || currentUrl.includes('completed')) {
            currentUrlElement.textContent = '✅ Analysis complete';
        } else if (currentUrl.startsWith('http')) {
            currentUrlElement.textContent = `🔍 Analyzing: ${extractDomain(currentUrl)}`;
        } else {
            currentUrlElement.textContent = currentUrl;
        }
    }
    
    if (progressStatus) {
        if (completed === total && total > 0) {
            progressStatus.textContent = 'Finalizing competitive analysis results...';
        } else if (completed > 0) {
            progressStatus.textContent = `Analyzing competitor websites and extracting UI/UX metrics...`;
        } else {
            progressStatus.textContent = 'Starting competitive analysis...';
        }
    }
}

function extractDomain(url) {
    try {
        return new URL(url).hostname.replace('www.', '');
    } catch {
        return url;
    }
}

function resetAnalysis() {
    document.getElementById('errorSection').style.display = 'none';
    document.getElementById('progressSection').style.display = 'none';
    enableForm();
    currentSessionId = null;
    stopStatusChecking();
    
    // Reset progress
    updateProgress(0, 0, '');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">
                ${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}
            </span>
            <span class="notification-message">${message}</span>
        </div>
    `;
    
    // Add notification styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--success-green)' : 
                    type === 'error' ? 'var(--error-red)' : 
                    type === 'warning' ? 'var(--warning-orange)' : 'var(--primary-blue)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        opacity: 0;
        transform: translateX(100px);
        transition: all 0.3s ease;
        max-width: 400px;
        font-weight: 500;
    `;
    
    const contentStyle = `
        display: flex;
        align-items: center;
        gap: 0.75rem;
    `;
    
    notification.querySelector('.notification-content').style.cssText = contentStyle;
    
    // Add to DOM
    document.body.appendChild(notification);
    
    // Animate in
    requestAnimationFrame(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    });
    
    // Remove after delay
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100px)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 4000);
}

// Add CSS for remove competitor buttons
function addRemoveButtonStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .remove-competitor-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 24px;
            height: 24px;
            background: var(--error-red);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.2s ease;
            z-index: 10;
        }
        
        .remove-competitor-btn:hover {
            background: #d93025;
            transform: scale(1.1);
        }
        
        .competitor-input {
            position: relative;
        }
        
        .competitor-input:nth-child(-n+3) .remove-competitor-btn {
            display: none;
        }
    `;
    document.head.appendChild(style);
}

// Initialize remove button styles
document.addEventListener('DOMContentLoaded', addRemoveButtonStyles);
