"""Build the final Arena frontend and migrate PostgreSQL before a release.

Fails closed while Arena is missing: never publishes the integration entry page
as the final application. No source kit data enters a deployment artifact.
"""
import json,os,shutil,subprocess
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent.parent
    frontend=root/'frontend'; package=frontend/'package.json'
    if not package.is_file(): raise RuntimeError('Arena frontend ZIP has not been integrated; final deployment is intentionally blocked')
    manifest=json.loads(package.read_text(encoding='utf-8'))
    if 'build' not in manifest.get('scripts',{}): raise RuntimeError('Arena frontend must provide a verified build script')
    npm=shutil.which('npm')
    if not npm: raise RuntimeError('Node/npm is required for the frontend build')
    if not (frontend/'package-lock.json').is_file(): raise RuntimeError('Commit the reviewed frontend package-lock.json before deployment')
    if not os.getenv('DATABASE_URL'): raise RuntimeError('Provision persistent PostgreSQL before building')
    python=shutil.which('python') or 'python'
    subprocess.run([python,'-m','scripts.generate_frontend_contract','--check'],check=True,cwd=root)
    subprocess.run([npm,'ci','--include=dev','--ignore-scripts','--prefix',str(frontend)],check=True)
    subprocess.run([npm,'run','build','--prefix',str(frontend)],check=True)
    if not (frontend/'dist'/'index.html').is_file(): raise RuntimeError('Expected a Vite build in frontend/dist')
    public=root/'public'; public.mkdir(exist_ok=True)
    shutil.copytree(frontend/'dist',public,dirs_exist_ok=True)
    subprocess.run([shutil.which('python') or 'python','-m','alembic','upgrade','head'],check=True,cwd=root)
    subprocess.run([shutil.which('python') or 'python','-m','scripts.bootstrap_db'],check=True,cwd=root)

if __name__=='__main__': main()
