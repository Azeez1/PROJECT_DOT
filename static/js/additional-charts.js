// Additional chart functions for PC Excessive Use, Safety Inbox, Unassigned HOS
// and new driver-related reports

// Normalize column names helper
const normalize = s => s.toLowerCase()
    .replace(/[^a-z\s]/g, '')
    .replace(/\s+/g, '_')
    .trim();

// Parse "HH:MM:SS" to decimal hours
function parseTimeToHours(timeStr) {
    if(!timeStr) return 0;
    const parts = String(timeStr).split(":");
    if(parts.length < 3) return parseFloat(timeStr) || 0;
    return parseInt(parts[0],10) + parseInt(parts[1],10)/60 + parseInt(parts[2],10)/3600;
}

// Parse "M/D/YYYY, HH:MM" to Date
function parseDateTime(dateStr) {
    return new Date(dateStr);
}

// Consistent region mapping for tags
const regionMap = {
    'Great Lakes': ['Great Lakes','GL'],
    'Ohio Valley': ['Ohio Valley','OV'],
    'Southeast': ['Southeast','SE'],
    'Midwest': ['Midwest','MW'],
    'Corporate': ['Corporate','Corp']
};

function extractRegion(tagStr){
    const lower = String(tagStr || '').toLowerCase();
    for(const [reg, vals] of Object.entries(regionMap)){
        for(const v of vals){
            if(lower.includes(v.toLowerCase())) return reg;
        }
    }
    return 'Other';
}

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

function drawPCChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[PC Dashboard] Starting with ${rows.length} rows`);
    const driverIdx = cols.findIndex(c => normalize(c) === 'driver_name');
    const durationIdx = cols.findIndex(c => normalize(c).startsWith('personal_conveyance'));
    console.log(`[PC Dashboard] driverIdx=${driverIdx}, durationIdx=${durationIdx}`);
    if (driverIdx === -1 || durationIdx === -1) {
        console.log('[PC Dashboard] Required columns not found');
        return;
    }
    const totals = {};
    rows.forEach(r => {
        const d = r[driverIdx];
        const hrs = parseFloat(r[durationIdx]) || 0;
        if (d) totals[d] = (totals[d] || 0) + hrs;
    });
    const sorted = Object.entries(totals).sort((a,b)=>b[1]-a[1]);
    if (chartType === 'pie') {
        const top = sorted.slice(0,10);
        const others = sorted.slice(10).reduce((sum,[,h])=>sum+h,0);
        const labels = top.map(([d])=>d);
        const data = top.map(([,h])=>h);
        if(others>0){ labels.push('Others'); data.push(others); }
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        console.log('[PC Dashboard] Creating pie chart with data:', data);
        console.log('[PC Dashboard] Chart created');
        return new Chart(ctx,{ type:'pie', data:{ labels, datasets:[{ data, backgroundColor:colors }] } });
    }
    const top = sorted.slice(0,15);
    const labels = top.map(([d])=>d);
    const data = top.map(([,h])=>h);
    const colors = data.map(h=>h>14?'red':h>10?'orange':'green');
    console.log('[PC Dashboard] Creating bar chart with data:', data);
    console.log('[PC Dashboard] Chart created');
    return new Chart(ctx,{ type:'bar', data:{ labels, datasets:[{ label:'Hours', data, backgroundColor:colors }] }, options:{ scales:{ y:{ beginAtZero:true } } } });
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

function drawSafetyChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[Safety Dashboard] Starting with ${rows.length} rows`);
    const typeIdx = cols.findIndex(c => normalize(c) === 'event_type');
    const statusIdx = cols.findIndex(c => normalize(c) === 'status');
    const tagIdx = cols.findIndex(c => normalize(c) === 'driver_tags');
    console.log(`[Safety Dashboard] typeIdx=${typeIdx}, statusIdx=${statusIdx}, tagIdx=${tagIdx}`);
    if (typeIdx === -1 || tagIdx === -1) {
        console.log('[Safety Dashboard] Required columns missing');
        return;
    }
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
        const datasets = statuses.map(s => ({ label:s, data: labels.map(l=>counts[l][s]), backgroundColor: colors[s] }));
        console.log('[Safety Dashboard] Creating bar chart with data:', counts);
        console.log('[Safety Dashboard] Chart created');
        return new Chart(ctx,{ type:'bar', data:{ labels, datasets }, options:{ scales:{ x:{ stacked:true }, y:{ stacked:true, beginAtZero:true } } } });
    }
    const regions = ['Great Lakes','Ohio Valley','Southeast','Midwest','Corporate','Gulf Coast'];
    const counts = {};
    rows.forEach(r => {
        const tags = (r[tagIdx] || '').toLowerCase();
        let found = false;
        regions.forEach(reg => {
            if (tags.includes(reg.toLowerCase())) { counts[reg] = (counts[reg]||0)+1; found = true; }
        });
        if(!found) counts['Other'] = (counts['Other']||0)+1;
    });
    const labels = Object.keys(counts);
    const data = labels.map(l=>counts[l]);
    const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
    console.log('[Safety Dashboard] Creating pie chart with data:', counts);
    console.log('[Safety Dashboard] Chart created');
    return new Chart(ctx,{ type:'pie', data:{ labels, datasets:[{ data, backgroundColor:colors }] } });
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

function drawUnassignedChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[Unassigned Dashboard] Starting with ${rows.length} rows`);
    const vehicleIdx = cols.findIndex(c => normalize(c) === 'vehicle');
    const timeIdx = cols.findIndex(c => normalize(c) === 'unassigned_time');
    const segIdx = cols.findIndex(c => normalize(c) === 'unassigned_segments');
    const tagIdx = cols.findIndex(c => normalize(c) === 'tags');
    console.log(`[Unassigned Dashboard] vehicleIdx=${vehicleIdx}, timeIdx=${timeIdx}, segIdx=${segIdx}, tagIdx=${tagIdx}`);
    if (vehicleIdx === -1 || timeIdx === -1) {
        console.log('[Unassigned Dashboard] Required columns missing');
        return;
    }
    const parseHours = str => {
        if (typeof str !== 'string') return parseFloat(str) || 0;
        const m = str.match(/(\d+)h/); const h = m ? parseInt(m[1],10) : 0;
        const m2 = str.match(/(\d+)m/); const mins = m2 ? parseInt(m2[1],10) : 0;
        return h + mins/60;
    };
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
        console.log('[Unassigned Dashboard] Creating pie chart with data:', counts);
        console.log('[Unassigned Dashboard] Chart created');
        return new Chart(ctx,{ type:'pie', data:{ labels, datasets:[{ data, backgroundColor:colors }] } });
    }
    const totals = {};
    rows.forEach(r => {
        const veh = r[vehicleIdx];
        const hrs = parseHours(r[timeIdx]);
        if (veh) totals[veh] = (totals[veh] || 0) + hrs;
    });
    const sorted = Object.entries(totals).sort((a,b)=>b[1]-a[1]).slice(0,15);
    const labels = sorted.map(([v]) => v.length > 30 ? v.slice(0,27)+'...' : v);
    const data = sorted.map(([,h]) => h);
    const colors = data.map(()=>'#FF6384');
    console.log('[Unassigned Dashboard] Creating bar chart with data:', data);
    console.log('[Unassigned Dashboard] Chart created');
    return new Chart(ctx,{ type:'bar', data:{ labels, datasets:[{ label:'Hours', data, backgroundColor:colors }] }, options:{ scales:{ y:{ beginAtZero:true } } } });
}

// Driver Safety Behaviors Charts
function drawDriverBehaviorsCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const tagsIdx = cols.findIndex(c => normalize(c) === 'tags');
    const scoreIdx = cols.findIndex(c => normalize(c).includes('safety_score'));
    const driverIdx = cols.findIndex(c => normalize(c).includes('driver'));
    if (scoreIdx === -1 || driverIdx === -1) { canvas.classList.add('hidden'); return; }

    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'pie' && tagsIdx !== -1) {
        const counts = {};
        rows.forEach(r => {
            const reg = extractRegion(r[tagsIdx]);
            counts[reg] = (counts[reg] || 0) + 1;
        });
        const labels = Object.keys(counts);
        const data = labels.map(l => counts[l]);
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        window.currentChart = new Chart(ctx, {
            type:'pie',
            data:{ labels, datasets:[{ data, backgroundColor: colors }] },
            options:{ plugins:{ title:{ display:true, text:name } } }
        });
        return;
    }

    if (tagsIdx !== -1) {
        const regionScores = {};
        const regionCounts = {};
        rows.forEach(r => {
            const reg = extractRegion(r[tagsIdx]);
            const s = parseFloat(r[scoreIdx]);
            if (!isNaN(s)) {
                regionScores[reg] = (regionScores[reg] || 0) + s;
                regionCounts[reg] = (regionCounts[reg] || 0) + 1;
            }
        });
        if (Object.keys(regionScores).length) {
            const labels = Object.keys(regionScores);
            const data = labels.map(l => regionScores[l] / regionCounts[l]);
            const colors = data.map(v => v > 90 ? 'green' : v >= 80 ? 'yellow' : 'red');
            window.currentChart = new Chart(ctx, {
                type:'bar',
                data:{ labels, datasets:[{ label:'Safety Score', data, backgroundColor: colors }] },
                options:{ plugins:{ title:{ display:true, text:name } }, scales:{ y:{ beginAtZero:true, max:100 } } }
            });
            return;
        }
    }

    const scores = rows.map(r => {
        const sc = parseFloat(r[scoreIdx]);
        const d = r[driverIdx];
        if (!isNaN(sc) && d) return { d, sc };
    }).filter(Boolean).sort((a,b)=>a.sc-b.sc).slice(0,10);
    if (!scores.length) { canvas.classList.add('hidden'); return; }
    const labels = scores.map(s => s.d);
    const data = scores.map(s => s.sc);
    window.currentChart = new Chart(ctx, {
        type:'bar',
        data:{ labels, datasets:[{ label:'Safety Score', data, backgroundColor:'#FF6384' }] },
        options:{ indexAxis:'y', plugins:{ title:{ display:true, text:name } }, scales:{ x:{ beginAtZero:true, max:100 } } }
    });
}

function drawDriverBehaviorsChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[Behaviors Dashboard] Starting with ${rows.length} rows`);
    if (!rows.length) return;
    const tagsIdx = cols.findIndex(c => normalize(c) === 'tags');
    const scoreIdx = cols.findIndex(c => normalize(c).includes('safety_score'));
    const driverIdx = cols.findIndex(c => normalize(c).includes('driver'));
    console.log(`[Behaviors Dashboard] tagsIdx=${tagsIdx}, scoreIdx=${scoreIdx}, driverIdx=${driverIdx}`);
    if (scoreIdx === -1 || driverIdx === -1) {
        console.log('[Behaviors Dashboard] Required columns missing');
        return;
    }
    if (chartType === 'pie' && tagsIdx !== -1) {
        const counts = {};
        rows.forEach(r => { const reg = extractRegion(r[tagsIdx]); counts[reg] = (counts[reg]||0)+1; });
        const labels = Object.keys(counts);
        const data = labels.map(l=>counts[l]);
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        console.log('[Behaviors Dashboard] Creating pie chart with data:', counts);
        console.log('[Behaviors Dashboard] Chart created');
        return new Chart(ctx,{ type:'pie', data:{ labels, datasets:[{ data, backgroundColor:colors }] } });
    }
    if (tagsIdx !== -1) {
        const regionScores = {};
        const regionCounts = {};
        rows.forEach(r => {
            const reg = extractRegion(r[tagsIdx]);
            const s = parseFloat(r[scoreIdx]);
            if(!isNaN(s)) { regionScores[reg] = (regionScores[reg]||0)+s; regionCounts[reg]=(regionCounts[reg]||0)+1; }
        });
        if (Object.keys(regionScores).length) {
            const labels = Object.keys(regionScores);
            const data = labels.map(l=>regionScores[l]/regionCounts[l]);
            const colors = data.map(v => v>90?'green':v>=80?'yellow':'red');
            console.log('[Behaviors Dashboard] Creating bar chart with regional scores:', data);
            console.log('[Behaviors Dashboard] Chart created');
            return new Chart(ctx,{ type:'bar', data:{ labels, datasets:[{ label:'Safety Score', data, backgroundColor:colors }] }, options:{ scales:{ y:{ beginAtZero:true, max:100 } } } });
        }
    }
    const scores = rows.map(r => { const sc=parseFloat(r[scoreIdx]); const d=r[driverIdx]; if(!isNaN(sc)&&d) return {d,sc}; }).filter(Boolean).sort((a,b)=>a.sc-b.sc).slice(0,10);
    if(!scores.length) return;
    const labels = scores.map(s=>s.d);
    const data = scores.map(s=>s.sc);
    console.log('[Behaviors Dashboard] Creating bar chart with data:', data);
    console.log('[Behaviors Dashboard] Chart created');
    return new Chart(ctx,{ type:'bar', data:{ labels, datasets:[{ label:'Safety Score', data, backgroundColor:'#FF6384' }] }, options:{ indexAxis:'y', scales:{ x:{ beginAtZero:true, max:100 } } } });
}

