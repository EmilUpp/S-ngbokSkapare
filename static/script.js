// Campfire Program State Management using localStorage
document.addEventListener('DOMContentLoaded', () => {
    updateProgramBadge();

    // Bind song select buttons
    document.querySelectorAll('.toggle-program-btn').forEach(btn => {
        const songId = btn.getAttribute('data-song-id');
        updateButtonState(btn, songId);

        btn.addEventListener('click', () => {
            toggleSongInProgram(songId);
            updateButtonState(btn, songId);
            updateProgramBadge();
        });
    });
});

function getSelectedSongs() {
    try {
        const stored = localStorage.getItem('campfire_songs');
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function saveSelectedSongs(songs) {
    localStorage.setItem('campfire_songs', JSON.stringify(songs));
}

function toggleSongInProgram(songId) {
    let songs = getSelectedSongs();
    songId = parseInt(songId);
    const index = songs.indexOf(songId);
    if (index > -1) {
        songs.splice(index, 1);
    } else {
        songs.push(songId);
    }
    saveSelectedSongs(songs);
}

function isSongSelected(songId) {
    let songs = getSelectedSongs();
    return songs.includes(parseInt(songId));
}

function updateButtonState(btn, songId) {
    if (isSongSelected(songId)) {
        btn.classList.remove('btn-outline-warning', 'btn-outline-dark');
        btn.classList.add('btn-warning', 'text-dark');
        btn.innerHTML = '<i class="fa-solid fa-check me-1"></i> In Program';
    } else {
        btn.classList.remove('btn-warning', 'text-dark');
        btn.classList.add('btn-outline-dark');
        btn.innerHTML = '<i class="fa-solid fa-plus me-1"></i> Add to Program';
    }
}

function updateProgramBadge() {
    const songs = getSelectedSongs();
    const badge = document.getElementById('program-badge');
    if (badge) {
        badge.textContent = songs.length;
    }
}
