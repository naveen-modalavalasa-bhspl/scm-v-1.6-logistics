"""
Improve fetchData() to use Promise.allSettled for parallel resilience.
Keeps the speed of parallel requests but handles individual failures.
"""
import re

with open('../frontend/src/pages/logistics/LogisticsDispatch.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch MDOs independently (this is the primary data)
      try {
        const mdoRes = await api.get('/logistics/mdo');
        setMdos(mdoRes.data);
      } catch (mdoErr) {
        console.error('Failed to load MDOs:', mdoErr);
      }
      
      // Fetch masters independently
      try {
        const masterRes = await api.get('/logistics/masters');
        setMasters(masterRes.data);
      } catch (masterErr) {
        console.error('Failed to load masters:', masterErr);
      }
      
      // Fetch material issues independently (403 is expected for non-warehouse roles)
      try {
        const issuesRes = await api.get('/warehouse/material-issues', { params: { page_size: 100, status: 'issued' } });
        const issuesList = issuesRes.data.items || issuesRes.data.data || issuesRes.data || [];
        setMaterialIssues(issuesList.filter(i => i.status === 'issued'));
      } catch (issuesErr) {
        console.warn('Could not load material issues (may require warehouse permissions):', issuesErr);
      }
      
      // Fetch indents independently
      try {
        const indentRes = await api.get('/indents', { params: { page_size: 100, available_for_issue: true } });
        const indentsList = indentRes.data.items || indentRes.data.data || indentRes.data || [];
        setIndents(indentsList.map(i => ({ label: i.indent_number, value: i.id })));
      } catch (indentErr) {
        console.warn('Could not load indents:', indentErr);
      }
    } finally {
      setLoading(false);
    }
  };"""

new_block = """  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Use Promise.allSettled so one failed endpoint doesn't block the others
      const [mdoResult, masterResult, issuesResult, indentResult] = await Promise.allSettled([
        api.get('/logistics/mdo'),
        api.get('/logistics/masters'),
        api.get('/warehouse/material-issues', { params: { page_size: 100, status: 'issued' } }),
        api.get('/indents', { params: { page_size: 100, available_for_issue: true } })
      ]);
      
      // MDOs (primary data)
      if (mdoResult.status === 'fulfilled') {
        setMdos(mdoResult.value.data);
      } else {
        console.error('Failed to load MDOs:', mdoResult.reason);
      }
      
      // Masters
      if (masterResult.status === 'fulfilled') {
        setMasters(masterResult.value.data);
      } else {
        console.error('Failed to load masters:', masterResult.reason);
      }
      
      // Material Issues (403 expected for non-warehouse roles)
      if (issuesResult.status === 'fulfilled') {
        const issuesList = issuesResult.value.data.items || issuesResult.value.data.data || issuesResult.value.data || [];
        setMaterialIssues(issuesList.filter(i => i.status === 'issued'));
      } else {
        console.warn('Could not load material issues (may require warehouse permissions):', issuesResult.reason);
      }
      
      // Indents
      if (indentResult.status === 'fulfilled') {
        const indentsList = indentResult.value.data.items || indentResult.value.data.data || indentResult.value.data || [];
        setIndents(indentsList.map(i => ({ label: i.indent_number, value: i.id })));
      } else {
        console.warn('Could not load indents:', indentResult.reason);
      }
    } finally {
      setLoading(false);
    }
  };"""

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print("SUCCESS: fetchData() updated to use Promise.allSettled for parallel resilience")
else:
    print("FAIL: Could not find the fetchData block")
    idx = content.find("const fetchData = async () =>")
    if idx >= 0:
        print(f"Found at index {idx}")
        print(repr(content[idx:idx+500]))

with open('../frontend/src/pages/logistics/LogisticsDispatch.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("File saved.")
