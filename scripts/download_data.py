"""Download only the CSV and public metadata from the selected Kaggle dataset."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATASET = 'faviovaz/marketing-ab-testing'
PAGE = 'https://www.kaggle.com/datasets/' + DATASET


def main():
    folder = ROOT / 'data' / 'raw'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'marketing_AB.csv'
    metadata_url = 'https://www.kaggle.com/api/v1/datasets/metadata/' + DATASET
    try:
        with urllib.request.urlopen(metadata_url, timeout=60) as response:
            metadata = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        metadata = {'title': 'Marketing A/B Testing', 'description': None,
                    'metadata_note': 'Kaggle metadata endpoint returned 404; inspect dataset page for provenance and terms.'}
    # Save description and license, without account/telemetry fields.
    public = {k: metadata.get(k) for k in ('title', 'subtitle', 'description', 'licenseName', 'licenses', 'lastUpdated', 'currentVersionNumber','metadata_note')}
    (ROOT / 'data' / 'kaggle-metadata.json').write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding='utf-8')
    actual_url = PAGE
    if not path.exists():
        url = 'https://www.kaggle.com/api/v1/datasets/download/' + DATASET
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                archive = response.read()
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                files = [n for n in z.namelist() if Path(n).name == 'marketing_AB.csv']
                if len(files) != 1:
                    raise RuntimeError(f'Expected marketing_AB.csv; found {z.namelist()}')
                path.write_bytes(z.read(files[0]))
            actual_url = url
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            actual_url = 'https://psantanna.com/Econ520/files/marketing_AB.csv'
            with urllib.request.urlopen(actual_url, timeout=90) as response:
                contents = response.read()
            if b'user id' not in contents[:300]:
                raise RuntimeError('Mirror did not return the expected CSV header')
            path.write_bytes(contents)
    elif (ROOT / 'data' / 'source.json').exists():
        actual_url = json.loads((ROOT / 'data' / 'source.json').read_text(encoding='utf-8')).get('download_url', PAGE)
    manifest = {'dataset': DATASET, 'source_url': PAGE, 'file': 'marketing_AB.csv',
                'download_url': actual_url, 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT / 'data' / 'source.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print('Title:', public['title'], 'License:', public.get('licenseName') or public.get('licenses'))


if __name__ == '__main__':
    main()
