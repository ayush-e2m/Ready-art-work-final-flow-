let currentSessionId = null;
let statusCheckInterval = null;
let urlCounter = 1;
const maxUrls = 10;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    document.getElementById('scrapeForm').addEventListener('submit', handleFormSubmit);
    
    // Add URL button
    document.getElementById('addUrlBtn').addEventListener('click', addUrlInput);
}

function addUrlInput() {
    if (urlCounter >= maxUrls) {
        alert(`You can analyze a maximum of ${maxUrls} websites at once.`);
        return;
    }
    
    urlCounter++;
    const urlInputs = document.getElementById('urlInputs');
    
    // Create new input group
    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group';
    inputGroup.setAttribute('data-index', urlCounter);
    
    inputGroup.innerHTML = `
        <label for="url${urlCounter}">Website ${urlCounter}:</label>
        <div class="input-with-controls">
            <input type="url" id="url${urlCounter}" name="url${urlCounter}" placeholder="https://example.com">
            <button type="button" class="remove-url-btn" onclick="removeUrlInput(${urlCounter})">
                <span class="remove-icon">×</span>
            </button>
        </div>
    `;
    
    urlInputs.appendChild(inputGroup);
    
    // Update add button visibility
    updateAddButtonVisibility();
    
    // Focus on new input
    document.getElementById(`url${urlCounter}`).focus();
}

function removeUrlInput(index) {
    const inputGroup = document.querySelector(`[data-index="${index}"]`);
    if (inputGroup) {
        inputGroup.remove();
        
        // Renumber remaining inputs
        renumberInputs();
        
        // Update add button visibility
        updateAddButtonVisibility();
    }
}

function renumberInputs() {
    const inputGroups = document.querySelectorAll('.input-group');
    urlCounter = 0;
    
    inputGroups.forEach((group, index) => {
        urlCounter = index + 1;
        const newIndex = urlCounter;
        
        // Update data attribute
        group.setAttribute('data-index', newIndex);
        
        // Update label
        const label = group.querySelector('label');
        label.textContent = `Website ${newIndex}:`;
        label.setAttribute('for', `url${newIndex}`);
        
        // Update input
        const input = group.querySelector('input');
        input.id = `url${newIndex}`;
        input.name = `url${newIndex}`;
        
        // Update remove button if it exists
        const removeBtn = group.querySelector('.remove-url-btn');
        if (removeBtn) {
            removeBtn.setAttribute('onclick', `removeUrlInput(${newIndex})`);
        }
        
        // Make first input required, others optional
        if (newIndex === 1) {
            input.required = true;
            // Remove remove button from first input if it exists
            if (removeBtn) {
                removeBtn.remove();
            }
        } else {
            input.required = false;
        }
    });
}

function updateAddButtonVisibility() {
    const addBtn = document.getElementById('addUrlBtn');
    const limitText = document.querySelector('.url-limit-text');
    
    if (urlCounter >= maxUrls) {
        addBtn.style.display = 'none';
        limitText.textContent = `Maximum of ${maxUrls} websites reached`;
        limitText.style.color = '#e53e3e';
    } else {
        addBtn.style.display = 'flex';
        limitText.textContent = `You can analyze up to ${maxUrls} websites at once`;
        limitText.style.color = '#718096';
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {};
    
    // Collect all URL inputs dynamically
    for (let i = 1; i <= urlCounter; i++) {
        const urlInput = document.getElementById(`url${i}`);
        if (urlInput) {
            data[`url${i}`] = urlInput.value || '';
        }
    }
    
    // Update UI to show loading state
    showProgress();
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
            throw new Error(result.message || 'Failed to start analysis');
        }
        
        currentSessionId = result.session_id;
        startStatusChecking();
        
    } catch (error) {
        showError(error.message);
        enableForm();
    }
}

function showProgress() {
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('errorContainer').style.display = 'none';
}

function showError(message) {
    document.getElementById('errorContainer').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('progressContainer').style.display = 'none';
}

function disableForm() {
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('btnText').style.display = 'none';
    document.getElementById('spinner').style.display = 'inline-block';
    
    // Disable all inputs and buttons
    const inputs = document.querySelectorAll('input, button:not(#analyzeBtn)');
    inputs.forEach(input => input.disabled = true);
}

function enableForm() {
    document.getElementById('analyzeBtn').disabled = false;
    document.getElementById('btnText').style.display = 'inline';
    document.getElementById('spinner').style.display = 'none';
    
    // Enable all inputs and buttons
    const inputs = document.querySelectorAll('input, button');
    inputs.forEach(input => input.disabled = false);
}

function startStatusChecking() {
    statusCheckInterval = setInterval(checkStatus, 2000);
}

function stopStatusChecking() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

async function checkStatus() {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch('/status/' + currentSessionId);
        const status = await response.json();
        
        if (!response.ok) {
            throw new Error('Failed to get status');
        }
        
        updateProgressUI(status);
        
        if (status.status === 'completed') {
            stopStatusChecking();
            // Redirect to results page
            window.location.href = '/results/' + currentSessionId;
        } else if (status.status === 'error') {
            stopStatusChecking();
            showError(status.error || 'An error occurred during analysis');
            enableForm();
        }
        
    } catch (error) {
        console.error('Status check failed:', error);
        // Continue checking, might be temporary network issue
    }
}

function updateProgressUI(status) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const currentStatus = document.getElementById('currentStatus');
    
    const percentage = status.total > 0 ? (status.completed / status.total) * 100 : 0;
    
    progressFill.style.width = percentage + '%';
    progressText.textContent = status.completed + ' of ' + status.total + ' completed';
    
    if (status.current_url) {
        currentStatus.textContent = 'Analyzing: ' + status.current_url;
    } else if (status.status === 'processing') {
        currentStatus.textContent = 'Processing websites...';
    }
}

function resetForm() {
    document.getElementById('errorContainer').style.display = 'none';
    document.getElementById('progressContainer').style.display = 'none';
    enableForm();
    currentSessionId = null;
    stopStatusChecking();
}
