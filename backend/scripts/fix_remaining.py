"""Fix remaining frontend issues - add chain preview trigger and handover photos display."""
filepath = 'frontend/src/pages/logistics/LogisticsDispatch.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# 1. Add chain preview fetch trigger in handleIssueSelect
old1 = '  };\n\n  const fetchChainPreview'
new1 = (
    '  };\n'
    '\n'
    '    // Fetch chain preview when MI is selected and mode is multi-level\n'
    "    if (issueId && form.getFieldValue('dispatch_mode') === 'multi-level') {\n"
    '      fetchChainPreview(issueId);\n'
    '    }\n'
    '  };\n'
    '\n'
    '  const fetchChainPreview'
)
assert old1 in content, "Cannot find anchor 1"
content = content.replace(old1, new1, 1)
changes += 1
print(f"1. Chain preview fetch trigger added")

# 2. Add handover photos/signature display before received_by_name in SDO timeline
old2 = (
    '                          {sdo.received_by_name && (\n'
    '                          <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    "                            <span style={{ color: '#64748b', fontWeight: 500 }}>📥 Acknowledged: </span>"
)
new2 = (
    '                        {sdo.handover_photos && sdo.handover_photos.length > 0 && (\n'
    '                          <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    "                            <span style={{ color: '#64748b', fontWeight: 500 }}>📸 Handover Photos: </span>\n"
    '                            <Image.PreviewGroup>\n'
    '                              <Space size={4} wrap>\n'
    '                                {sdo.handover_photos.map((url, i) => (\n'
    "                                  <Image key={i} src={url} alt={`Handover ${i+1}`} style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: null }} />\n"
    '                                ))}\n'
    '                              </Space>\n'
    '                            </Image.PreviewGroup>\n'
    '                          </div>\n'
    '                        )}\n'
    '                        {sdo.handover_signature && (\n'
    '                          <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    "                            <span style={{ color: '#64748b', fontWeight: 500 }}>✍️ Handover Signature: </span>\n"
    "                            <Image src={sdo.handover_signature} alt=\"Handover Signature\" style={{ maxHeight: 40, borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: 'Zoom' }} />\n"
    '                          </div>\n'
    '                        )}\n'
    '\n'
    '                          {sdo.received_by_name && (\n'
    '                          <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    "                            <span style={{ color: '#64748b', fontWeight: 500 }}>📥 Acknowledged: </span>"
)

# Replace first occurrence
pos1 = content.find(old2)
assert pos1 >= 0, "Cannot find anchor 2"
content = content[:pos1] + new2 + content[pos1 + len(old2):]
changes += 1
print(f"2. First handover photos display added")

# Replace second occurrence (for hierarchy view)
pos2 = content.find(old2)
if pos2 >= 0:
    content = content[:pos2] + new2 + content[pos2 + len(old2):]
    changes += 1
    print(f"3. Second handover photos display added")
else:
    print(f"   (second occurrence not found - expected for hierarchy view)")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\nAll {changes} changes applied!")
