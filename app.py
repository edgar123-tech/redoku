import io
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, url_for, session
from config import Config
from models import db, Subscriber
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from pathlib import Path



def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Urika2021!")
    app.config.from_object(Config)
    db.init_app(app)

    # Try register Comic Sans or fallback
    register_fonts(app)

    # Ensure instance folder exists and database tables are created once at startup
    with app.app_context():
        os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
        db.create_all()  # This replaces @before_first_request

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    


    @app.route("/generate", methods=["POST"])
    def generate():
        # Get provided text and email
        text = request.form.get("text", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not text:
            flash("Please enter the text you want converted to PDF.", "error")
            return redirect(url_for("index"))

        # Save email if provided (and valid-looking)
        # Save email if provided (and valid-looking)
        if email:
            if "@" in email and "." in email.split("@")[-1]:
                existing = Subscriber.query.filter_by(email=email).first()
                if not existing:
                    sub = Subscriber(email=email, created_at=datetime.utcnow(), pdf_count=1)
                    db.session.add(sub)
                    db.session.commit()
                    flash("Email saved. Thank you!", "success")
                else:
                    # increment counter
                    existing.pdf_count += 1
                    db.session.commit()
                    flash("Email already saved. Good to see you again !", "info")
            else:
                flash("Email looks invalid — not saved.", "error")


        # Generate PDF in-memory
        pdf_bytes = create_dyslexia_pdf(app, text)

        # Send PDF for download
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="redoku_output.pdf",
        )

    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if "logged_in" in session and session["logged_in"]:
            # Query all subscribers here
            subs = Subscriber.query.order_by(Subscriber.created_at.desc()).all()
            return render_template("admin.html", subs=subs)
        if request.method == "POST":
            password = request.form.get("password")
            if password == ADMIN_PASSWORD:
                session["logged_in"] = True
                return redirect(url_for("admin"))
            else:
                return render_template("login.html", error="Incorrect password.")
        return render_template("login.html")

    return app


def register_fonts(app):
    """
    Register a Comic-like font if present in static/fonts; else register a fallback.
    Place a TTF named ComicSans.ttf (or any TTF) in static/fonts/ to use it.
    """
    fonts_dir = Path(app.root_path) / "static" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    comic_ttf = fonts_dir / "Comic-Sans.ttf"
    fallback_name = "DejaVuSans"  # usually available on most systems

    try:
        if comic_ttf.exists():
            pdfmetrics.registerFont(TTFont("ComicSansCustom", str(comic_ttf)))
            app.config["REDOKU_FONT"] = "ComicSansCustom"
        else:
            # Try to register a common TTF if available in system fonts dir
            pdfmetrics.registerFont(TTFont(fallback_name, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
            app.config["REDOKU_FONT"] = fallback_name
    except Exception:
        # Last resort: register a default built-in font name
        app.config["REDOKU_FONT"] = "Helvetica"

def create_dyslexia_pdf(app, text):
    from reportlab.pdfbase.pdfmetrics import getAscent, getDescent

    PAGE_WIDTH, PAGE_HEIGHT = A4
    margin = 20 * mm
    max_width = PAGE_WIDTH - 2 * margin
    x_start = margin
    y_start = PAGE_HEIGHT - margin

    font_name = app.config.get("REDOKU_FONT", "Helvetica")
    font_size = 22
    word_spacing = 10
    line_spacing = font_size * 1.8

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    def draw_background():
        c.setFillColor(HexColor("#fbfbf7"))
        c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        panel_padding = 12 * mm
        panel_w = PAGE_WIDTH - 2 * margin + panel_padding
        panel_x = margin - panel_padding / 2
        panel_y = margin - panel_padding / 2
        c.setFillColor(HexColor("#f6f9f7"))
        c.roundRect(panel_x, panel_y, panel_w, PAGE_HEIGHT - 2 * margin + panel_padding, 8 * mm, fill=1, stroke=0)

    draw_background()
    c.setFont(font_name, font_size)

    # Split words while preserving newlines
    words = []
    for para in text.splitlines():
        if para.strip() == "":
            words.append({"word": "", "newline": True})
            continue
        for w in para.split():
            words.append({"word": w, "newline": False})
        words.append({"word": "", "newline": True})

    cur_x = x_start
    cur_y = y_start - font_size

    for item in words:
        if item["newline"]:
            cur_x = x_start
            cur_y -= line_spacing + font_size * 0.4
            if cur_y < margin + font_size:
                c.showPage()
                draw_background()
                c.setFont(font_name, font_size)
                cur_y = y_start - font_size
            continue

        w = item["word"]
        if not w:
            continue

        word_width = pdfmetrics.stringWidth(w, font_name, font_size)
        first_letter = w[0]
        first_letter_width = pdfmetrics.stringWidth(first_letter, font_name, font_size)
        total_word_width = word_width + word_spacing

        if cur_x + total_word_width > margin + max_width:
            cur_x = x_start
            cur_y -= line_spacing
            if cur_y < margin + font_size:
                c.showPage()
                draw_background()
                c.setFont(font_name, font_size)
                cur_y = y_start - font_size

        # Get precise font metrics for highlight rectangle
        ascent = getAscent(font_name, font_size)
        descent = abs(getDescent(font_name, font_size))
        hl_height = ascent + descent + 2  # extra padding 2 pts
        hl_width = first_letter_width + 4  # extra padding 4 pts
        hl_y = cur_y - descent
        hl_x = cur_x - 2  # left padding

        c.setFillColor(HexColor("#fff3b0"))
        c.roundRect(hl_x, hl_y, hl_width, hl_height, 2, fill=1, stroke=0)

        c.setFillColor(HexColor("#222222"))
        c.drawString(cur_x, cur_y, first_letter)
        if len(w) > 1:
            c.drawString(cur_x + first_letter_width, cur_y, w[1:])

        cur_x += total_word_width

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
