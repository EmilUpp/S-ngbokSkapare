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
            'subtitle': 'Campfire',
            'include_toc': 'on'
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

    # Saddle-stitch imposition: content pages of 4 are combined 2-per-side.
    # With 4 songs + cover + TOC the content is >= 6 pages, padded to 8 -> 2 sheets.
    # Sheets: front [n,1], back [2,n-1], front [n-2,3], back [4,n-3] (1-indexed).
    texts = [reader.pages[i].extract_text() or '' for i in range(pages)]
    print("Page contents (first line):")
    for i, text in enumerate(texts):
        first_line = text.split('\n')[0] if text else '(empty)'
        print(f"  Page {i+1}: {first_line!r}")

    all_text = '\n'.join(texts)
    assert 'Scout Night' in all_text, "Cover missing title"
    assert 'Program' in all_text, "TOC missing 'Program'"
    assert 'Country Roads' in all_text, "First song missing"
    assert 'Kumbaya' in all_text, "Second song missing"
    assert 'Lean on Me' in all_text, "Fourth song missing"

    # Booklet page-count: sheets are printed both sides; PDF pages = 2 per sheet,
    # and sheet count must be a whole number (content pages multiple of 4).
    assert pages % 2 == 0, f"Expected even PDF page count (front+back per sheet), got {pages}"

    # PDF pages = 2 sides per sheet; content page count is a multiple of 4
    assert pages % 2 == 0, f"Expected even PDF page count (sheet front+back), got {pages}"
    # 4 songs + cover + TOC = 6 content pages -> padded to 8 -> 4 sides = 2 PDF pages
    assert pages == 2, f"Expected 2 PDF pages (1 sheet, 4 A5 pages) for this content, got {pages}"

    print("All booklet tests passed.")

if __name__ == '__main__':
    test_booklet()
