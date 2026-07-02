const fs=require("fs");const path=require("path");const {JSDOM}=require("jsdom");
// Load the real index.html and inject a test hook before the BOOT banner.
const src=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const hook='  window.__test={game,submit,useHint,LEVELS,DICT,ring,levelProg,openSun,serialize,buildGardens,fit,ui,checkAuto,maybeComplete,solveWord};\n';
const marker="/* ============================ BOOT";
if(!src.includes(marker)) throw new Error("boot marker missing");
const html=src.replace(marker,hook+marker);
const mem={};const storage={async get(k){return k in mem?{key:k,value:mem[k]}:null;},async set(k,v){mem[k]=v;return{key:k,value:v};}};
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,beforeParse(w){w.storage=storage;}});
const win=dom.window;
let pass=0,fail=0;
const ok=(c,m)=>{(c?pass++:fail++);console.log((c?"  ok  ":"FAIL  ")+m);};
const eq=(a,b,m)=>ok(a===b,`${m} (got ${a}, want ${b})`);
const wait=ms=>new Promise(r=>setTimeout(r,ms));

function gridFromData(L){ // independent reconstruction from level data
  const g={};
  for(const w of L.targets){ const [r0,c0,d]=L.pos[w],dr=d?1:0,dc=d?0:1;
    for(let k=0;k<w.length;k++){ const key=(r0+dr*k)+","+(c0+dc*k);
      if(g[key]&&g[key]!==w[k]) throw new Error("data letter clash "+key);
      g[key]=w[k]; } }
  return g;
}

