(function () {
    if (!window.location.hostname.match(/^(localhost|127\.0\.0\.1)$/)) return;

    let lastMtime = null;
    let pollTimer = null;

    function reloadPage() {
        if (pollTimer) clearInterval(pollTimer);
        window.location.reload();
    }

    function poll() {
        fetch('/reload-status', { cache: 'no-store' })
            .then(r => r.json())
            .then(data => {
                if (!data.enabled) return;
                if (lastMtime === null) {
                    lastMtime = data.mtime;
                } else if (data.mtime !== lastMtime) {
                    reloadPage();
                }
            })
            .catch(() => {});
    }

    document.addEventListener('DOMContentLoaded', () => {
        poll();
        pollTimer = setInterval(poll, 1000);
    });
})();
