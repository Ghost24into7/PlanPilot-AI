/**
 * Client-side JS: Handles form submission, loading animations, Markdown rendering.
 * Sequential URL animation: Simulates "exploring" each source with fade.
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('goalForm');
    const loadingSection = document.getElementById('loadingSection');
    const urlLoader = document.getElementById('urlLoader');
    const loadMsg = document.getElementById('loadMsg');
    const sourcesList = document.getElementById('sourcesList');
    const progressMsg = document.getElementById('progressMsg');
    const planOutput = document.getElementById('planOutput');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const goal = document.getElementById('goalInput').value.trim();
        if (!goal) return;

        loadingSection.style.display = 'block';
        urlLoader.style.display = 'block';
        loadMsg.textContent = 'Exploring sources...';
        sourcesList.innerHTML = '';

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal })
            });

            const data = await response.json();

            if (data.error) {
                planOutput.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            } else {
                // Animate sources
                data.sources.forEach((source, index) => {
                    setTimeout(() => {
                        const item = document.createElement('div');
                        item.className = 'url-item text-center';
                        item.innerHTML = `🔍 Link ${index + 1}: <a href="${source.url}" target="_blank">${source.url}</a>`;
                        sourcesList.appendChild(item);
                        if (index < data.sources.length - 1) {
                            item.style.animationDelay = `${index * 1.5}s`;
                        }
                    }, index * 1500);
                });

                // After sources, show progress
                setTimeout(() => {
                    urlLoader.style.display = 'none';
                    progressMsg.style.display = 'block';
                    loadMsg.textContent = 'Sources gathered! Generating report...';
                }, data.sources.length * 1500);

                // Render plan
                setTimeout(() => {
                    loadingSection.style.display = 'none';
                    progressMsg.style.display = 'none';
                    const renderedPlan = DOMPurify.sanitize(marked.parse(data.plan));
                    planOutput.innerHTML = `<div class="card"><div class="card-body">${renderedPlan}</div></div>`;
                    planOutput.style.display = 'block';
                }, (data.sources.length * 1500) + 2000);
            }
        } catch (error) {
            planOutput.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
    });
});