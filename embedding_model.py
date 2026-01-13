""" Hugging Face """
import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn as nn

""" Load the model and Save the Embeddings"""

tokenizer_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
model_name = tokenizer_name

#Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
tokenizer.add_special_tokens({'pad_token': '[PAD]'})

#Load the pre-trained model (Token embedding layer, transformer layer, not language modeling head)
model = AutoModel.from_pretrained(model_name)
model.resize_token_embeddings(len(tokenizer))

#Extract the embeddings layer (the matrix that maps token_ids -> vectors)
embeddings = model.get_input_embeddings()

#Print out the embeddings
print(f"Extract Embeddings Layer for {model_name}: {embeddings}")

#Save the embeddings layer to disk (save only the parameters of the embedding layer, stores as dictionary {'weight': tensor([...])}). Tensor is multidimensional array of numbers
torch.save(embeddings.state_dict(), "embeddings_qwen.pth")

""" Load the model embeddings """
class EmbeddingModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim):
        super(EmbeddingModel, self).__init__()

        # Learnable embedding matrix
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embedding_dim)

    # Look up embedding for input token ids
    def forward(self, input_ids):
        return self.embedding(input_ids)
    
vocab_size = 151936
dimensions = 1536
embedding_filename = r"embeddings_qwen.pth"

#Initialise the custom embedding model
models = EmbeddingModel(vocab_size=vocab_size, embedding_dim=dimensions)

# Load the saved embeddings from the file
saved_embeddings = torch.load(embedding_filename)

# Ensure the 'weight' key exists in the saved embeddings dictionary
if 'weight' not in saved_embeddings:
    raise KeyError("The saved embeddings file does not contain 'weight' key.")

embeddings_tensor = saved_embeddings['weight']

# Check if the dimensions match
if embeddings_tensor.size() != (vocab_size, dimensions):
    raise ValueError(f"The dimensions of the loaded embeddings do not match the model epcted dimensions ({vocab_size}, {dimensions})")

# Assign the extracted embeddings tensor to the model's embedding layer
models.embedding.weight.data = embeddings_tensor

#Put the model in eval mode
models.eval()


""" Convert Prompt to Embeddings """
def find_similar_embeddings(target_embedding, n=10):

    """
    Find the n most similar embeddings to the target embedding using cosine similarity
    Args:
        target_embedding: The embedding vector to compare against
        n: Number of similar embeddings to return (default 3)
    Returns:
        List of tuples containing (word, similarity_score) sorted by similarity
    """

    # Convert target to tensor if not already
    if not isinstance(target_embedding, torch.Tensor):
        target_embedding = torch.tensor(target_embedding)

    # Get all embeddings from the model
    all_embeddings = models.embedding.weight

    # Compute cosine similarity between target and all embeddings
    similarities = torch.nn.functional.cosine_similarity(
        target_embedding.unsqueeze(0),
        all_embeddings
    )

    # Get top n similar embeddings
    top_n_similarities, top_n_indices = torch.topk(similarities, n)

    # Convert to word-similarity pairs
    results = []
    for idex, score in zip(top_n_indices, top_n_similarities):
        word = tokenizer.decode(idex)
        results.append((word, score.items()))

    return results

def prompt_to_embeddings(prompt):
    # tokenize the input text
    tokens = tokenizer(prompt, return_tensors="pt")
    input_ids = tokens['input_ids']

    # Make a forward pass
    outputs = models(input_ids)

    # directly use the embeddings layer to get embeddings for the input_ids
    embeddings = outputs

    # print each token
    token_id_list = tokenizer.encode(prompt, add_special_tokens=True)
    for token_id in token_id_list:
        token_str = tokenizer.decode(token_id, skip_special_tokens=True)

    return token_id_list, embeddings, token_str


""" Find Similar Embeddings """
token_id_list, prompt_embeddings, prompt_token_str = prompt_to_embeddings("USA and China are the most prominent countries in AI.")

tokens_and_neighbors = {}
for i in range(1, len(prompt_embeddings[0])):
    token_results = find_similar_embeddings(prompt_embeddings[0][i], n=6)
    similar_embs = []
    for word, score in token_results:
        similar_embs.append(word.replace(" ", "#"))
    tokens_and_neighbors[prompt_token_str[i]] = similar_embs

all_token_embeddings = {}

# Process each token and its neighbors
for token, neighbors in tokens_and_neighbors.items():
    # Get embedding for the original token
    token_id, token_emb, _ = prompt_to_embeddings(token)
    all_token_embeddings[token] = token_emb[0][1]
    
    # Get embeddings for each neighbor token
    for neighbor in neighbors:
        # Replace # with space
        neighbor = neighbor.replace("#", " ")
        # Get embedding
        neighbor_id, neighbor_emb, _ = prompt_to_embeddings(neighbor)
        all_token_embeddings[neighbor] = neighbor_emb[0][1]