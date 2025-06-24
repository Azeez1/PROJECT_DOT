const wizId   = location.pathname.split('/').pop();
const buildBtn = document.getElementById('build-pdf');
const incChk   = document.getElementById('include-charts');

// global object updated by table.js
window.activeFilters = window.activeFilters || {};

if (buildBtn) {
  buildBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    const payload = {
      filters: window.activeFilters,
      include_charts: incChk ? incChk.checked : true,
    };
    const res = await fetch(`/finalize/${wizId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      alert('Failed to build PDF');
      return;
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'DOT_Compliance_Snapshot.pdf';
    a.click();
  });
}
