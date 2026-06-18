"""
Apply all frontend changes to LogisticsDispatch.jsx in a single pass.
"""
filepath = 'frontend/src/pages/logistics/LogisticsDispatch.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = []

# 1. Chain preview state
replacements.append((
    "  const [uploadedUrls, setUploadedUrls] = useState({});\n  const [selectedMdo, setSelectedMdo] = useState(null);",
    "  const [uploadedUrls, setUploadedUrls] = useState({});\n  const [selectedMdo, setSelectedMdo] = useState(null);\n  const [chainPreview, setChainPreview] = useState(null);\n  const [loadingChain, setLoadingChain] = useState(false);"
))

# 2. Insert fetchChainPreview function BEFORE handleViewDetails
# We replace just the beginning of handleViewDetails with the new function + handleViewDetails
replacements.append((
    "  const handleViewDetails = async (mdo) => {",
    """  const fetchChainPreview = async (materialIssueId) => {
    if (!materialIssueId) {
      setChainPreview(null);
      return;
    }
    setLoadingChain(true);
    try {
      const res = await api.get('/logistics/preview-dispatch-chain', {
        params: { material_issue_id: materialIssueId }
      });
      setChainPreview(res.data);
    } catch (err) {
      console.error('Failed to fetch chain preview:', err);
      setChainPreview(null);
    } finally {
      setLoadingChain(false);
    }
  };

  const handleViewDetails = async (mdo) => {"""
))

# 3. Insert chain preview fetch trigger at ending of handleIssueSelect catch block
replacements.append((
    "      message.error('Failed to load material issue items');\n    } finally {\n      setLoadingIssue(false);\n    }\n  };\n\n  const handleViewDetails",
    """      message.error('Failed to load material issue items');
    } finally {
      setLoadingIssue(false);
    }
    
    // Fetch chain preview when MI is selected and mode is multi-level
    if (issueId && form.getFieldValue('dispatch_mode') === 'multi-level') {
      fetchChainPreview(issueId);
    }
  };

  const handleViewDetails"""
))

