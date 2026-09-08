const { spawn, execFileSync } = require('node:child_process');
const { mkdirSync } = require('node:fs');
const assert = require('node:assert/strict');
const cli = require('node:path').resolve('node_modules/.bin/agent-browser');
const env = {
  ...process.env,
  AGENT_BROWSER_SESSION: `soprano-${process.env.GITHUB_RUN_ID || process.pid}`,
  AGENT_BROWSER_EXECUTABLE_PATH: '/usr/bin/google-chrome',
  AGENT_BROWSER_ARGS: '--autoplay-policy=no-user-gesture-required',
  AGENT_BROWSER_ALLOWED_DOMAINS: '127.0.0.1',
  AGENT_BROWSER_DEFAULT_TIMEOUT: '240000',
};
function browser(...args) {
  const output = execFileSync(cli, ['--json', ...args], {env, encoding:'utf8', timeout:270000});
  const result = JSON.parse(output);
  if (!result.success) throw new Error(JSON.stringify(result));
  return result.data;
}
const server = spawn('python3', ['-m','http.server','8765','--bind','127.0.0.1','--directory','content/web'], {stdio:'ignore'});
(async () => {
  try {
    for (let i = 0; i < 50; i++) {
      try { if ((await fetch('http://127.0.0.1:8765/')).ok) break; } catch {}
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    console.log('Opening packaged Release page');
    browser('open','http://127.0.0.1:8765/');
    browser('wait','--fn',"['Ready','Init Error'].includes(document.querySelector('#stat-status')?.textContent)");
    assert.equal(browser('eval',"document.querySelector('#stat-status').textContent").result,'Ready');
    browser('eval',`(async () => {
      const {PCMPlayerWorklet} = await import('/PCMPlayerWorklet.js');
      const original = PCMPlayerWorklet.prototype.playAudio;
      window.__audioProof = {samples:0, peak:0};
      const resume = AudioContext.prototype.resume;
      AudioContext.prototype.resume = function(...args) {
        window.__audioResume = {before:this.state, after:null};
        const result = resume.apply(this,args);
        result.then(() => { window.__audioResume.after = this.state; });
        return result;
      };
      PCMPlayerWorklet.prototype.playAudio = function(data) {
        window.__audioProof.samples += data.length;
        for (const value of data) window.__audioProof.peak = Math.max(window.__audioProof.peak, Math.abs(value));
        return original.call(this, data);
      };
      return true;
    })()`);
    browser('click','#device-cpu');
    browser('fill','#text-input','Hello.');
    console.log('Generating PCM on CPU/WASM');
    browser('click','#generate-btn');
    const started = browser('eval',`new Promise(resolve => {
      const deadline = Date.now()+10000;
      const timer = setInterval(() => {
        const status=document.querySelector('#stat-status').textContent;
        if (status!=='Ready' || Date.now()>deadline) {
          clearInterval(timer); resolve({status,audioResume:window.__audioResume});
        }
      },100);
    })`).result;
    console.log('Synthesis startup:',JSON.stringify(started));
    assert.notEqual(started.status,'Ready','Generate must leave Ready after audio initialization');
    browser('wait','--fn',"['Finished','Error'].includes(document.querySelector('#stat-status')?.textContent)");
    const proof = browser('eval',`({status:document.querySelector('#stat-status').textContent, model:document.querySelector('.model-status__text').textContent, audio:window.__audioProof, external:performance.getEntriesByType('resource').map(x=>x.name).filter(x=>/^https?:/.test(x)&&new URL(x).origin!==location.origin)})`).result;
    console.log('Browser synthesis verification:', JSON.stringify(proof));
    assert.equal(proof.status,'Finished');
    assert.ok(proof.audio.samples > 1000 && proof.audio.peak > 0, 'Expected generated, non-silent PCM audio');
    assert.deepEqual(proof.external,[], 'App must not request external resources');
    mkdirSync('.lazycat-build',{recursive:true});
    browser('screenshot','.lazycat-build/browser-smoke.png');
  } catch (error) {
    for (const args of [
      ['errors'], ['console'], ['eval', "({state:document.readyState, ort:typeof ort, audioResume:window.__audioResume, audio:window.__audioProof, scripts:[...document.scripts].map(s=>s.src), resources:performance.getEntriesByType('resource').map(r=>({name:r.name,status:r.responseStatus,size:r.transferSize}))})"], ['snapshot']
    ]) {
      try { console.error('Browser diagnostic ' + args[0] + ':',JSON.stringify(browser(...args))); } catch (diagnosticError) { console.error(String(diagnosticError)); }
    }
    throw error;
  } finally {
    try { browser('close'); } finally { server.kill(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
