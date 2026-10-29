import json
import os

import pytest

from backend.services.mfds import local_probe


def test_default_no_prompt_no_request(monkeypatch,capsys):
    monkeypatch.setattr(local_probe.getpass,'getpass',lambda *a:pytest.fail('no prompt'))
    monkeypatch.setattr(local_probe.probe,'main',lambda *a:pytest.fail('no request'))
    assert local_probe.main([])==0
    assert 'instructions_only' in capsys.readouterr().out


@pytest.mark.parametrize('args,expected',[
    (['--check-key'],[]),
    (['--live'],['--live','--name','타이레놀','--page','1','--rows','3'])])
def test_private_entry_delegates_once_restores_environment(monkeypatch,capsys,args,expected):
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-PREVIOUS')
    monkeypatch.setattr(local_probe.getpass,'getpass',lambda *a:'SYNTHETIC-SECRET')
    calls=[]
    def fake(argv):
        calls.append(argv)
        assert os.environ['MFDS_API_KEY']=='SYNTHETIC-SECRET'
        return 0
    monkeypatch.setattr(local_probe.probe,'main',fake)
    assert local_probe.main(args)==0 and calls==[expected]
    assert os.environ['MFDS_API_KEY']=='SYNTHETIC-PREVIOUS'
    out=capsys.readouterr().out
    assert 'SYNTHETIC-SECRET' not in out and 'SYNTHETIC-PREVIOUS' not in out
    assert len(json.loads(out)['probe_sha256'])==64


def test_no_prior_key_removed_after_failure(monkeypatch,capsys):
    monkeypatch.delenv('MFDS_API_KEY',raising=False)
    monkeypatch.setattr(local_probe.getpass,'getpass',lambda *a:'SYNTHETIC-SECRET')
    monkeypatch.setattr(local_probe.probe,'main',lambda *a:1)
    assert local_probe.main(['--live'])==1
    assert 'MFDS_API_KEY' not in os.environ


def test_unsupported_console_never_uses_visible_fallback(monkeypatch,capsys):
    import warnings
    def unsupported(*a):
        warnings.warn('unavailable',local_probe.getpass.GetPassWarning)
        pytest.fail('visible fallback must not run')
    monkeypatch.setattr(local_probe.getpass,'getpass',unsupported)
    monkeypatch.setattr(local_probe.probe,'main',lambda *a:pytest.fail('no request'))
    assert local_probe.main(['--live'])==1
    assert json.loads(capsys.readouterr().out)['error']=='PRIVATE_INPUT_UNAVAILABLE_USE_TERMINAL'


def test_empty_key_no_request(monkeypatch,capsys):
    monkeypatch.setattr(local_probe.getpass,'getpass',lambda *a:'  ')
    monkeypatch.setattr(local_probe.probe,'main',lambda *a:pytest.fail('no request'))
    assert local_probe.main(['--live'])==1
    assert json.loads(capsys.readouterr().out)['request_attempts']==0


def test_unexpected_failure_hides_exception_and_restores_key(monkeypatch,capsys):
    monkeypatch.delenv('MFDS_API_KEY',raising=False)
    monkeypatch.setattr(local_probe.getpass,'getpass',lambda *a:'SYNTHETIC-SECRET')
    def fail(*a):
        raise RuntimeError('SYNTHETIC-SECRET https://private.invalid')
    monkeypatch.setattr(local_probe.probe,'main',fail)
    assert local_probe.main(['--live'])==1
    assert 'MFDS_API_KEY' not in os.environ
    out=capsys.readouterr().out
    assert 'SYNTHETIC-SECRET' not in out and 'https://' not in out
    assert 'LOCAL_EXECUTION_FAILURE' in out
