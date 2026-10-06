"""Start the installed local H2 GUI from Explorer, without requiring Codex."""
from pathlib import Path
import argparse
import json
from datetime import datetime, timezone
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

REPO = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8510/'
HERE = Path(__file__).resolve().parent

def healthy():
    try:
        request = urllib.request.Request(URL+'_stcore/health')
        # The loopback GUI must not be routed through an external proxy.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=2) as response:
            return response.status==200 and response.read(32).strip()==b'ok'
    except (urllib.error.URLError, TimeoutError, OSError):
        return False

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser',action='store_true',help='Check/start without opening a browser window.')
    args = parser.parse_args()
    app = REPO/'gui/app.py'
    if not app.is_file():
        raise FileNotFoundError(f'Die installierte GUI fehlt: {app}')
    process = None
    if not healthy():
        environment = dict(os.environ, H2_REPO_ROOT=str(REPO))
        runtime = REPO/'outputs_h2/gui_runtime'
        runtime.mkdir(parents=True,exist_ok=True)
        log = runtime/'server.log'
        with log.open('ab') as output:
            process = subprocess.Popen([sys.executable,'-m','streamlit','run',str(app),
                '--server.address','127.0.0.1','--server.port','8510',
                '--server.headless','true','--browser.gatherUsageStats','false',
                '--server.fileWatcherType','none'],cwd=str(REPO),env=environment,
                stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        (runtime/'server.json').write_text(json.dumps({
            'server_pid':process.pid,'created_utc':datetime.now(timezone.utc).isoformat(),
            'GUI_python':sys.executable,'GUI_app':str(app),'URL':URL,
            'log':str(log)},indent=2)+'\n',encoding='utf-8')
        ready = False
        for _ in range(60):
            if healthy():
                ready = True
                break
            if process.poll() is not None:
                raise RuntimeError(f'Die GUI konnte nicht starten. Protokoll: {log}')
            time.sleep(.5)
        if not ready:
            raise RuntimeError(f'Die GUI antwortet noch nicht. Protokoll: {log}')
    print(f'H2-Modelloberflaeche bereit: {URL}')
    if not args.no_browser:
        if not webbrowser.open(URL):
            print('Bitte diese Adresse im Browser öffnen.')
    return 0

if __name__=='__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError) as exc:
        print(f'Start fehlgeschlagen: {exc}',file=sys.stderr)
        sys.exit(1)
