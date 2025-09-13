from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    local_dir=r"C:\Users\ATHARVA\mistral_models\Llama-3.1-8B-Instruct",
    # allow common tokenizer filenames
    allow_patterns=["tokenizer.model*", "tokenizer.json", "tokenizer_config.json", "vocab.json", "*.bin", "*.json"]
)

print("Done")
