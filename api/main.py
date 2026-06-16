import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKey, APIKeyHeader
from pydantic import BaseModel

from core.rag.generate import generate_answer
from core.retriever import retrieve as semantic_search
from core.ingest import ingest_directory
from core.embed import main as embed_pipeline
from core.export import (
    export_chunks_to_docx,
    export_chunks_to_excel,
    export_qa_to_docx,
    export_qa_to_excel,
    load_chunks,
)
from core.logger import log_query
from core.profile import change_password, get_profile, logout_profile, update_profile
from core.security import redact_sensitive, verify_api_key

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Knowledge Assistant API",
    description="RAG-powered API for semantic search and answer generation",
    version="1.0.0",
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables and security settings
BASE_DIR = Path.cwd()
load_dotenv(BASE_DIR / ".env")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
AUTHORIZATION_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


def get_api_key(
    api_key: str = Security(API_KEY_HEADER),
    authorization: str = Security(AUTHORIZATION_HEADER),
) -> APIKey:
    if api_key and verify_api_key(api_key):
        return api_key
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and verify_api_key(token):
            return token
    raise HTTPException(status_code=401, detail="Unauthorized")


# Global state for metrics
metrics = {
    "total_questions": 0,
    "total_searches": 0,
    "total_reindexes": 0,
    "api_start_time": datetime.now().isoformat(),
}

RAW_DIR = Path.cwd() / "data" / "raw"


# ============================================================================
# Pydantic Models
# ============================================================================

class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str
    n_results: int = 5


class SearchResult(BaseModel):
    """Single search result."""
    id: str
    text: str
    source: str
    similarity: float


class SearchResponse(BaseModel):
    """Response model for semantic search."""
    query: str
    num_results: int
    results: list[SearchResult]


class AskRequest(BaseModel):
    """Request model for RAG question answering."""
    question: str
    n_retrieve: int = 3
    model: str = "llama3.1"
    temperature: float = 0.3


class Citation(BaseModel):
    """Citation metadata."""
    source: str
    relevance: float


class AskResponse(BaseModel):
    """Response model for RAG pipeline."""
    query: str
    answer: str
    sources: list[Citation]
    chunks_used: int
    chunks_requested: int
    truncation_used: bool = False
    fallback_used: bool = False
    model: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    api_start_time: str


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_questions: int
    total_searches: int
    total_reindexes: int
    api_start_time: str


class ReindexResponse(BaseModel):
    """Reindex operation response."""
    status: str
    chunks_ingested: int
    chunks_embedded: int
    timestamp: str


class ExportResponse(BaseModel):
    """File export response."""
    status: str
    docx_path: str
    xlsx_path: str
    timestamp: str


class QAExportRow(BaseModel):
    question: str
    answer: str
    source: Optional[str] = None


class QAExportRequest(BaseModel):
    rows: List[QAExportRow]


class UploadResponse(BaseModel):
    """File upload and ingestion response."""
    status: str
    uploaded_files: int
    chunks_ingested: int
    chunks_embedded: int
    timestamp: str


class ProfileResponse(BaseModel):
    """Profile information response."""
    avatar_url: str
    name: str
    employee_id: str
    department: str
    email: str
    role: str
    joining_date: str
    about_me: str


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    avatar_url: Optional[str] = None
    name: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    joining_date: Optional[str] = None
    about_me: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str
    confirm_password: str


class ActionResponse(BaseModel):
    """Generic action response for simple operations."""
    status: str
    message: str