# 4. Add chain preview card before Reference Panel
replacements.append((
    "          {/* Side-by-Side Reference Panel */}\n          <Row gutter={[20, 20]} style={{ marginBottom: '20px' }}>",
    """          {/* Chain Preview Card - shown for multi-level mode */}
          {dispatchMode === 'multi-level' && chainPreview && chainPreview.chain && chainPreview.chain.length > 0 && (
            <Card
              size="small"
              title={
                <span style={{ color: '#0f172a', fontWeight: 700, fontSize: '13px' }}>
                  <GoldOutlined style={{ color: '#f59e0b' }} /> DISPATCH CHAIN - MULTI-LEVEL ROUTING
                </span>
              }
              style={{
                marginBottom: '20px',
                borderRadius: '12px',
                border: '1.5px solid #fde68a',
                background: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)',
                boxShadow: '0 2px 8px rgba(245, 158, 11, 0.08)'
              }}
            >
              <div style={{ marginBottom: '12px', padding: '8px 12px', background: '#ffffff', borderRadius: '8px', border: '1px solid #fde68a' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: '#92400e', fontWeight: 700, letterSpacing: '0.5px' }}>
                  <EnvironmentOutlined style={{ color: '#059669' }} /> ORIGIN: 
                </span>
                <strong style={{ color: '#78350f', fontSize: '13px', marginLeft: '6px' }}>{chainPreview.source_warehouse}</strong>
                <span style={{ color: '#92400e', fontSize: '11px', marginLeft: '8px' }}>-- Material flows through configured positions</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', position: 'relative', paddingLeft: '16px' }}>
                <div style={{
                  position: 'absolute', left: '7px', top: '14px', bottom: '14px',
                  width: '2px', background: 'linear-gradient(to bottom, #f59e0b, #e2e8f0)', zIndex: 1
                }} />
                {chainPreview.chain.map((pos, idx) => (
                  <div key={pos.position_id} style={{ display: 'flex', gap: '12px', position: 'relative', zIndex: 2 }}>
                    <div style={{
                      position: 'absolute', left: '-15px', top: '6px', width: '12px', height: '12px',
                      borderRadius: '50%', backgroundColor: '#ffffff',
                      border: pos.is_destination ? '3px solid #22c55e' : pos.can_approve ? '3px solid #f59e0b' : '3px solid #94a3b8',
                      zIndex: 3
                    }} />
                    <div style={{
                      flex: 1, background: '#ffffff', padding: '10px 14px', borderRadius: '8px',
                      border: pos.is_destination ? '1px solid #86efac' : '1px solid #fde68a'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          {pos.is_destination && <Tag color="green" style={{ border: 'none', fontWeight: 700, fontSize: '9px', padding: '0 4px', marginRight: '4px' }}>FINISH</Tag>}
                          {pos.can_view && !pos.can_approve && <Tag color="default" style={{ border: 'none', fontWeight: 700, fontSize: '9px', padding: '0 4px', marginRight: '4px' }}>VIEW ONLY</Tag>}
                          {pos.can_approve && <Tag color="gold" style={{ border: 'none', fontWeight: 700, fontSize: '9px', padding: '0 4px', marginRight: '4px' }}>HANDOVER</Tag>}
                          <strong style={{ fontSize: '12px', color: '#0f172a' }}>{pos.role_name}</strong>
                        </div>
                        <span style={{ fontSize: '10px', color: '#64748b', fontFamily: 'monospace', fontWeight: 600 }}>
                          Leg #{idx + 1}
                        </span>
                      </div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#475569' }}>
                        <span style={{ fontFamily: 'monospace', background: '#f1f5f9', padding: '1px 6px', borderRadius: '4px', marginRight: '6px' }}>
                          {pos.employee_code || '---'}
                        </span>
                        <strong>{pos.employee_name || 'Unassigned'}</strong>
                        <span style={{ color: '#94a3b8', marginLeft: '6px' }}>{pos.position_name}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {chainPreview.chain.length === 0 && (
                <Alert message="No custody chain configured for this project." type="info" showIcon style={{ borderRadius: '8px' }} />
              )}
            </Card>
          )}

          {/* Side-by-Side Reference Panel */}
          <Row gutter={[20, 20]} style={{ marginBottom: '20px' }}>"""
))

# 5. Chain preview reset on submit
replacements.append((
    "          setSelectedIssue(null);\n          setSelectedIndent(null);\n          setSelectedIndentItems([]);\n          setSelectedIssueItems([]);\n          setUploadedUrls({});\n          await fetchData();",
    "          setSelectedIssue(null);\n          setSelectedIndent(null);\n          setSelectedIndentItems([]);\n          setSelectedIssueItems([]);\n          setUploadedUrls({});\n          setChainPreview(null);\n          await fetchData();"
))

# 6. Chain preview reset on modal cancel
replacements.append((
    "          setSelectedIssue(null);\n          setUploadedUrls({});\n          setIsReadOnly(false);\n          setSelectedMdo(null);\n        }}",
    "          setSelectedIssue(null);\n          setUploadedUrls({});\n          setChainPreview(null);\n          setIsReadOnly(false);\n          setSelectedMdo(null);\n        }}"
))

# 7. Handover payload - add photos
replacements.append((
    "        otp: values.otp\n      };\n      await api.post(`/logistics/sdo/${activeLeg.id}/handover`, payload);",
    "        otp: values.otp,\n        handover_photos: values.handover_photos || undefined,\n        handover_signature: values.handover_signature || undefined\n      };\n      await api.post(`/logistics/sdo/${activeLeg.id}/handover`, payload);"
))

# 8. Receive payload - add photos
replacements.append((
    "        receiving_remarks: values.receiving_remarks\n      };\n      await api.post(`/logistics/sdo/${activeLeg.id}/receive`, payload);",
    "        receiving_remarks: values.receiving_remarks,\n        receipt_photos: values.receipt_photos || undefined,\n        receipt_signature: values.receipt_signature || undefined\n      };\n      await api.post(`/logistics/sdo/${activeLeg.id}/receive`, payload);"
))

