const form = document.getElementById('finalize');
if (form) {
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const data = new FormData(form);
    const wizId = window.ticket || form.dataset.ticket;
    await fetch(`/finalize/${wizId}`, {
      method: 'POST',
      body: data
    });
    const link = document.createElement('a');
    link.href = `/download/${wizId}`;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    link.remove();
  });
}
