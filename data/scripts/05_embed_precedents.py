"""
Generates text-embedding-004 embeddings for all precedents and updates MongoDB.
Run AFTER 04_seed_mongo.py.

Prerequisites:
  - MONGODB_URI, GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS in .env
  - Precedents collection already seeded

Run: python data/scripts/05_embed_precedents.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import vertexai
from vertexai.language_models import TextEmbeddingModel
from pymongo import MongoClient

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB = os.environ.get("MONGODB_DB", "root_trees")
GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if not all([MONGODB_URI, GCP_PROJECT]):
    sys.exit("ERROR: Set MONGODB_URI and GOOGLE_CLOUD_PROJECT in .env")


def main():
    vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")

    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    precedents = list(db.precedents.find({"embedding": {"$exists": False}}))
    print(f"Found {len(precedents)} precedents needing embeddings...")

    for prec in precedents:
        text = f"{prec.get('title', '')}. {prec.get('comment_text', '')}"
        embedding = model.get_embeddings([text[:8000]])[0].values  # 8k char limit
        db.precedents.update_one(
            {"_id": prec["_id"]},
            {"$set": {"embedding": list(embedding)}}
        )
        print(f"  Embedded: {prec.get('title', prec['_id'])}")

    print(f"\nDone. {len(precedents)} precedents embedded.")
    print(
        "\nACTION REQUIRED: Create Atlas Vector Search index via Atlas UI:\n"
        "  Collection: precedents\n"
        "  Index name: precedents_vector_index\n"
        "  Field: embedding\n"
        "  Dimensions: 768\n"
        "  Similarity: cosine"
    )


if __name__ == "__main__":
    main()
