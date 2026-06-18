"""Add handover photos/signature display to SDO timeline."""
filepath = 'frontend/src/pages/logistics/LogisticsDispatch.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The exact anchor text (first occurrence in collapseItems timeline)
anchor = (
    '              {sdo.received_by_name && (\n'
    '                        <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    '                          <span style={{ color: \'#64748b\', fontWeight: 500 }}>📥 Acknowledged: </span>'
)

insert = (
    '              {sdo.handover_photos && sdo.handover_photos.length > 0 && (\n'
    '                        <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    '                          <span style={{ color: \'#64748b\', fontWeight: 500 }}>📸 Handover Photos: </span>\n'
    '                          <Image.PreviewGroup>\n'
    '                            <Space size={4} wrap>\n'
    '                              {sdo.handover_photos.map((url, i) => (\n'
    "                                <Image key={i} src={url} alt={`Handover ${i+1}`} style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: null }} />\n"
    '                              ))}\n'
    '                            </Space>\n'
    '                          </Image.PreviewGroup>\n'
    '                        </div>\n'
    '              )}\n'
    '              {sdo.handover_signature && (\n'
    '                        <div style={{ marginTop: \'8px\', fontSize: \'12px\', borderTop: \'1px dashed #e2e8f0\', paddingTop: \'6px\' }}>\n'
    '                          <span style={{ color: \'#64748b\', fontWeight: 500 }}>✍️ Handover Signature: </span>\n'
    "                        <Image src={sdo.handover_signature} alt=\"Handover Signature\" style={{ maxHeight: 40, borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: 'Zoom' }} />\n"
    '                        </div>\n'
    '              )}\n'
    '\n'
)

pos = 0
count = 0
while True:
    idx = content.find(anchor, pos)
    if idx < 0:
        break
    content = content[:idx] + insert + content[idx:]
    pos = idx + len(insert) + 10
    count += 1
    if count >= 2:
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Added {count} handover photos display blocks to SDO timeline")
