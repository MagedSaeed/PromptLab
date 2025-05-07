/**
 * OpenRouter API Key Management
 * Handles the OpenRouter API key modal functionality including:
 * - Saving API keys
 * - Deleting API keys
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const apiForm = document.getElementById('openRouterApiForm');
    const apiKeyInput = document.getElementById('id_openrouter_api_key');
    const deleteApiKeyBtn = document.getElementById('deleteApiKeyBtn');
    const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    const saveSpinner = document.getElementById('saveSpinner');
    const saveSuccessAlert = document.getElementById('saveSuccessAlert');
    const saveErrorAlert = document.getElementById('saveErrorAlert');
    const saveErrorMessage = document.getElementById('saveErrorMessage');
    const keyValidationMessage = document.getElementById('keyValidationMessage');
    
    // Helper function to get CSRF token
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    // Show validation error
    function showInputError(input, message) {
        input.classList.add('is-invalid');
        if (keyValidationMessage) {
            keyValidationMessage.textContent = message;
        }
    }
    
    // Clear validation error
    function clearInputError(input) {
        input.classList.remove('is-invalid');
    }
    
    // Reset save alerts
    function resetSaveAlerts() {
        if (saveSuccessAlert) {
            saveSuccessAlert.classList.add('d-none');
        }
        if (saveErrorAlert) {
            saveErrorAlert.classList.add('d-none');
        }
    }
    
    // Initialize by hiding all alerts when the modal is shown
    const openRouterModal = document.getElementById('openRouterApiModal');
    if (openRouterModal) {
        openRouterModal.addEventListener('shown.bs.modal', function() {
            resetSaveAlerts();
        });
    }
    
    // Handle API key save
    if (apiForm) {
        apiForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate the API key format - basic validation
            const apiKey = apiKeyInput.value.trim();
            if (!apiKey) {
                showInputError(apiKeyInput, 'API key cannot be empty');
                return;
            }
            
            if (apiKey.length < 10) {
                showInputError(apiKeyInput, 'API key appears to be too short');
                return;
            }
            
            clearInputError(apiKeyInput);
            resetSaveAlerts();
            
            if (saveSpinner) {
                saveSpinner.classList.remove('d-none');
            }
            if (saveApiKeyBtn) {
                saveApiKeyBtn.disabled = true;
            }
            
            // Send API request to save the key
            fetch('/core/openrouter/api-key/', {
                method: 'POST',
                body: new FormData(apiForm),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (saveSuccessAlert) {
                        saveSuccessAlert.classList.remove('d-none');
                    }
                    if (saveErrorAlert) {
                        saveErrorAlert.classList.add('d-none');
                    }
                    
                    // Force a full page reload (not just modal refresh)
                    window.location.href = window.location.href;
                } else {
                    if (saveSuccessAlert) {
                        saveSuccessAlert.classList.add('d-none');
                    }
                    if (saveErrorAlert) {
                        saveErrorAlert.classList.remove('d-none');
                    }
                    if (saveErrorMessage) {
                        saveErrorMessage.textContent = data.error || 'Error saving API key';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (saveSuccessAlert) {
                    saveSuccessAlert.classList.add('d-none');
                }
                if (saveErrorAlert) {
                    saveErrorAlert.classList.remove('d-none');
                }
                if (saveErrorMessage) {
                    saveErrorMessage.textContent = 'An unexpected error occurred';
                }
            })
            .finally(() => {
                if (saveSpinner) {
                    saveSpinner.classList.add('d-none');
                }
                if (saveApiKeyBtn) {
                    saveApiKeyBtn.disabled = false;
                }
            });
        });
    }
    
    // Client-side validation for API key input
    if (apiKeyInput) {
        apiKeyInput.addEventListener('input', function() {
            if (this.validity.valueMissing) {
                showInputError(this, 'API key cannot be empty');
            } else if (this.validity.tooShort) {
                showInputError(this, 'API key appears to be too short');
            } else {
                clearInputError(this);
            }
        });
    }
    
    // Handle API key delete
    if (deleteApiKeyBtn) {
        deleteApiKeyBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete your API key? This action cannot be undone.')) {
                resetSaveAlerts();
                
                fetch('/core/openrouter/delete-api-key/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Force a full page reload
                        window.location.href = window.location.href;
                    } else {
                        if (saveSuccessAlert) {
                            saveSuccessAlert.classList.add('d-none');
                        }
                        if (saveErrorAlert) {
                            saveErrorAlert.classList.remove('d-none');
                        }
                        if (saveErrorMessage) {
                            saveErrorMessage.textContent = data.error || 'Error deleting API key';
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (saveSuccessAlert) {
                        saveSuccessAlert.classList.add('d-none');
                    }
                    if (saveErrorAlert) {
                        saveErrorAlert.classList.remove('d-none');
                    }
                    if (saveErrorMessage) {
                        saveErrorMessage.textContent = 'An unexpected error occurred';
                    }
                });
            }
        });
    }
});