# 9. Add photo fields to Handover Leg Modal
replacements.append((
    '          <Form.Item name="remarks" label="Remarks">\n            <Input.TextArea rows={2} placeholder="Optional instructions or handoff notes" />\n          </Form.Item>\n\n          <Form.Item name="otp" label="Verification OTP (If required)">',
    """          <div style={{ background: '#f0fdf4', padding: '12px', borderRadius: '8px', border: '1px solid #bbf7d0', marginBottom: '16px' }}>
            <Text style={{ fontSize: '12px', fontWeight: 700, color: '#166534', display: 'block', marginBottom: '8px' }}>
              <UploadOutlined /> Material Photos & Signature
            </Text>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="handover_photos" label="Material Photos (URLs)" style={{ marginBottom: '8px' }}>
                  <Select mode="tags" placeholder="Paste photo URLs" tokenSeparators={[',']} open={false} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="handover_signature" label="Handover Signature (URL)" style={{ marginBottom: '8px' }}>
                  <Input placeholder="Paste signature image URL" />
                </Form.Item>
              </Col>
            </Row>
          </div>

          <Form.Item name="remarks" label="Remarks">
            <Input.TextArea rows={2} placeholder="Optional instructions or handoff notes" />
          </Form.Item>

          <Form.Item name="otp" label="Verification OTP (If required)">"""
))

# 10. Add photo fields to Receive Leg Modal
replacements.append((
    '          <Form.Item name="receiving_remarks" label="Receiving Remarks / Notes">\n            <Input.TextArea rows={3} placeholder="Describe package condition, discrepancy details, etc." />\n          </Form.Item>\n\n          <div style={{ display: \'flex\', justifyContent: \'flex-end\', gap: \'8px\', marginTop: \'20px\' }}>',
    """          <div style={{ background: '#fef2f2', padding: '12px', borderRadius: '8px', border: '1px solid #fecaca', marginBottom: '16px' }}>
            <Text style={{ fontSize: '12px', fontWeight: 700, color: '#991b1b', display: 'block', marginBottom: '8px' }}>
              <UploadOutlined /> Receipt Photos & Signature
            </Text>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="receipt_photos" label="Condition Photos (URLs)" style={{ marginBottom: '8px' }}>
                  <Select mode="tags" placeholder="Paste photo URLs" tokenSeparators={[',']} open={false} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="receipt_signature" label="Receiver Signature (URL)" style={{ marginBottom: '8px' }}>
                  <Input placeholder="Paste signature image URL" />
                </Form.Item>
              </Col>
            </Row>
          </div>

          <Form.Item name="receiving_remarks" label="Receiving Remarks / Notes">
            <Input.TextArea rows={3} placeholder="Describe package condition, discrepancy details, etc." />
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>"""
))

