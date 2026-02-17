# Learning_Ai
Leaning ai

## RAG Pipeline
1. Ingestion
2. Preprocessing
3. Chunking
4. Embedding
5. Vector Store
6. Retriever
7. Generator
8. Evaluation

# Install package
pip install -r requirements.txt

# Install Ollama
https://ollama.com/download -> install ollama on local machine (computer)

## command
ollama list -> show model
ollama pull <model> -> load model
ollama run <model> -> run model
ollama rm <model> -> remove model

## load model
ollama run qwen3:4b
ollama run typhoon-ocr1.5-3b:latest
ollama run bge-m3:latest