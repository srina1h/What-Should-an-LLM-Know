"""Check the pinned HKMA embedding model, or explicitly download it once."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Download pinned weights to the Hugging Face cache')
    args=parser.parse_args()
    config=json.loads((Path(__file__).resolve().parent/'manifest.json').read_text())['embedding']
    from transformers import AutoModel, AutoTokenizer
    options=dict(revision=config['revision'],local_files_only=not args.download)
    AutoTokenizer.from_pretrained(config['model'],**options)
    AutoModel.from_pretrained(config['model'],**options)
    print(f"Pinned retrieval model available locally: {config['model']} @ {config['revision']}")


if __name__=='__main__':
    main()
