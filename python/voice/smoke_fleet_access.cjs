// Optional packaged desktop smoke. Uses a private profile; never launches a model turn.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {_electron}=require(path.resolve(process.argv[2], 'node_modules/playwright'));
(async()=>{
 if (!process.argv[2] || !process.argv[3] || !process.argv[4]) throw new Error('Usage: node smoke_fleet_access.cjs CHECKOUT RUNTIME OUTPUT');
 const output=path.resolve(process.argv[4]); fs.mkdirSync(output,{recursive:true});
 const home=fs.mkdtempSync(path.join(os.tmpdir(),'kotoba-access-'));
 const app=await _electron.launch({executablePath:path.resolve(process.argv[3], 'KotobaAgents.exe'),args:[],env:{...process.env,KOTOBA_FLEET_HOME:home,KOTOBA_FLEET_NONCE:'owned-test',ORCA_BACKGROUND_LAUNCH:'1',DO_NOT_TRACK:'1',ORCA_TELEMETRY_DISABLED:'1'},timeout:60000});
 try {
 const page=await app.firstWindow(); page.setDefaultTimeout(15000); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await app.evaluate(({BrowserWindow})=>{ const win=BrowserWindow.getAllWindows()[0]; win.webContents.setBackgroundThrottling(false); win.showInactive() });
 await page.waitForFunction(()=>typeof window.kotobaWorkspace==='object');
 await page.evaluate(()=>window.kotobaWorkspace.snapshot('en'));
 await page.evaluate(()=>window.kotobaWorkspace.navigate('permissions'));
 await page.getByRole('heading',{name:'Agent access',exact:true}).waitFor();
 assert.equal(await page.getByText('Yolo / Dangerously skip permissions',{exact:true}).count(),0);
 assert.equal(await page.getByText('Orca Mobile',{exact:true}).count(),0);
 assert.equal(await page.getByText('Orca Account',{exact:false}).count(),0);
 await page.evaluate(()=>window.kotobaWorkspace.navigate('accounts'));
 await page.locator('#accounts').waitFor();
 assert.equal(await page.getByText('Sign in to Kotoba Studio',{exact:true}).count(),0);
 await page.evaluate(()=>window.kotobaWorkspace.navigate('permissions'));
 await page.getByRole('heading',{name:'Agent access',exact:true}).waitFor();
 for(const agent of ['codex','claude','opencode']) {
  await page.getByRole('combobox',{name:'Agent for access settings'}).selectOption(agent);
  for(const mode of ['plan','ask','workspace']) {
   await page.locator(`input[name="kotoba-agent-access"][value="${mode}"]`).check({force:true});
   await page.getByRole('button',{name:'Apply access level',exact:true}).click();
   await page.getByText('Saved for new sessions. Existing sessions retain their own permissions.',{exact:true}).waitFor();
   assert.equal(await page.getByRole('button',{name:'Apply access level',exact:true}).isDisabled(),true);
  }
 }
 await page.reload();
 await page.waitForFunction(()=>typeof window.kotobaWorkspace==='object');
 await page.evaluate(()=>window.kotobaWorkspace.navigate('permissions'));
 await page.getByRole('heading',{name:'Agent access',exact:true}).waitFor();
 for (const agent of ['codex','claude','opencode']) {
  await page.getByRole('combobox',{name:'Agent for access settings'}).selectOption(agent);
  assert.equal(await page.locator('input[value=workspace][name=kotoba-agent-access]').isChecked(),true);
 }
 await page.getByRole('combobox',{name:'Agent for access settings'}).selectOption('pi');
 await page.getByText('Pi does not provide built-in approval levels.',{exact:false}).waitFor();
 assert.equal(await page.locator('input[name="kotoba-agent-access"]').count(),0);
 await page.getByRole('combobox',{name:'Agent for access settings'}).selectOption('codex');
 await page.screenshot({path:path.join(output,'access-en.png')});
 await page.evaluate(()=>window.kotobaWorkspace.snapshot('ja'));
 await page.getByRole('heading',{name:'エージェントのアクセス',exact:true}).waitFor();
 await page.screenshot({path:path.join(output,'access-ja.png')});
 assert.equal(errors.length,0,JSON.stringify(errors));
 console.log(JSON.stringify({passed:true,checks:19,profile:home}));
 }catch(error){
  const page=await app.firstWindow();
  await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});
  console.error(await page.locator('h1,h2,h3').allTextContents());
  throw error;
 }finally{await app.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
