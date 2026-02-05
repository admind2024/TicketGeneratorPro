# 🎫 Ticket Generator - Uputstvo za upotrebu

## Opis aplikacije

Ticket Generator je desktop aplikacija za generisanje ulaznica u PDF formatu sa QR kodovima. Aplikacija omogućava:
- Učitavanje CSV fajla sa podacima o kartama
- Automatsko sortiranje karata po zonama
- Generisanje PDF fajlova sa 4 ulaznice po stranici
- Podešavanje pozicije QR koda i ID-a ulaznice

---

## Pokretanje aplikacije

```bash
C:/Users/Korisnik/Documents/repos/StadionTicketing/.venv/Scripts/Activate.ps1
python ticket_generator.py
```

---

## Korak 1: Učitavanje CSV fajla

### Drag & Drop
1. Prevucite CSV fajl direktno na sivu zonu u aplikaciji

### Ili korištenjem dugmeta
1. Kliknite na **"📁 Izaberite CSV fajl"**
2. Pronađite i izaberite željeni CSV fajl

### Potrebne kolone u CSV fajlu:
| Kolona | Opis |
|--------|------|
| `ticketId` | Jedinstveni ID ulaznice |
| `QR Code` | URL ili podatak za QR kod |
| `categoryKey` | Naziv zone/kategorije |

### Šta aplikacija radi:
- Kreira folder `events/{naziv-fajla}/`
- Kreira podfolder `zones/` sa podfolderima za svaku zonu
- Generiše CSV fajl za svaku zonu sa kolonama `ticketId` i `qr_code`
- Automatski dekodira QR podatke iz URL formata

Nakon uspješnog učitavanja, kliknite **"Dalje ➡️"**

---

## Korak 2: Generisanje PDF ulaznica

### Lijeva strana - Lista zona
- ✅ Zona ima template sliku
- ❌ Zona nema template sliku

### Postavljanje template slike
1. Izaberite zonu iz liste
2. Kliknite **"🖼️ Izaberi template za zonu"**
3. Izaberite sliku ulaznice (PNG, JPG, JPEG, BMP, GIF)

> **Napomena:** Aplikacija automatski traži prvu sliku u folderu zone. Možete je postaviti ručno prije pokretanja aplikacije.

### Desna strana - Podešavanja pozicije

| Opcija | Opis |
|--------|------|
| **QR X pozicija (%)** | Horizontalna pozicija QR koda (0-100%) |
| **QR Y pozicija (%)** | Vertikalna pozicija QR koda (0-100%) |
| **QR veličina (%)** | Veličina QR koda kao % širine slike |
| **Ticket ID X (%)** | Horizontalna pozicija teksta |
| **Ticket ID Y (%)** | Vertikalna pozicija teksta |
| **Font veličina** | Veličina fonta za ID ulaznice |

### Optimizacija PDF-a
- **📦 Optimizuj PDF (manji fajl)** - Čekirajte za manje PDF fajlove
  - Koristi JPEG kompresiju
  - Smanjuje rezoluciju na 1400px
  - Značajno smanjuje veličinu fajla

### Preview
Kliknite **"👁️ Preview"** da vidite kako će izgledati ulaznica sa trenutnim podešavanjima.

### Generisanje PDF-a

| Dugme | Funkcija |
|-------|----------|
| **🎫 Generiši za izabranu zonu** | Generiše PDF samo za izabranu zonu |
| **🎫 Generiši SVE ulaznice** | Generiše PDF za sve zone koje imaju template |

Tokom generisanja:
- Progress bar pokazuje napredak
- Dugmad su onemogućena dok traje proces
- Po završetku se otvara folder sa PDF fajlom

---

## Struktura foldera

```
ticketGenerator/
├── ticket_generator.py
├── codes/                          # Folder za ulazne CSV fajlove
│   └── naziv-eventa.csv
└── events/
    └── naziv-eventa/               # Automatski kreiran folder
        └── zones/
            ├── zona-1/
            │   ├── zona-1.csv      # Filtrirani podaci
            │   ├── template.png    # Template slika (ručno dodati)
            │   └── zona-1_tickets.pdf  # Generisani PDF
            ├── zona-2/
            │   ├── zona-2.csv
            │   ├── template.jpg
            │   └── zona-2_tickets.pdf
            └── ...
```

---

## Savjeti

1. **Priprema template slike:**
   - Koristite slike u proporciji koja odgovara formatu ulaznice
   - Ostavite prazan prostor gdje će biti QR kod i ID

2. **QR kod pozicija:**
   - 50% X i 50% Y = centar slike
   - 75% X = desna strana
   - 25% X = lijeva strana

3. **Optimizacija:**
   - Za štampu visokog kvaliteta, isključite optimizaciju
   - Za digitalne ulaznice ili testiranje, uključite optimizaciju

4. **Veličina fonta:**
   - Za manje ulaznice koristite font 16-20
   - Za veće ulaznice koristite font 24-36

---

## Rješavanje problema

| Problem | Rješenje |
|---------|----------|
| Drag & Drop ne radi | Koristite dugme za odabir fajla |
| CSV se ne učitava | Provjerite da li ima kolone `ticketId`, `QR Code`, `categoryKey` |
| PDF je prevelik | Uključite opciju "Optimizuj PDF" |
| Font je premali/prevelik | Podesite "Font veličina" u podešavanjima |
| QR kod je na pogrešnom mjestu | Podesite X i Y poziciju, koristite Preview |

---

## Tehnički zahtjevi

- Python 3.8+
- Biblioteke:
  - `tkinter` (ugrađeno)
  - `tkinterdnd2` (za drag & drop)
  - `Pillow` (obrada slika)
  - `reportlab` (generisanje PDF-a)
  - `qrcode` (generisanje QR kodova)

### Instalacija biblioteka:
```bash
pip install tkinterdnd2 Pillow reportlab qrcode
```

---

*Verzija 1.0 - Februar 2026*