# 11. Add photo display to SDO timeline - content block to insert after handover info and before received_by_name section
replacements.append((
    """                        {sdo.received_by_name && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>📥 Acknowledged: </span>
                            <span style={{ color: '#334155' }}>
                              by <strong>{sdo.received_by_name}</strong> at {formatDate(sdo.received_at)}
                            </span>
                            <div style={{ background: '#ffffff', padding: '6px 10px', borderRadius: '4px', marginTop: '4px', fontSize: '11px', border: '1px solid #f1f5f9' }}>
                              <span><strong>Seal Intact:</strong> {sdo.seal_intact ? 'Yes' : 'No'} | </span>
                              <span><strong>Condition:</strong> <Tag color={sdo.packaging_condition === 'INTACT' ? 'green' : 'red'} style={{ border: 'none', fontSize: '10px', padding: '0 4px', margin: 0 }}>{sdo.packaging_condition}</Tag> | </span>
                              {sdo.discrepancy_reported ? <span style={{ color: '#ef4444' }}><strong>Discrepancy Reported!</strong> | </span> : null}
                              {sdo.receiving_remarks && <span><strong>Remarks:</strong> {sdo.receiving_remarks}</span>}
                            </div>
                          </div>
                        )}""",
    """                        {sdo.handover_photos && sdo.handover_photos.length > 0 && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>📸 Handover Photos: </span>
                            <Image.PreviewGroup>
                              <Space size={4} wrap>
                                {sdo.handover_photos.map((url, i) => (
                                  <Image key={i} src={url} alt={`Handover ${i+1}`} style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: null }} />
                                ))}
                              </Space>
                            </Image.PreviewGroup>
                          </div>
                        )}
                        {sdo.handover_signature && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>Sign: </span>
                            <Image src={sdo.handover_signature} alt="Handover Signature" style={{ maxHeight: 40, borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: 'Zoom' }} />
                          </div>
                        )}
                        {sdo.received_by_name && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>📥 Acknowledged: </span>
                            <span style={{ color: '#334155' }}>
                              by <strong>{sdo.received_by_name}</strong> at {formatDate(sdo.received_at)}
                            </span>
                            <div style={{ background: '#ffffff', padding: '6px 10px', borderRadius: '4px', marginTop: '4px', fontSize: '11px', border: '1px solid #f1f5f9' }}>
                              <span><strong>Seal Intact:</strong> {sdo.seal_intact ? 'Yes' : 'No'} | </span>
                              <span><strong>Condition:</strong> <Tag color={sdo.packaging_condition === 'INTACT' ? 'green' : 'red'} style={{ border: 'none', fontSize: '10px', padding: '0 4px', margin: 0 }}>{sdo.packaging_condition}</Tag> | </span>
                              {sdo.discrepancy_reported ? <span style={{ color: '#ef4444' }}><strong>Discrepancy Reported!</strong> | </span> : null}
                              {sdo.receiving_remarks && <span><strong>Remarks:</strong> {sdo.receiving_remarks}</span>}
                            </div>
                          </div>
                        )}
                        {sdo.receipt_photos && sdo.receipt_photos.length > 0 && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>📸 Receipt Photos: </span>
                            <Image.PreviewGroup>
                              <Space size={4} wrap>
                                {sdo.receipt_photos.map((url, i) => (
                                  <Image key={i} src={url} alt={`Receipt ${i+1}`} style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: null }} />
                                ))}
                              </Space>
                            </Image.PreviewGroup>
                          </div>
                        )}
                        {sdo.receipt_signature && (
                          <div style={{ marginTop: '8px', fontSize: '12px', borderTop: '1px dashed #e2e8f0', paddingTop: '6px' }}>
                            <span style={{ color: '#64748b', fontWeight: 500 }}>Sign: </span>
                            <Image src={sdo.receipt_signature} alt="Receiver Signature" style={{ maxHeight: 40, borderRadius: '4px', border: '1px solid #e2e8f0', cursor: 'pointer' }} preview={{ mask: 'Zoom' }} />
                          </div>
                        )}"""
))

# 12. Same for SECOND occurrence (hierarchy view) - same replacement using same old string
# (By using replace with a count of 2 total, both occurrences get replaced)
# But we need 2 replacements, and the first replace consumes one instance...

# Let's use a different approach - replace first occurrence, then second
first_pos = content.find(replacements[-1][0])
if first_pos >= 0:
    # Insert the replacement at the first position
    old_str = replacements[-1][0]
    new_str = replacements[-1][1]
    content = content[:first_pos] + new_str + content[first_pos + len(old_str):]
    print(f"11. First SDO timeline photo display added")
    
    # Find second occurrence
    second_pos = content.find(old_str, first_pos + len(new_str))
    if second_pos >= 0:
        content = content[:second_pos] + new_str + content[second_pos + len(old_str):]
        print(f"12. Second SDO timeline photo display added")
else:
    print("ERROR: Cannot find anchor 11")
    # Try all other replacements first

# Apply all other replacements
for i, (old, new) in enumerate(replacements[:-1], 1):
    if old in content:
        content = content.replace(old, new, 1)
        print(f"{i}. Applied successfully")
    else:
        print(f"{i}. Skipped - pattern not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\nDone! File written.")
