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

// Driver Safety Report Charts
function drawDriverSafetyCharts(name, rows, cols, chartType) {
    const canvas = document.getElementById('preview');
    if (!rows.length) { canvas.classList.add('hidden'); return; }

    const scoreIdx = cols.findIndex(c => normalize(c).includes('safety_score'));
    const driveIdx = cols.findIndex(c => normalize(c).includes('drive_time'));
    const distIdx = cols.findIndex(c => normalize(c).includes('total_distance'));
    const tagsIdx = cols.findIndex(c => normalize(c) === 'tags');

    const eventMap = {
        'Harsh Accel':'harsh_accel',
        'Harsh Brake':'harsh_brake',
        'Harsh Turn':'harsh_turn',
        'Mobile Usage':'mobile_usage',
        'Inattentive Driving':'inattentive_driving',
        'Drowsy':'drowsy',
        'Rolling Stop':'rolling_stop',
        'No Seat Belt':'no_seat_belt'
    };
    const eventIdx = {};
    Object.entries(eventMap).forEach(([k,v])=>{
        const idx = cols.findIndex(c => normalize(c) === v);
        if(idx !== -1) eventIdx[k] = idx;
    });

    const ctx = canvas.getContext('2d');
    if (window.currentChart) window.currentChart.destroy();
    canvas.classList.remove('hidden');

    if (chartType === 'pie' && Object.keys(eventIdx).length) {
        const totals = {};
        Object.keys(eventIdx).forEach(k => totals[k] = 0);
        rows.forEach(r => {
            Object.entries(eventIdx).forEach(([k,idx]) => {
                const val = parseInt(r[idx],10) || 0;
                totals[k] += val;
            });
        });
        const labels = Object.keys(totals);
        const data = labels.map(l => totals[l]);
        const colors = labels.map((_,i)=>`hsl(${i*40},70%,60%)`);
        window.currentChart = new Chart(ctx, {
            type:'radar',
            data:{ labels, datasets:[{ label:'Events', data, backgroundColor:'rgba(54,162,235,0.2)', borderColor:'#36A2EB' }] },
            options:{ plugins:{ title:{ display:true, text:name } }, scales:{ r:{ beginAtZero:true } } }
        });
        return;
    }

    if (chartType === 'line' && scoreIdx !== -1 && driveIdx !== -1) {
        const points = [];
        rows.forEach(r => {
            const score = parseFloat(r[scoreIdx]);
            const drive = parseTimeToHours(r[driveIdx]);
            if (isNaN(score) || isNaN(drive)) return;
            const dist = distIdx !== -1 ? parseFloat(r[distIdx]) || 0 : 0;
            const reg = tagsIdx !== -1 ? extractRegion(r[tagsIdx]) : 'Other';
            points.push({ x: drive, y: score, r: Math.max(3, Math.sqrt(dist)/10), reg });
        });
        const regions = [...new Set(points.map(p=>p.reg))];
        const palette = ['#3366CC','#DC3912','#FF9900','#109618','#990099','#0099C6'];
        const datasets = regions.map((reg,i)=>({
            label: reg,
            data: points.filter(p=>p.reg===reg),
            backgroundColor: palette[i % palette.length]
        }));
        window.currentChart = new Chart(ctx, {
            type:'scatter',
            data:{ datasets },
            options:{ plugins:{ title:{ display:true, text:name } }, scales:{ x:{ title:{ display:true, text:'Drive Hours' } }, y:{ title:{ display:true, text:'Safety Score' }, beginAtZero:true, max:100 } } }
        });
        return;
    }

    if (chartType === 'bar' && tagsIdx !== -1) {
        const severities = ['heavy_speeding_time','severe_speeding_time'];
        const regData = {};
        rows.forEach(r => {
            const reg = extractRegion(r[tagsIdx]);
            if(!regData[reg]) regData[reg] = { heavy:0, severe:0 };
            const heavyIdx = cols.findIndex(c=>normalize(c)===severities[0]);
            const severeIdx = cols.findIndex(c=>normalize(c)===severities[1]);
            const heavy = heavyIdx !== -1 ? parseTimeToHours(r[heavyIdx]) : 0;
            const severe = severeIdx !== -1 ? parseTimeToHours(r[severeIdx]) : 0;
            regData[reg].heavy += heavy;
            regData[reg].severe += severe;
        });
        const labels = Object.keys(regData);
        const heavyData = labels.map(l=>regData[l].heavy);
        const severeData = labels.map(l=>regData[l].severe);
        window.currentChart = new Chart(ctx, {
            type:'bar',
            data:{ labels, datasets:[{label:'Heavy Speeding',data:heavyData,backgroundColor:'#F1C40F'},{label:'Severe Speeding',data:severeData,backgroundColor:'#E74C3C'}] },
            options:{ plugins:{ title:{ display:true, text:name } }, scales:{ x:{ stacked:true }, y:{ stacked:true, beginAtZero:true } } }
        });
        return;
    }

    canvas.classList.add('hidden');
}

// Export functions
window.drawPCCharts = drawPCCharts;
window.drawSafetyCharts = drawSafetyCharts;
window.drawUnassignedCharts = drawUnassignedCharts;
window.drawDriverBehaviorsCharts = drawDriverBehaviorsCharts;
window.drawMissedDVIRCharts = drawMissedDVIRCharts;
window.drawDriverSafetyCharts = drawDriverSafetyCharts;

