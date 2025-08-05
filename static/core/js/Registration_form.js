// Student Onboarding Form JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const form = document.getElementById('studentForm');
    const orgYesBtn = document.getElementById('orgYesBtn');
    const orgNoBtn = document.getElementById('orgNoBtn');
    const organizationDetailsField = document.getElementById('organizationDetailsField');
    const organizationName = document.getElementById('organizationName');
    const organizationRole = document.getElementById('organizationRole');
    const submitBtn = document.querySelector('.submit-btn');

    let isPartOfOrganization = null;

    // Handle Yes button click
    orgYesBtn.addEventListener('click', function() {
        isPartOfOrganization = true;
        orgYesBtn.classList.add('active');
        orgNoBtn.classList.remove('active');
        organizationDetailsField.style.display = 'block';
        organizationDetailsField.classList.add('fade-in');
    });

    // Handle No button click
    orgNoBtn.addEventListener('click', function() {
        isPartOfOrganization = false;
        orgNoBtn.classList.add('active');
        orgYesBtn.classList.remove('active');
        organizationDetailsField.style.display = 'none';
        organizationName.value = '';
        organizationRole.value = '';
    });

    // Form validation
    function validateRegistrationNumber(regNum) {
        return regNum && regNum.trim().length > 0;
    }

    function validateField(element, validationFunction, errorMessage) {
        const existingError = element.parentNode.querySelector('.error-message');
        
        if (validationFunction(element.value)) {
            element.classList.remove('error');
            if (existingError) {
                existingError.remove();
            }
            return true;
        } else {
            element.classList.add('error');
            
            if (!existingError) {
                const errorSpan = document.createElement('span');
                errorSpan.className = 'error-message';
                errorSpan.textContent = errorMessage;
                element.parentNode.appendChild(errorSpan);
            }
            return false;
        }
    }

    // Form submission handler
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Clear any existing error messages
        const errorMessages = form.querySelectorAll('.error-message');
        errorMessages.forEach(msg => msg.remove());
        
        // Remove error classes
        const errorFields = form.querySelectorAll('.error');
        errorFields.forEach(field => field.classList.remove('error'));

        // Validate registration number
        const regNum = document.getElementById('registrationNumber');
        let isValid = validateField(regNum, validateRegistrationNumber, 'Registration number is required');

        // Validate organization details if user selected "Yes"
        if (isPartOfOrganization === true) {
            if (!organizationName.value.trim()) {
                organizationName.classList.add('error');
                const errorSpan = document.createElement('span');
                errorSpan.className = 'error-message';
                errorSpan.textContent = 'Organization name is required';
                organizationName.parentNode.appendChild(errorSpan);
                isValid = false;
            }
            
            if (!organizationRole.value.trim()) {
                organizationRole.classList.add('error');
                const errorSpan = document.createElement('span');
                errorSpan.className = 'error-message';
                errorSpan.textContent = 'Organization role is required';
                organizationRole.parentNode.appendChild(errorSpan);
                isValid = false;
            }
        }

        if (isValid) {
            // Show loading state
            submitBtn.classList.add('loading');
            submitBtn.textContent = 'Submitting...';
            form.classList.add('loading');

            // Simulate form submission
            setTimeout(() => {
                // Collect form data
                const formData = {
                    registrationNumber: regNum.value,
                    partOfOrganization: isPartOfOrganization
                };
                
                if (isPartOfOrganization === true) {
                    formData.organizationName = organizationName.value;
                    formData.organizationRole = organizationRole.value;
                }
                
                console.log('Form Data:', formData);
                
                // Show success message
                showSuccessMessage();
                
                // Reset loading state
                submitBtn.classList.remove('loading');
                submitBtn.textContent = 'Submit Application';
                form.classList.remove('loading');
                
            }, 2000);
        } else {
            // Focus on the first error field
            const firstErrorField = form.querySelector('.error');
            if (firstErrorField) {
                firstErrorField.focus();
            }
        }
    });

    // Form reset handler
    form.addEventListener('reset', function() {
        setTimeout(() => {
            isPartOfOrganization = null;
            orgYesBtn.classList.remove('active');
            orgNoBtn.classList.remove('active');
            organizationDetailsField.style.display = 'none';
            organizationName.value = '';
            organizationRole.value = '';
            
            // Clear validation states
            const allFields = form.querySelectorAll('input');
            const errorMessages = form.querySelectorAll('.error-message');
            
            allFields.forEach(field => {
                field.classList.remove('error');
            });
            
            errorMessages.forEach(msg => msg.remove());
        }, 10);
    });

    function showSuccessMessage() {
        // Create success modal
        const successDiv = document.createElement('div');
        successDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;
        
        const messageBox = document.createElement('div');
        messageBox.style.cssText = `
            background: white;
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;
        
        messageBox.innerHTML = `
            <div style="color: #28a745; font-size: 48px; margin-bottom: 20px;">✓</div>
            <h3 style="color: #2A4B8D; margin-bottom: 16px;">Form Submitted Successfully!</h3>
            <p style="color: #666; margin-bottom: 24px;">Thank you for your submission.</p>
            <button onclick="this.closest('[style*=\"position: fixed\"]').remove()" 
                    style="background: #2A4B8D; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 500;">
                Close
            </button>
        `;
        
        successDiv.appendChild(messageBox);
        document.body.appendChild(successDiv);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(successDiv)) {
                successDiv.remove();
            }
        }, 5000);
    }
});