import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import io
from pypdf import PdfWriter, PdfReader, Transformation

app = Flask(__name__)

SONGS_FILE = os.path.join(os.path.dirname(__file__), 'songs.json')

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
        '…': '...',
        '•': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin1', errors='replace').decode('latin1')

@app.route('/export-pdf', methods=['POST'])
@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    song_ids_str = request.form.get('song_ids', '[]')
    title = clean_pdf_text(request.form.get('title', 'Campfire Songbook'))
    subtitle = clean_pdf_text(request.form.get('subtitle', 'Campfire Program'))
    include_toc = request.form.get('include_toc') == 'on'

    try:
        song_ids = json.loads(song_ids_str)
    except Exception:
        song_ids = []

    songs = load_songs()
    song_map = {s['id']: s for s in songs}
    selected_songs = [song_map[int(sid)] for sid in song_ids if int(sid) in song_map]

    INK = (0, 0, 0)
    GREY = (110, 110, 110)

    # Step 1: compose content as sequential A5 portrait pages
    pdf = FPDF(orientation='P', unit='mm', format='A5')
    pdf.set_auto_page_break(auto=True, margin=10)

    # Front cover
    pdf.add_page()
    pdf.set_draw_color(*INK)
    pdf.set_line_width(0.4)
    pdf.rect(8, 8, 210 - 16, 148 - 16)
    pdf.set_text_color(*INK)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_xy(16, 60)
    pdf.multi_cell(210 - 32, 9, title, align="C")
    if subtitle:
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(*GREY)
        pdf.set_xy(16, pdf.get_y() + 4)
        pdf.multi_cell(210 - 32, 5, subtitle, align="C")
    pdf.set_text_color(0, 0, 0)

    # Optional TOC
    if include_toc:
        pdf.add_page()
        pdf.set_text_color(*INK)
        pdf.set_font("helvetica", "B", 14)
        pdf.set_xy(0, 14)
        pdf.cell(210, 8, "Program", new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
        pdf.set_font("helvetica", "", 10)
        y = 34
        for i, s in enumerate(selected_songs, 1):
            s_title = clean_pdf_text(s.get('title', ''))
            s_key = clean_pdf_text(s.get('key', ''))
            if y > 132:
                pdf.add_page()
                y = 14
            pdf.set_xy(14, y)
            pdf.cell(8, 6, f"{i}.", new_x=XPos.RIGHT, new_y=YPos.TOP, align="R")
            pdf.set_xy(24, y)
            pdf.cell(172, 6, f"{s_title}  (Key: {s_key})", new_x=XPos.RIGHT, new_y=YPos.TOP)
            y += 7
        pdf.set_text_color(0, 0, 0)

    # Song pages: one song after another flowing down A5 pages
    for idx, s in enumerate(selected_songs):
        number = idx + 1
        s_title = clean_pdf_text(s.get('title', ''))
        s_artist = clean_pdf_text(s.get('artist', ''))
        s_key = clean_pdf_text(s.get('key', ''))
        lyrics_text = s.get('lyrics', '') or ''

        if idx > 0 and pdf.get_y() > 100:
            pdf.add_page()

        pdf.set_text_color(*INK)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_x(12)
        pdf.multi_cell(186, 6, f"{number}. {s_title}")
        if s_artist:
            pdf.set_text_color(*GREY)
            pdf.set_font("helvetica", "I", 8)
            pdf.set_x(12)
            pdf.multi_cell(186, 4, f"{s_artist}  -  Tonart: {s_key}")
        pdf.set_text_color(*INK)
        pdf.set_font("helvetica", "", 9)
        pdf.set_x(12)
        pdf.multi_cell(186, 4.6, lyrics_text)

    # Pad to a multiple of 4 pages for saddle-stitch folding
    total_pages = pdf.page_no()
    blanks = (4 - total_pages % 4) % 4
    for _ in range(blanks):
        pdf.add_page()

    content_bytes = bytes(pdf.output())

    # Step 2: saddle-stitch imposition.
    # A4 landscape sheet holds two A5 pages per side. For a booklet of n pages:
    #   sheet 1 front: [n, 1]   (back cover left, front cover right)
    #   sheet 1 back:  [2, n-1]
    #   sheet 2 front: [n-2, 3] ... etc. (1-indexed)
    reader = PdfReader(io.BytesIO(content_bytes))
    writer = PdfWriter()
    n = len(reader.pages)

    W = 297 / 25.4 * 72   # A4 landscape width in pt
    H = 297 / 25.4 * 72 * 210 / 297  # = A4 landscape height
    HW = W / 2

    def add_sheet(left_idx, right_idx):
        """left_idx/right_idx: 0-based content page indices on this side."""
        page = writer.add_blank_page(width=W, height=H)
        t = Transformation().translate(HW, 0)
        page.merge_transformed_page(reader.pages[right_idx], t)
        page.merge_transformed_page(reader.pages[left_idx], Transformation())

    for sheet in range(n // 4):
        first = sheet * 2          # first content page of this sheet pair
        last = n - 1 - sheet * 2   # last content page
        add_sheet(last, first)            # front side of the sheet
        add_sheet(first + 1, last - 1)    # back side of the sheet

    out = io.BytesIO()
    writer.write(out)
    pdf_bytes = out.getvalue()

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='Campfire_Songbook_Booklet.pdf'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
