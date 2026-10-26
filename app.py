import os
import json
import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from fpdf import FPDF
import io
from pypdf import PdfWriter, PdfReader

app = Flask(__name__)

SONGS_FILE = os.path.join(os.path.dirname(__file__), 'songs.json')

RELOAD_WATCHED_DIRS = ['templates', 'static']
reload_lock = threading.Lock()
reload_state = {'mtime': 0}

def _scan_mtimes():
    mtimes = []
    for d in RELOAD_WATCHED_DIRS:
        base = os.path.join(os.path.dirname(__file__), d)
        for root, _, files in os.walk(base):
            for name in files:
                p = os.path.join(root, name)
                try:
                    mtimes.append(os.path.getmtime(p))
                except OSError:
                    pass
    if os.path.exists(SONGS_FILE):
        try:
            mtimes.append(os.path.getmtime(SONGS_FILE))
        except OSError:
            pass
    return max(mtimes, default=0)

@app.route('/reload-status')
def reload_status():
    if not app.debug:
        return jsonify(enabled=False)
    with reload_lock:
        current = _scan_mtimes()
        if current != reload_state['mtime']:
            reload_state['mtime'] = current
    return jsonify(enabled=True, mtime=reload_state['mtime'])

def load_songs():
    if not os.path.exists(SONGS_FILE):
        return []
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_songs(songs):
    with open(SONGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)

@app.route('/')
def index():
    query = request.args.get('q', '').strip().lower()
    songs = load_songs()

    tag_filter = request.args.get('tag')
    if tag_filter:
        songs = [s for s in songs if tag_filter in s.get('tags', [])]
    
    all_tags = sorted(set(tag for s in load_songs() for tag in s.get('tags', []) if tag))

    if query:
        filtered = []
        for s in songs:
            tags_str = ' '.join(s.get('tags', []))
            if (query in s.get('title', '').lower() or
                query in s.get('artist', '').lower() or
                query in s.get('category', '').lower() or
                query in s.get('lyrics', '').lower() or
                query in tags_str.lower()):
                filtered.append(s)
        songs = filtered

    return render_template('index.html', songs=songs, query=query, all_tags=all_tags, tag_filter=tag_filter)

@app.route('/song/<int:song_id>')
def song_detail(song_id):
    songs = load_songs()
    song = next((s for s in songs if s['id'] == song_id), None)
    if not song:
        return "Song not found", 404
    return render_template('song_detail.html', song=song)

@app.route('/new-song', methods=['GET', 'POST'])
def new_song():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        artist = request.form.get('artist', '').strip()
        category = request.form.get('category', '').strip() or 'General'
        key = request.form.get('key', '').strip() or 'C'
        lyrics = request.form.get('lyrics', '').strip()

        if not title or not lyrics:
            return "Title and lyrics are required", 400

        songs = load_songs()
        new_id = max([s['id'] for s in songs], default=0) + 1

        song_entry = {
            "id": new_id,
            "title": title,
            "artist": artist or "Traditional",
            "category": category,
            "key": key,
            "lyrics": lyrics,
            "tags": request.form.get('tags', '').split(',') if request.form.get('tags') else []
        }
        songs.append(song_entry)
        save_songs(songs)

        return redirect(url_for('song_detail', song_id=new_id))

    return render_template('new_song.html')

@app.route('/program')
def view_program():
    return render_template('program.html')

@app.route('/api/songs')
def api_songs():
    songs = load_songs()
    return jsonify(songs)