// Missed DVIR Charts
function drawMissedDVIRCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const driverIdx = cols.findIndex(c => normalize(c).includes('driver'));
    const typeIdx = cols.findIndex(c => normalize(c) === 'type');
    const startIdx = cols.findIndex(c => normalize(c).startsWith('start_time'));
    if (driverIdx === -1 || typeIdx === -1) { canvas.classList.add('hidden'); return; }

    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'pie') {
        let pre = 0, post = 0;
        rows.forEach(r => {
            const t = (r[typeIdx] || '').toUpperCase();
            if (t.includes('PRE')) pre++; else if (t.includes('POST')) post++;
        });
        const labels = ['PRE-TRIP','POST-TRIP'];
        const data = [pre, post];
        window.currentChart = new Chart(ctx, {
            type:'pie',
            data:{ labels, datasets:[{ data, backgroundColor:['#3498db','#e74c3c'] }] },
            options:{ plugins:{ title:{ display:true, text:name } } }
        });
        return;
    }

    if (chartType === 'line' && startIdx !== -1) {
        const counts = {};
        rows.forEach(r => {
            const d = parseDateTime(r[startIdx]);
            if(isNaN(d)) return;
            const day = d.toISOString().split('T')[0];
            const t = (r[typeIdx] || '').toUpperCase().includes('PRE') ? 'PRE-TRIP':'POST-TRIP';
            counts[day] = counts[day] || { 'PRE-TRIP':0, 'POST-TRIP':0 };
            counts[day][t] += 1;
        });
        const labels = Object.keys(counts).sort();
        const preData = labels.map(l => counts[l]['PRE-TRIP']);
        const postData = labels.map(l => counts[l]['POST-TRIP']);
        window.currentChart = new Chart(ctx, {
            type:'line',
            data:{ labels, datasets:[{label:'PRE-TRIP',data:preData,borderColor:'#3498db',fill:false},{label:'POST-TRIP',data:postData,borderColor:'#e74c3c',fill:false}] },
            options:{ plugins:{ title:{ display:true, text:name } }, scales:{ y:{ beginAtZero:true } } }
        });
        return;
    }

    const counts = {};
    rows.forEach(r => {
        const d = r[driverIdx];
        const t = (r[typeIdx] || '').toUpperCase().includes('PRE') ? 'PRE-TRIP':'POST-TRIP';
        if(!counts[d]) counts[d] = { 'PRE-TRIP':0, 'POST-TRIP':0 };
        counts[d][t] += 1;
    });
    const sorted = Object.entries(counts).sort((a,b)=>
        (b[1]['PRE-TRIP']+b[1]['POST-TRIP'])-(a[1]['PRE-TRIP']+a[1]['POST-TRIP'])).slice(0,15);
    const labels = sorted.map(([d])=>d);
    const preData = sorted.map(([ ,v])=>v['PRE-TRIP']);
    const postData = sorted.map(([ ,v])=>v['POST-TRIP']);
    window.currentChart = new Chart(ctx, {
        type:'bar',
        data:{ labels, datasets:[{label:'PRE-TRIP',data:preData,backgroundColor:'#3498db'},{label:'POST-TRIP',data:postData,backgroundColor:'#e74c3c'}] },
        options:{ plugins:{ title:{ display:true, text:name } }, scales:{ x:{ stacked:true }, y:{ stacked:true, beginAtZero:true } } }
    });
}

function drawMissedDVIRChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[DVIR Dashboard] Starting with ${rows.length} rows`);
    if (!rows.length) return;
    const driverIdx = cols.findIndex(c => normalize(c).includes('driver'));
    const typeIdx = cols.findIndex(c => normalize(c) === 'type');
    const startIdx = cols.findIndex(c => normalize(c).startsWith('start_time'));
    console.log(`[DVIR Dashboard] driverIdx=${driverIdx}, typeIdx=${typeIdx}, startIdx=${startIdx}`);
    if (driverIdx === -1 || typeIdx === -1) {
        console.log('[DVIR Dashboard] Required columns missing');
        return;
    }
    if (chartType === 'pie') {
        let pre=0, post=0;
        rows.forEach(r=>{ const t=(r[typeIdx]||'').toUpperCase(); if(t.includes('PRE')) pre++; else if(t.includes('POST')) post++; });
        const labels=['PRE-TRIP','POST-TRIP'];
        const data=[pre,post];
        console.log('[DVIR Dashboard] Creating pie chart with data:', {pre,post});
        console.log('[DVIR Dashboard] Chart created');
        return new Chart(ctx,{ type:'pie', data:{ labels, datasets:[{ data, backgroundColor:['#3498db','#e74c3c'] }] } });
    }
    if (chartType === 'line' && startIdx !== -1) {
        const counts={};
        rows.forEach(r=>{ const d=parseDateTime(r[startIdx]); if(isNaN(d)) return; const day=d.toISOString().split('T')[0]; const t=(r[typeIdx]||'').toUpperCase().includes('PRE')?'PRE-TRIP':'POST-TRIP'; counts[day]=counts[day]||{ 'PRE-TRIP':0,'POST-TRIP':0 }; counts[day][t]+=1; });
        const labels=Object.keys(counts).sort();
        const preData=labels.map(l=>counts[l]['PRE-TRIP']);
        const postData=labels.map(l=>counts[l]['POST-TRIP']);
        console.log('[DVIR Dashboard] Creating line chart with data:', counts);
        console.log('[DVIR Dashboard] Chart created');
        return new Chart(ctx,{ type:'line', data:{ labels, datasets:[{label:'PRE-TRIP',data:preData,borderColor:'#3498db',fill:false},{label:'POST-TRIP',data:postData,borderColor:'#e74c3c',fill:false}] }, options:{ scales:{ y:{ beginAtZero:true } } });
    }
    const counts={};
    rows.forEach(r=>{ const d=r[driverIdx]; const t=(r[typeIdx]||'').toUpperCase().includes('PRE')?'PRE-TRIP':'POST-TRIP'; if(!counts[d]){ counts[d]={ 'PRE-TRIP':0,'POST-TRIP':0 }; counts[d][t]+=1; });
    const sorted=Object.entries(counts).sort((a,b)=>(b[1]['PRE-TRIP']+b[1]['POST-TRIP'])-(a[1]['PRE-TRIP']+a[1]['POST-TRIP'])).slice(0,15);
    const labels=sorted.map(([d])=>d);
    const preData=sorted.map(([ ,v])=>v['PRE-TRIP']);
    const postData=sorted.map(([ ,v])=>v['POST-TRIP']);
    console.log('[DVIR Dashboard] Creating bar chart with data:', counts);
    console.log('[DVIR Dashboard] Chart created');
    return new Chart(ctx,{ type:'bar', data:{ labels, datasets:[{label:'PRE-TRIP',data:preData,backgroundColor:'#3498db'},{label:'POST-TRIP',data:postData,backgroundColor:'#e74c3c'}] }, options:{ scales:{ x:{ stacked:true }, y:{ stacked:true, beginAtZero:true } } } });
}

// Driver Safety Report Charts
function drawDriverSafetyCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    const ctx = canvas.getContext('2d');

    if (window.currentChart) {
        window.currentChart.destroy();
    }

    canvas.classList.remove('hidden');

    // Find column indices - handle both exact matches and contains matches
    const normalize = s => s.toLowerCase().replace(/[^a-z\s]/g, '').replace(/\s+/g, '_').trim();

    // Find driver name column
    const driverIdx = cols.findIndex(c => {
        const norm = normalize(c);
        return norm === 'driver_name' || norm.includes('driver_name') || 
               (norm.includes('driver') && !norm.includes('driver_id'));
    });

    // Find other columns
    const scoreIdx = cols.findIndex(c => normalize(c) === 'safety_score' || normalize(c).includes('safety_score'));
    const distanceIdx = cols.findIndex(c => {
        const norm = normalize(c);
        return norm.includes('total_distance') || norm === 'total_distance_mi';
    });

    if (chartType === 'bar') {
        // Bar Chart: Top 10 Drivers by Safety Score (showing best performers)
        const driverScores = [];

        rows.forEach(row => {
            const driver = row[driverIdx];
            const score = scoreIdx !== -1 ? parseFloat(row[scoreIdx]) : null;
            const driveTimeStr = row[cols.findIndex(c => normalize(c).includes('drive_time'))];

            if (driver && score !== null && !isNaN(score)) {
                // Parse drive time if available
                let driveHours = 0;
                if (driveTimeStr) {
                    driveHours = parseTimeToHours(driveTimeStr);
                }

                driverScores.push({
                    driver,
                    score,
                    driveHours
                });
            }
        });

        if (driverScores.length === 0) {
            // Alternative: Show speeding percentages by severity
            const speedingCols = {
                'Light': cols.findIndex(c => normalize(c).includes('percent_light_speeding')),
                'Moderate': cols.findIndex(c => normalize(c).includes('percent_moderate_speeding')),
                'Heavy': cols.findIndex(c => normalize(c).includes('percent_heavy_speeding')),
                'Severe': cols.findIndex(c => normalize(c).includes('percent_severe_speeding'))
            };

            const speedingTotals = {
                'Light': 0,
                'Moderate': 0,
                'Heavy': 0,
                'Severe': 0
            };

            let validRows = 0;

            rows.forEach(row => {
                let hasValidData = false;
                Object.entries(speedingCols).forEach(([severity, idx]) => {
                    if (idx !== -1) {
                        const value = parseFloat(row[idx]);
                        if (!isNaN(value)) {
                            speedingTotals[severity] += value;
                            hasValidData = true;
                        }
                    }
                });
                if (hasValidData) validRows++;
            });

            if (validRows > 0) {
                // Calculate averages
                const averages = Object.entries(speedingTotals).map(([severity, total]) => ({
                    severity,
                    average: (total / validRows).toFixed(2)
                }));

                window.currentChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: averages.map(a => a.severity),
                        datasets: [{
                            label: 'Average Speeding %',
                            data: averages.map(a => a.average),
                            backgroundColor: ['#4CAF50', '#FFC107', '#FF9800', '#F44336']
                        }]
                    },
                    options: {
                        plugins: {
                            title: {
                                display: true,
                                text: 'Fleet Average Speeding by Severity'
                            },
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Percentage of Drive Time'
                                }
                            }
                        }
                    }
                });
                return;
            }
        }

        // Sort by safety score descending (best drivers first)
        const sorted = driverScores.sort((a, b) => b.score - a.score).slice(0, 10);

        // Color based on score
        const colors = sorted.map(d => {
            if (d.score >= 95) return '#4CAF50'; // Green
            if (d.score >= 90) return '#8BC34A'; // Light Green
            if (d.score >= 80) return '#FFC107'; // Yellow
            if (d.score >= 70) return '#FF9800'; // Orange
            return '#F44336'; // Red
        });

        window.currentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sorted.map(d => d.driver),
                datasets: [{
                    label: 'Safety Score',
                    data: sorted.map(d => d.score),
                    backgroundColor: colors
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal bars
                plugins: {
                    title: {
                        display: true,
                        text: 'Top 10 Drivers by Safety Score'
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const driver = sorted[context.dataIndex];
                                if (driver.driveHours > 0) {
                                    return `Drive Time: ${driver.driveHours.toFixed(1)} hours`;
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Safety Score'
                        }
                    }
                }
            }
        });
    } else if (chartType === 'pie') {
        // Pie Chart: Top 10 drivers by distance
        if (driverIdx === -1 || distanceIdx === -1) {
            ctx.font = '16px Arial';
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('Driver or Distance columns not found', canvas.width / 2, canvas.height / 2);
            return;
        }

        const driverData = [];

        rows.forEach(row => {
            const driver = row[driverIdx];
            const distance = parseFloat(row[distanceIdx]) || 0;
            const score = scoreIdx !== -1 ? parseFloat(row[scoreIdx]) || 0 : 0;

            if (driver && distance > 0) {
                driverData.push({ driver, distance, score });
            }
        });

        if (driverData.length === 0) {
            ctx.font = '16px Arial';
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('No valid driver distance data found', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Sort by distance and get top 10
        const top10 = driverData.sort((a, b) => b.distance - a.distance).slice(0, 10);

        window.currentChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: top10.map(d => d.driver),
                datasets: [{
                    data: top10.map(d => d.distance),
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                        '#FF9F40', '#FF6B35', '#C9CBCF', '#4BC0C0', '#F7931E'
                    ]
                }]
            },
            options: {
                plugins: {
                    title: {
                        display: true,
                        text: 'Top 10 Drivers by Distance Driven'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                const driver = top10[index];
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return [`${driver.driver}`, `Distance: ${value.toFixed(0)} miles (${percentage}%)`, `Safety Score: ${driver.score}`];
                            }
                        }
                    }
                }
            }
        });
    }
}

function drawDriverSafetyChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[Driver Safety Dashboard] Starting with ${rows.length} rows`);
    const normalize = s => s.toLowerCase().replace(/[^a-z\s]/g,'').replace(/\s+/g,'_').trim();
    const driverIdx = cols.findIndex(c => { const n = normalize(c); return n==='driver_name' || n.includes('driver_name') || (n.includes('driver') && !n.includes('driver_id')); });
    const scoreIdx = cols.findIndex(c => normalize(c)==='safety_score' || normalize(c).includes('safety_score'));
    const distanceIdx = cols.findIndex(c => { const n=normalize(c); return n.includes('total_distance') || n==='total_distance_mi'; });
    console.log(`[Driver Safety Dashboard] driverIdx=${driverIdx}, scoreIdx=${scoreIdx}, distanceIdx=${distanceIdx}`);
    if (chartType === 'bar') {
        const driverScores=[];
        rows.forEach(row=>{ const driver=row[driverIdx]; const score=scoreIdx!==-1?parseFloat(row[scoreIdx]):null; const driveTimeStr=row[cols.findIndex(c=>normalize(c).includes('drive_time'))]; if(driver && score!==null && !isNaN(score)){ let driveHours=0; if(driveTimeStr){ driveHours=parseTimeToHours(driveTimeStr); } driverScores.push({driver,score,driveHours}); }});
        if(driverScores.length===0){ return; }
        const sorted=driverScores.sort((a,b)=>b.score-a.score).slice(0,10);
        const colors=sorted.map(d=>d.score>=95?'#4CAF50':d.score>=90?'#8BC34A':d.score>=80?'#FFC107':d.score>=70?'#FF9800':'#F44336');
        console.log('[Driver Safety Dashboard] Creating bar chart with data:', sorted);
        console.log('[Driver Safety Dashboard] Chart created');
        return new Chart(ctx,{ type:'bar', data:{ labels:sorted.map(d=>d.driver), datasets:[{ label:'Safety Score', data:sorted.map(d=>d.score), backgroundColor:colors }] }, options:{ indexAxis:'y', scales:{ x:{ beginAtZero:true, max:100 } } } });
    } else if (chartType === 'pie') {
        if (driverIdx === -1 || distanceIdx === -1) return;
        const driverData=[];
        rows.forEach(row=>{ const driver=row[driverIdx]; const distance=parseFloat(row[distanceIdx])||0; if(driver && distance>0){ driverData.push({driver,distance}); }});
        if(!driverData.length) return;
        const top10=driverData.sort((a,b)=>b.distance-a.distance).slice(0,10);
        console.log('[Driver Safety Dashboard] Creating pie chart with data:', top10);
        console.log('[Driver Safety Dashboard] Chart created');
        return new Chart(ctx,{ type:'pie', data:{ labels:top10.map(d=>d.driver), datasets:[{ data:top10.map(d=>d.distance), backgroundColor:['#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF','#FF9F40','#FF6B35','#C9CBCF','#4BC0C0','#F7931E'] }] }});
    }
}

