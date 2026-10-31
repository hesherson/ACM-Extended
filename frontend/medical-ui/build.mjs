import { build } from 'esbuild';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createHash } from 'node:crypto';
const here = path.dirname(fileURLToPath(import.meta.url));
const result = await build({ entryPoints: [path.join(here, 'App.jsx')], bundle: true, write: false,
  minify: true, format: 'iife', target: 'chrome90', legalComments: 'inline',
  define: { 'process.env.NODE_ENV': '"production"' } });
const js = result.outputFiles[0].text.replaceAll('</script', '<\\/script');
const font = await readFile(path.join(here, 'assets/RobotoCondensed.woff2'));
const css = `@font-face{font-family:"Roboto Condensed";font-style:normal;font-weight:100 900;src:url(data:font/woff2;base64,${font.toString('base64')}) format('woff2');}` + await readFile(path.join(here, 'style.css'), 'utf8');
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ACME Transfusion Cards</title><style>${css}</style></head><body><div id="root"></div><script>${js}</script></body></html>\n`;
const target = path.resolve(here, '../../addons/acm_extended/ui/react');
await mkdir(target, { recursive: true });
const licenses = 'Roboto Condensed\n' + (await readFile(path.join(here, 'assets/OFL.txt'), 'utf8')).replace(/[ \t]+$/gm, '') + '\n' + (await Promise.all(['react', 'react-dom', 'scheduler'].map(async name =>
  `${name}\n${(await readFile(path.join(here, 'node_modules', name, 'LICENSE'), 'utf8')).trimEnd()}\n`))).join('\n');
const digest = value => createHash('sha256').update(value).digest('hex');
const inputs = ['App.jsx', 'bridge.mjs', 'style.css', 'build.mjs', 'package.json', 'package-lock.json', 'assets/RobotoCondensed.woff2', 'assets/OFL.txt'];
const sources = Object.fromEntries(await Promise.all(inputs.map(async name => [name, digest(await readFile(path.join(here, name)))])));
const manifest = JSON.stringify({ schema: 1, sources, htmlSha256: digest(html), licensesSha256: digest(licenses) }, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (html !== await readFile(path.join(target, 'index.html'), 'utf8')) throw new Error('React bundle differs from committed source; run npm run build');
  if (licenses !== await readFile(path.join(target, 'THIRD_PARTY_LICENSES.txt'), 'utf8')) throw new Error('Missing or stale runtime licenses');
  if (manifest !== await readFile(path.join(here, 'bundle-manifest.json'), 'utf8')) throw new Error('Stale frontend source fingerprints');
} else {
  await writeFile(path.join(target, 'index.html'), html);
  await writeFile(path.join(target, 'THIRD_PARTY_LICENSES.txt'), licenses);
  await writeFile(path.join(here, 'bundle-manifest.json'), manifest);
}
console.log(`React single-file bundle: ${Buffer.byteLength(html)} bytes`);
