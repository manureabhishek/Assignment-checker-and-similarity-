/**
 * AssignCheck - Intelligent Assignment Checker
 * Complete Frontend Application Logic
 */

// Application State
const state = {
    activePage: 'overview',
    summary: {
        total_submissions: 0,
        successful_compilations: 0,
        failed_compilations: 0,
        average_correctness: 0.0,
        similarity_alerts: 0,
        max_similarity: 0.0,
    },
    submissions: [],
    similarities: [],
    testCases: [],
    rawReport: '',
    compileErrorLog: '',
    lastRun: null,
    charts: {
        correctness: null,
        similarity: null
    },
    simFilter: 'all',
    syncScrollActive: true,
    isSyncingScroll: false,
};

// Starter Code Templates for C++ submissions
const CODE_TEMPLATES = {
    if_else: `#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;

    if (a > b) {
        cout << a;
    } else {
        cout << b;
    }

    return 0;
}`,
    ternary: `#include <iostream>
using namespace std;

int main() {
    int x, y;
    cin >> x >> y;

    int maximum = (x >= y) ? x : y;
    cout << maximum;

    return 0;
}`,
    function: `#include <iostream>
using namespace std;

int getMax(int first, int second) {
    return (first > second) ? first : second;
}

int main() {
    int val1, val2;
    cin >> val1 >> val2;
    cout << getMax(val1, val2);
    return 0;
}`,
    syntax_error: `#include <iostream>
using namespace std;

int main() {
    int x, y;
    cin >> x >> y;
    // Missing semicolon below to test compile error diagnostics
    cout << (x > y ? x : y)
    return 0;
}`
};

// DOM Content Loaded Initialization
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initRunCheckerButton();
    initFileUpload();
    initCodeEditor();
    initModals();
    initCopyButtons();
    initDownloadButtons();
    initTestCasesManager();
    initSyncScroll();
    loadDashboardData();
    loadTestCases();
});

/* ==========================================================================
   Navigation & Routing
   ========================================================================== */

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const page = item.getAttribute('data-page');
            navigateTo(page);
        });
    });

    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Similarity filter pills
    const filterPills = document.querySelectorAll('.filter-pill');
    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.simFilter = pill.getAttribute('data-sim-filter');
            renderSimilarityCards();
        });
    });

    // Refresh button
    const btnRefresh = document.getElementById('btn-refresh');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            loadDashboardData(true);
            loadTestCases();
        });
    }

    // Clear console button
    const btnClearConsole = document.getElementById('btn-clear-console');
    if (btnClearConsole) {
        btnClearConsole.addEventListener('click', () => {
            const consoleOutput = document.getElementById('console-output');
            if (consoleOutput) consoleOutput.innerText = 'Console cleared.';
        });
    }
}

function navigateTo(pageId) {
    state.activePage = pageId;

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-page') === pageId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update page view active state
    document.querySelectorAll('.page-view').forEach(view => {
        view.classList.remove('active');
    });

    const targetView = document.getElementById(`page-${pageId}`);
    if (targetView) {
        targetView.classList.add('active');
    }

    // Update Header Text
    const heading = document.getElementById('page-heading');
    const subheading = document.getElementById('page-subheading');

    const meta = {
        'overview': { title: 'Dashboard Overview', desc: 'Intelligent Assignment Checker &bull; Automated C++ Evaluation' },
        'submissions': { title: 'Student Submissions', desc: 'Compilation status, test passes, bracket checks & correctness scores' },
        'similarity': { title: 'Structural Similarity Analysis', desc: 'Token multiset, Tree block-structure and Graph token transition comparisons' },
        'testcases': { title: 'Test Cases Suite Management', desc: 'Configure and persist automated test inputs & expected outputs for the C++ engine' },
        'report': { title: 'Engine Final Report', desc: 'Live verification report from reports/final_report.txt with CSV export' },
        'add-submission': { title: 'Add Submission', desc: 'Upload .cpp source files or compose code directly in browser' },
        'dsa-architecture': { title: 'DSA Architecture & Engine Overview', desc: 'Stack, Hash Table, Queue, Max Heap, Tree Block Structure and Graph transitions' },
        'console': { title: 'Engine Execution Console', desc: 'Live execution logs and compiler diagnostics from checker.exe' }
    };

    if (meta[pageId]) {
        if (heading) heading.innerHTML = meta[pageId].title;
        if (subheading) subheading.innerHTML = meta[pageId].desc;
    }

    // If switching to mobile, close sidebar
    const sidebar = document.querySelector('.sidebar');
    if (sidebar && window.innerWidth <= 768) {
        sidebar.classList.remove('open');
    }
}

/* ==========================================================================
   Data Loading & Rendering
   ========================================================================== */

async function loadDashboardData(showToastNotification = false) {
    try {
        const [resultsRes, statusRes] = await Promise.all([
            fetch('/api/results'),
            fetch('/api/status')
        ]);

        const results = await resultsRes.json();
        const status = await statusRes.json();

        // Update state
        state.summary = results.summary || state.summary;
        state.submissions = results.submissions || [];
        state.similarities = results.similarities || [];
        state.rawReport = results.raw_text || '';
        state.compileErrorLog = results.compile_error_log || '';
        state.lastRun = results.last_modified || status.last_run;

        // Render UI components
        renderOverviewCards();
        renderSubmissionsTables();
        renderSimilarityCards();
        renderReportViewer();
        renderConsoleDiagnostics();
        renderCharts();
        updateEngineStatus(status);
        updateDownloadButtonsState();

        if (showToastNotification) {
            showToast('Dashboard data refreshed with real execution results.', 'info');
        }
    } catch (err) {
        console.error('Failed to load dashboard data:', err);
        showToast('Error loading dashboard data. Check backend server.', 'error');
    }
}

function updateEngineStatus(status) {
    const dot = document.getElementById('engine-dot');
    const subtext = document.getElementById('engine-subtext');
    const navSubCount = document.getElementById('nav-sub-count');
    const navTestsCount = document.getElementById('nav-tests-count');
    const lastRunText = document.getElementById('last-run-text');

    if (dot && subtext) {
        if (status.checker_exists) {
            dot.className = 'status-indicator-dot online';
            subtext.innerText = 'checker.exe ready';
        } else {
            dot.className = 'status-indicator-dot busy';
            subtext.innerText = 'g++ build needed';
        }
    }

    if (navSubCount) {
        navSubCount.innerText = status.submissions_count || state.submissions.length || '0';
    }

    if (navTestsCount) {
        navTestsCount.innerText = status.test_cases_count || state.testCases.length || '3';
    }

    if (lastRunText) {
        lastRunText.innerText = state.lastRun ? `Last Run: ${state.lastRun}` : 'No runs yet';
    }
}

