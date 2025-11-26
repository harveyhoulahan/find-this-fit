import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "clip")  # options: openai, clip
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "image-embedding-3-large")
EMBEDDING_DIMENSION = 768
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
