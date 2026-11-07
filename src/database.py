"""PostgreSQL load with a durable journal and a SHA256 idempotency key."""
import argparse
import hashlib
import io
import json
import os
from .data import ROOT, RAW, load_data


def connect():
    import psycopg2
    env=ROOT/'.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key,value=line.split('=',1); os.environ.setdefault(key.strip(),value.strip())
    name=os.getenv('PGDATABASE','')
    if not name.startswith('marketing_ab_'):
        raise ValueError('Use a dedicated database named marketing_ab_*')
    return psycopg2.connect(host=os.getenv('PGHOST','localhost'),port=os.getenv('PGPORT','5432'),
                            dbname=name,user=os.getenv('PGUSER','marketing_ab_app'),
                            password=os.getenv('PGPASSWORD',''),connect_timeout=5)


def load(path=RAW,init=False):
    source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    con=connect(); con.autocommit=True
    try:
        with con.cursor() as cur:
            # Session lock covers journal commits and serializes concurrent loaders.
            cur.execute("SELECT pg_advisory_lock(hashtext('marketing-ab-analysis-loader'))")
            if init:
                cur.execute((ROOT/'sql/schema.sql').read_text(encoding='utf-8'))
            cur.execute('SELECT batch_id,status,row_count FROM campaign.loads WHERE source_sha256=%s',(source_hash,))
            previous=cur.fetchone()
            if previous and previous[1]=='success':
                return {'batch_id':previous[0],'status':'skipped','rows':previous[2],'reason':'Identical source hash already loaded'}
            if previous:
                batch=previous[0]
                cur.execute("UPDATE campaign.loads SET status='loading',started_at=CURRENT_TIMESTAMP,finished_at=NULL,error_class=NULL WHERE batch_id=%s",(batch,))
            else:
                cur.execute("INSERT INTO campaign.loads (source_sha256,source_name,status) VALUES (%s,%s,'loading') RETURNING batch_id",(source_hash,path.name))
                batch=cur.fetchone()[0]
            try:
                frame,meta=load_data(path)
                if meta['source_sha256']!=source_hash:
                    raise ValueError('Source changed during reading')
                csv=io.StringIO()
                frame.insert(0,'batch_id',batch)
                frame.to_csv(csv,index=False,header=False); csv.seek(0)
                cur.execute('BEGIN')
                cur.execute('DELETE FROM campaign.users WHERE batch_id=%s',(batch,))
                cur.copy_expert('COPY campaign.users (batch_id,user_id,test_group,converted,total_ads,most_ads_day,most_ads_hour) FROM STDIN WITH (FORMAT CSV)',csv)
                cur.execute("UPDATE campaign.loads SET status='success',row_count=%s,finished_at=CURRENT_TIMESTAMP WHERE batch_id=%s",(len(frame),batch))
                cur.execute('COMMIT')
                return {'batch_id':batch,'status':'success','rows':len(frame)}
            except Exception as exc:
                cur.execute('ROLLBACK')
                cur.execute("UPDATE campaign.loads SET status='failed',error_class=%s,finished_at=CURRENT_TIMESTAMP WHERE batch_id=%s",(type(exc).__name__,batch))
                raise
    finally:
        con.close()  # Also releases the session advisory lock.


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init',action='store_true',help='Create project tables inside the dedicated database')
    args=parser.parse_args()
    print(json.dumps(load(init=args.init),indent=2))
