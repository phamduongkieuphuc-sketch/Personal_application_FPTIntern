import os
import requests
from dotenv import load_dotenv
import torch
import torch.nn.functional as F

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")

API_URL = "https://mkp-api.fptcloud.com/v1/embeddings"
MODEL_NAME = "multilingual-e5-large"

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
}

# Get the embeddings fromm FPT model
def get_embeddings(texts, dimensions=1024):
    """
    texts: list[str]
    returns" torch.Tensor [len(texts), dimensions]
    """
    payload = {
        "model": MODEL_NAME,
        "input": texts,
        "dimensions": dimensions,
        "encoding_format": "float",
        "input_text_truncate": "none",
        "input_type": "passage",
    }

    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
    )

    response.raise_for_status()

    data = response.json()["data"]

    embeddings = [item["embedding"] for item in data]

    return torch.Tensor(embeddings)

def prompt_to_embeddings(prompt: str, input_type: str = "passage"):
    """
    Convert text prompt into a single embedding vector
    """
    embeddings = get_embeddings([input_type + f": " + prompt])

    return embeddings[0]  # shape: [1024]

def cosine_similarity(a, b):
    return F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item()


def find_similar_texts(query, candidates, top_k=None):
    """
    query: str
    candidates: list[str]
    """
    if top_k is None:
        top_k = len(candidates)

    query_emb = prompt_to_embeddings(query, "query")
    candidate_embs = get_embeddings([f"query: {c}" for c in candidates])


        

    scores = F.cosine_similarity(
        query_emb.unsqueeze(0),
        candidate_embs
    )

    top_scores, top_indices = torch.topk(scores, top_k)

    results = []
    for idx, score in zip(top_indices, top_scores):
        results.append((candidates[idx], score.item()))

    return results


if __name__ == "__main__":
    # Prompt user for input
   '''user_text = input("Enter text to embed: ")

    # Generate embedding
   embedding = prompt_to_embeddings(user_text)

    # Print embedding info
   print("\nEmbedding generated successfully!")
   print("Embedding shape:", embedding.shape)
   with open("embedding.txt", "w") as f:
        f.write(str(embedding.tolist()))'''

   print(" -----The section below is for find similarities between embeddings----- ")
   
   query = "Con Voi"
   candidates = [
        "Elephant",
        "Car",
        "Thailand"
    ]
   
   embedding = prompt_to_embeddings(query, "query")
   print("First 8 embedding values:", embedding[:8])

   print("\nCandidates:")
   for idx, candidate in enumerate(candidates):
        cand_embed = prompt_to_embeddings(candidate, "passage")
        print(f"  [{idx}] {candidate}")
        print("      First 8 embedding values:", cand_embed[:8])

   
   results = find_similar_texts(query, candidates)
   
   for text, score in results:
        print(text, score)


