"""Small local operator menu. It does not start, install or call an AI service."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def command(*arguments):
    return subprocess.call([sys.executable,str(ROOT/'scripts/run_lab.py'),*arguments],cwd=ROOT)

def open_file(path):
    if not path.exists():
        print('File not available yet: '+path.name);return
    if os.name=='nt':
        os.startfile(path)
    else:
        print(path)

def main():
    while True:
        print('\nCantaX Propeller Lab — local preliminary engineering\n'
              '1  Create/open input workbook\n2  Run native engineering pipeline\n'
              '3  Run diameter study\n4  Verify saved demonstration (no native engines)\n'
              '5  Open latest results\n6  Open latest report\n7  Check local tools\n'
              '8  Open README\n0  Exit')
        try:choice=input('Choice: ').strip()
        except (EOFError,KeyboardInterrupt):return 0
        if choice=='0':return 0
        if choice=='1':
            workbook=ROOT/'CantaX_Propeller_Lab.xlsx'
            if not workbook.exists() and command('--create-input')!=0:continue
            open_file(workbook)
        elif choice=='2':command('--run')
        elif choice=='3':command('--run','--diameter-sweep','--tag','diameter_study')
        elif choice=='4':command('--demo')
        elif choice in {'5','6'}:
            latest=ROOT/'config/latest_run.json'
            if not latest.exists():print('No complete native run yet.');continue
            result=json.loads(latest.read_text(encoding='utf-8'))
            # Ignore a tampered latest pointer that points outside this checkout.
            path=Path(result['results_workbook' if choice=='5' else 'pdf']).resolve()
            if not path.is_relative_to(ROOT/'runs'):raise ValueError('Latest output pointer outside runs')
            open_file(path)
        elif choice=='7':command('--check-tools')
        elif choice=='8':open_file(ROOT/'README.md')
        else:print('Choose one of the listed numbers.')

if __name__=='__main__':raise SystemExit(main())
