// static/js/script.js
/**
 * Client-side JavaScript for dashboard interactions.
 * Handles form submission, progress animations (fade in/out sources),
 * Markdown rendering, history loading, and API calls.
 */

document.addEventListener('DOMContentLoaded', () => {
    const goalInput = document.getElementById('goal-input');
    const generateBtn = document.getElementById('generate-btn');
    const progressSection = document.getElementById('progress-section');
    const resultSection = document.getElementById('result-section');
    const planOutput = document.getElementById('plan-output');
    const newPlanBtn = document.getElementById('new-plan-btn');
    const sourcesList = document.getElementById('sources-list');
    const progressMessage = document.getElementById('progress-message');
    const stageMessage = document.getElementById('stage-message');
    const historyList = document.getElementById('history-list');

    // Load history on start
    loadHistory();

    generateBtn.addEventListener('click', async () => {
        const goal = goalInput.value.trim();
        if (!goal) return alert('Please enter a goal!');

        // Show progress, hide others
        progressSection.classList.remove('hidden');
        resultSection.classList.add('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        // Simulate staged progress
        updateProgress('searching', '🔍 Hunting for the best resources...');

        try {
            const response = await fetch('/api/generate-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal })
            });

            const data = await response.json();

            if (data.status === 'success') {
                // Animate sources one by one (from progress)
                sourcesList.innerHTML = '';
                const sources = data.progress.sources || [];
                sources.forEach((source, index) => {
                    setTimeout(() => {
                        const item = document.createElement('div');
                        item.className = 'source-item';
                        item.innerHTML = `<strong>${index + 1}.</strong> <a href="${source.url}" target="_blank">${source.url}</a><br>Query: ${source.search_query}`;
                        sourcesList.appendChild(item);
                    }, index * 800);  // Staggered fade-in
                });

                setTimeout(() => {
                    updateProgress('summarizing', '✂️ Summarizing key insights...');
                }, sources.length * 800 + 500);

                setTimeout(() => {
                    updateProgress('generating', '🎨 Crafting your awesome plan...');
                }, sources.length * 800 + 1500);

                // Render plan after delay
                setTimeout(() => {
                    progressSection.classList.add('hidden');
                    planOutput.innerHTML = marked.parse(data.plan);  // Render Markdown
                    resultSection.classList.remove('hidden');
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Plan ✨';
                }, 3000);
            } else {
                alert(data.message);
                resetUI();
            }
        } catch (error) {
            alert('Oops! Something went wrong. Try again.');
            resetUI();
        }
    });

    newPlanBtn.addEventListener('click', () => {
        resultSection.classList.add('hidden');
        goalInput.value = '';
        goalInput.focus();
    });

    function updateProgress(stage, message) {
        progressMessage.textContent = message;
        stageMessage.textContent = `Stage: ${stage}`;
        // Update bar animation via CSS class if needed
    }

    function resetUI() {
        progressSection.classList.add('hidden');
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Plan ✨';
    }

    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            const plans = await response.json();
            historyList.innerHTML = plans.map(plan => `
                <div class="history-item" onclick="showPlan('${plan.goal}', '${plan.plan.replace(/'/g, "\\'")}')">
                    <strong>${plan.goal.substring(0, 50)}...</strong><br>
                    <small>${new Date(plan.timestamp).toLocaleString()}</small>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load history');
        }
    }

    window.showPlan = (goal, plan) => {
        planOutput.innerHTML = marked.parse(plan);
        resultSection.scrollIntoView({ behavior: 'smooth' });
    };

    // Auto-save goal on input for UX
    goalInput.addEventListener('input', () => localStorage.setItem('last-goal', goalInput.value));
    goalInput.value = localStorage.getItem('last-goal') || '';
});