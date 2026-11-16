"""Fail before publication if prohibited task artifacts or obvious tokens are tracked."""
import re,subprocess
from pathlib import Path

def main():
    files=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
    if not any(files): raise SystemExit('No tracked files: stage the reviewed source tree before checking publication hygiene')
    problems=[]
    patterns=[rb'gh[pousr]_[A-Za-z0-9]{25,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'AKIA[A-Z0-9]{16}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    for filename in filter(None,files):
        path=Path(filename); name=path.name
        if filename.startswith(('.private/','.venv/','.vercel/')) or (name.startswith('.env') and name!='.env.example'):
            problems.append(filename+': private configuration/data path')
        if path.suffix.lower() in {'.pdf','.zip','.db','.sqlite','.sqlite3'} or (path.suffix.lower() in {'.csv','.tsv','.xlsx'} and not filename.startswith('submission/')):
            problems.append(filename+': prohibited data artifact')
        blob=subprocess.check_output(['git','show',':'+filename])
        if any(re.search(pattern,blob) for pattern in patterns): problems.append(filename+': potential credential')
    if problems: raise SystemExit('\n'.join(problems))
    print(f'Repository hygiene passed: {len(list(filter(None,files)))} tracked files; no prohibited artifacts or obvious credentials')
if __name__=='__main__': main()
