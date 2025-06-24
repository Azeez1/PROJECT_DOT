const form = document.querySelector('#finalize-form');
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const wizId = window.ticket || form.dataset.ticket;
    const res = await fetch(`/finalize/${wizId}`, { method: 'POST', body: data });
    window.location = res.headers.get('Location');      // triggers download
  });
}
