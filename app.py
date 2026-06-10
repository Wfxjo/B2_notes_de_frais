import os
import uuid
import html as html_module

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from backend import ExpenseAgent
from sheets import GoogleSheetsClient

load_dotenv()

app = FastAPI()
agent = ExpenseAgent()
sheets_client = GoogleSheetsClient()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024

# Temporary in-memory store: image_id -> (image_bytes, media_type)
image_store: dict = {}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return HTMLResponse(
        content=f"<p> Unexpected error: {str(exc)}</p>",
        status_code=500
    )


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return HTMLResponse(
        content=f"<p> {exc.detail}</p>",
        status_code=exc.status_code
    )


def validate_image(file: UploadFile, content: bytes) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB).")


def build_option(value: str, selected_value: str) -> str:
    selected = "selected" if selected_value == value else ""
    return f'<option {selected}>{value}</option>'


def build_expense_form(expense_data: dict, image_id: str) -> str:
    type_options = "".join(
        build_option(value, expense_data.get("type_document", ""))
        for value in ["restaurant", "transport", "hotel", "autre"]
    )
    return f"""
    <form hx-post="/api/submit" hx-target="#confirmation-container"
          hx-encoding="application/x-www-form-urlencoded">
        <input type="hidden" name="image_id" value="{image_id}" />
        <label>Type</label>
        <select name="type_document">{type_options}</select>
        <label>Supplier</label>
        <input type="text" name="fournisseur"
               value="{html_module.escape(expense_data.get('fournisseur') or '')}" />
        <label>Date</label>
        <input type="text" name="date" value="{expense_data.get('date') or ''}" />
        <label>Total amount (€)</label>
        <input type="number" step="0.01" name="montant_ttc"
               value="{expense_data.get('montant_ttc') or ''}" />
        <label>VAT (€)</label>
        <input type="number" step="0.01" name="tva"
               value="{expense_data.get('tva') or ''}" />
        <label>Currency</label>
        <input type="text" name="devise"
               value="{expense_data.get('devise') or 'EUR'}" />
        <label>Description</label>
        <input type="text" name="description"
               value="{html_module.escape(expense_data.get('description') or '')}" />
        <label>Confidence</label>
        <input type="text" name="confiance"
               value="{expense_data.get('confiance') or ''}" readonly />
        <button type="submit">Send to Google Sheet</button>
    </form>
    """


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join("static", "index.html"), "r", encoding="utf-8") as html_file:
        return html_file.read()


@app.post("/api/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    validate_image(file, content)
    expense_data = agent.extract_from_bytes(content, file.content_type)
    image_id = str(uuid.uuid4())
    image_store[image_id] = (content, file.content_type)
    return build_expense_form(expense_data, image_id)


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
    image_entry = image_store.pop(image_id, None)
    if image_entry:
        image_bytes, media_type = image_entry
        try:
            image_url = sheets_client.upload_image(image_bytes, media_type)
        except Exception as upload_error:
            print(f"Image upload failed: {upload_error}")
            image_url = None
    else:
        image_url = None

    expense_data = {
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
        sheets_client.append_expense(expense_data, image_url)
        return "<p>✅ Expense successfully sent to Google Sheet.</p>"
    except Exception as sheets_error:
        return f"<p> Error: {str(sheets_error)}</p>"


app.mount("/static", StaticFiles(directory="static"), name="static")