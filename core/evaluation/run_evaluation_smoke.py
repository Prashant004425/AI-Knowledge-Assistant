from core.evaluation.evaluate import log_query, load_logs, evaluate_recall, plot_usage

log_query('What is FloCard?', 120.5, [{'id': 'chunk_001', 'source': 'guide.md', 'similarity': 0.96}])
logs = load_logs()
print('logs count:', len(logs))
result = evaluate_recall(logs, {'What is FloCard?': ['chunk_001']}, k=1)
print('recall', result['average_recall_at_k'], 'accuracy', result['accuracy_at_k'])
print('usage plot file:', plot_usage(logs))
