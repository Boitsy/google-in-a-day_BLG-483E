import os
from core.index import CrawlIndex

def save_index(index: CrawlIndex, path: str = "data/storage/p.data") -> None:
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Write to the file with utf-8 encoding, overwriting each time
    with open(path, 'w', encoding='utf-8') as f:
        # Iterate over all PageRecord entries
        for record in index.get_all_records():
            # For each record, write one line per word in word_freq
            for word, frequency in record.word_freq.items():
                f.write(f"{word}\t{record.url}\t{record.origin_url}\t{record.depth}\t{frequency}\n")
