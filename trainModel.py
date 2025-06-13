import json
import torch
from sentence_transformers import SentenceTransformer

# Path to your dataset
DATA_PATH = "output.json"
EMBEDDINGS_PATH = "trained_embeddings.pt"
TEXTS_PATH = "trained_texts.json"

# Load product data
with open(DATA_PATH, "r", encoding="utf-8") as f:
    products = json.load(f)

if isinstance(products, dict):
    products = [products]

# Convert products to searchable text
def make_text(product):
    fields = [
        "Product Name", "Web/App Product_Name", "AppCategoryMain",
        "AppSubcategory", "विवरण", "उपयोग", "ब्रांड", "प्रकार",
        "फार्मुलेशन", "घटक", "उपयोगिता", "कारण उपयोग का"
    ]
    return " | ".join(str(product.get(field, "")) for field in fields)

product_texts = [make_text(p) for p in products]

# Load multilingual sentence transformer
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Encode all product texts
embeddings = model.encode(product_texts, convert_to_tensor=True)

# Save embeddings and raw text for inference
torch.save(embeddings, EMBEDDINGS_PATH)

with open(TEXTS_PATH, "w", encoding="utf-8") as f:
    json.dump(product_texts, f, ensure_ascii=False, indent=2)

print("✅ Training complete. Embeddings and texts saved.")
