// summary.js: Handles summary metrics and upload for summary.html

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const uploadStatus = document.getElementById('upload-status');
    const reportTypeSelect = document.getElementById('report-type');
    const metricsDiv = document.getElementById('metrics');

    // --- File Upload Logic ---
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const file = fileInput.files[0];
            const reportType = reportTypeSelect.value;
            if (!file) {
                if (uploadStatus) {
                    uploadStatus.textContent = 'Please select a file to upload.';
                    uploadStatus.style.color = '#dc3545';
                }
                return;
            }
            const formData = new FormData();
            formData.append('file', file);
            formData.append('report_type', reportType);
            if (uploadStatus) {
                uploadStatus.textContent = 'Uploading and analyzing...';
                uploadStatus.style.color = '#333';
            }
            uploadButton.disabled = true;
            uploadButton.innerHTML = '<div class="spinner"></div> Processing...';
            try {
                const response = await fetch('/upload-cucumber-report/', {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Server error occurred.');
                }
                const result = await response.json();
                if (uploadStatus) {
                    uploadStatus.textContent = `✅ ${result.message}`;
                    uploadStatus.style.color = '#28a745';
                }
                fileInput.value = '';
                fetchAndRenderSummaryMetrics();
            } catch (error) {
                if (uploadStatus) {
                    uploadStatus.textContent = `❌ Upload failed: ${error.message}`;
                    uploadStatus.style.color = '#dc3545';
                }
                console.error('Upload Error:', error);
            } finally {
                uploadButton.disabled = false;
                uploadButton.innerHTML = 'Upload & Analyze Report';
            }
        });
    }

    // --- Summary Metrics Rendering ---
    async function fetchAndRenderSummaryMetrics() {
        if (!metricsDiv) return;
        metricsDiv.innerHTML = '<div class="loading">Loading summary metrics...</div>';
        try {
            const response = await fetch('/api/summary-metrics');
            if (!response.ok) throw new Error('Failed to fetch summary metrics');
            const metrics = await response.json();
            metricsDiv.innerHTML = renderSummaryMetrics(metrics);
        } catch (error) {
            metricsDiv.innerHTML = `<div style="color:red;">Error loading metrics: ${error.message}</div>`;
        }
    }

    function renderSummaryMetrics(metrics) {
        if (!metrics || Object.keys(metrics).length === 0) {
            return '<div>No summary metrics available.</div>';
        }
        let html = '<div class="metrics-section">';
        html += '<h2>Feature Failures</h2>';
        html += '<table class="metrics-table"><thead><tr><th>Feature</th><th>Failures</th></tr></thead><tbody>';
        html += metrics.featureFailures.map(f => `<tr><td>${f.feature}</td><td>${f.failed}</td></tr>`).join('');
        html += '</tbody></table>';
        html += '<h2>Step Failures</h2>';
        html += '<table class="metrics-table"><thead><tr><th>Step</th><th>Failures</th><th>Affected Features</th><th>Affected Files</th></tr></thead><tbody>';
        html += metrics.stepFailures.map(s => `<tr><td>${s.step}</td><td>${s.count}</td><td>${s.affectedFeatures}</td><td>${s.affectedFiles}</td></tr>`).join('');
        html += '</tbody></table>';
        html += '<h2>Error Type Patterns</h2>';
        html += '<table class="metrics-table"><thead><tr><th>Error Type</th><th>Failures</th><th>Affected Features</th></tr></thead><tbody>';
        html += metrics.errorTypeFailures.map(e => `<tr><td>${e.errorType}</td><td>${e.count}</td><td>${e.affectedFeatures}</td></tr>`).join('');
        html += '</tbody></table>';
        html += '</div>';
        return html;
    }

    // Initial load
    fetchAndRenderSummaryMetrics();
});
