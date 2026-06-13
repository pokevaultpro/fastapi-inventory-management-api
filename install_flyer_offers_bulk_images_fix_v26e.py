from __future__ import annotations
import py_compile, shutil
from pathlib import Path
FILES = [
    "app/services/flyer_offer_bulk_images_v26e.py",
    "app/routers/flyer_offer_bulk_admin_v26e.py",
    "frontend/js/flyer-offers-bulk-images-v26e.js",
    "frontend/css/flyer-offers-bulk-images-v26e.css",
    "docs/FLYER_OFFERS_BULK_IMAGES_FIX_V26E.md",
]

def ensure_import(text: str, line: str) -> str:
    if line in text: return text
    lines=text.splitlines(); idx=0
    for i,l in enumerate(lines):
        if l.startswith('from ') or l.startswith('import '): idx=i+1
    lines.insert(idx,line)
    return '\n'.join(lines)+'\n'

def main():
    root=Path.cwd(); patch=Path(__file__).resolve().parent
    if not (root/'app').exists() or not (root/'frontend').exists():
        raise RuntimeError('Estrai lo ZIP nella root del progetto, dove esistono app/ e frontend/.')
    for rel in FILES:
        src=patch/rel; dst=root/rel; dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            bak=dst.with_suffix(dst.suffix+'.bak_v26e')
            if not bak.exists(): shutil.copy2(dst,bak)
        shutil.copy2(src,dst); print('OK copied', rel)
    mainpy=root/'app/main.py'
    text=mainpy.read_text(encoding='utf-8')
    text=ensure_import(text, 'from app.routers import flyer_offer_bulk_admin_v26e')
    if 'app.include_router(flyer_offer_bulk_admin_v26e.router)' not in text:
        text=text.rstrip()+"\napp.include_router(flyer_offer_bulk_admin_v26e.router)\n"
    mainpy.write_text(text, encoding='utf-8')
    admin=root/'frontend/admin.html'
    if admin.exists():
        html=admin.read_text(encoding='utf-8')
        css='<link rel="stylesheet" href="css/flyer-offers-bulk-images-v26e.css">'
        js='<script type="module" src="js/flyer-offers-bulk-images-v26e.js"></script>'
        if css not in html: html=html.replace('</head>', '  '+css+'\n</head>', 1)
        if js not in html: html=html.replace('</body>', js+'\n</body>', 1)
        admin.write_text(html, encoding='utf-8')
        print('OK patched frontend/admin.html')
    for rel in ['app/services/flyer_offer_bulk_images_v26e.py','app/routers/flyer_offer_bulk_admin_v26e.py','app/main.py']:
        py_compile.compile(str(root/rel), doraise=True); print('OK compile', rel)
    print('\nPatch v26e installata. Commit/push/redeploy Render e carica i 2 file frontend + admin.html su SiteGround.')
if __name__=='__main__': main()
