import chromadb

client = chromadb.PersistentClient(path="data/vectorstore")

collection = client.get_collection("knowledge_base")

print("Documents in DB:", collection.count())