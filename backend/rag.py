import os
import glob
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle

# Model for embeddings (lightweight, runs locally)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def get_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def chunk_text(text, source_doc):
    """
    Split text into simple overlapping chunks.
    Chunking strategy: Fixed-size character chunks with overlap.
    We use character chunking as it is simple, deterministic, and preserves
    enough context per chunk (1000 chars ~ 200-250 words) for a RAG system
    without being too large or using external libraries.
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + CHUNK_SIZE
        chunk_str = text[start:end]
        chunks.append({
            "text": chunk_str,
            "source": source_doc
        })
        start += (CHUNK_SIZE - CHUNK_OVERLAP)
        
    return chunks

def build_index(docs_dir="../docs", index_path="faiss_index.bin", metadata_path="metadata.pkl"):
    """
    Processes all PDFs in doc_dir, chunks them, computes embeddings, 
    and saves the FAISS index + chunk metadata.
    """
    print(f"Scanning for PDFs in {docs_dir}...")
    pdf_files = glob.glob(os.path.join(docs_dir, "*.pdf"))
    
    all_chunks = []
    
    for pdf in pdf_files:
        print(f"Processing {pdf}...")
        text = get_text_from_pdf(pdf)
        filename = os.path.basename(pdf)
        doc_chunks = chunk_text(text, filename)
        all_chunks.extend(doc_chunks)

    print(f"Extracted a total of {len(all_chunks)} chunks. Building embeddings...")
    texts = [c["text"] for c in all_chunks]
    
    # Generate embeddings
    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")
    
    # Initialize FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    
    # Save the index and metadata
    faiss.write_index(index, index_path)
    with open(metadata_path, 'wb') as f:
        pickle.dump(all_chunks, f)
        
    print("Index and metadata saved successfully.")

def load_index(index_path="faiss_index.bin", metadata_path="metadata.pkl"):
    index = faiss.read_index(index_path)
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata

def retrieve(query, index, metadata, top_k=5):
    """
    Given a query, returns the top_k most relevant chunks.
    """
    query_vector = embedding_model.encode([query]).astype("float32")
    distances, indices = index.search(query_vector, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:  # -1 means not found
            chunk = metadata[idx]
            results.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "distance": float(distances[0][i])
            })
    return results

if __name__ == "__main__":
    # If run directly as a script, build the index.
    build_index()
