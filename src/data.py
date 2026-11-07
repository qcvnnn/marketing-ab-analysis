"""Read and validate the original CSV without silently removing observations."""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/marketing_AB.csv'
RENAME = {'user id':'user_id', 'test group':'test_group', 'converted':'converted',
          'total ads':'total_ads', 'most ads day':'most_ads_day', 'most ads hour':'most_ads_hour'}
DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']


def load_data(path=RAW):
    path=Path(path)
    raw=pd.read_csv(path)
    return validate(raw), {'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'raw_rows':len(raw), 'raw_columns':list(raw.columns),
                          'dropped_columns':[c for c in raw.columns if c not in RENAME]}


def validate(raw):
    missing=set(RENAME)-set(raw.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')
    unknown=set(raw.columns)-set(RENAME)-{'Unnamed: 0'}
    if unknown:
        raise ValueError(f'Unexpected columns: {sorted(unknown)}')
    if 'Unnamed: 0' in raw and raw['Unnamed: 0'].tolist()!=list(range(len(raw))):
        raise ValueError('Unnamed: 0 is not the expected sequential export index')
    frame=raw[list(RENAME)].rename(columns=RENAME).copy()
    if frame.empty or frame.isna().any().any():
        raise ValueError('Empty dataset or missing values; inspect input before analysis')
    converted=frame.converted.astype(str).str.lower().map({'true':True,'false':False,'1':True,'0':False})
    if converted.isna().any():
        raise ValueError('converted must contain boolean values')
    frame['converted']=converted.astype(bool)
    for col in ['user_id','total_ads','most_ads_hour']:
        numbers=pd.to_numeric(frame[col],errors='raise')
        if not numbers.mod(1).eq(0).all():
            raise ValueError(f'{col} must be integral')
        frame[col]=numbers.astype('int64')
    if frame.user_id.duplicated().any():
        raise ValueError('Duplicate user_id; each observation must represent one user')
    if not set(frame.test_group)=={'ad','psa'}:
        raise ValueError('Both ad and psa groups are required; unknown labels are forbidden')
    if not frame.user_id.gt(0).all() or not frame.total_ads.ge(0).all():
        raise ValueError('Invalid ID or negative exposure count')
    if not frame.most_ads_hour.between(0,23).all() or not frame.most_ads_day.isin(DAYS).all():
        raise ValueError('Invalid hour or day label')
    return frame
