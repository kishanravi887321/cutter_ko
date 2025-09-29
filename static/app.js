document.getElementById('splitForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const url = document.getElementById('url').value;
    const interval = document.getElementById('interval').value;
    const base_name = document.getElementById('base_name').value;
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Processing...';
    statusDiv.style.color = '#2a5298';

    try {
        const response = await fetch(`/split?url=${encodeURIComponent(url)}&interval=${interval}&base_name=${encodeURIComponent(base_name)}`);
        if (response.ok) {
            const blob = await response.blob();
            const filename = response.headers.get('content-disposition')?.split('filename=')[1] || 'clips.zip';
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename.replace(/"/g, '');
            link.click();
            statusDiv.textContent = 'Download started!';
            statusDiv.style.color = '#1e3c72';
        } else {
            const error = await response.json();
            statusDiv.textContent = error.error || 'Error occurred.';
            statusDiv.style.color = 'red';
        }
    } catch (err) {
        statusDiv.textContent = 'Network error.';
        statusDiv.style.color = 'red';
    }
});