def clean_pdf_text(text):
    if not text:
        return ""
    replacements = {
        '—': '-',
        '–': '-',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '…': '...'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin1', errors='replace').decode('latin1')

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    song_ids_str = request.form.get('song_ids', '[]')
    title = clean_pdf_text(request.form.get('title', 'Campfire Songbook'))
    subtitle = clean_pdf_text(request.form.get('subtitle', 'Campfire Program'))

    try:
        song_ids = json.loads(song_ids_str)
    except Exception:
        song_ids = []

    songs = load_songs()
    song_map = {s['id']: s for s in songs}
    selected_songs = [song_map[int(sid)] for sid in song_ids if int(sid) in song_map]

    # Generate booklet-form PDF (A4 landscape, one song per page)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=12)

    def add_song_page(s, number):
        pdf.add_page()
        pdf.set_font("helvetica", "B", 14)
        pdf.set_x(15)
        s_title = clean_pdf_text(s.get('title', ''))
        s_artist = clean_pdf_text(s.get('artist', ''))
        s_key = clean_pdf_text(s.get('key', ''))
        header = f"{number}. {s_title} (Key: {s_key})"
        if s_artist:
            header += f" - {s_artist}"
        pdf.multi_cell(282, 7, header)
        pdf.set_font("helvetica", "", 11)
        pdf.set_x(15)
        lyrics_text = s.get('lyrics', '') or ''
        pdf.multi_cell(282, 5, lyrics_text)

    # Cover page (front of booklet) - A4 landscape
    # Layout: left half = front cover (title centered there), right half = back cover (blank)
    # After folding the right half over, the title appears centered on the front.
    pdf.add_page()
    front_w = 297 / 2  # left half
    pdf.set_font("helvetica", "B", 28)
    pdf.set_xy(0, 100)
    pdf.cell(front_w, 14, title, ln=False, align="C")
    if subtitle:
        pdf.set_font("helvetica", "I", 14)
        pdf.set_text_color(100, 100, 100)
        pdf.set_xy(0, 120)
        pdf.cell(front_w, 7, subtitle, ln=False, align="C")
    pdf.set_text_color(0, 0, 0)

    # TOC / inside cover - simple list (no lyrics), content on left half
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.set_xy(0, 15)
    pdf.cell(148.5, 10, "Program", ln=False, align="C")
    pdf.set_font("helvetica", "", 12)
    y = 35
    for i, s in enumerate(selected_songs, 1):
        s_title = clean_pdf_text(s.get('title', ''))
        s_key = clean_pdf_text(s.get('key', ''))
        if y > 190:
            pdf.add_page()
            y = 20
        pdf.set_xy(20, y)
        pdf.cell(118, 7, f"{i}. {s_title}  (Key: {s_key})", ln=False)
        y += 8

    # Song pages - 2 columns per A4 landscape page (left/right), songs flow top-to-bottom
    # Each column 135mm wide with gap, full 210mm page height
    pdf.add_page()
    page_height = 210
    margin_top = 10
    margin_bottom = 10
    col_w = 135
    col_gap = 8
    col_x_left = 15
    col_x_right = 15 + col_w + col_gap

    def estimate_song_height(s):
        lyrics = s.get('lyrics', '') or ''
        lines = lyrics.split('\n') if lyrics else ['']
        return 8 + max(len(lines) * 4.5, 4) + 4

    # Two columns: collect songs into left then right column
    current_col = 0  # 0 = left, 1 = right
    current_y = margin_top
    for idx, s in enumerate(selected_songs):
        number = idx + 1
        s_title = clean_pdf_text(s.get('title', ''))
        s_artist = clean_pdf_text(s.get('artist', ''))
        s_key = clean_pdf_text(s.get('key', ''))
        header = f"{number}. {s_title} (Key: {s_key})"
        if s_artist:
            header += f" - {s_artist}"
        lyrics_text = s.get('lyrics', '') or ''

        est_h = estimate_song_height(s)
        # If this song doesn't fit in current column, move to next column/page
        if current_y + est_h > page_height - margin_bottom:
            current_col += 1
            current_y = margin_top
            if current_col > 1:
                pdf.add_page()
                current_col = 0
        if current_col == 0:
            current_x = col_x_left
        else:
            current_x = col_x_right

        pdf.set_xy(current_x, current_y)
        pdf.set_font("helvetica", "B", 11)
        pdf.multi_cell(col_w, 6, header)
        pdf.set_xy(current_x, pdf.get_y())
        pdf.set_font("helvetica", "", 9)
        pdf.multi_cell(col_w, 4.5, lyrics_text)
        current_y = pdf.get_y() + 3

    # Pad to multiple of 4 for booklet printing (blank pages if needed)
    # Note: booklet expects total pages divisible by 4 for clean folding
    total_pages = pdf.page_no()
    blanks_needed = (4 - total_pages % 4) % 4
    for _ in range(blanks_needed):
        pdf.add_page()

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_bytes = pdf_output.encode('latin1')
    else:
        pdf_bytes = bytes(pdf_output)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='Campfire_Songbook_Booklet.pdf'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