# ============================================================================
# Health & Metrics Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint.
    
    Returns status of API and dependencies.
    """
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "version": "1.0.0",
        "api_start_time": metrics["api_start_time"],
    }


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    """
    Get API metrics and statistics.
    
    Returns counts of operations and uptime.
    """
    logger.info("Metrics requested")
    return {
        "total_questions": metrics["total_questions"],
        "total_searches": metrics["total_searches"],
        "total_reindexes": metrics["total_reindexes"],
        "api_start_time": metrics["api_start_time"],
    }


# ============================================================================
# Search Endpoint
# ============================================================================

@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, api_key: APIKey = Depends(get_api_key)):
    """
    Semantic search endpoint.
    
    Retrieves relevant chunks from the knowledge base using semantic similarity.
    
    Args:
        request: SearchRequest with query and n_results
    
    Returns:
        SearchResponse with ranked results
    
    Example:
        POST /search
        {
            "query": "What is FloCard?",
            "n_results": 5
        }
    """
    logger.info("Search request: %s", request.query)
    
    try:
        start_time = time.perf_counter()
        results = semantic_search(
            query=request.query,
            n_results=request.n_results,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Update metrics
        metrics["total_searches"] += 1
        log_query(request.query, latency_ms, results["results"])
        
        # Convert results to response model and redact any sensitive data
        formatted_results = [
            SearchResult(
                id=r["id"],
                text=redact_sensitive(r["text"]),
                source=r["source"],
                similarity=r["similarity"],
            )
            for r in results["results"]
        ]
        
        logger.info("Search complete: %d results", len(formatted_results))
        
        return SearchResponse(
            query=results["query"],
            num_results=len(formatted_results),
            results=formatted_results,
        )
        
    except Exception as exc:
        logger.error("Search error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(exc)}"
        )


# ============================================================================
# RAG Pipeline Endpoint
# ============================================================================

@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest, api_key: APIKey = Depends(get_api_key)):
    """
    RAG pipeline endpoint.
    
    Retrieves relevant chunks and generates an answer using local LLM.
    
    Args:
        request: AskRequest with question and parameters
    
    Returns:
        AskResponse with generated answer and citations
    
    Example:
        POST /ask
        {
            "question": "What is FloCard?",
            "n_retrieve": 5,
            "model": "llama3.1",
            "temperature": 0.3
        }
    """
    logger.info("Question received: %s", request.question)
    
    try:
        # Check if Ollama is available
        import requests
        try:
            requests.get("http://localhost:11434/api/tags", timeout=2)
        except requests.exceptions.ConnectionError:
            logger.error("Ollama not running")
            raise HTTPException(
                status_code=503,
                detail=(
                    "LLM service (Ollama) is not running. "
                    "Start it with: ollama serve"
                )
            )
        
        # Generate answer using RAG pipeline
        start_time = time.perf_counter()
        result = generate_answer(
            question=request.question,
            model=request.model,
            n_retrieve=request.n_retrieve,
            temperature=request.temperature,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        if not result:
            logger.error("RAG pipeline failed")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate answer"
            )
        
        # Update metrics and log query evaluation data
        metrics["total_questions"] += 1
        log_query(request.question, latency_ms, result.get("retrieved_chunks", []))
        
        # Convert sources to Citation model
        citations = [
            Citation(
                source=s["source"],
                relevance=s["relevance"],
            )
            for s in result["sources"]
        ]

        redacted_answer = redact_sensitive(result["answer"])
        
        logger.info("Answer generated for question: %s", request.question)
        
        return AskResponse(
            query=result["query"],
            answer=redacted_answer,
            sources=citations,
            chunks_used=result["chunks_used"],
            chunks_requested=result.get("chunks_requested", request.n_retrieve),
            truncation_used=result.get("truncation_used", False),
            fallback_used=result.get("fallback_used", False),
            model=result["model"],
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("RAG pipeline error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Answer generation failed: {str(exc)}"
        )


# ============================================================================
# Upload Endpoint
# ============================================================================

@app.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...), api_key: APIKey = Depends(get_api_key)):
    """
    Upload files to the raw data directory and rebuild the knowledge base.

    Accepted file types: .md, .pdf, .docx, .csv, .txt, .text
    """
    logger.info("Upload requested for %d file(s)", len(files))

    if not files:
        logger.error("Upload failed: no files provided")
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved_files = 0
    for upload in files:
        destination = RAW_DIR / upload.filename
        try:
            content = await upload.read()
            destination.write_bytes(content)
            saved_files += 1
            logger.info("Saved uploaded file: %s", destination.name)
        except Exception as exc:
            logger.error("Failed to save uploaded file %s: %s", upload.filename, exc)
            raise HTTPException(status_code=500, detail=f"Failed to save {upload.filename}: {str(exc)}")

    try:
        chunks = ingest_directory(RAW_DIR)
        embed_pipeline()
        metrics["total_reindexes"] += 1
        return UploadResponse(
            status="success",
            uploaded_files=saved_files,
            chunks_ingested=len(chunks),
            chunks_embedded=len(chunks),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as exc:
        logger.error("Upload reindex error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}")


# ============================================================================
# Profile Endpoints
# ============================================================================

@app.get("/profile", response_model=ProfileResponse)
def profile_get(api_key: APIKey = Depends(get_api_key)):
    """Fetch the current user's profile details."""
    logger.info("Profile fetch requested")
    return get_profile()


