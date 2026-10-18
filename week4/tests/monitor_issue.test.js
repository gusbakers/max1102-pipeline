const assert = require('node:assert/strict');
const test = require('node:test');
const manage = require('../../.github/scripts/monitor_issue.js');

function fixture(issues) {
  const calls = [];
  const github = {paginate: async () => issues, rest: {issues: {
    listForRepo: () => {},
    create: async x => calls.push(['create', x]),
    update: async x => calls.push(['update', x]),
    createComment: async x => calls.push(['comment', x])
  }}};
  const summary = {addHeading() { return this; }, addCodeBlock() { return this; }, async write() {}};
  return {calls, github, core: {summary}, context: {repo: {owner:'test', repo:'test'}, serverUrl:'https://github.com', runId:1}};
}

test('failure creates one incident; repeated failure updates it', async () => {
  const result = {status:'failed', drill:false};
  const fresh = fixture([]);
  await manage({...fresh, result});
  assert.equal(fresh.calls[0][0], 'create');
  const existing = fixture([{number:5, title:fresh.calls[0][1].title, body:fresh.calls[0][1].body}]);
  await manage({...existing, result});
  assert.equal(existing.calls.length, 1);
  assert.equal(existing.calls[0][0], 'update');
  assert.equal(existing.calls[0][1].issue_number, 5);
});

test('recovery closes only its matching incident, leaving drills separate', async () => {
  const state = fixture([
    {number:1, title:'[MAX] Monitor alert drill', body:'<!-- max1102-monitor-drill -->'},
    {number:2, title:'[MAX] Production monitor incident', body:'<!-- max1102-monitor-production -->'}
  ]);
  await manage({...state, result:{status:'ok', drill:false}});
  assert.deepEqual(state.calls.map(x => [x[0], x[1].issue_number]), [['comment',2], ['update',2]]);
  assert.equal(state.calls[1][1].state, 'closed');
});

test('healthy probe with no incident creates no issue', async () => {
  const state = fixture([]);
  await manage({...state, result:{status:'ok', drill:false}});
  assert.deepEqual(state.calls, []);
});
