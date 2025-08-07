document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const tableBody = document.querySelector('#results-table tbody');
    const squadFilter = document.getElementById('squad-filter');
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const uploadStatus = document.getElementById('upload-status');
    const reportTypeSelect = document.getElementById('report-type');
    
    let allResults = [];

    // --- File Upload Logic ---
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const file = fileInput.files[0];
            const reportType = reportTypeSelect.value;

            if (!file) {
                uploadStatus.textContent = 'Please select a file to upload.';
                uploadStatus.style.color = '#dc3545';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('report_type', reportType); 

            // Add loading state
            uploadStatus.textContent = 'Uploading and analyzing...';
            uploadStatus.style.color = '#333';
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
                uploadStatus.textContent = `✅ ${result.message}`;
                uploadStatus.style.color = '#28a745';
                
                await fetchData();
                fileInput.value = ''; // Clear file input
            } catch (error) {
                uploadStatus.textContent = `❌ Upload failed: ${error.message}`;
                uploadStatus.style.color = '#dc3545';
                console.error('Upload Error:', error);
            } finally {
                // Remove loading state
                uploadButton.disabled = false;
                uploadButton.innerHTML = 'Upload & Analyze Report';
            }
        });
    }

    // --- Dashboard Data & Rendering Logic ---
    async function fetchData() {
        try {
            const response = await fetch('/api/results');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            allResults = await response.json();
            populateSquadFilter(allResults);
            renderTable(allResults);
        } catch (error) {
            console.error('Error fetching data:', error);
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:red;">Failed to load data.</td></tr>';
        }
    }

    function populateSquadFilter(data) {
        const uniqueSquads = [...new Set(data.map(item => item.squad_name))].sort();
        squadFilter.innerHTML = '<option value="all">All Squads</option>';
        uniqueSquads.forEach(squad => {
            const option = document.createElement('option');
            option.value = squad;
            option.textContent = squad;
            squadFilter.appendChild(option);
        });
    }

    function renderTable(data) {
        tableBody.innerHTML = '';
        if (data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No results found.</td></tr>';
            return;
        }

        data.forEach((result, index) => {
            const rowIndex = tableBody.children.length;
            const mainRow = document.createElement('tr');
            mainRow.innerHTML = `
                <td class="col-num">${rowIndex + 1}</td>
                <td class="col-feature">${result.feature_name}</td>
                <td class="col-scenario">${result.scenario_name}</td>
                <td class="col-error-msg">${result.error_message}</td>
                <td class="col-detailed-reason">${result.detailed_reason.substring(0, 150)}${result.detailed_reason.length > 150 ? '...' : ''}</td>
                <td class="col-squad">${result.squad_name}</td>
                <td class="col-actions">
                    <button class="details-button" data-id="${rowIndex}" title="Show Details">+</button>
                </td>
            `;
            tableBody.appendChild(mainRow);

            const detailsRow = document.createElement('tr');
            detailsRow.classList.add('details-row');
            detailsRow.id = `details-row-${rowIndex}`;
            detailsRow.innerHTML = `
                <td colspan="7">
                    <div class="details-content">
                        <div>
                            <h4>Full Detailed Reason</h4>
                            <p>${result.detailed_reason}</p>
                        </div>
                        <div>
                            <h4>Possible Causes</h4>
                            <ul>${result.possible_causes.map(c => `<li>${c}</li>`).join('') || '<li>No causes provided.</li>'}</ul>
                        </div>
                        <div>
                            <h4>Recommended Fixes</h4>
                            <ul>${result.recommended_fixes.map(f => `<li>${f}</li>`).join('') || '<li>No fixes provided.</li>'}</ul>
                        </div>
                    </div>
                </td>
            `;
            tableBody.appendChild(detailsRow);
        });

        document.querySelectorAll('.details-button').forEach(button => {
            button.onclick = (event) => {
                const id = event.target.dataset.id;
                toggleDetails(id);
                if (event.target.textContent === '+') {
                    event.target.textContent = '-';
                } else {
                    event.target.textContent = '+';
                }
            };
        });
    }

    function toggleDetails(id) {
        const row = document.getElementById(`details-row-${id}`);
        if (row.style.display === 'table-row') {
            row.style.display = 'none';
        } else {
            row.style.display = 'table-row';
        }
    }

    squadFilter.addEventListener('change', (e) => {
        const selectedSquad = e.target.value;
        const filteredData = selectedSquad === 'all'
            ? allResults
            : allResults.filter(item => item.squad_name === selectedSquad);
        renderTable(filteredData);
    });

    fetchData();
});