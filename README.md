# Notes de Frais — Application Agentique

Cette app web permet à un salarié de photographier une note de frais,
d'en extraire automatiquement les informations comptables via un modèle de vision IA,
de les corriger manuellement, puis de les synchroniser dans un Google Sheet partagé.

## Structure du projet

expense-tracker/
├── backend.py        # Classe ExpenseAgent — logique IA
├── app.py            # Serveur FastAPI — routes et orchestration
├── sheets.py         # Classe GoogleSheetsClient — intégration Google Sheets
├── context.txt       # Prompt système du modèle
├── prompt.txt        # Prompt utilisateur envoyé avec l'image
├── requirements.txt
├── .env.example
└── static/
├── index.html    # Interface HTMX
├── style.css     # Feuille de style
└── app.js        # JS Vanilla

## Configuration Google Cloud

1. Créez un projet sur [Google Cloud Console](https://console.cloud.google.com)
2. Activez **Google Sheets API** et **Google Drive API**
3. Créez un compte de service et téléchargez la clé JSON
4. Partagez votre Google Sheet et votre dossier Drive avec l'email du compte de service (rôle Éditeur)

## Lancement de l'application

```bash
uvicorn app:app --reload
```

Ouvrez [http://localhost:8000](http://localhost:8000)

## Exemple de réponse JSON du modèle

```json
{
  "type_document": "restaurant",
  "fournisseur": "Carrefour",
  "date": "08/01/2021",
  "montant_ttc": 53.03,
  "tva": 8.84,
  "devise": "EUR",
  "description": "Courses professionnelles",
  "confiance": "moyen"
}
```