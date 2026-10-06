"""Restore the shipped scientific snapshot, without replacing different local files."""
from pathlib import Path,PureWindowsPath
import argparse,hashlib,json,os,tempfile,zipfile

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def restore(repo,*,check_only=False):
    repo=Path(repo).resolve();folder=repo/'gui/data_snapshot'
    data=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name,item in data['parts'].items():
        part=folder/name
        if Path(name).name!=name or not part.is_file() or sha(part)!=item['sha256']:
            raise ValueError(f'Archiv fehlt oder Prüfsumme stimmt nicht: {name}')
    missing=[]
    for name,item in data['files'].items():
        supplied=Path(name);target=(repo/supplied).resolve()
        if supplied.is_absolute() or PureWindowsPath(name).is_absolute() or '..' in supplied.parts or not target.is_relative_to(repo):
            raise ValueError(f'Unzulässiger Archivpfad: {name}')
        if target.exists():
            if not target.is_file() or sha(target)!=item['sha256']:
                raise ValueError(f'Vorhandene Datei weicht ab; keine Überschreibung: {name}')
        else:missing.append(name)
    if check_only:
        if missing:raise ValueError(f'{len(missing)} Snapshotdateien fehlen. Ohne --check entpacken.')
    else:
        grouped={}
        for name in missing:grouped.setdefault(data['files'][name]['part'],[]).append(name)
        for part,names in grouped.items():
            with zipfile.ZipFile(folder/part) as archive:
                for name in names:
                    target=(repo/name).resolve();target.parent.mkdir(parents=True,exist_ok=True)
                    fd,tmp=tempfile.mkstemp(prefix='.h2-restore-',dir=target.parent)
                    temporary=Path(tmp)
                    try:
                        with os.fdopen(fd,'wb') as out,archive.open(name) as inp:
                            for block in iter(lambda:inp.read(1024*1024),b''):out.write(block)
                        if sha(temporary)!=data['files'][name]['sha256']:raise ValueError(f'Dateiprüfsumme falsch: {name}')
                        if target.exists():raise ValueError(f'Ziel wurde während der Wiederherstellung angelegt: {name}')
                        os.replace(temporary,target)
                    finally:
                        if temporary.exists():temporary.unlink()
    result={'status':'passed','snapshot_files':len(data['files']),'restored_files':0 if check_only else len(missing),'native_result_directories':data['result_directories'],'optimizer_calls':0}
    print(json.dumps(result));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Verify already restored files.')
    args=parser.parse_args();restore(Path(__file__).resolve().parents[1],check_only=args.check)
