import os
import base64
import uuid
import html as html_lib

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from backend import ExpenseAgent
from sheets import GoogleSheetsClient

load_dotenv()

app = FastAPI()
agent = ExpenseAgent()
sheets_client = GoogleSheetsClient()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024

# Stockage temporaire en mémoire : id -> (bytes, media_type)
_image_store: dict = {}


def validate_image(file: UploadFile, content: bytes) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Type de fichier non supporté.")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Image trop lourde (max 10 Mo).")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join("static", "index.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    validate_image(file, content)
    data = agent.extract_from_bytes(content, file.content_type)

    image_id = str(uuid.uuid4())
    _image_store[image_id] = (content, file.content_type)

    return f"""
    <form hx-post="/api/submit" hx-target="#confirmation-container"
          hx-encoding="application/x-www-form-urlencoded">
        <input type="hidden" name="image_id" value="{image_id}" />
        <label>Type</label>
        <select name="type_document">
            <option {"selected" if data.get("type_document") == "restaurant" else ""}>restaurant</option>
            <option {"selected" if data.get("type_document") == "transport" else ""}>transport</option>
            <option {"selected" if data.get("type_document") == "hotel" else ""}>hotel</option>
            <option {"selected" if data.get("type_document") == "autre" else ""}>autre</option>
        </select>
        <label>Fournisseur</label>
        <input type="text" name="fournisseur" value="{html_lib.escape(data.get('fournisseur') or '')}" />
        <label>Date</label>
        <input type="text" name="date" value="{data.get('date') or ''}" />
        <label>Montant TTC (€)</label>
        <input type="number" step="0.01" name="montant_ttc" value="{data.get('montant_ttc') or ''}" />
        <label>TVA (€)</label>
        <input type="number" step="0.01" name="tva" value="{data.get('tva') or ''}" />
        <label>Devise</label>
        <input type="text" name="devise" value="{data.get('devise') or 'EUR'}" />
        <label>Description</label>
        <input type="text" name="description" value="{html_lib.escape(data.get('description') or '')}" />
        <label>Confiance</label>
        <input type="text" name="confiance" value="{data.get('confiance') or ''}" readonly />
        <button type="submit">Envoyer vers le Google Sheet</button>
    </form>
    """


@app.post("/api/submit", response_class=HTMLResponse)
async def submit(
    image_id: str = Form(...),
    type_document: str = Form(None),
    fournisseur: str = Form(None),
    date: str = Form(None),
    montant_ttc: float = Form(None),
    tva: float = Form(None),
    devise: str = Form(None),
    description: str = Form(None),
    confiance: str = Form(None)
):
    image_entry = _image_store.pop(image_id, None)
    print(f"image_entry found: {image_entry is not None}")
    if image_entry:
        image_bytes, media_type = image_entry
        try:
            image_url = sheets_client.upload_image(image_bytes, media_type)
            print(f"image_url: {image_url}")
        except Exception as e:
            print(f"Upload error: {e}")
            image_url = None
    else:
        image_url = None

    data = {
        "type_document": type_document,
        "fournisseur": fournisseur,
        "date": date,
        "montant_ttc": montant_ttc,
        "tva": tva,
        "devise": devise,
        "description": description,
        "confiance": confiance
    }

    try:
        sheets_client.append_expense(data, image_url)
        return "<p>✅ Note de frais envoyée avec succès.</p>"
    except Exception as e:
        return f"<p>❌ Erreur : {str(e)}</p>"


app.mount("/static", StaticFiles(directory="static"), name="static")