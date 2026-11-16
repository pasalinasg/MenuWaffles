"""Export the current menu and its bestseller photos to a shareable PDF.

Run: uv run --no-project --with reportlab --with pymupdf python scripts/export-menu-pdf.py
"""
from pathlib import Path
from html import escape, unescape
import csv
import re

import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/pdf/Belfit Waffles - Menu.pdf'
PREVIEW = ROOT / 'tmp/pdfs'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
for name, filename in [('Sans', 'arial.ttf'), ('SansBold', 'arialbd.ttf'), ('Serif', 'georgia.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / filename)))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='SansBold')

html = (ROOT / 'index.html').read_text(encoding='utf-8')
with (ROOT / 'menu.csv').open(encoding='utf-8-sig', newline='') as source:
    rows = list(csv.DictReader(source, delimiter=';'))
groups = {}
for row in rows:
    groups.setdefault(row['categoria'], []).append(row)


def plain(markup):
    return unescape(re.sub(r'<[^>]*>', '', markup)).strip()


def paragraph_text(css_class):
    return plain(re.search(r'<p class="' + css_class + r'">(.*?)</p>', html, re.S)[1])


care_markup = re.search(r'<aside class="care">(.*?)</aside>', html, re.S)[1]
care_body = re.search(r'<p>(.*?)</p>', care_markup, re.S)[1]
care_lines = [plain(part) for part in re.split(r'<br\s*/?>', care_body)]
footer_text = plain(re.search(r'<footer>(.*?)</footer>', html, re.S)[1])
title = plain(re.search(r'<title>(.*?)</title>', html, re.S)[1])
W, H = A4
MARGIN = 42
WIDTH = W - 2 * MARGIN
GREEN = HexColor(re.search(r'--olive:\s*(#[0-9a-fA-F]{6})', html)[1])
EARTH = HexColor('#816856')
MUTED = HexColor('#59634f')
PAPER = HexColor('#faf7ef')
SOFT = HexColor('#e8ecde')
LINE = HexColor('#d4d6c8')
PAGE_COUNT = 3
c = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
c.setTitle(title)
c.setAuthor('belfit')
c.setSubject('Menú de waffles saludables con toppings y fotos de los más vendidos')


def paragraph(text, size=10.5, leading=16, font='Sans', color=MUTED):
    return Paragraph(escape(text), ParagraphStyle('p', fontName=font, fontSize=size, leading=leading, textColor=color))


def para(text, top, x=MARGIN, width=WIDTH, **style):
    p = paragraph(text, **style)
    _, height = p.wrap(width, H)
    p.drawOn(c, x, top - height)
    return top - height


def rule(y, x=MARGIN, width=WIDTH):
    c.setStrokeColor(LINE)
    c.setLineWidth(.6)
    c.line(x, y, x + width, y)


def start_page():
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    top, size = H - 30, 62
    c.saveState()
    clip = c.beginPath()
    clip.circle(W / 2, top - size / 2, size / 2)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(str(ROOT / 'assets/logo-belfit.png'), (W - size) / 2, top - size, size, size)
    c.restoreState()
    c.setFillColor(GREEN)
    c.setFont('SansBold', 8)
    c.drawCentredString(W / 2, top - size - 16, paragraph_text('top-note').upper())
    return top - size - 45


def finish_page(number):
    rule(42)
    c.setFillColor(EARTH)
    c.setFont('Sans', 9)
    c.drawString(MARGIN, 27, footer_text)
    c.drawRightString(W - MARGIN, 27, f'{number} / {PAGE_COUNT}')
    c.showPage()


def product(row, top, spacing=34):
    amount = f"Gs. {int(row['precio']):,}".replace(',', '.')
    bottom = para(row['nombre'], top, width=WIDTH - 88, size=17, leading=22, font='Serif', color=GREEN)
    c.setFillColor(GREEN)
    c.setFont('SansBold', 11)
    c.drawRightString(W - MARGIN, top - 17, amount)
    bottom = para(row['descripcion'], bottom - 6, size=10.5, leading=15)
    rule(bottom - 16)
    return bottom - spacing


# Page one: packs and the current refrigeration notice, without the removed heading.
y = start_page()
y = para('Nuestros waffles', y, size=29, leading=35, font='Serif', color=GREEN) - 14
y = para(paragraph_text('attributes'), y, size=8.6, leading=13, font='SansBold', color=EARTH) - 12
y = para(paragraph_text('intro'), y, leading=17) - 26
y = para('Sin agregados', y, size=21, leading=26, font='Serif', color=GREEN) - 12
y = para(paragraph_text('pack-note'), y, size=8, leading=12, color=EARTH) - 18
for row in groups['Waffles']:
    y = product(row, y)
care_top = y - 4
c.setFillColor(SOFT)
c.roundRect(MARGIN, care_top - 64, WIDTH, 64, 10, stroke=0, fill=1)
yy = para(care_lines[0], care_top - 14, x=MARGIN + 16, width=WIDTH - 32, font='SansBold', color=GREEN)
yy = para(care_lines[1], yy - 5, x=MARGIN + 16, width=WIDTH - 32, size=10, leading=15)
assert yy > care_top - 64 + 8
finish_page(1)

# Page two: the three priced waffles, followed by toppings without prices.
y = start_page()
y = para('Con toppings', y, size=29, leading=35, font='Serif', color=GREEN) - 18
for row in groups['Waffles con toppings']:
    y = product(row, y, spacing=22)
column_gap = 26
column_width = (WIDTH - column_gap) / 2
for i, category in enumerate(['Toppings clásicos', 'Toppings especiales']):
    x = MARGIN + i * (column_width + column_gap)
    yy = para(category.replace('Toppings ', '').capitalize(), y, x=x, width=column_width, size=19, leading=24, font='Serif', color=GREEN) - 10
    for row in groups[category]:
        yy = para('• ' + row['nombre'], yy, x=x, width=column_width, size=10.5, leading=16) - 4
    assert yy > 60
finish_page(2)

# Page three: all three supplied photos, in the CSV order, with their combinations.
y = start_page()
y = para('Los más vendidos', y, size=29, leading=35, font='Serif', color=GREEN) - 22
padding, photo_size, row_gap = 16, 160, 20
bestsellers = groups['Los más vendidos']
panel_height = padding * 2 + len(bestsellers) * photo_size + (len(bestsellers) - 1) * row_gap
assert y - panel_height > 60, 'Photo panel does not fit'
c.setFillColor(SOFT)
c.roundRect(MARGIN, y - panel_height, WIDTH, panel_height, 10, stroke=0, fill=1)
row_top = y - padding
text_x = MARGIN + padding + photo_size + 20
text_width = WIDTH - padding * 2 - photo_size - 20
for i, row in enumerate(bestsellers):
    source = ROOT / row['imagen']
    assert source.is_file(), f'Missing photo: {source}'
    image = ImageReader(str(source))
    iw, ih = image.getSize()
    scale = max(photo_size / iw, photo_size / ih)
    dw, dh = iw * scale, ih * scale
    bottom = row_top - photo_size
    c.saveState()
    clip = c.beginPath()
    clip.rect(MARGIN + padding, bottom, photo_size, photo_size)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(str(source), MARGIN + padding - (dw - photo_size) / 2,
                bottom - (dh - photo_size) * .35, dw, dh)
    c.restoreState()
    name = paragraph(row['nombre'], size=16, leading=21, font='Serif', color=GREEN)
    desc = paragraph(row['descripcion'], size=10.5, leading=16)
    name_height = name.wrap(text_width, H)[1]
    desc_height = desc.wrap(text_width, H)[1]
    text_height = name_height + 8 + desc_height
    assert text_height < photo_size
    top = row_top - (photo_size - text_height) / 2
    name.drawOn(c, text_x, top - name_height)
    desc.drawOn(c, text_x, top - name_height - 8 - desc_height)
    if i < len(bestsellers) - 1:
        rule(bottom - row_gap / 2, x=MARGIN + padding, width=WIDTH - 2 * padding)
    row_top = bottom - row_gap
finish_page(3)
c.save()

# Verify the artifact content and render every page for visual inspection.
doc = pymupdf.open(OUTPUT)
assert len(doc) == PAGE_COUNT
text = '\n'.join(page.get_text() for page in doc)
for row in rows:
    assert row['nombre'] in text, f"Missing entry: {row['nombre']}"
assert 'MANTENER REFRIGERADOS.' in text
assert 'Para disfrutarlos mejor' not in text
assert len(doc[2].get_images(full=True)) >= 4, 'Expected logo plus three bestseller photos'
for i, page in enumerate(doc):
    page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(PREVIEW / f'page-{i + 1}.png')
print(f'Updated {OUTPUT}')
print(f'Validated {PAGE_COUNT} pages, {len(rows)} entries and 3 bestseller photos; {OUTPUT.stat().st_size} bytes.')
