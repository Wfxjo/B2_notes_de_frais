import os
import io
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_NAME = "Notes de frais"

HEADERS = [
    "Horodatage", "Type", "Fournisseur", "Date",
    "Montant TTC (€)", "TVA (€)", "Devise",
    "Description", "Confiance", "Image"
]

EXPENSE_FIELDS = [
    "type_document", "fournisseur", "date",
    "montant_ttc", "tva", "devise", "description", "confiance"
]


def get_credentials() -> Credentials:
    json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    return Credentials.from_service_account_file(json_path, scopes=SCOPES)


class GoogleSheetsClient:
    def __init__(self):
        self.creds = get_credentials()
        self.client = gspread.authorize(self.creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.sheet = self.client.open_by_key(sheet_id).worksheet(SHEET_NAME)
        self.drive = build("drive", "v3", credentials=self.creds)

    def _upload_to_drive(self, image_bytes: bytes, media_type: str) -> str:
        filename = f"expense_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=media_type)
        file = self.drive.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id"
        ).execute()
        return file.get("id")

    def _make_public(self, file_id: str) -> None:
        self.drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"}
        ).execute()

    def upload_image(self, image_bytes: bytes, media_type: str) -> str:
        file_id = self._upload_to_drive(image_bytes, media_type)
        self._make_public(file_id)
        return f"https://drive.google.com/uc?id={file_id}"

    def append_expense(self, data: dict, image_url: str = None) -> None:
        row = (
            [datetime.now().strftime("%d/%m/%Y %H:%M:%S")]
            + [data.get(field) for field in EXPENSE_FIELDS]
            + [f'=IMAGE("{image_url}")' if image_url else ""]
        )
        self.sheet.append_row(row)


if __name__ == "__main__":
    client = GoogleSheetsClient()
    test_data = {
        "type_document": "restaurant",
        "fournisseur": "Test Bistrot",
        "date": "08/06/2026",
        "montant_ttc": 25.50,
        "tva": 2.55,
        "devise": "EUR",
        "description": "Déjeuner client",
        "confiance": "haute"
    }
    client.append_expense(test_data, None)
    print("Ligne ajoutée avec succès.")