// Retain Orca's production dependency closure and packaged-runtime verification.
const path = require('node:path')
const fs = require('node:fs')
const root = process.env.KOTOBA_ORCA_CHECKOUT
if (!root) throw new Error('KOTOBA_ORCA_CHECKOUT is required')
const base = require(path.join(root, 'config/electron-builder.config.cjs'))
// electron-builder's dependency collector can discard rebuilt native outputs.
// Preserve the validated bytes before collection, then run the upstream probes
// against the resulting package (never permit fallback to unpatched prebuilds).
const nativeFiles = []
for (const name of ['node-pty', 'windows-native-registry', '@vscode/windows-process-tree']) {
  const directory = path.join(root, 'node_modules', name, 'build/Release')
  for (const relative of fs.readdirSync(directory, { recursive: true })) {
    const source = path.join(directory, relative)
    if (/\.(node|dll|exe)$/.test(relative) && fs.statSync(source).isFile()) {
      nativeFiles.push([path.join('node_modules', name, 'build/Release', relative), fs.readFileSync(source)])
    }
  }
}
module.exports = {
  ...base,
  appId: 'studio.kotoba.agents',
  productName: 'KotobaAgents',
  protocols: [],
  publish: null,
  directories: { ...base.directories, output: process.env.KOTOBA_FLEET_OUTPUT },
  files: ['out/**/*', 'resources/**/*', 'package.json', 'LICENSE', ...base.files.filter(item => item !== '**/*')],
  // The preparation step already checks the patched Electron native modules.
  beforeBuild: async () => false,
  npmRebuild: false,
  afterPack: async context => {
    for (const [relative, bytes] of nativeFiles) {
      const target = path.join(context.appOutDir, 'resources', relative)
      fs.mkdirSync(path.dirname(target), { recursive: true })
      fs.writeFileSync(target, bytes)
      const source = path.join(root, relative)
      fs.mkdirSync(path.dirname(source), { recursive: true })
      fs.writeFileSync(source, bytes)
    }
    await base.afterPack(context)
  },
  win: {
    ...base.win,
    executableName: 'KotobaAgents',
    icon: path.join(__dirname, 'assets/kotoba.ico'),
    signtoolOptions: {},
    signAndEditExecutable: false,
    verifyUpdateCodeSignature: true,
    target: ['dir'],
  },
}