function renderOverviewCards() {
    const { total_submissions, successful_compilations, failed_compilations, average_correctness, similarity_alerts, max_similarity } = state.summary;

    const elTotal = document.getElementById('card-total-submissions');
    const elSubBadge = document.getElementById('card-submissions-badge');
    const elComps = document.getElementById('card-compilations');
    const elCompRate = document.getElementById('card-compilation-rate');
    const elAvgCorr = document.getElementById('card-avg-correctness');
    const elCorrBar = document.getElementById('card-correctness-bar');
    const elAlerts = document.getElementById('card-similarity-alerts');
    const elMaxSim = document.getElementById('card-max-similarity');
    const navAlertCount = document.getElementById('nav-alert-count');

    if (elTotal) elTotal.innerText = total_submissions;
    if (elSubBadge) elSubBadge.innerText = `${total_submissions} in Priority Queue`;

    if (elComps) elComps.innerText = `${successful_compilations}/${total_submissions}`;
    if (elCompRate) {
        const rate = total_submissions > 0 ? Math.round((successful_compilations / total_submissions) * 100) : 0;
        elCompRate.innerText = `${rate}% Success Rate`;
        elCompRate.className = rate === 100 ? 'stat-badge badge-success' : rate >= 50 ? 'stat-badge badge-warning' : 'stat-badge badge-danger';
    }

    if (elAvgCorr) elAvgCorr.innerText = `${average_correctness}%`;
    if (elCorrBar) elCorrBar.style.width = `${Math.min(100, average_correctness)}%`;

    if (elAlerts) elAlerts.innerText = similarity_alerts;
    if (elMaxSim) {
        elMaxSim.innerText = `Max: ${max_similarity}%`;
        elMaxSim.className = similarity_alerts > 0 ? 'stat-badge badge-danger' : 'stat-badge badge-neutral';
    }

    if (navAlertCount) {
        if (similarity_alerts > 0) {
            navAlertCount.style.display = 'inline-block';
            navAlertCount.innerText = similarity_alerts;
        } else {
            navAlertCount.style.display = 'none';
        }
    }

    // Dynamic Alert Banner if failed compilations or similarity alerts exist
    const bannerContainer = document.getElementById('alert-banner-container');
    if (bannerContainer) {
        bannerContainer.innerHTML = '';
        if (failed_compilations > 0) {
            bannerContainer.innerHTML += `
                <div class="modal-alert-box alert-danger-box mb-3 flex-between align-center">
                    <div>
                        <strong>Compilation Alert:</strong> ${failed_compilations} submission(s) failed compilation.
                    </div>
                    <button class="btn btn-sm btn-secondary" onclick="navigateTo('console')">View Compiler Output &rarr;</button>
                </div>
            `;
        }
        if (similarity_alerts > 0) {
            bannerContainer.innerHTML += `
                <div class="modal-alert-box alert-warning-box mb-3 flex-between align-center">
                    <div>
                        <strong>Similarity Warning:</strong> ${similarity_alerts} pair(s) exceed the 70% threshold. (Structural likeness indicator; does not prove plagiarism).
                    </div>
                    <button class="btn btn-sm btn-secondary" onclick="navigateTo('similarity')">Inspect Pairs &rarr;</button>
                </div>
            `;
        }
    }
}

