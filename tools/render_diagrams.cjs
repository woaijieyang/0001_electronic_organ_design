// Requires Playwright and a local Mermaid 10.9.3 browser bundle.
// Usage: node tools/render_diagrams.cjs /path/to/mermaid.min.js
const fs=require('fs'), path=require('path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1600,height:1200}});
 await page.setContent('<html><head><meta charset="UTF-8"></head><body></body></html>');
 await page.addScriptTag({path:path.resolve(process.argv[2])});
 await page.evaluate(()=>mermaid.initialize({startOnLoad:false,theme:'base',securityLevel:'strict',fontFamily:'Microsoft YaHei',themeVariables:{primaryColor:'#f8e9e7',primaryTextColor:'#3b252b',primaryBorderColor:'#a55962',lineColor:'#8f1d2c',secondaryColor:'#f7f3e9',tertiaryColor:'#f6f2ed',fontSize:'18px'},flowchart:{htmlLabels:false,useMaxWidth:false,curve:'linear',nodeSpacing:28,rankSpacing:40},sequence:{useMaxWidth:false,actorFontSize:18,messageFontSize:17}}));
 for(const file of fs.readdirSync(path.join(root,'assets/diagrams')).filter(x=>x.endsWith('.mmd')&&!['system.mmd','modes.mmd'].includes(x))){
  const code=fs.readFileSync(path.join(root,'assets/diagrams',file),'utf8');
  const result=await page.evaluate(async({code})=>{document.body.innerHTML='';return (await mermaid.render('diagram',code)).svg},{code});
  const out=path.join(root,'assets/figures',file.replace('.mmd','.svg'));
  fs.writeFileSync(out,result,'utf8');
  await page.setContent('<html><body style="margin:0;padding:24px;background:#fffdf9">'+result+'</body></html>');
  await page.locator('svg').screenshot({path:out.replace('.svg','.png')});
  console.log(file);
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
