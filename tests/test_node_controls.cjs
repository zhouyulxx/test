const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const file of ['nodes.html','branches.html']){
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{dataset:{},getContext:()=>({drawImage(){}}),append(){}});return elements.get(id)};
 let code=fs.readFileSync(require('path').join(__dirname,'../viewer',file),'utf8').split('<script>')[1].split('</script>')[0];code=code.slice(0,code.indexOf('async function start()'));
 const c=vm.createContext({document:{getElementById:el},performance:{now:()=>0},requestAnimationFrame(){},window:{},Map,Set});vm.runInContext(code,c);
 vm.runInContext("nodes=[0,1,2];maxS=2;routeFrames=nodes.map(s=>({s,yaw:0,url:'center'+s}));endViews=nodes.flatMap(s=>[-60,0,60].map(yaw=>({s,yaw,url:'view'+s+yaw})));",c);
 for(const n of [0,1,2]){vm.runInContext(`s=targetS=${n};setYaw(100)`,c);assert.equal(vm.runInContext('yaw',c),60);assert.equal(vm.runInContext('s',c),n);vm.runInContext('setYaw(-100)',c);assert.equal(vm.runInContext('yaw',c),-60)}
 vm.runInContext('s=targetS=0;move(1)',c);assert.equal(vm.runInContext('targetS',c),1);vm.runInContext('move(1)',c);assert.equal(vm.runInContext('targetS',c),1);vm.runInContext('s=.5;setYaw(45)',c);assert.equal(vm.runInContext('yaw',c),0);assert.equal(vm.runInContext('hasSides()',c),false);
 console.log(file+': PASS yaw bounds, stationary turning, no skipped nodes, no side views during transitions');
}
