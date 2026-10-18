const fs = require('fs');
module.exports = async ({github, context, core, result: suppliedResult}) => {
  const result = suppliedResult || JSON.parse(fs.readFileSync('monitor-result.json', 'utf8'));
  const marker = result.drill ? '<!-- max1102-monitor-drill -->' : '<!-- max1102-monitor-production -->';
  const title = result.drill ? '[MAX] Monitor alert drill' : '[MAX] Production monitor incident';
  const url = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const issues = await github.paginate(github.rest.issues.listForRepo, {...context.repo, state:'open', per_page:100, creator:'github-actions[bot]'});
  const incident = issues.find(i => !i.pull_request && i.title === title && (i.body || '').includes(marker));
  const body = `${marker}\nMonitor result: **${result.status}**.\n\n[Workflow evidence](${url})\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``;
  if (result.status !== 'ok') {
    if (incident) await github.rest.issues.update({...context.repo, issue_number:incident.number, body});
    else await github.rest.issues.create({...context.repo, title, body});
  } else if (incident) {
    await github.rest.issues.createComment({...context.repo, issue_number:incident.number, body:`Recovered. [Successful probe](${url}).`});
    await github.rest.issues.update({...context.repo, issue_number:incident.number, state:'closed', state_reason:'completed'});
  }
  await core.summary.addHeading(result.drill ? 'Alert drill' : 'Production monitor').addCodeBlock(JSON.stringify(result, null, 2), 'json').write();
};
