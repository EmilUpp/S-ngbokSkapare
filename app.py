import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from fpdf import FPDF
import io

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

    if query:
        filtered = []
        for s in songs:
            if (query in s.get('title', '').lower() or
                query in s.get('artist', '').lower() or
                query in s.get('category', '').lower() or
                query in s.get('lyrics', '').lower()):
                filtered.append(s)
        songs = filtered

    return render_template('index.html', songs=songs, query=query)

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
            "lyrics": lyrics
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

@app.route('/export-pdf', methods=['POST'])
import json

def export_pdf():
    song_ids_str = request.form.get('song_ids', '[]')
    title = request.form.get('title', 'Campfire Songbook')
    subtitle = request.form.get('subtitle', 'Campfire Program')

    try:
        song_ids = json.loads(song_ids_str)
    except Exception:
        song_ids = []

    songs = load_songs()
    song_map = {s['id']: s for s in songs}
    selected_songs = [song_map[int(sid)] for sid in song_ids if int(sid) in song_map]

    # Generate PDF using fpdf2
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title Page / Header
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 15, title, ln=True, align="C")

    if subtitle:
        pdf.set_font("helvetica", "I", 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, subtitle, ln=True, align="C")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Table of Contents
    if selected_songs:
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Program Song List:", ln=True)
        pdf.set_font("helvetica", "", 11)
        for i, s in enumerate(selected_songs, 1):
            pdf.cell(0, 7, f"{i}. {s['title']} (Key: {s['key']}) - {s['artist']}", ln=True)
        pdf.ln(10)

    # Song Pages
    for i, s in enumerate(selected_songs, 1):
        pdf.add_page()

        # Song Header
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 10, f"{i}. {s['title']}", ln=True)

        pdf.set_font("helvetica", "I", 11)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, f"Artist: {s['artist']}  |  Category: {s['category']}  |  Key: {s['key']}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # Lyrics
        pdf.set_font("helvetica", "", 11)
        # Handle multi-line lyrics cleanly
        for line in s['lyrics'].split('\n'):
            if line.strip() == '':
                pdf.ln(4)
            else:
                pdf.cell(0, 6, line, ln=True)

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_bytes = pdf_output.encode('latin1')
    else:
        pdf_bytes = bytes(pdf_output)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='Campfire_Songbook.pdf'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
