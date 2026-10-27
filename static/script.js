// Lägereldsprogram - tillståndshantering med localStorage
document.addEventListener('DOMContentLoaded', () => {
    updateProgramBadge();

    // Koppla sångvalsknappar
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
        btn.classList.add('is-in-program');
        btn.innerHTML = '<i class="fa-solid fa-check me-1"></i> I programmet';
    } else {
        btn.classList.remove('is-in-program');
        btn.innerHTML = '<i class="fa-solid fa-plus me-1"></i> Lägg till i program';
    }
}

function updateProgramBadge() {
    const songs = getSelectedSongs();
    const badge = document.getElementById('program-badge');
    if (badge) {
        badge.textContent = songs.length;
    }
}

function loadPreset(preset, redirectUrl) {
    const presets = {
        classic: [],
        swedish: [],
        short: []
    };

    fetch('/api/songs')
        .then(r => r.json())
        .then(allSongs => {
            const map = {};
            allSongs.forEach(s => {
                const t = s.title.toLowerCase();
                map[t] = s.id;
                if (t.includes('country')) map['country'] = s.id;
                if (t.includes('kumbaya')) map['kumbaya'] = s.id;
                if (t.includes('lean on me')) map['lean'] = s.id;
                if (t.includes('sunshine')) map['sunshine'] = s.id;
                if (t.includes('helan')) map['helan'] = s.id;
                if (t.includes('vi är bäst')) map['vi_ar_bast'] = s.id;
                if (t.includes('scout')) map['scout'] = s.id;
                if (t.includes('fire')) map['fire'] = s.id;
                if (t.includes('land')) map['land'] = s.id;
            });

            if (preset === 'classic') {
                presets.classic = ['country', 'kumbaya', 'lean', 'sunshine'].map(k => map[k]).filter(Boolean);
            } else if (preset === 'swedish') {
                presets.swedish = ['helan', 'vi_ar_bast', 'scout'].map(k => map[k]).filter(Boolean);
            } else if (preset === 'short') {
                presets.short = ['country', 'kumbaya', 'kumbaya'].map(k => map[k]).filter(Boolean).slice(0, 3);
            }

            if (presets[preset].length > 0) {
                localStorage.setItem('campfire_songs', JSON.stringify(presets[preset]));
                if (redirectUrl) {
                    window.location.href = redirectUrl;
                } else {
                    loadProgramSongs();
                    updateProgramBadge();
                }
            }
        });
}
