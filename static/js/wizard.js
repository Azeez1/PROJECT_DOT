const wizId   = location.pathname.split('/').pop();
const buildBtn = document.getElementById('build-pdf');
const wordChk = document.getElementById('include-word');

// global object updated by table.js
window.activeFilters = window.activeFilters || {};

if (buildBtn) {
  buildBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    const payload = {
      filters: window.activeFilters,
      trend_end: document.getElementById('trend-end')?.value || null,
      include_word: wordChk?.checked || false,
    };
    const msg = document.getElementById('message');
    msg.textContent = '';
    const res = await fetch(`/finalize/${wizId}`, {
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
    if (wordChk?.checked) {
      a.download = 'DOT_Compliance_Snapshot.zip';
    } else {
      a.download = 'DOT_Compliance_Snapshot.pdf';
    }
    a.click();
  });
}
