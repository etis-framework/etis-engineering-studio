const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const slice=src.slice(src.indexOf('function concernArtifact('),src.indexOf('function updateReviewJourney()',src.indexOf('function concernArtifact(')));
const choose=vm.runInNewContext(`${slice}; concernArtifact`);
const weak={items:[{title:'docs/planning/estimates.md'}],artifacts:[]};
const average={items:[{title:'docs/planning/estimates.md',equivalent_path:'docs/team/cycle-plan.md'}],artifacts:[{path:'docs/team/cycle-plan.md'}]};
const strong={items:[{title:'docs/planning/estimates.md'}],artifacts:[{path:'docs/planning/estimates.md'}]};
const shapes=[
 {finding:{evidence_refs:['PATH:docs/planning/estimates.md']}},
 {evidence_refs:['PATH:docs/planning/estimates.md']},
 {finding:{evidence_refs:[]},evidence_refs:['PATH:docs/planning/estimates.md']}
];
for(const [name,evidence,expected] of [['weak',weak,null],['average',average,'docs/team/cycle-plan.md'],['strong',strong,'docs/planning/estimates.md']]){
 for(const [student,challenge] of ['new','average','challenging'].map((x,i)=>[x,shapes[i]])){
  const actual=choose(challenge,evidence);
  assert.equal(actual?.path||null,expected,`${name} repository / ${student} student`);
 }
}
assert.equal(choose({evidence_refs:['PATH:docs/unknown.md']},strong),null);
assert.equal(choose({},strong),null);
assert.equal(choose({evidence_refs:['PATH:docs/unknown.md','PATH:docs/planning/estimates.md']},strong)?.path,'docs/planning/estimates.md');
console.log('Review journey: 9 repo/student combinations and 3 outliers passed');
