"""Prepare a local marketing_AB.csv and record its checksum; no network access."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import load_data


def prepare(source=None):
    destination = ROOT / 'data/raw/marketing_AB.csv'
    source = Path(source).expanduser().resolve() if source else destination
    if not source.is_file():
        raise FileNotFoundError('Укажите исходный CSV: python scripts/download_data.py --csv "путь/к/marketing_AB.csv"')
    frame, metadata = load_data(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    if checksum != metadata['source_sha256']:
        raise RuntimeError('Файл изменился во время подготовки; повторите операцию')
    manifest = {'dataset':'faviovaz/marketing-ab-testing',
                'source_url':'https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing',
                'file':'marketing_AB.csv', 'input_method':'user-provided local CSV',
                'bytes':destination.stat().st_size, 'sha256':checksum,
                'validated_rows':len(frame)}
    (ROOT/'data/source.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,help='Path to the original marketing_AB.csv')
    args = parser.parse_args()
    prepare(args.csv)
