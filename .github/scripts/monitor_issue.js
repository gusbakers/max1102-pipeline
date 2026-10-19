const fs = require('fs');
module.exports = async ({github, context, core, result: suppliedResult, incidentNumber}) => {
  const result = suppliedResult || JSON.parse(fs.readFileSync('monitor-result.json', 'utf8'));
  const marker = result.drill ? '<!-- max1102-monitor-drill -->' : '<!-- max1102-monitor-production -->';
  const title = result.drill ? '[MAX] Monitor alert drill' : '[MAX] Production monitor incident';
  const url = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const owned = i => !i.pull_request && i.user?.login === 'github-actions[bot]' && i.title === title && (i.body || '').includes(marker);
  let incident;
  if (incidentNumber !== undefined) {
    if (!Number.isSafeInteger(incidentNumber) || incidentNumber <= 0) throw new Error('Invalid incident number');
    incident = (await github.rest.issues.get({...context.repo, issue_number:incidentNumber})).data;
    if (!owned(incident)) throw new Error('Incident does not belong to this monitor');
  } else {
    // Avoid server-side bot filtering. During a drill use the create response ID:
    // a just-created issue may not immediately appear in a subsequent listing.
    const issues = await github.paginate(github.rest.issues.listForRepo, {...context.repo, state:'open', per_page:100});
    incident = issues.find(owned);
  }
  const body = `${marker}\nMonitor result: **${result.status}**.\n\n[Workflow evidence](${url})\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``;
  if (result.status !== 'ok') {
    if (incident) {
      await github.rest.issues.update({...context.repo, issue_number:incident.number, body, state:'open'});
    } else {
      incident = (await github.rest.issues.create({...context.repo, title, body})).data;
    }
  } else if (incident && incident.state !== 'closed') {
    await github.rest.issues.createComment({...context.repo, issue_number:incident.number, body:`Recovered. [Successful probe](${url}).`});
    await github.rest.issues.update({...context.repo, issue_number:incident.number, state:'closed', state_reason:'completed'});
  }
  await core.summary.addHeading(result.drill ? 'Alert drill' : 'Production monitor').addCodeBlock(JSON.stringify(result, null, 2), 'json').write();
  return {issueNumber:incident?.number ?? null, status:result.status};
};