@app.put("/profile", response_model=ProfileResponse)
def profile_update(request: ProfileUpdateRequest, api_key: APIKey = Depends(get_api_key)):
    """Update profile fields like name, email, department, and about_me."""
    logger.info("Profile update requested")
    try:
        updated_profile = update_profile(request.dict(exclude_unset=True))
        return updated_profile
    except ValueError as exc:
        logger.error("Profile update failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Profile update failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(exc)}")


@app.post("/profile/change-password", response_model=ActionResponse)
def profile_change_password(request: ChangePasswordRequest, api_key: APIKey = Depends(get_api_key)):
    """Change the current user's password."""
    logger.info("Profile change password requested")
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match.")
    try:
        change_password(request.current_password, request.new_password)
        return ActionResponse(status="success", message="Password updated successfully.")
    except ValueError as exc:
        logger.error("Change password failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Change password failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(exc)}")


@app.post("/logout", response_model=ActionResponse)
def profile_logout(api_key: APIKey = Depends(get_api_key)):
    """Perform a local logout operation."""
    logger.info("Logout requested")
    logout_profile()
    return ActionResponse(status="success", message="You have been logged out.")


# ============================================================================
# Export Endpoints
# ============================================================================

@app.post("/export/chunks", response_model=ExportResponse)
def export_chunks(api_key: APIKey = Depends(get_api_key)):
    """
    Export all current document chunks to Word and Excel files.
    """
    logger.info("Export chunks requested")
    try:
        chunks = load_chunks()
        if not chunks:
            raise HTTPException(status_code=404, detail="No chunks available to export.")

        docx_path = export_chunks_to_docx(chunks)
        xlsx_path = export_chunks_to_excel(chunks)

        return ExportResponse(
            status="success",
            docx_path=str(docx_path),
            xlsx_path=str(xlsx_path),
            timestamp=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Export chunks failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(exc)}")


@app.post("/export/qa", response_model=ExportResponse)
def export_qa(request: QAExportRequest, api_key: APIKey = Depends(get_api_key)):
    """
    Export question-answer pairs to Word and Excel.
    """
    logger.info("Export QA requested for %d row(s)", len(request.rows))
    try:
        qa_rows = [row.dict() for row in request.rows]
        docx_path = export_qa_to_docx(qa_rows)
        xlsx_path = export_qa_to_excel(qa_rows)

        return ExportResponse(
            status="success",
            docx_path=str(docx_path),
            xlsx_path=str(xlsx_path),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as exc:
        logger.error("Export QA failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(exc)}")


# ============================================================================
# Reindex Endpoint
# ============================================================================

@app.post("/reindex", response_model=ReindexResponse)
def reindex_knowledge_base(api_key: APIKey = Depends(get_api_key)):
    """
    Rebuild vector database.
    
    Re-ingests all raw documents, generates embeddings, and stores in vector DB.
    This is useful after adding new documents to data/raw/.
    
    Returns:
        ReindexResponse with operation status and statistics
    
    Example:
        POST /reindex
    """
    logger.info("Reindex requested")
    
    try:
        # Step 1: Ingest documents
        logger.info("Step 1: Ingesting documents...")
        chunks = ingest_directory()
        logger.info("Ingested %d chunks", len(chunks))
        
        # Step 2: Generate embeddings
        logger.info("Step 2: Generating embeddings...")
        embed_pipeline()
        logger.info("Embeddings generated")
        
        # Update metrics
        metrics["total_reindexes"] += 1
        
        logger.info("Reindex complete")
        
        return ReindexResponse(
            status="success",
            chunks_ingested=len(chunks),
            chunks_embedded=len(chunks),
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as exc:
        logger.error("Reindex error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Reindex failed: {str(exc)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Knowledge Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "metrics": "GET /metrics",
            "search": "POST /search",
            "ask": "POST /ask",
            "upload": "POST /upload",
            "reindex": "POST /reindex",
            "profile": "GET /profile",
            "update_profile": "PUT /profile",
            "change_password": "POST /profile/change-password",
            "logout": "POST /logout",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json",
        },
        "documentation": "Visit http://localhost:8000/docs for interactive API docs",
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    logger.error("ValueError: %s", exc)
    return {
        "detail": f"Invalid input: {str(exc)}",
        "status_code": 400,
    }


@app.exception_handler(FileNotFoundError)
def file_not_found_handler(request, exc):
    """Handle FileNotFoundError exceptions."""
    logger.error("FileNotFoundError: %s", exc)
    return {
        "detail": f"File not found: {str(exc)}",
        "status_code": 404,
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AI Knowledge Assistant API...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