(async()=>{
  await wait(70);
  const T=win.__test, D=win.document;
  ok(T&&T.LEVELS,"internals exposed");
  eq(T.LEVELS.length,142,"142 gardens");
  ok(T.DICT.size>5000,`dictionary loaded (${T.DICT.size} words)`);
  eq(T.game.pollen,150,"starting pollen");
  ok(T.LEVELS.every(L=>L.pos&&L.gw&&L.gh),"every garden carries a crossword layout");

  // --- first-run intro ---
  eq(D.getElementById("introScrim").classList.contains("on"),true,"intro shown on fresh boot");
  D.getElementById("introBtn").click();
  eq(D.getElementById("introScrim").classList.contains("on"),false,"intro dismissed");
  eq(T.game.seenIntro,true,"seenIntro set");

  // fit sizes ring + cell var without crashing
  T.fit();
  ok(T.ring.forced>=150&&T.ring.forced<=300,`fit ring ${T.ring.forced}px`);
  const cellVar=D.getElementById("app").style.getPropertyValue("--cell");
  ok(/^\d+px$/.test(cellVar)&&parseInt(cellVar)>=20&&parseInt(cellVar)<=40,`fit cell ${cellVar}`);

  // --- crossword grid integrity for garden 0 ---
  const L0=T.LEVELS[0];
  const dataGrid=gridFromData(L0);
  eq(Object.keys(T.ui.cellMap).length,Object.keys(dataGrid).length,"DOM cells = layout cells");
  let lettersMatch=true;
  for(const k in dataGrid) if(T.ui.cellLetter[k]!==dataGrid[k]) lettersMatch=false;
  ok(lettersMatch,"cell letters match layout data");
  const shared=Object.keys(T.ui.cellWords).filter(k=>T.ui.cellWords[k].length>=2);
  ok(shared.length>=L0.targets.length-1,`grid interlocks (${shared.length} crossings)`);

  // --- crossing visibility: solve one word, its letters appear in a crossing word's cell ---
  const first=L0.targets[0];                            // TULIP
  T.submit(first);
  const p0=T.levelProg(0);
  ok(p0.solved.has(first),"first word solved");
  const crossKey=T.ui.wordKeys[first].find(k=>T.ui.cellWords[k].length>=2);
  ok(!!crossKey,"first word has a crossing cell");
  eq(T.ui.cellMap[crossKey].textContent,T.ui.cellLetter[crossKey],"crossing letter now visible for unsolved neighbor");

  // --- solve the rest; economy must equal sum(len*2) regardless of auto-completions ---
  L0.targets.slice(1).forEach(w=>T.submit(w));          // "already grown" for autos is fine
  eq(p0.solved.size,L0.targets.length,"all targets solved");
  const expSolve=150+L0.targets.reduce((a,w)=>a+w.length*2,0);
  eq(T.game.pollen,expSolve,"pollen = sum of solve rewards exactly (auto pays same, no double-pay)");

  await wait(720);
  eq(D.getElementById("levelScrim").classList.contains("on"),true,"level-complete overlay");
  eq(T.game.pollen,expSolve+30,"clear bonus +30 once");
  eq(T.game.unlocked,1,"garden 2 unlocked");

  // --- open-ended pressing (any real 3-letter word from garden 0's letters
  //     that isn't a board target — derived so it survives content changes) ---
  const L0set=new Set(L0.letters);
  const press=[...T.DICT].find(w=>w.length===3 && new Set(w).size===3
    && [...w].every(c=>L0set.has(c)) && !L0.targets.includes(w));
  ok(!!press,`a pressing exists for garden 0 (${press})`);
  const beforeP=T.game.pollen; T.submit(press);
  eq(T.game.pollen,beforeP+6,"pressing pays base 6");
  ok(T.ui.pressList.includes(press),"pressing in journal list");

  // invalid
  const beforeBad=T.game.pollen; T.submit("ZZQ");
  eq(T.game.pollen,beforeBad,"invalid pays nothing");
  eq(D.getElementById("preview").classList.contains("msg-warn"),true,"invalid warns");

  // --- garden 1: hint reveals a cell; auto-solve via reveals pays normally ---
  D.getElementById("gardensBtn").click();
  D.querySelectorAll(".gcard")[1].click(); await wait(20);
  const L1=T.LEVELS[1], p1=T.levelProg(1);
  const beforeHint=T.game.pollen; T.useHint();
  eq(T.game.pollen,beforeHint-20,"hint costs 20");
  eq(p1.rev.size,1,"hint revealed exactly one cell");
  const rk=[...p1.rev][0];
  eq(T.ui.cellMap[rk].textContent,T.ui.cellLetter[rk],"revealed cell shows its letter");
  ok(T.ui.cellMap[rk].classList.contains("hint"),"revealed cell styled as hint");

  // deterministic auto-solve: reveal every cell of one unsolved word, then checkAuto
  const target=L1.targets.find(w=>!p1.solved.has(w));
  T.ui.wordKeys[target].forEach(k=>p1.rev.add(k));
  const beforeAuto=T.game.pollen;
  T.checkAuto();
  ok(p1.solved.has(target),"fully-revealed word auto-solves");
  ok(T.game.pollen>=beforeAuto+target.length*2,"auto-solve pays solve reward (cascades may add more)");

  // --- daily sun modal ---
  T.game.pollen=100; T.game.lastSun=null; T.openSun();
  eq(T.game.pollen,140,"sun grants +40");
  eq(D.getElementById("sunScrim").classList.contains("on"),true,"sun overlay shown");
  eq(D.getElementById("sunTitle").textContent,"Morning sun","sun title on claim");
  const afterSun=T.game.pollen; T.openSun();
  eq(T.game.pollen,afterSun,"second sun same day pays nothing");
  eq(D.getElementById("sunTitle").textContent,"Already gathered","already-gathered state");

  // --- sun streak: yesterday's claim escalates today's ---
  const yd=new Date(Date.now()-86400000);
  T.game.lastSun=`${yd.getFullYear()}-${yd.getMonth()+1}-${yd.getDate()}`;
  T.game.sunStreak=1;
  const beforeStreak=T.game.pollen; T.openSun();
  eq(T.game.pollen,beforeStreak+45,"day-2 sun pays 40+5");
  ok(D.getElementById("sunSub").textContent.includes("Day 2"),"streak shown in modal");
  T.game.lastSun=`${yd.getFullYear()}-${yd.getMonth()+1}-${yd.getDate()}`;
  T.game.sunStreak=7;
  const beforeCap=T.game.pollen; T.openSun();
  eq(T.game.pollen,beforeCap+60,"streak reward caps at 60");

  // gardens stats
  T.buildGardens();
  ok(D.getElementById("tBloom").textContent.startsWith("1/"),"index shows 1 in bloom");

  // persistence v4
  await wait(260);
  ok("bloom.save.v4" in mem,"saved under v4 key");
  const saved=JSON.parse(mem["bloom.save.v4"]);
  eq(saved.unlocked,1,"unlocked persisted");
  ok(saved.prog[0].bonus.includes(press),"pressing persisted");
  ok(Array.isArray(saved.prog[1].rev)&&saved.prog[1].rev.length>=1,"revealed cells persisted");
  eq(saved.seenIntro,true,"seenIntro persisted");
  ok(saved.sunStreak>=1,"sunStreak persisted");

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail?1:0);
})().catch(e=>{console.error("THREW:",e);process.exit(1);});
