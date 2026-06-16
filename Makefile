run:
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	python -m streamlit run streamlit_app.py

reindex:
	python -c "from core.ingestion.ingest import ingest_directory; from core.embeddings.embed import main as embed_pipeline; ingest_directory(); embed_pipeline()"

eval:
	python -m core.evaluation.evaluate
