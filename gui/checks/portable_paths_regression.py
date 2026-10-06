"""Relocation requires an explicit snapshot declaration and keeps containment."""
from pathlib import Path
import json,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from gui.case_study_registry import contained_path,RegistryError,_snapshot_paths
from gui.restore_shared_data import restore

@pytest.fixture
def relocated(tmp_path):
    snapshot=tmp_path/'gui/data_snapshot';snapshot.mkdir(parents=True)
    data=tmp_path/'outputs_h2/example/input.csv';data.parent.mkdir(parents=True);data.write_text('value\n1\n')
    (snapshot/'manifest.json').write_text(json.dumps({'source_repository_root':'C:/original/model','files':{'outputs_h2/example/input.csv':{}}}))
    _snapshot_paths.cache_clear();return tmp_path,data

def test_declared_windows_source_maps_only_to_current_checkout(relocated):
    root,data=relocated
    assert contained_path(root,r'C:\original\model\outputs_h2\example\input.csv',must_exist=True)==data
    assert contained_path(root,r'\\?\C:\original\model\outputs_h2\example\input.csv',must_exist=True)==data
    assert contained_path(root,'C:/original/model/outputs_h2/example')==data.parent
    assert contained_path(root,'outputs_h2/example/input.csv',must_exist=True)==data

@pytest.mark.parametrize('path',['C:/other/model/outputs_h2/example/input.csv','C:/original/model-other/outputs_h2/example/input.csv','C:/original/model/outputs_h2/undeclared.csv','C:/original/model/outputs_h2/example/../../secret.txt','../../outside.csv'])
def test_unapproved_path_is_rejected(relocated,path):
    with pytest.raises(RegistryError):contained_path(relocated[0],path)

def test_restore_checks_hashes_and_preserves_different_existing_files(tmp_path):
    import hashlib,zipfile
    root=tmp_path/'model';folder=root/'gui/data_snapshot';folder.mkdir(parents=True)
    content=b'original\n';name='outputs_h2/record.csv'
    part=folder/'part-001.zip'
    with zipfile.ZipFile(part,'w') as z:z.writestr(name,content)
    h=lambda b:hashlib.sha256(b).hexdigest()
    manifest={'parts':{part.name:{'sha256':h(part.read_bytes())}},'files':{name:{'sha256':h(content),'part':part.name}},'result_directories':1}
    (folder/'manifest.json').write_text(json.dumps(manifest))
    assert restore(root)['restored_files']==1
    assert restore(root,check_only=True)['restored_files']==0
    target=root/name;target.write_bytes(b'different\n')
    with pytest.raises(ValueError,match='keine Überschreibung'):restore(root)
    assert target.read_bytes()==b'different\n'

def test_model_interpreter_can_be_selected_without_personal_directory(tmp_path,monkeypatch):
    from gui.model_adapter import _python
    interpreter=tmp_path/'python.exe';interpreter.write_bytes(b'fixture')
    monkeypatch.setenv('H2_MODEL_PYTHON',str(interpreter))
    assert _python()==str(interpreter.resolve())
