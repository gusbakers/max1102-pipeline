const assert = require('node:assert/strict');
const test = require('node:test');
const manage = require('../../.github/scripts/monitor_issue.js');

function fixture(issues) {
  const calls = [];
  const stored = new Map(issues.map(i => [i.number, i]));
  const github = {paginate: async () => issues, rest: {issues: {
    listForRepo: () => {},
    get: async x => ({data:stored.get(x.issue_number)}),
    create: async x => {
      calls.push(['create', x]);
      const data = {...x, number:99, state:'open', user:{login:'github-actions[bot]'}};
      stored.set(data.number, data);
      return {data};
    },
    update: async x => {
      calls.push(['update', x]);
      const data = {...stored.get(x.issue_number), ...x};
      stored.set(x.issue_number, data);
      return {data};
    },
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
  const existing = fixture([{number:5, user:{login:'github-actions[bot]'}, title:fresh.calls[0][1].title, body:fresh.calls[0][1].body}]);
  await manage({...existing, result});
  assert.equal(existing.calls.length, 1);
  assert.equal(existing.calls[0][0], 'update');
  assert.equal(existing.calls[0][1].issue_number, 5);
});

test('recovery closes only its matching incident, leaving drills separate', async () => {
  const state = fixture([
    {number:1, user:{login:'github-actions[bot]'}, title:'[MAX] Monitor alert drill', body:'<!-- max1102-monitor-drill -->'},
    {number:2, user:{login:'github-actions[bot]'}, title:'[MAX] Production monitor incident', body:'<!-- max1102-monitor-production -->'}
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

test('immediate recovery uses the returned ID even before listings include it', async () => {
  const state = fixture([]);
  const created = await manage({...state, result:{status:'failed', drill:true}});
  assert.equal(created.issueNumber, 99);
  await manage({...state, incidentNumber:created.issueNumber, result:{status:'ok', drill:true}});
  assert.deepEqual(state.calls.map(x => x[0]), ['create','comment','update']);
  assert.equal(state.calls.at(-1)[1].state, 'closed');
});

test('recovery refuses an issue belonging to a person or another monitor', async () => {
  const state = fixture([{number:8, user:{login:'someone'}, title:'[MAX] Monitor alert drill', body:'<!-- max1102-monitor-drill -->'}]);
  await assert.rejects(manage({...state, incidentNumber:8, result:{status:'ok', drill:true}}), /does not belong/);
  assert.deepEqual(state.calls, []);
});
