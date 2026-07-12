"""
Download the exercise corpus (~570 Harel insurance documents, 12 domains) into
./corpus. This is the frozen snapshot your answers are graded against — do NOT
re-scrape the live site; it has drifted and will keep drifting.

    pip install huggingface_hub
    python get_corpus.py

Layout after download:
    corpus/<domain>/files/*.pdf    policy documents (page numbers matter!)
    corpus/<domain>/pages/*.txt    scraped web pages
    corpus/manifest.json           local path -> original source URL
"""
from huggingface_hub import snapshot_download

path = snapshot_download(
    "orik/apex-ex2-harel-corpus",
    repo_type="dataset",
    local_dir="corpus",
)
print(f"corpus ready at: {path}")
