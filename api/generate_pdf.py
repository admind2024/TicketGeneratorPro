from http.server import BaseHTTPRequestHandler
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def create_ticket_image(template_img, ticket_id, qr_data, ordinal, settings, scale_ratio=1.0):
    """Create a ticket image with QR code, ordinal and ticket ID overlaid"""
    img = template_img.copy()
    img_width, img_height = img.size

    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_size = int(img_width * settings["qr_size_percent"] / 100)
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

    qr_x = int(img_width * settings["qr_x_percent"] / 100 - qr_size / 2)
    qr_y = int(img_height * settings["qr_y_percent"] / 100 - qr_size / 2)
    qr_x = max(0, min(qr_x, img_width - qr_size))
    qr_y = max(0, min(qr_y, img_height - qr_size))

    if img.mode != "RGBA":
        img = img.convert("RGBA")
    qr_img = qr_img.convert("RGBA")
    img.paste(qr_img, (qr_x, qr_y))

    draw = ImageDraw.Draw(img)

    # Draw ordinal
    if ordinal is not None:
        ordinal_font_size = int(settings.get("ordinal_font_size", 36) * scale_ratio)
        ordinal_font_size = max(12, ordinal_font_size)
        try:
            ordinal_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", ordinal_font_size)
        except:
            ordinal_font = ImageFont.load_default()

        ordinal_x = int(img_width * settings.get("ordinal_x_percent", 75) / 100)
        ordinal_y = int(img_height * settings.get("ordinal_y_percent", 35) / 100)
        ordinal_text = str(ordinal)

        outline_range = [-2, -1, 0, 1, 2] if scale_ratio >= 0.5 else [-1, 0, 1]
        for dx in outline_range:
            for dy in outline_range:
                draw.text((ordinal_x + dx, ordinal_y + dy), ordinal_text, font=ordinal_font, fill="white", anchor="mm")
        draw.text((ordinal_x, ordinal_y), ordinal_text, font=ordinal_font, fill="black", anchor="mm")

    # Draw ticket ID
    scaled_font_size = int(settings.get("ticket_id_font_size", 24) * scale_ratio)
    scaled_font_size = max(10, scaled_font_size)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", scaled_font_size)
    except:
        font = ImageFont.load_default()

    text_x = int(img_width * settings.get("ticket_id_x_percent", 75) / 100)
    text_y = int(img_height * settings.get("ticket_id_y_percent", 75) / 100)

    outline_range = [-2, -1, 0, 1, 2] if scale_ratio >= 0.5 else [-1, 0, 1]
    for dx in outline_range:
        for dy in outline_range:
            draw.text((text_x + dx, text_y + dy), ticket_id, font=font, fill="white", anchor="mm")
    draw.text((text_x, text_y), ticket_id, font=font, fill="black", anchor="mm")

    return img


def reorder_tickets_for_cutting(tickets, pages_per_deck=100):
    """Reorder tickets so that when pages are stacked and cut, ordinals come in sequence."""
    tickets_per_page = 4
    chunk_size = pages_per_deck * tickets_per_page

    total_tickets = len(tickets)
    reordered = []
    num_chunks = (total_tickets + chunk_size - 1) // chunk_size

    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, total_tickets)
        chunk = tickets[start:end]

        pad_count = chunk_size - len(chunk)
        if pad_count > 0:
            chunk = chunk + [None] * pad_count

        matrix = []
        for row in range(tickets_per_page):
            matrix.append(chunk[row * pages_per_deck: (row + 1) * pages_per_deck])

        for col in range(pages_per_deck):
            for row in range(tickets_per_page):
                if col < len(matrix[row]) and matrix[row][col] is not None:
                    reordered.append(matrix[row][col])

    return reordered


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            template_b64 = data["template"]
            tickets = data["tickets"]
            settings = data["settings"]
            zone_name = data.get("zone_name", "tickets")
            optimize = settings.get("optimize_pdf", True)
            reorder = settings.get("reorder_for_cutting", False)
            pages_per_deck = settings.get("pages_per_deck", 100)

            # Decode template image
            img_data = base64.b64decode(template_b64)
            template_img = Image.open(BytesIO(img_data))

            # Apply reordering if enabled
            if reorder:
                tickets = reorder_tickets_for_cutting(tickets, pages_per_deck)

            # Optimize template if needed
            ratio = 1.0
            if optimize:
                target_width = 1400
                ratio = target_width / template_img.width
                target_height = int(template_img.height * ratio)
                template_img = template_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Create PDF
            pdf_buffer = BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            page_width, page_height = A4

            margin = 20
            ticket_width = page_width - 2 * margin
            ticket_height = (page_height - 5 * margin) / 4

            for i, ticket in enumerate(tickets):
                if ticket is None:
                    continue

                position_on_page = i % 4
                if position_on_page == 0 and i > 0:
                    c.showPage()

                ticket_img = create_ticket_image(
                    template_img,
                    ticket["ticketId"],
                    ticket["qr_code"],
                    ordinal=ticket.get("ordinal"),
                    settings=settings,
                    scale_ratio=ratio if optimize else 1.0
                )

                y_position = page_height - margin - (position_on_page + 1) * (ticket_height + margin / 2)

                img_buffer = BytesIO()
                if optimize:
                    if ticket_img.mode == 'RGBA':
                        rgb_img = Image.new('RGB', ticket_img.size, (255, 255, 255))
                        rgb_img.paste(ticket_img, mask=ticket_img.split()[3])
                        ticket_img = rgb_img
                    elif ticket_img.mode != 'RGB':
                        ticket_img = ticket_img.convert('RGB')
                    ticket_img.save(img_buffer, format='JPEG', quality=85, optimize=True)
                else:
                    ticket_img.save(img_buffer, format='PNG')

                img_buffer.seek(0)

                c.drawImage(
                    ImageReader(img_buffer),
                    margin,
                    y_position,
                    width=ticket_width,
                    height=ticket_height,
                    preserveAspectRatio=True,
                    anchor='c'
                )

            c.save()
            pdf_buffer.seek(0)

            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{zone_name}_tickets.pdf"')
            self.end_headers()
            self.wfile.write(pdf_buffer.read())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
