// static/js/script.js
/**
 * Client-side JavaScript for the Task Planning Agent Dashboard.
 * Handles form submission, progress animations, markdown rendering, history loading.
 * Implements accordion-style history, editing/saving plans.
 */

document.addEventListener('DOMContentLoaded', () => {
    const goalInput = document.getElementById('goal-input');
    const generateBtn = document.getElementById('generate-btn');
    const progressSection = document.getElementById('progress-section');
    const planSection = document.getElementById('plan-section');
    const progressMessage = document.getElementById('progress-message');
    const searchAnimation = document.getElementById('search-animation');
    const generatingMessage = document.getElementById('generating-message');
    const planContent = document.getElementById('plan-content');
    const editSection = document.getElementById('edit-section');
    const editTextarea = document.getElementById('edit-textarea');
    const saveEditBtn = document.getElementById('save-edit-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const editPlanBtn = document.getElementById('edit-plan-btn');
    const newPlanBtn = document.getElementById('new-plan-btn');
    const historyList = document.getElementById('history-list');

    let currentEditId = null;

    // Load history on page load
    loadHistory();

    generateBtn.addEventListener('click', async () => {
        const goal = goalInput.value.trim();
        if (!goal) {
            alert('Please enter a goal!');
            return;
        }

        // Show progress, hide others
        progressSection.classList.remove('hidden');
        planSection.classList.add('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        // Reset progress
        document.querySelector('.progress-fill').style.width = '0%';
        progressMessage.textContent = 'Generating search queries...';
        searchAnimation.classList.add('hidden');
        generatingMessage.classList.add('hidden');

        try {
            const response = await fetch('/generate_plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal })
            });

            if (!response.ok) {
                const data = await response.json();
                progressMessage.textContent = data.error || 'An error occurred.';
                return;
            }

            const data = await response.json();

            // Animate search links
            const links = data.sources || [];
            for (let i = 0; i < links.length; i++) {
                setTimeout(() => {
                    const linkItem = document.getElementById(`link-${i + 1}`);
                    const linkUrl = document.getElementById(`link-url-${i + 1}`);
                    linkUrl.href = links[i].url;
                    linkUrl.textContent = `Link ${i + 1}: ${links[i].search_query}`;
                    linkItem.classList.remove('hidden');
                    linkItem.classList.add('visible');
                    searchAnimation.classList.remove('hidden');
                }, i * 1500);  // Stagger by 1.5s
            }

            // Simulate progress bar
            let progress = 0;
            const interval = setInterval(() => {
                progress += 10;
                document.querySelector('.progress-fill').style.width = `${progress}%`;
                if (progress >= 100) clearInterval(interval);
            }, 500);

            // After searches, show generating
            setTimeout(() => {
                searchAnimation.classList.add('hidden');
                [...searchAnimation.children].forEach(child => {
                    child.classList.remove('visible');
                    child.classList.add('hidden');
                });
                generatingMessage.classList.remove('hidden');
                progressMessage.textContent = 'Finalizing your answer...';
            }, links.length * 1500 + 1000);

            // Show plan
            setTimeout(() => {
                progressSection.classList.add('hidden');
                planContent.innerHTML = marked.parse(data.plan || 'No response generated.');
                planSection.classList.remove('hidden');
                planSection.scrollIntoView({ behavior: 'smooth' });
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Answer ✨';
                goalInput.value = '';  // Clear input
                loadHistory();  // Refresh history to include new plan
                currentEditId = data.id;  // Set for editing
                editPlanBtn.classList.remove('hidden');
            }, links.length * 1500 + 3000);

        } catch (error) {
            progressMessage.textContent = 'Network error. Please try again.';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Answer ✨';
        }
    });

    newPlanBtn.addEventListener('click', () => {
        planSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        goalInput.value = '';
        generateBtn.disabled = false;
        editSection.classList.add('hidden');
        editPlanBtn.classList.remove('hidden');
        currentEditId = null;
    });

    editPlanBtn.addEventListener('click', () => {
        if (!currentEditId) return;
        editTextarea.value = planContent.textContent;  // Get raw text for editing
        planContent.classList.add('hidden');
        editSection.classList.remove('hidden');
        editPlanBtn.classList.add('hidden');
    });

    cancelEditBtn.addEventListener('click', () => {
        editSection.classList.add('hidden');
        planContent.classList.remove('hidden');
        editPlanBtn.classList.remove('hidden');
    });

    saveEditBtn.addEventListener('click', async () => {
        const newPlan = editTextarea.value;
        if (!newPlan || !currentEditId) return;

        try {
            const response = await fetch('/update_plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: currentEditId, plan: newPlan })
            });

            if (response.ok) {
                planContent.innerHTML = marked.parse(newPlan);
                editSection.classList.add('hidden');
                planContent.classList.remove('hidden');
                editPlanBtn.classList.remove('hidden');
                loadHistory();  // Refresh history
            } else {
                alert('Failed to save changes.');
            }
        } catch (error) {
            alert('Network error while saving.');
        }
    });

    async function loadHistory() {
        try {
            const response = await fetch('/history');
            const plans = await response.json();
            historyList.innerHTML = plans.map(plan => `
                <div class="history-item" data-id="${plan.id}">
                    <div class="history-header">
                        <h3>${plan.goal}</h3>
                        <small>${new Date(plan.timestamp).toLocaleString()}</small>
                    </div>
                    <div class="history-content">
                        <div>${marked.parse(plan.plan)}</div>
                    </div>
                </div>
            `).join('');

            // Add click listeners for accordion
            document.querySelectorAll('.history-item .history-header').forEach(header => {
                header.addEventListener('click', () => {
                    const content = header.nextElementSibling;
                    const isOpen = content.classList.contains('open');

                    // Close all others
                    document.querySelectorAll('.history-content.open').forEach(openContent => {
                        if (openContent !== content) {
                            openContent.classList.remove('open');
                        }
                    });

                    // Toggle current
                    content.classList.toggle('open', !isOpen);
                });
            });
        } catch (error) {
            console.error('Failed to load history:', error);
            historyList.innerHTML = '<p>Failed to load history.</p>';
        }
    }
});