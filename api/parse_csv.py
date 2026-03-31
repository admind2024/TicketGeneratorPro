from http.server import BaseHTTPRequestHandler
import json
import csv
import io
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, unquote


def extract_qr_data(qr_code_raw):
    """Extract QR data from URL or return as-is if not a URL"""
    if not qr_code_raw:
        return qr_code_raw
    if qr_code_raw.startswith("http"):
        try:
            parsed = urlparse(qr_code_raw)
            query_params = parse_qs(parsed.query)
            if "data" in query_params:
                return unquote(query_params["data"][0])
        except:
            pass
    return unquote(qr_code_raw)


def find_column(fieldnames, *possible_names):
    for name in fieldnames:
        for possible in possible_names:
            if name.lower().strip() == possible.lower():
                return name
    return None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            # Parse multipart form data or raw CSV
            content_type = self.headers.get('Content-Type', '')

            if 'application/json' in content_type:
                data = json.loads(body)
                csv_text = data.get('csv', '')
            else:
                csv_text = body.decode('utf-8-sig')

            reader = csv.DictReader(io.StringIO(csv_text))
            fieldnames = reader.fieldnames if reader.fieldnames else []

            ticket_id_col = find_column(fieldnames, "ticketId", "ticket_id", "ticketid")
            qr_code_col = find_column(fieldnames, "QR Code", "qr_code", "qrcode", "QRCode", "qrCodeRaw", "qrcoderaw")
            category_key_col = find_column(fieldnames, "categoryKey", "category_key", "categorykey", "category")

            if not all([ticket_id_col, qr_code_col, category_key_col]):
                missing = []
                if not ticket_id_col:
                    missing.append("ticketId")
                if not qr_code_col:
                    missing.append("QR Code")
                if not category_key_col:
                    missing.append("categoryKey")
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"CSV nema potrebne kolone: {', '.join(missing)}",
                    "found_columns": fieldnames
                }).encode())
                return

            tickets_by_category = defaultdict(list)
            total_tickets = 0

            for row in reader:
                ticket_id = row.get(ticket_id_col, "").strip()
                qr_code_raw = row.get(qr_code_col, "").strip()
                category_key = row.get(category_key_col, "").strip()

                qr_code = extract_qr_data(qr_code_raw)

                if ticket_id and qr_code and category_key:
                    tickets_by_category[category_key].append({
                        "ticketId": ticket_id,
                        "qr_code": qr_code
                    })
                    total_tickets += 1

            # Assign ordinals per zone
            zones = {}
            for category_key, tickets in tickets_by_category.items():
                for ordinal, ticket in enumerate(tickets, start=1):
                    ticket["ordinal"] = ordinal
                zones[category_key] = {
                    "tickets": tickets,
                    "count": len(tickets)
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "zones": zones,
                "total_tickets": total_tickets
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
