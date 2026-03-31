from http.server import BaseHTTPRequestHandler
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode


def create_ticket_image(template_img, ticket_id, qr_data, ordinal, settings):
    """Create a ticket image with QR code, ordinal and ticket ID overlaid"""
    img = template_img.copy()
    img_width, img_height = img.size

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Calculate QR size and position
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
        ordinal_font_size = max(12, int(settings.get("ordinal_font_size", 36)))
        try:
            ordinal_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", ordinal_font_size)
        except:
            ordinal_font = ImageFont.load_default()

        ordinal_x = int(img_width * settings.get("ordinal_x_percent", 75) / 100)
        ordinal_y = int(img_height * settings.get("ordinal_y_percent", 35) / 100)
        ordinal_text = str(ordinal)

        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((ordinal_x + dx, ordinal_y + dy), ordinal_text, font=ordinal_font, fill="white", anchor="mm")
        draw.text((ordinal_x, ordinal_y), ordinal_text, font=ordinal_font, fill="black", anchor="mm")

    # Draw ticket ID
    font_size = max(10, int(settings.get("ticket_id_font_size", 24)))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text_x = int(img_width * settings.get("ticket_id_x_percent", 75) / 100)
    text_y = int(img_height * settings.get("ticket_id_y_percent", 75) / 100)

    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            draw.text((text_x + dx, text_y + dy), ticket_id, font=font, fill="white", anchor="mm")
    draw.text((text_x, text_y), ticket_id, font=font, fill="black", anchor="mm")

    return img


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            template_b64 = data["template"]
            settings = data["settings"]

            # Decode template image
            img_data = base64.b64decode(template_b64)
            template_img = Image.open(BytesIO(img_data))

            # Generate preview
            preview = create_ticket_image(
                template_img,
                "SAMPLE-TICKET-ID",
                "https://example.com/qr",
                ordinal=1,
                settings=settings
            )

            # Resize for preview (max 800px wide)
            max_width = 800
            if preview.width > max_width:
                ratio = max_width / preview.width
                preview = preview.resize(
                    (max_width, int(preview.height * ratio)),
                    Image.Resampling.LANCZOS
                )

            # Convert to JPEG
            if preview.mode == 'RGBA':
                rgb = Image.new('RGB', preview.size, (255, 255, 255))
                rgb.paste(preview, mask=preview.split()[3])
                preview = rgb

            buf = BytesIO()
            preview.save(buf, format='JPEG', quality=85)
            buf.seek(0)

            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(buf.read())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
