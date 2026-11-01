const esbuild = require('esbuild');

const isWatch = process.argv.includes('--watch');

/** @type {import('esbuild').BuildOptions} */
const buildOptions = {
  entryPoints: [
    { in: 'src/main.ts', out: 'main' },
    { in: 'src/sped.ts', out: 'sped' }
  ],
  outdir: 'static/js',
  bundle: true,
  sourcemap: true,
  target: ['es2020'],
  minify: false,
  logLevel: 'info'
};

async function run() {
  if (isWatch) {
    const ctx = await esbuild.context(buildOptions);
    await ctx.watch();
    console.log('👀 Observando alterações nos arquivos TypeScript...');
  } else {
    await esbuild.build(buildOptions);
    console.log('✅ Build TypeScript concluído com sucesso!');
  }
}

run().catch((err) => {
  console.error('❌ Erro no build:', err);
  process.exit(1);
});
