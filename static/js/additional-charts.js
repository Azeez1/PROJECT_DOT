// Additional chart functions for PC Excessive Use, Safety Inbox, and Unassigned HOS

// Normalize column names helper
const normalize = s => s.toLowerCase()
    .replace(/[^a-z\s]/g, '')
    .replace(/\s+/g, '_')
    .trim();

// PC Excessive Use Charts
function drawPCCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const driverIdx = cols.findIndex(c => normalize(c) === 'driver_name');
    const durationIdx = cols.findIndex(c => normalize(c).startsWith('personal_conveyance'));
    if (driverIdx === -1 || durationIdx === -1) { canvas.classList.add('hidden'); return; }

    const totals = {};
    rows.forEach(r => {
        const d = r[driverIdx];
        const hrs = parseFloat(r[durationIdx]) || 0;
        if (d) totals[d] = (totals[d] || 0) + hrs;
    });

    const sorted = Object.entries(totals).sort((a,b) => b[1] - a[1]);
    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'pie') {
        const top = sorted.slice(0,10);
        const others = sorted.slice(10).reduce((sum,[,h]) => sum+h, 0);
        const labels = top.map(([d]) => d);
        const data = top.map(([,h]) => h);
        if (others > 0) { labels.push('Others'); data.push(others); }
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        window.currentChart = new Chart(ctx, {
            type: 'pie',
            data: { labels, datasets: [{ data, backgroundColor: colors }] },
            options: { plugins: { title: { display: true, text: name } } }
        });
        return;
    }

    const top = sorted.slice(0,15);
    const labels = top.map(([d]) => d);
    const data = top.map(([,h]) => h);
    const colors = data.map(h => h > 14 ? 'red' : h > 10 ? 'orange' : 'green');
    window.currentChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Hours', data, backgroundColor: colors }] },
        options: {
            plugins: { title: { display: true, text: name } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

// Safety Inbox Charts
function drawSafetyCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const typeIdx = cols.findIndex(c => normalize(c) === 'event_type');
    const statusIdx = cols.findIndex(c => normalize(c) === 'status');
    const tagIdx = cols.findIndex(c => normalize(c) === 'driver_tags');
    if (typeIdx === -1 || tagIdx === -1) { canvas.classList.add('hidden'); return; }

    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'bar' && statusIdx !== -1) {
        const counts = {};
        rows.forEach(r => {
            const type = r[typeIdx];
            const raw = (r[statusIdx] || '').toLowerCase();
            const st = raw.includes('dismiss') ? 'Dismissed' : raw.includes('review') ? 'Reviewed' : 'Other';
            if (!counts[type]) counts[type] = { Dismissed:0, Reviewed:0, Other:0 };
            counts[type][st] += 1;
        });
        const labels = Object.keys(counts);
        const statuses = ['Dismissed','Reviewed','Other'];
        const colors = { Dismissed:'#00D9FF', Reviewed:'#FF6B35', Other:'#FF0000' };
        const datasets = statuses.map(s => ({
            label: s,
            data: labels.map(l => counts[l][s]),
            backgroundColor: colors[s]
        }));
        window.currentChart = new Chart(ctx, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                plugins: { title: { display: true, text: name } },
                scales: { x:{ stacked:true }, y:{ stacked:true, beginAtZero:true } }
            }
        });
        return;
    }

    const regions = ['Great Lakes','Ohio Valley','Southeast','Midwest','Corporate','Gulf Coast'];
    const counts = {};
    rows.forEach(r => {
        const tags = (r[tagIdx] || '').toLowerCase();
        let found = false;
        regions.forEach(reg => {
            if (tags.includes(reg.toLowerCase())) {
                counts[reg] = (counts[reg] || 0) + 1;
                found = true;
            }
        });
        if (!found) counts['Other'] = (counts['Other'] || 0) + 1;
    });
    const labels = Object.keys(counts);
    const data = labels.map(l => counts[l]);
    const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
    window.currentChart = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{ data, backgroundColor: colors }] },
        options: { plugins: { title: { display: true, text: name } } }
    });
}

// Unassigned HOS Charts
function drawUnassignedCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const vehicleIdx = cols.findIndex(c => normalize(c) === 'vehicle');
    const timeIdx = cols.findIndex(c => normalize(c) === 'unassigned_time');
    const segIdx = cols.findIndex(c => normalize(c) === 'unassigned_segments');
    const tagIdx = cols.findIndex(c => normalize(c) === 'tags');
    if (vehicleIdx === -1 || timeIdx === -1) { canvas.classList.add('hidden'); return; }

    const parseHours = str => {
        if (typeof str !== 'string') return parseFloat(str) || 0;
        const m = str.match(/(\d+)h/); const h = m ? parseInt(m[1],10) : 0;
        const m2 = str.match(/(\d+)m/); const mins = m2 ? parseInt(m2[1],10) : 0;
        return h + mins/60;
    };

    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'pie' && tagIdx !== -1 && segIdx !== -1) {
        const regions = ['Great Lakes','Ohio Valley','Southeast','Midwest','Corporate','Gulf Coast'];
        const counts = {};
        rows.forEach(r => {
            const tags = (r[tagIdx] || '').toLowerCase();
            let region = 'Other';
            regions.forEach(reg => { if (tags.includes(reg.toLowerCase())) region = reg; });
            const seg = parseInt(r[segIdx],10) || 0;
            counts[region] = (counts[region] || 0) + seg;
        });
        Object.keys(counts).forEach(k => { if (counts[k] === 0) delete counts[k]; });
        const labels = Object.keys(counts);
        const data = labels.map(l => counts[l]);
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        window.currentChart = new Chart(ctx, {
            type: 'pie',
            data: { labels, datasets: [{ data, backgroundColor: colors }] },
            options: { plugins: { title: { display: true, text: name } } }
        });
        return;
    }

    const totals = {};
    rows.forEach(r => {
        const veh = r[vehicleIdx];
        const hrs = parseHours(r[timeIdx]);
        if (veh) totals[veh] = (totals[veh] || 0) + hrs;
    });
    const sorted = Object.entries(totals).sort((a,b) => b[1] - a[1]).slice(0,15);
    const labels = sorted.map(([v]) => v.length > 30 ? v.slice(0,27) + '...' : v);
    const data = sorted.map(([,h]) => h);
    const colors = data.map(() => '#FF6384');
    window.currentChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Hours', data, backgroundColor: colors }] },
        options: {
            plugins: { title: { display: true, text: name } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

// Export functions
window.drawPCCharts = drawPCCharts;
window.drawSafetyCharts = drawSafetyCharts;
window.drawUnassignedCharts = drawUnassignedCharts;