function renderSubmissionsTables() {
    const overviewBody = document.getElementById('overview-submissions-body');
    const fullBody = document.getElementById('submissions-full-body');

    if (!state.submissions || state.submissions.length === 0) {
        const emptyRow = `<tr><td colspan="7" class="text-center py-4 text-muted">No student submissions found in submissions/ folder. Add .cpp files to begin.</td></tr>`;
        if (overviewBody) overviewBody.innerHTML = emptyRow;
        if (fullBody) fullBody.innerHTML = emptyRow;
        return;
    }

    // Render Overview Mini Table
    if (overviewBody) {
        overviewBody.innerHTML = state.submissions.slice(0, 5).map(sub => `
            <tr>
                <td>
                    <div class="file-name-cell">
                        <svg class="file-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <span>${escapeHtml(sub.filename)}</span>
                    </div>
                </td>
                <td>
                    <span class="badge ${sub.compiled ? 'badge-success' : 'badge-danger'}">
                        <span class="badge-dot"></span>
                        ${sub.compilation}
                    </span>
                </td>
                <td>
                    <span class="badge ${sub.balanced ? 'badge-neutral' : 'badge-danger'}">
                        ${sub.bracket_check}
                    </span>
                </td>
                <td>
                    <span class="font-mono">${sub.tests_passed}/${sub.total_tests}</span>
                </td>
                <td>
                    <div class="progress-cell-wrapper">
                        <div class="progress-cell-bar">
                            <div class="progress-cell-fill ${getProgressFillClass(sub.correctness)}" style="width: ${sub.correctness}%"></div>
                        </div>
                        <span class="progress-cell-text">${sub.correctness}%</span>
                    </div>
                </td>
                <td>
                    <div class="flex-align-center gap-1">
                        <button class="btn btn-sm btn-secondary" onclick="viewSubmissionCode('${escapeHtml(sub.filename)}')">Inspect</button>
                        <button class="btn btn-sm btn-secondary text-danger" onclick="confirmDeleteSubmission('${escapeHtml(sub.filename)}')" title="Delete ${escapeHtml(sub.filename)}">&times;</button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    // Render Full Submissions Table with search filter
    renderFullSubmissionsTable();
}

function renderFullSubmissionsTable() {
    const fullBody = document.getElementById('submissions-full-body');
    const searchInput = document.getElementById('submissions-search');
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

    if (!fullBody) return;

    const filtered = state.submissions.filter(s => s.filename.toLowerCase().includes(query));

    if (filtered.length === 0) {
        fullBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No submissions matched search criteria.</td></tr>`;
        return;
    }

    fullBody.innerHTML = filtered.map(sub => `
        <tr>
            <td>
                <div class="file-name-cell">
                    <svg class="file-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <strong>${escapeHtml(sub.filename)}</strong>
                </div>
            </td>
            <td>
                <span class="font-mono text-muted">${sub.file_size ? sub.file_size + ' B' : 'Heap node'}</span>
            </td>
            <td>
                <span class="badge ${sub.compiled ? 'badge-success' : 'badge-danger'}">
                    <span class="badge-dot"></span>
                    ${sub.compilation}
                </span>
            </td>
            <td>
                <span class="badge ${sub.balanced ? 'badge-neutral' : 'badge-danger'}">
                    ${sub.bracket_check}
                </span>
            </td>
            <td>
                <span class="font-mono font-semibold">${sub.tests_passed}/${sub.total_tests}</span>
            </td>
            <td>
                <div class="progress-cell-wrapper">
                    <div class="progress-cell-bar">
                        <div class="progress-cell-fill ${getProgressFillClass(sub.correctness)}" style="width: ${sub.correctness}%"></div>
                    </div>
                    <span class="progress-cell-text">${sub.correctness}%</span>
                </div>
            </td>
            <td class="text-right">
                <div class="flex-align-center justify-end gap-1">
                    <button class="btn btn-sm btn-secondary" onclick="viewSubmissionCode('${escapeHtml(sub.filename)}')" title="View Source Code">
                        Inspect
                    </button>
                    ${sub.test_details && sub.test_details.length > 0 ? `
                        <button class="btn btn-sm btn-secondary" onclick="viewTestResults('${escapeHtml(sub.filename)}')" title="View Individual Test Results">
                            Tests (${sub.tests_passed}/${sub.total_tests})
                        </button>
                    ` : ''}
                    ${!sub.compiled ? `
                        <button class="btn btn-sm btn-secondary text-danger" onclick="viewCompileError('${escapeHtml(sub.filename)}')" title="View Compilation Error">
                            Errors
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary text-danger" onclick="confirmDeleteSubmission('${escapeHtml(sub.filename)}')" title="Delete Submission">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                        <span>Delete</span>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Search input listener
const searchInput = document.getElementById('submissions-search');
if (searchInput) {
    searchInput.addEventListener('input', () => {
        renderFullSubmissionsTable();
    });
}

function getProgressFillClass(score) {
    if (score >= 80) return 'progress-fill-success';
    if (score >= 40) return 'progress-fill-warn';
    return 'progress-fill-danger';
}

function renderSimilarityCards() {
    const container = document.getElementById('similarity-cards-container');
    const countAll = document.getElementById('sim-count-all');
    const countAlerts = document.getElementById('sim-count-alerts');
    const countNormal = document.getElementById('sim-count-normal');

    const allPairs = state.similarities || [];
    const alerts = allPairs.filter(p => p.is_alert);
    const normals = allPairs.filter(p => !p.is_alert);

    if (countAll) countAll.innerText = allPairs.length;
    if (countAlerts) countAlerts.innerText = alerts.length;
    if (countNormal) countNormal.innerText = normals.length;

    if (!container) return;

    let displayList = allPairs;
    if (state.simFilter === 'alerts') displayList = alerts;
    if (state.simFilter === 'normal') displayList = normals;

    if (displayList.length === 0) {
        container.innerHTML = `
            <div class="glass-panel text-center py-4 text-muted" style="grid-column: 1 / -1;">
                No comparison pairs match the selected filter.
            </div>
        `;
        return;
    }

    container.innerHTML = displayList.map(pair => `
        <div class="similarity-card ${pair.is_alert ? 'is-alert' : ''}">
            <div>
                <div class="sim-card-header">
                    <div>
                        <div class="sim-pair-names">${escapeHtml(pair.file1)} <span class="text-muted">vs</span> ${escapeHtml(pair.file2)}</div>
                        <span class="badge ${pair.is_alert ? 'badge-danger' : 'badge-neutral'} mt-1">
                            ${pair.status}
                        </span>
                    </div>
                    <div class="sim-overall-badge">
                        <div class="sim-score-huge ${pair.is_alert ? 'text-danger' : ''}">${pair.overall_similarity}%</div>
                        <span class="text-xs text-muted">Overall Match</span>
                    </div>
                </div>

                <div class="sim-metrics-list">
                    <!-- Token Similarity (50%) -->
                    <div class="sim-metric-row">
                        <div class="sim-metric-meta">
                            <span>Token Multiset Similarity (50% weight)</span>
                            <span class="sim-metric-val">${pair.token_similarity}%</span>
                        </div>
                        <div class="sim-progress-track">
                            <div class="sim-progress-bar bar-token" style="width: ${pair.token_similarity}%"></div>
                        </div>
                    </div>

                    <!-- Tree Block Structure Similarity (25%) -->
                    <div class="sim-metric-row">
                        <div class="sim-metric-meta">
                            <span>Tree Block Structure (25% weight)</span>
                            <span class="sim-metric-val">${pair.tree_similarity}%</span>
                        </div>
                        <div class="sim-progress-track">
                            <div class="sim-progress-bar bar-tree" style="width: ${pair.tree_similarity}%"></div>
                        </div>
                    </div>

                    <!-- Graph Token Transition Similarity (25%) -->
                    <div class="sim-metric-row">
                        <div class="sim-metric-meta">
                            <span>Graph Token Transitions (25% weight)</span>
                            <span class="sim-metric-val">${pair.graph_similarity}%</span>
                        </div>
                        <div class="sim-progress-track">
                            <div class="sim-progress-bar bar-graph" style="width: ${pair.graph_similarity}%"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex-between align-center mt-3">
                <span class="text-xs text-muted">Formula: 0.5T + 0.25Tree + 0.25Graph</span>
                <button class="btn btn-sm btn-secondary" onclick="openPairComparison('${escapeHtml(pair.file1)}', '${escapeHtml(pair.file2)}')">
                    <span>Compare Code</span>
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

function renderReportViewer() {
    const reportBox = document.getElementById('report-raw-content');
    if (reportBox) {
        if (state.rawReport) {
            reportBox.innerText = state.rawReport;
        } else {
            reportBox.innerText = 'No report found in reports/final_report.txt. Click "Run Checker" to execute C++ evaluation.';
        }
    }
}

function renderConsoleDiagnostics() {
    const errorSection = document.getElementById('compile-error-section');
    const errorContent = document.getElementById('compile-error-content');

    if (errorSection && errorContent) {
        if (state.compileErrorLog && state.compileErrorLog.trim().length > 0) {
            errorSection.style.display = 'block';
            errorContent.innerText = state.compileErrorLog;
        } else {
            errorSection.style.display = 'none';
        }
    }
}

/* ==========================================================================
   Interactive Chart.js Visualizations
   ========================================================================== */

function renderCharts() {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is not loaded.');
        return;
    }

    renderCorrectnessChart();
    renderSimilarityChart();
}

function renderCorrectnessChart() {
    const ctx = document.getElementById('correctnessChart');
    if (!ctx) return;

    if (state.charts.correctness) {
        state.charts.correctness.destroy();
    }

    const labels = state.submissions.map(s => s.filename);
    const dataValues = state.submissions.map(s => s.correctness);
    const backgroundColors = state.submissions.map(s => {
        if (!s.compiled) return 'rgba(239, 68, 68, 0.7)';
        if (s.correctness >= 80) return 'rgba(16, 185, 129, 0.7)';
        return 'rgba(245, 158, 11, 0.7)';
    });
    const borderColors = state.submissions.map(s => {
        if (!s.compiled) return '#ef4444';
        if (s.correctness >= 80) return '#10b981';
        return '#f59e0b';
    });

    state.charts.correctness = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length > 0 ? labels : ['No Data'],
            datasets: [{
                label: 'Correctness (%)',
                data: dataValues.length > 0 ? dataValues : [0],
                backgroundColor: backgroundColors.length > 0 ? backgroundColors : ['rgba(99, 102, 241, 0.5)'],
                borderColor: borderColors.length > 0 ? borderColors : ['#6366f1'],
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#cbd5e1', font: { family: 'JetBrains Mono', size: 12 } }
                }
            }
        }
    });
}

function renderSimilarityChart() {
    const ctx = document.getElementById('similarityChart');
    if (!ctx) return;

    if (state.charts.similarity) {
        state.charts.similarity.destroy();
    }

    const pairs = state.similarities.slice(0, 6);
    const labels = pairs.map(p => `${p.file1.replace('.cpp', '')} v ${p.file2.replace('.cpp', '')}`);

    const tokenData = pairs.map(p => p.token_similarity);
    const treeData = pairs.map(p => p.tree_similarity);
    const graphData = pairs.map(p => p.graph_similarity);
    const overallData = pairs.map(p => p.overall_similarity);

    state.charts.similarity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length > 0 ? labels : ['No Pairs'],
            datasets: [
                {
                    label: 'Token Sim (50%)',
                    data: tokenData.length > 0 ? tokenData : [0],
                    backgroundColor: 'rgba(59, 130, 246, 0.75)',
                    borderRadius: 4
                },
                {
                    label: 'Tree Block (25%)',
                    data: treeData.length > 0 ? treeData : [0],
                    backgroundColor: 'rgba(99, 102, 241, 0.75)',
                    borderRadius: 4
                },
                {
                    label: 'Graph Trans (25%)',
                    data: graphData.length > 0 ? graphData : [0],
                    backgroundColor: 'rgba(139, 92, 246, 0.75)',
                    borderRadius: 4
                },
                {
                    label: 'Overall Sim',
                    data: overallData.length > 0 ? overallData : [0],
                    backgroundColor: 'rgba(6, 182, 212, 0.9)',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#94a3b8', boxWidth: 12, font: { size: 11 } }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#cbd5e1', font: { family: 'JetBrains Mono', size: 11 } }
                }
            }
        }
    });
}

/* ==========================================================================
   Run Checker Execution
   ========================================================================== */

function initRunCheckerButton() {
    const btn = document.getElementById('btn-run-checker');
    const spinner = document.getElementById('run-spinner');
    const btnText = document.getElementById('run-btn-text');
    const runIcon = document.querySelector('.run-icon');
    const consoleOutput = document.getElementById('console-output');

    if (!btn) return;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        if (spinner) spinner.style.display = 'inline-block';
        if (runIcon) runIcon.style.display = 'none';
        if (btnText) btnText.innerText = 'Evaluating C++...';

        showToast('Running Intelligent Assignment Checker engine...', 'info');

        try {
            const res = await fetch('/api/run-checker', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await res.json();

            if (data.success) {
                showToast(`Checker complete in ${data.elapsed_seconds}s!`, 'success');

                if (consoleOutput && data.stdout) {
                    consoleOutput.innerText = data.stdout;
                }

                // Refresh dashboard with real new results
                await loadDashboardData(false);
            } else {
                showToast(data.error || 'Checker execution failed.', 'error');
                if (consoleOutput) {
                    consoleOutput.innerText = `Error: ${data.error || 'Unknown error'}\n\nDetails:\n${data.details || data.stderr || ''}`;
                }
                navigateTo('console');
            }
        } catch (err) {
            console.error('Run checker request failed:', err);
            showToast('Network error while running checker.', 'error');
        } finally {
            btn.disabled = false;
            if (spinner) spinner.style.display = 'none';
            if (runIcon) runIcon.style.display = 'inline-block';
            if (btnText) btnText.innerText = 'Run Checker';
        }
    });
}

/* ==========================================================================
   Test Cases Suite Management
   ========================================================================== */

function initTestCasesManager() {
    const form = document.getElementById('testcase-form');
    const btnReset = document.getElementById('btn-reset-testcases');
    const btnCancel = document.getElementById('btn-cancel-tc-edit');

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const inputVal = document.getElementById('tc-input').value.trim();
            const expVal = document.getElementById('tc-expected').value.trim();
            const editId = document.getElementById('edit-testcase-id').value;

            if (!inputVal || !expVal) {
                showToast('Input and expected output cannot be empty.', 'error');
                return;
            }

            let updatedList = [...state.testCases];

            if (editId) {
                const idx = parseInt(editId, 10) - 1;
                if (idx >= 0 && idx < updatedList.length) {
                    updatedList[idx] = { id: idx + 1, input: inputVal, expected: expVal };
                }
            } else {
                updatedList.push({ id: updatedList.length + 1, input: inputVal, expected: expVal });
            }

            try {
                const res = await fetch('/api/testcases', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tests: updatedList })
                });

                const data = await res.json();
                if (data.success) {
                    showToast(data.message, 'success');
                    resetTestcaseForm();
                    await loadTestCases();
                } else {
                    showToast(data.error || 'Failed to save test cases.', 'error');
                }
            } catch (err) {
                showToast('Error saving test cases: ' + err.message, 'error');
            }
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            if (!confirm('Reset test cases to the default suite (3 cases)?')) return;
            try {
                const res = await fetch('/api/testcases/reset', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, 'success');
                    resetTestcaseForm();
                    await loadTestCases();
                }
            } catch (err) {
                showToast('Error resetting test cases: ' + err.message, 'error');
            }
        });
    }

    if (btnCancel) {
        btnCancel.addEventListener('click', () => {
            resetTestcaseForm();
        });
    }
}

async function loadTestCases() {
    try {
        const res = await fetch('/api/testcases');
        const data = await res.json();
        state.testCases = data.tests || [];

        renderTestCasesTable();

        const navCount = document.getElementById('nav-tests-count');
        if (navCount) navCount.innerText = state.testCases.length;
    } catch (err) {
        console.error('Failed to load test cases:', err);
    }
}

function renderTestCasesTable() {
    const tbody = document.getElementById('testcases-body');
    if (!tbody) return;

    if (state.testCases.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">No test cases configured. Add one using the form.</td></tr>`;
        return;
    }

    tbody.innerHTML = state.testCases.map((tc, idx) => `
        <tr>
            <td><span class="badge badge-accent">Test ${idx + 1}</span></td>
            <td><code class="font-mono text-cyan">${escapeHtml(tc.input)}</code></td>
            <td><code class="font-mono text-green">${escapeHtml(tc.expected)}</code></td>
            <td class="text-right">
                <button class="btn btn-sm btn-secondary" onclick="editTestCase(${idx + 1})">Edit</button>
                <button class="btn btn-sm btn-secondary text-danger" onclick="deleteTestCase(${idx + 1})">&times;</button>
            </td>
        </tr>
    `).join('');
}

function editTestCase(id) {
    const tc = state.testCases[id - 1];
    if (!tc) return;

    document.getElementById('edit-testcase-id').value = id;
    document.getElementById('tc-input').value = tc.input;
    document.getElementById('tc-expected').value = tc.expected;
    document.getElementById('testcase-form-title').innerText = `Edit Test Case #${id}`;
    document.getElementById('btn-save-tc-text').innerText = 'Update Test Case';
    document.getElementById('btn-cancel-tc-edit').style.display = 'inline-block';

    navigateTo('testcases');
}

async function deleteTestCase(id) {
    if (state.testCases.length <= 1) {
        showToast('At least one test case must remain.', 'error');
        return;
    }

    if (!confirm(`Delete Test Case #${id}?`)) return;

    const updated = state.testCases.filter((_, idx) => idx !== (id - 1));

    try {
        const res = await fetch('/api/testcases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tests: updated })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Deleted test case #${id}.`, 'info');
            await loadTestCases();
        }
    } catch (err) {
        showToast('Error deleting test case: ' + err.message, 'error');
    }
}

function resetTestcaseForm() {
    document.getElementById('edit-testcase-id').value = '';
    document.getElementById('tc-input').value = '';
    document.getElementById('tc-expected').value = '';
    document.getElementById('testcase-form-title').innerText = 'Add / Edit Test Case';
    document.getElementById('btn-save-tc-text').innerText = 'Save Test Case';
    document.getElementById('btn-cancel-tc-edit').style.display = 'none';
}

/* ==========================================================================
   Code Inspection & Test Results Modals
   ========================================================================== */

function initModals() {
    const codeModal = document.getElementById('code-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalDismissBtn = document.getElementById('modal-dismiss-btn');

    const testResultsModal = document.getElementById('test-results-modal');
    const testResultsCloseBtn = document.getElementById('test-results-close-btn');
    const testResultsDismissBtn = document.getElementById('test-results-dismiss-btn');

    const compareModal = document.getElementById('compare-modal');
    const compareCloseBtn = document.getElementById('compare-modal-close-btn');
    const compareDismissBtn = document.getElementById('compare-dismiss-btn');

    const closeModal = () => {
        if (codeModal) codeModal.classList.remove('active');
        if (testResultsModal) testResultsModal.classList.remove('active');
        if (compareModal) compareModal.classList.remove('active');
    };

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (modalDismissBtn) modalDismissBtn.addEventListener('click', closeModal);
    if (testResultsCloseBtn) testResultsCloseBtn.addEventListener('click', closeModal);
    if (testResultsDismissBtn) testResultsDismissBtn.addEventListener('click', closeModal);
    if (compareCloseBtn) compareCloseBtn.addEventListener('click', closeModal);
    if (compareDismissBtn) compareDismissBtn.addEventListener('click', closeModal);

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    const modalCopyBtn = document.getElementById('modal-copy-code-btn');
    if (modalCopyBtn) {
        modalCopyBtn.addEventListener('click', () => {
            const codeLines = document.querySelectorAll('#modal-code-wrapper .diff-text');
            if (codeLines.length > 0) {
                const text = Array.from(codeLines).map(l => l.innerText).join('\n');
                navigator.clipboard.writeText(text);
                showToast('Code copied to clipboard!', 'success');
            }
        });
    }

    const modalDeleteBtn = document.getElementById('modal-delete-code-btn');
    if (modalDeleteBtn) {
        modalDeleteBtn.addEventListener('click', () => {
            const modalFilename = document.getElementById('modal-filename');
            if (modalFilename && modalFilename.innerText) {
                confirmDeleteSubmission(modalFilename.innerText.trim());
            }
        });
    }

    // Modal Pair Selectors Listener
    const sel1 = document.getElementById('compare-select-f1');
    const sel2 = document.getElementById('compare-select-f2');
    if (sel1 && sel2) {
        const changeHandler = () => {
            const f1 = sel1.value;
            const f2 = sel2.value;
            if (f1 && f2 && f1 !== f2) {
                loadPairComparison(f1, f2);
            }
        };
        sel1.addEventListener('change', changeHandler);
        sel2.addEventListener('change', changeHandler);
    }
}

async function viewSubmissionCode(filename) {
    const modal = document.getElementById('code-modal');
    const modalFilename = document.getElementById('modal-filename');
    const modalSize = document.getElementById('modal-size');
    const modalWrapper = document.getElementById('modal-code-wrapper');
    const modalAlert = document.getElementById('modal-compile-alert');

    if (!modal) return;

    if (modalFilename) modalFilename.innerText = filename;
    if (modalSize) modalSize.innerText = 'Loading...';
    if (modalWrapper) modalWrapper.innerHTML = '<div class="p-3 text-muted">Loading source code...</div>';
    if (modalAlert) modalAlert.style.display = 'none';

    modal.classList.add('active');

    try {
        const res = await fetch(`/api/submissions/${encodeURIComponent(filename)}`);
        const data = await res.json();

        if (data.error) {
            if (modalWrapper) modalWrapper.innerHTML = `<div class="p-3 text-danger">// Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        if (modalSize) modalSize.innerText = `${data.size} bytes &bull; Correctness: ${data.correctness}%`;

        // Render with line numbers
        const lines = data.content.split('\n');
        const rowsHtml = lines.map((line, idx) => `
            <div class="diff-row">
                <span class="diff-num">${idx + 1}</span>
                <span class="diff-text">${escapeHtml(line)}</span>
            </div>
        `).join('');

        if (modalWrapper) {
            modalWrapper.innerHTML = `<div class="diff-content">${rowsHtml}</div>`;
        }

        if (data.compile_error && modalAlert) {
            modalAlert.style.display = 'block';
            modalAlert.className = 'modal-alert-box alert-danger-box';
            modalAlert.innerHTML = `<strong>Compilation Diagnostics:</strong><pre style="margin-top: 6px; white-space: pre-wrap;">${escapeHtml(data.compile_error)}</pre>`;
        }
    } catch (err) {
        if (modalWrapper) modalWrapper.innerHTML = `<div class="p-3 text-danger">// Failed to load code: ${escapeHtml(err.message)}</div>`;
    }
}

function viewTestResults(filename) {
    const modal = document.getElementById('test-results-modal');
    const title = document.getElementById('test-results-title');
    const tbody = document.getElementById('test-results-table-body');

    if (!modal || !tbody) return;

    const sub = state.submissions.find(s => s.filename === filename);
    if (!sub) return;

    if (title) title.innerText = `Individual Test Results: ${filename}`;

    if (!sub.test_details || sub.test_details.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No individual test details recorded for this run.</td></tr>`;
    } else {
        tbody.innerHTML = sub.test_details.map(t => `
            <tr>
                <td><span class="badge badge-accent">Test ${t.test_num}</span></td>
                <td>
                    <span class="badge ${t.passed ? 'badge-success' : 'badge-danger'}">
                        ${t.passed ? 'PASS' : 'FAIL'}
                    </span>
                </td>
                <td><code class="font-mono text-cyan">${escapeHtml(t.input)}</code></td>
                <td><code class="font-mono text-green">${escapeHtml(t.expected)}</code></td>
                <td><code class="font-mono ${t.passed ? 'text-green' : 'text-danger'}">${escapeHtml(t.actual || '(no output)')}</code></td>
            </tr>
        `).join('');
    }

    modal.classList.add('active');
}

function viewCompileError(filename) {
    viewSubmissionCode(filename);
}

async function confirmDeleteSubmission(filename) {
    if (!filename) return;

    const confirmed = confirm(`Are you sure you want to delete '${filename}'?\n\nThis will remove the file from submissions/ and update the execution queue.`);
    if (!confirmed) return;

    showToast(`Deleting '${filename}'...`, 'info');

    try {
        const res = await fetch(`/api/submissions/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        const data = await res.json();

        if (res.ok && data.success) {
            showToast(data.message || `Deleted '${filename}'.`, 'success');
            // If code-modal is open for this file, close it
            const modal = document.getElementById('code-modal');
            const modalFilename = document.getElementById('modal-filename');
            if (modal && modalFilename && modalFilename.innerText === filename) {
                modal.classList.remove('active');
            }
            // Refresh dashboard data
            await loadDashboardData(false);
        } else {
            showToast(data.error || `Failed to delete '${filename}'.`, 'error');
        }
    } catch (err) {
        console.error('Delete submission error:', err);
        showToast('Error deleting submission: ' + err.message, 'error');
    }
}

/* ==========================================================================
   Code Comparison with Line-by-Line Diff & Synchronized Scrolling
   ========================================================================== */

function initSyncScroll() {
    const toggle = document.getElementById('sync-scroll-toggle');
    const pane1 = document.getElementById('compare-pane-1');
    const pane2 = document.getElementById('compare-pane-2');

    if (toggle) {
        toggle.addEventListener('change', () => {
            state.syncScrollActive = toggle.checked;
        });
    }

    if (pane1 && pane2) {
        pane1.addEventListener('scroll', () => {
            if (!state.syncScrollActive || state.isSyncingScroll) return;
            state.isSyncingScroll = true;
            const ratio = pane1.scrollTop / (pane1.scrollHeight - pane1.clientHeight || 1);
            pane2.scrollTop = ratio * (pane2.scrollHeight - pane2.clientHeight);
            setTimeout(() => { state.isSyncingScroll = false; }, 20);
        });

        pane2.addEventListener('scroll', () => {
            if (!state.syncScrollActive || state.isSyncingScroll) return;
            state.isSyncingScroll = true;
            const ratio = pane2.scrollTop / (pane2.scrollHeight - pane2.clientHeight || 1);
            pane1.scrollTop = ratio * (pane1.scrollHeight - pane1.clientHeight);
            setTimeout(() => { state.isSyncingScroll = false; }, 20);
        });
    }
}

async function openPairComparison(file1, file2) {
    const modal = document.getElementById('compare-modal');
    if (!modal) return;

    // Populate dropdowns with all submissions
    const sel1 = document.getElementById('compare-select-f1');
    const sel2 = document.getElementById('compare-select-f2');

    if (sel1 && sel2) {
        const optionsHtml = state.submissions.map(s => `
            <option value="${escapeHtml(s.filename)}">${escapeHtml(s.filename)}</option>
        `).join('');

        sel1.innerHTML = optionsHtml;
        sel2.innerHTML = optionsHtml;

        sel1.value = file1;
        sel2.value = file2;
    }

    modal.classList.add('active');
    await loadPairComparison(file1, file2);
}

async function loadPairComparison(file1, file2) {
    const title = document.getElementById('compare-modal-title');
    const f1Header = document.getElementById('compare-file1-name');
    const f2Header = document.getElementById('compare-file2-name');
    const banner = document.getElementById('compare-metrics-banner');
    const f1Diff = document.getElementById('compare-file1-diff');
    const f2Diff = document.getElementById('compare-file2-diff');

    if (title) title.innerText = `${file1} vs ${file2}`;
    if (f1Header) f1Header.innerText = file1;
    if (f2Header) f2Header.innerText = file2;

    if (f1Diff) f1Diff.innerHTML = '<div class="p-3 text-muted">Loading code diff...</div>';
    if (f2Diff) f2Diff.innerHTML = '<div class="p-3 text-muted">Loading code diff...</div>';

    try {
        const res = await fetch(`/api/similarity/pair?file1=${encodeURIComponent(file1)}&file2=${encodeURIComponent(file2)}`);
        const data = await res.json();

        // Render Metric Score Banner
        const m = data.metrics || {};
        if (banner) {
            banner.innerHTML = `
                <div class="metric-pill">
                    <span>Overall Match:</span>
                    <strong class="${m.is_alert ? 'text-danger' : 'text-cyan'}">${m.overall_similarity}%</strong>
                </div>
                <div class="metric-pill">
                    <span>Token Multiset (50%):</span>
                    <strong>${m.token_similarity}%</strong>
                </div>
                <div class="metric-pill">
                    <span>Tree Structure (25%):</span>
                    <strong>${m.tree_similarity}%</strong>
                </div>
                <div class="metric-pill">
                    <span>Graph Transitions (25%):</span>
                    <strong>${m.graph_similarity}%</strong>
                </div>
                <div class="metric-pill">
                    <span>Status:</span>
                    <span class="badge ${m.is_alert ? 'badge-danger' : 'badge-neutral'}">${m.status}</span>
                </div>
            `;
        }

        // Render Side-by-Side Diff
        const lines1 = (data.content1 || '').split('\n');
        const lines2 = (data.content2 || '').split('\n');

        const { diff1, diff2 } = computeSideBySideDiff(lines1, lines2);

        if (f1Diff) f1Diff.innerHTML = diff1;
        if (f2Diff) f2Diff.innerHTML = diff2;

        const btnComp = document.getElementById('btn-download-comparison');
        if (btnComp) {
            btnComp.classList.remove('disabled');
            btnComp.removeAttribute('aria-disabled');
            btnComp.disabled = false;
        }
    } catch (err) {
        console.error('Error loading comparison:', err);
        showToast('Error loading comparison data.', 'error');
        const btnComp = document.getElementById('btn-download-comparison');
        if (btnComp) {
            btnComp.classList.add('disabled');
            btnComp.setAttribute('aria-disabled', 'true');
            btnComp.disabled = true;
        }
    }
}

/**
 * Computes side-by-side aligned diff lines with highlighting.
 */
function computeSideBySideDiff(lines1, lines2) {
    const set2 = new Set(lines2.map(l => l.trim()));
    const set1 = new Set(lines1.map(l => l.trim()));

    const diff1 = lines1.map((line, idx) => {
        const trimmed = line.trim();
        let diffClass = '';
        let sign = ' ';
        if (trimmed && !set2.has(trimmed)) {
            diffClass = 'diff-del';
            sign = '-';
        }
        return `
            <div class="diff-row ${diffClass}">
                <span class="diff-num">${idx + 1}</span>
                <span class="diff-text"><span class="diff-sign">${sign}</span>${escapeHtml(line)}</span>
            </div>
        `;
    }).join('');

    const diff2 = lines2.map((line, idx) => {
        const trimmed = line.trim();
        let diffClass = '';
        let sign = ' ';
        if (trimmed && !set1.has(trimmed)) {
            diffClass = 'diff-add';
            sign = '+';
        }
        return `
            <div class="diff-row ${diffClass}">
                <span class="diff-num">${idx + 1}</span>
                <span class="diff-text"><span class="diff-sign">${sign}</span>${escapeHtml(line)}</span>
            </div>
        `;
    }).join('');

    return { diff1, diff2 };
}

/* ==========================================================================
   Add Submission: File Upload & Direct Code Editor
   ========================================================================== */

function initFileUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const allowOverwrite = document.getElementById('upload-allow-overwrite');
    const uploadStatus = document.getElementById('upload-status');

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.cpp')) {
            showToast('Only .cpp files are supported.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('overwrite', allowOverwrite && allowOverwrite.checked ? 'true' : 'false');

        if (uploadStatus) {
            uploadStatus.innerHTML = `<span class="text-muted">Uploading ${escapeHtml(file.name)}...</span>`;
        }

        try {
            const res = await fetch('/api/submissions/upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.status === 409) {
                if (uploadStatus) {
                    uploadStatus.innerHTML = `
                        <div class="modal-alert-box alert-warning-box">
                            <strong>File Exists:</strong> '${escapeHtml(file.name)}' is already in submissions folder.
                            Check "Allow overwrite" to replace it.
                        </div>
                    `;
                }
                showToast(`'${file.name}' already exists. Overwrite protected.`, 'error');
                return;
            }

            if (data.success) {
                if (uploadStatus) {
                    uploadStatus.innerHTML = `
                        <div class="modal-alert-box alert-success-box flex-between align-center" style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #6ee7b7;">
                            <span>Successfully added <strong>${escapeHtml(data.filename)}</strong>!</span>
                            <button class="btn btn-sm btn-primary" onclick="document.getElementById('btn-run-checker').click()">Run Checker</button>
                        </div>
                    `;
                }
                showToast(`Submission '${data.filename}' added!`, 'success');
                fileInput.value = '';
                await loadDashboardData(false);
            } else {
                showToast(data.error || 'Upload failed.', 'error');
                if (uploadStatus) uploadStatus.innerHTML = `<span class="text-danger">${data.error}</span>`;
            }
        } catch (err) {
            showToast('Upload error: ' + err.message, 'error');
        }
    }
}

function initCodeEditor() {
    const templateSelect = document.getElementById('code-template-select');
    const editorFilename = document.getElementById('editor-filename');
    const editorCode = document.getElementById('editor-code');
    const form = document.getElementById('direct-code-form');
    const allowOverwrite = document.getElementById('editor-allow-overwrite');

    if (templateSelect && editorCode) {
        templateSelect.addEventListener('change', () => {
            const choice = templateSelect.value;
            if (choice && CODE_TEMPLATES[choice]) {
                editorCode.value = CODE_TEMPLATES[choice];
                if (editorFilename && !editorFilename.value) {
                    const nextNum = state.submissions.length + 1;
                    editorFilename.value = `student${nextNum}.cpp`;
                }
            }
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            let filename = editorFilename.value.trim();
            if (!filename) {
                showToast('Please provide a filename.', 'error');
                return;
            }
            if (!filename.endsWith('.cpp')) filename += '.cpp';

            const code = editorCode.value;
            if (!code.trim()) {
                showToast('Please provide C++ code.', 'error');
                return;
            }

            const payload = {
                filename: filename,
                code: code,
                overwrite: allowOverwrite && allowOverwrite.checked ? 'true' : 'false'
            };

            try {
                const res = await fetch('/api/submissions/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();

                if (res.status === 409) {
                    showToast(`'${filename}' already exists. Enable "Allow overwrite" to update.`, 'error');
                    return;
                }

                if (data.success) {
                    showToast(`Submission '${data.filename}' saved successfully!`, 'success');
                    await loadDashboardData(false);
                    navigateTo('submissions');
                } else {
                    showToast(data.error || 'Failed to save submission.', 'error');
                }
            } catch (err) {
                showToast('Error saving code: ' + err.message, 'error');
            }
        });
    }
}

/* ==========================================================================
   Utilities & Helpers
   ========================================================================== */

function initCopyButtons() {
    const copyReportBtn = document.getElementById('btn-copy-report');
    if (copyReportBtn) {
        copyReportBtn.addEventListener('click', () => {
            const reportText = document.getElementById('report-raw-content');
            if (reportText) {
                navigator.clipboard.writeText(reportText.innerText);
                showToast('Report copied to clipboard!', 'success');
            }
        });
    }
}

function updateDownloadButtonsState() {
    const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
    const hasSubmissions = !!(state.submissions && state.submissions.length > 0);
    const hasSimilarities = !!(state.similarities && state.similarities.length > 0);

    const btnPdf = document.getElementById('btn-download-pdf');
    const btnResultsCsv = document.getElementById('btn-export-results-csv');
    const btnSubCsv = document.getElementById('btn-export-submissions-csv');
    const btnSubCsvRep = document.getElementById('btn-export-sub-csv-rep');
    const btnSimCsvRep = document.getElementById('btn-export-sim-csv-rep');
    const btnTxt = document.getElementById('btn-download-report');

    const setBtnState = (el, enabled, disabledTitle) => {
        if (!el) return;
        if (enabled) {
            el.classList.remove('disabled');
            el.removeAttribute('aria-disabled');
            el.removeAttribute('title');
        } else {
            el.classList.add('disabled');
            el.setAttribute('aria-disabled', 'true');
            if (disabledTitle) el.setAttribute('title', disabledTitle);
        }
    };

    setBtnState(btnPdf, hasReport, 'No evaluation report available. Run Checker first.');
    setBtnState(btnResultsCsv, hasReport, 'No evaluation report available. Run Checker first.');
    setBtnState(btnTxt, hasReport, 'No report file available. Run Checker first.');
    setBtnState(btnSubCsvRep, hasReport && hasSubmissions, 'No submissions data in report. Run Checker first.');
    setBtnState(btnSimCsvRep, hasReport && hasSimilarities, 'No similarity data in report. Run Checker first.');
    setBtnState(btnSubCsv, hasSubmissions, 'No submissions available to export.');
}

function initDownloadButtons() {
    const btnPdf = document.getElementById('btn-download-pdf');
    const btnResultsCsv = document.getElementById('btn-export-results-csv');
    const btnSubCsv = document.getElementById('btn-export-submissions-csv');
    const btnSubCsvRep = document.getElementById('btn-export-sub-csv-rep');
    const btnSimCsvRep = document.getElementById('btn-export-sim-csv-rep');
    const btnTxt = document.getElementById('btn-download-report');
    const btnComparison = document.getElementById('btn-download-comparison');

    if (btnPdf) {
        btnPdf.addEventListener('click', (e) => {
            const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
            if (!hasReport) {
                e.preventDefault();
                showToast('No evaluation report available. Please click "Run Checker" first.', 'error');
                return;
            }
            showToast('Generating and downloading PDF evaluation report...', 'info');
        });
    }

    if (btnResultsCsv) {
        btnResultsCsv.addEventListener('click', (e) => {
            const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
            if (!hasReport) {
                e.preventDefault();
                showToast('No evaluation report available to export. Run Checker first.', 'error');
                return;
            }
            showToast('Exporting comprehensive evaluation results to CSV...', 'info');
        });
    }

    if (btnSubCsv) {
        btnSubCsv.addEventListener('click', (e) => {
            if (!state.submissions || state.submissions.length === 0) {
                e.preventDefault();
                showToast('No submissions available to export.', 'error');
                return;
            }
            showToast('Exporting submissions data to CSV...', 'info');
        });
    }

    if (btnSubCsvRep) {
        btnSubCsvRep.addEventListener('click', (e) => {
            const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
            if (!hasReport || !state.submissions || state.submissions.length === 0) {
                e.preventDefault();
                showToast('No submissions data in current report. Run Checker first.', 'error');
                return;
            }
            showToast('Exporting submissions CSV...', 'info');
        });
    }

    if (btnSimCsvRep) {
        btnSimCsvRep.addEventListener('click', (e) => {
            const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
            if (!hasReport || !state.similarities || state.similarities.length === 0) {
                e.preventDefault();
                showToast('No pairwise similarity data available to export.', 'error');
                return;
            }
            showToast('Exporting similarity CSV...', 'info');
        });
    }

    if (btnTxt) {
        btnTxt.addEventListener('click', (e) => {
            const hasReport = !!(state.rawReport && state.rawReport.trim().length > 0 && !state.rawReport.startsWith('No report found'));
            if (!hasReport) {
                e.preventDefault();
                showToast('No report text file available. Run Checker first.', 'error');
                return;
            }
            showToast('Downloading final_report.txt...', 'info');
        });
    }

    if (btnComparison) {
        btnComparison.addEventListener('click', () => {
            const sel1 = document.getElementById('compare-select-f1');
            const sel2 = document.getElementById('compare-select-f2');
            const formatSelect = document.getElementById('compare-download-format');

            const f1 = sel1 ? sel1.value : '';
            const f2 = sel2 ? sel2.value : '';
            const fmt = (formatSelect ? formatSelect.value : 'html').toLowerCase();

            if (!f1 || !f2 || f1 === f2) {
                showToast('Please select two distinct submission files to compare.', 'error');
                return;
            }

            showToast(`Downloading comparison for ${f1} vs ${f2} (${fmt.toUpperCase()})...`, 'info');

            const downloadUrl = `/api/similarity/export-comparison?file1=${encodeURIComponent(f1)}&file2=${encodeURIComponent(f2)}&format=${encodeURIComponent(fmt)}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `comparison_${f1}_vs_${f2}.${fmt}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div style="flex: 1;">${escapeHtml(message)}</div>
        <button style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 1.1rem;" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}
