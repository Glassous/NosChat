// 用 @vue/compiler-sfc 直接编译所有 SFC，在不启动 Vite 的前提下复现 vite:vue 的编译期错误
// 用法：npm run check:sfc
const fs = require('fs')
const path = require('path')
const sfc = require('@vue/compiler-sfc')

const targets = [
  path.join(__dirname, 'src', 'App.vue'),
  ...fs.readdirSync(path.join(__dirname, 'src', 'components'))
    .filter(f => f.endsWith('.vue'))
    .map(f => path.join(__dirname, 'src', 'components', f))
]

let failed = 0
for (const file of targets) {
  const src = fs.readFileSync(file, 'utf8')
  const { descriptor, errors } = sfc.parse(src, { filename: file })
  if (errors.length) {
    failed++
    console.log(`FAIL ${path.basename(file)} :: parse :: ${errors.map(e => e.message).join(' | ')}`)
    continue
  }
  try {
    const compiled = sfc.compileScript(descriptor, { id: path.basename(file) })
    const tpl = sfc.compileTemplate({
      source: descriptor.template ? descriptor.template.content : '',
      filename: file,
      id: path.basename(file),
      compilerOptions: { bindingMetadata: compiled.bindings }
    })
    if (tpl.errors.length) {
      failed++
      console.log(`FAIL ${path.basename(file)} :: template :: ${tpl.errors.map(e => e.message || e).join(' | ')}`)
      continue
    }
    console.log(`OK   ${path.basename(file)}`)
  } catch (e) {
    failed++
    console.log(`FAIL ${path.basename(file)} :: ${e.message}`)
  }
}

console.log(failed ? `\n${failed} 个文件编译失败` : '\n全部 SFC 编译通过')
process.exitCode = failed ? 1 : 0
