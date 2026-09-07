#!/usr/bin/env python3
"""Test script for booklet PDF export."""
import io
import json
import sys
sys.path.insert(0, '.')

from app import app
from pypdf import PdfReader

SONGS_FILE = 'songs.json'

def load_songs():
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_booklet():
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    songs = data[:4] if len(data) >= 4 else data
    song_ids = [s['id'] for s in songs]

    with app.test_client() as client:
        response = client.post('/export-pdf', data={
            'song_ids': json.dumps(song_ids),
            'title': 'Scout Night',
            'subtitle': 'Campfire'
        })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.content_type == 'application/pdf', f"Expected PDF, got {response.content_type}"

    reader = PdfReader(io.BytesIO(response.data))
    pages = len(reader.pages)
    print(f"Pages: {pages}")

    # A4 landscape = 297 x 210 mm
    for i, page in enumerate(reader.pages):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        print(f"  Page {i+1}: {w/72*25.4:.0f} x {h/72*25.4:.0f} mm")
        assert abs(w - 841.89) < 5, f"Page {i+1}: width {w} not A4 landscape (841.89 pts)"
        assert abs(h - 595.28) < 5, f"Page {i+1}: height {h} not A4 landscape (595.28 pts)"

    # Check content: cover, TOC, then songs somewhere on remaining pages
    texts = [reader.pages[i].extract_text() or '' for i in range(pages)]
    print("Page contents (first line):")
    for i, text in enumerate(texts):
        first_line = text.split('\n')[0] if text else '(empty)'
        print(f"  Page {i+1}: {first_line!r}")

    assert 'Scout Night' in texts[0], "Cover missing title"
    assert 'Program' in texts[1], "TOC missing 'Program'"
    # Songs should be on pages 3+
    song_texts = texts[2:]
    all_song_text = '\n'.join(song_texts)
    assert 'Country Roads' in all_song_text, "First song missing"
    assert 'Kumbaya' in all_song_text, "Second song missing"
    assert 'Lean on Me' in all_song_text, "Fourth song missing"

    # Total should be even for double-sided printing (multiple of 4 preferred)
    assert pages % 2 == 0, f"Expected even page count for double-sided booklet, got {pages}"
    assert pages % 4 == 0, f"Expected multiple of 4 for booklet folding, got {pages}"

    print("All booklet tests passed.")

if __name__ == '__main__':
    test_booklet()