function drawHOSChartForDashboard(ctx, rows, cols, chartType) {
    console.log(`[HOS Dashboard] Starting with ${rows.length} rows`);
    const normalizeName = s => s.toLowerCase().replace(/[^a-z\s]/g,'').replace(/\s+/g,'_').trim();
    const vtIdx = cols.findIndex(c => normalizeName(c) === 'violation_type');
    console.log(`[HOS Dashboard] Violation type column index: ${vtIdx}`);
    if (vtIdx === -1) {
        console.log('[HOS Dashboard] No violation_type column found');
        return;
    }
    const weekIdx = cols.findIndex(c => normalizeName(c) === 'week');
    if(chartType === 'line' && weekIdx !== -1){
        const counts={};
        const weeks=new Set();
        rows.forEach(r=>{ const vt=r[vtIdx]; const wk=r[weekIdx]; if(vt && wk){ counts[vt]=counts[vt]||{}; counts[vt][wk]=(counts[vt][wk]||0)+1; weeks.add(wk); } });
        const weekLabels=Array.from(weeks).sort();
        const palette=['#3366CC','#DC3912','#FF9900','#109618','#990099','#0099C6','#DD4477','#66AA00','#B82E2E','#316395'];
        const datasets=Object.entries(counts).map(([type,byWeek],i)=>({label:type,data:weekLabels.map(w=>byWeek[w]||0),borderColor:palette[i%palette.length],fill:false}));
        console.log('[HOS Dashboard] Creating line chart with data:', counts);
        console.log('[HOS Dashboard] Chart created');
        const chart = new Chart(ctx,{type:'line',data:{ labels:weekLabels, datasets }});
        return chart;
    }else{
        const counts={};
        rows.forEach(r=>{ const val=r[vtIdx]; if(val!==null && val!==undefined && String(val).trim().toLowerCase()!=='null'){ counts[val]=(counts[val]||0)+1; }});
        console.log(`[HOS Dashboard] Creating ${chartType} chart with data:`, counts);
        console.log('[HOS Dashboard] Chart created');
        const chart = new Chart(ctx,{ type:chartType, data:{ labels:Object.keys(counts), datasets:[{ label:'count', data:Object.values(counts) }] } });
        return chart;
    }
}

// Export functions
window.drawPCCharts = drawPCCharts;
window.drawSafetyCharts = drawSafetyCharts;
window.drawUnassignedCharts = drawUnassignedCharts;
window.drawDriverBehaviorsCharts = drawDriverBehaviorsCharts;
window.drawMissedDVIRCharts = drawMissedDVIRCharts;
window.drawDriverSafetyCharts = drawDriverSafetyCharts;
window.drawPCChartForDashboard = drawPCChartForDashboard;
window.drawSafetyChartForDashboard = drawSafetyChartForDashboard;
window.drawUnassignedChartForDashboard = drawUnassignedChartForDashboard;
window.drawDriverBehaviorsChartForDashboard = drawDriverBehaviorsChartForDashboard;
window.drawMissedDVIRChartForDashboard = drawMissedDVIRChartForDashboard;
window.drawDriverSafetyChartForDashboard = drawDriverSafetyChartForDashboard;
window.drawHOSChartForDashboard = drawHOSChartForDashboard;