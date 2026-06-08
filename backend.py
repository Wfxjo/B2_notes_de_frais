import os
import base64
import json

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

EXPECTED_FIELDS = [
    "type_document", "fournisseur", "date", "montant_ttc",
    "tva", "devise", "description", "confiance"
]


def load_file(filename: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, filename), "r") as f:
        return f.read()


class ExpenseAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.system_prompt = load_file("context.txt")
        self.user_prompt = load_file("prompt.txt")

    def _build_messages(self, image_b64: str, media_type: str) -> list:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": self.user_prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:{media_type};base64,{image_b64}"
                }}
            ]}
        ]

    def extract_from_bytes(self, image_bytes: bytes, media_type: str) -> dict:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=self._build_messages(image_b64, media_type)
        )
        result = json.loads(response.choices[0].message.content)
        return {field: result.get(field) for field in EXPECTED_FIELDS}


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"
    with open(path, "rb") as f:
        data = f.read()

    agent = ExpenseAgent()
    print(json.dumps(
        agent.extract_from_bytes(data, "image/jpeg"),
        indent=2,
        ensure_ascii=False
    ))