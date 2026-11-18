"""M1a: validate layout contracts without project/media alteration.
UI test uses an isolated file:// fixture (Termux does not need Playwright)."""
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    html = (ROOT/'web/index.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\b[^>]*\bsrc="[^"]+"[^>]*>\s*</script>', '', html)
    html = re.sub(r'<link\b[^>]*\brel="stylesheet"[^>]*>', '', html)
    css = (ROOT/'web/style.css').read_text(encoding='utf-8')+'\n'+(ROOT/'web/studio-layout-v1.css').read_text(encoding='utf-8')
    js1 = (ROOT/'web/workspace-v38.js').read_text(encoding='utf-8')
    js2 = (ROOT/'web/studio-layout-v1.js').read_text(encoding='utf-8')
    mock = '''
    document.getElementById('openLibrary').onclick=()=>{document.getElementById('workspaceLibrary').hidden=false};
    document.getElementById('closeLibrary').onclick=()=>{document.getElementById('workspaceLibrary').hidden=true};
    document.getElementById('viewportInsert').onclick=()=>{window.__inserted=(window.__inserted||0)+1};
    document.getElementById('viewportFocus').onclick=()=>{document.body.classList.toggle('viewportFocus')};
    document.getElementById('objectCatalog').innerHTML=window.StudioWorkspaceV38.catalog.map(([id,title],i)=>
      `<button data-library-object="${id}">${title}</button>`).join('');
    document.getElementById('objectCatalog').onclick=()=>{window.__svgInsert=(window.__svgInsert||0)+1};
    document.getElementById('gilLibraryInsert').onclick=()=>{window.__gilPreview=document.getElementById('gilLibrarySelect').value};
    document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{window.__editor=b.dataset.edit});
    document.body.dataset.rdPane='previewPanel';
    '''
    html = html.replace('</head>','<style>'+css+'</style></head>',1)
    html = html.replace('</body>','<script>'+js1+'</script><script>'+mock+'</script><script>'+js2+'</script></body>',1)
    return html


class Contract(unittest.TestCase):
    def test_browser_allowlist(self):
        app = (ROOT/'app.py').read_text(encoding='utf-8')
        for file in ('studio-layout-v1.js','studio-layout-v1.css'):
            self.assertIn("'/"+file+"'", app)
        markup = (ROOT/'web/index.html').read_text(encoding='utf-8')
        for file in ('studio-layout-v1.js','studio-layout-v1.css'):
            self.assertIn('/'+file,markup)

    def test_legacy_handlers_are_reused(self):
        layout = (ROOT/'web/studio-layout-v1.js').read_text(encoding='utf-8')
        for id in ('viewportInsert','viewportInspector','viewportFocus','openLibrary','gilLibraryInsert','objectCatalog'):
            self.assertIn(id,layout)
        # Does not introduce any custom render/transport loop.
        for forbidden in ('MediaRecorder(', 'AudioContext(', 'requestAnimationFrame(', 'drawImage('):
            self.assertNotIn(forbidden, layout)

    def test_chromium_navigation_and_svg_confirmation(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest('Playwright not installed; HTML/CSS/JS contract still verified')
        with tempfile.TemporaryDirectory() as tmp:
            page_file=Path(tmp)/'fixture.html'
            page_file.write_text(fixture(),encoding='utf-8')
            with sync_playwright() as p:
                try:
                    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
                except Exception as exc:
                    self.skipTest('Chromium unavailable: '+str(exc))
                try:
                    for width,height in ((1200,800),(392,805),(915,410)):
                        page=browser.new_page(viewport={'width':width,'height':height})
                        errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
                        page.set_content(page_file.read_text(encoding='utf-8'),wait_until='domcontentloaded')
                        self.assertTrue(page.locator('#rdComposeNav').is_visible())
                        self.assertTrue(page.locator('#previewPanel').is_visible())
                        self.assertTrue(page.locator('#videoTimelinePanel').is_visible())
                        self.assertFalse(page.locator('#scenesPanel').is_visible())
                        page.locator('[data-rd-action="scenes"]').click()
                        self.assertTrue(page.locator('#scenesPanel').is_visible())
                        page.locator('.rdCloseSide').first.click()
                        self.assertFalse(page.locator('#scenesPanel').is_visible())
                        page.locator('[data-rd-action="library"]').click()
                        self.assertTrue(page.locator('#workspaceLibrary').is_visible())
                        self.assertEqual(page.locator('.rdNativeCards button').count(),4)
                        page.locator('#objectCatalog button').first.click()
                        self.assertTrue(page.locator('#rdSvgPreview').is_visible())
                        self.assertEqual(page.locator('#rdSvgPreviewStage svg').count(),1)
                        self.assertEqual(page.evaluate('window.__svgInsert||0'),0)
                        page.locator('#rdSvgPreviewClose').click()
                        self.assertEqual(page.evaluate('window.__svgInsert||0'),0)
                        page.locator('#objectCatalog button').first.click()
                        page.locator('#rdSvgPreviewInsert').click()
                        self.assertEqual(page.evaluate('window.__svgInsert||0'),1)
                        page.locator('.rdNativeCards button').first.click()
                        self.assertEqual(page.evaluate('window.__gilPreview'),'native-demo')
                        self.assertFalse(errors,errors)
                        page.close()
                finally:
                    browser.close()

if __name__ == '__main__':
    unittest.main()
