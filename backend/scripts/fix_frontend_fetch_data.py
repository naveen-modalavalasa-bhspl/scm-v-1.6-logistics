"""
Fix fetchData() in LogisticsDispatch.jsx to handle individual API failures.
Currently uses Promise.all which crashes entirely when material-issues returns 403 for RM/DM users.
"""
import re

with open('../frontend/src/pages/logistics/LogisticsDispatch.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """  const fetchData = async () => {
    try {
      setLoading(true);
      const [mdoRes, masterRes, issuesRes, indentRes] = await Promise.all([
        api.get('/logistics/mdo'),
        api.get('/logistics/masters'),
        api.get('/warehouse/material-issues', { params: { page_size: 100, status: 'issued' } }),
        api.get('/indents', { params: { page_size: 100, available_for_issue: true } })
      ]);
      setMdos(mdoRes.data);
      setMasters(masterRes.data);

      const issuesList = issuesRes.data.items || issuesRes.data.data || issuesRes.data || [];
      setMaterialIssues(issuesList.filter(i => i.status === 'issued'));

      const indentsList = indentRes.data.items || indentRes.data.data || indentRes.data || [];
      setIndents(indentsList.map(i => ({ label: i.indent_number, value: i.id })));
    } catch (err) {
      console.error(err);
      message.error("Failed to load SCM dispatch plan desk data.");
    } finally {
      setLoading(false);
    }
  };"""

new_block = """  const fetchData = async () => {
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

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print("SUCCESS: fetchData() updated to handle individual API failures")
else:
    print("FAIL: Could not find the exact fetchData() block")
    # Try to find it with partial match
    idx = content.find("const fetchData = async")
    if idx >= 0:
        end = content.find("};", idx)
        print(f"Found fetchData at index {idx}, ends at ~{end}")
        print("---FIRST 300 CHARS---")
        print(repr(content[idx:idx+300]))
        print("---LAST 300 CHARS---")
        if end > idx:
            print(repr(content[max(0,end-300):end+2]))

with open('../frontend/src/pages/logistics/LogisticsDispatch.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("File saved.")
