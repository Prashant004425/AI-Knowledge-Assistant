import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "query_logs.jsonl"
PLOTS_DIR = BASE_DIR / "data" / "reports"


def ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def log_query(query: str, latency_ms: float, retrieved_chunks: list[dict], log_file: Path = LOG_FILE) -> Path:
    ensure_dirs()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query": query,
        "latency_ms": latency_ms,
        "num_results": len(retrieved_chunks),
        "retrieved_chunks": [
            {
                "id": chunk.get("id"),
                "source": chunk.get("source"),
                "similarity": chunk.get("similarity"),
            }
            for chunk in retrieved_chunks
        ],
    }
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return log_file


def load_logs(log_file: Path = LOG_FILE) -> list[dict]:
    if not log_file.exists():
        return []
    entries = []
    with log_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    retrieved_top_k = set(retrieved_ids[:k])
    return len(retrieved_top_k.intersection(relevant_ids)) / len(set(relevant_ids))


def evaluate_recall(logs: list[dict], ground_truth: dict[str, list[str]], k: int = 5) -> dict:
    results = []
    for entry in logs:
        query = entry.get("query")
        relevant = ground_truth.get(query, [])
        retrieved_ids = [chunk.get("id") for chunk in entry.get("retrieved_chunks", []) if chunk.get("id")]
        recall = recall_at_k(retrieved_ids, relevant, k)
        results.append({
            "query": query,
            "recall_at_k": recall,
            "relevant_count": len(relevant),
            "retrieved_count": len(retrieved_ids),
        })
    average_recall = sum(r["recall_at_k"] for r in results) / len(results) if results else 0.0
    accuracy = sum(1 for r in results if r["recall_at_k"] > 0) / len(results) if results else 0.0
    return {
        "results": results,
        "average_recall_at_k": average_recall,
        "accuracy_at_k": accuracy,
        "k": k,
    }


def plot_latency(logs: list[dict], output_file: Path = None) -> Path:
    ensure_dirs()
    if output_file is None:
        output_file = PLOTS_DIR / "latency_plot.png"
    timestamps = [datetime.fromisoformat(entry["timestamp"].replace("Z", "")) for entry in logs]
    latencies = [entry["latency_ms"] for entry in logs]
    if not timestamps:
        raise ValueError("No logs available to plot latency.")
    plt.figure(figsize=(10, 4))
    plt.plot(timestamps, latencies, marker="o", linestyle="-", color="tab:blue")
    plt.title("Query Latency Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Latency (ms)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    return output_file


def plot_recall(evaluation: dict, output_file: Path = None) -> Path:
    ensure_dirs()
    if output_file is None:
        output_file = PLOTS_DIR / "recall_plot.png"
    queries = [entry["query"] for entry in evaluation["results"]]
    recalls = [entry["recall_at_k"] for entry in evaluation["results"]]
    if not queries:
        raise ValueError("No evaluation results available to plot recall.")
    plt.figure(figsize=(10, 4))
    plt.barh(queries, recalls, color="tab:green")
    plt.title(f"Recall@{evaluation['k']} by Query")
    plt.xlabel("Recall")
    plt.xlim(0, 1)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    return output_file


def plot_usage(logs: list[dict], output_file: Path = None) -> Path:
    ensure_dirs()
    if output_file is None:
        output_file = PLOTS_DIR / "usage_plot.png"
    query_counts = Counter(entry["query"] for entry in logs)
    if not query_counts:
        raise ValueError("No logs available to plot usage analytics.")
    keys = list(query_counts.keys())
    values = list(query_counts.values())
    plt.figure(figsize=(10, 4))
    plt.barh(keys, values, color="tab:orange")
    plt.title("Query Frequency")
    plt.xlabel("Number of times queried")
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation reporting and plotting.")
    parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to a ground truth JSON file for recall evaluation",
    )
    parser.add_argument("--k", type=int, default=5, help="Compute Recall@K")
    args = parser.parse_args()

    logs = load_logs()
    print(f"Loaded {len(logs)} query logs.")

    if logs:
        try:
            print(f"Latency plot: {plot_latency(logs)}")
        except Exception as exc:
            print(f"Latency plot failed: {exc}")

        try:
            print(f"Usage plot: {plot_usage(logs)}")
        except Exception as exc:
            print(f"Usage plot failed: {exc}")

        if args.ground_truth:
            ground_truth_path = Path(args.ground_truth)
            if ground_truth_path.exists():
                gt = json.loads(ground_truth_path.read_text(encoding="utf-8"))
                evaluation = evaluate_recall(logs, gt, k=args.k)
                print("Recall evaluation:")
                print(json.dumps(evaluation, indent=2))
                try:
                    print(f"Recall plot: {plot_recall(evaluation)}")
                except Exception as exc:
                    print(f"Recall plot failed: {exc}")
            else:
                print(f"Ground truth file not found: {ground_truth_path}")
        else:
            print("No ground truth provided; recall evaluation skipped.")
    else:
        print("No query logs found. Generate logs before running eval.")
