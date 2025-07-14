const wizId   = location.pathname.split('/').pop();
const buildBtn = document.getElementById('build-pdf');

// global object updated by table.js
window.activeFilters = window.activeFilters || {};

if (buildBtn) {
  buildBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    const payload = {
      filters: window.activeFilters,
      trend_end: document.getElementById('trend-end')?.value || null,
    };
    const msg = document.getElementById('message');
    msg.textContent = '';
    const includeDocx = document.getElementById('include-docx')?.checked;
    const url = includeDocx ? `/finalize/${wizId}?include_docx=1` : `/finalize/${wizId}`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      msg.textContent = 'Failed to build PDF.';
      return;
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = includeDocx ? 'DOT_Compliance_Snapshot.zip' : 'DOT_Compliance_Snapshot.pdf';
    a.click();
  });
}
