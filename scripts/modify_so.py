import re

with open('frontend/src/pages/logistics/LogisticsSO.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add consignment packages fetch after the whItems fallback section
old_fetch = """        // Fallback to warehouse dispatches
          const whRes = await api.get('/warehouse/dispatch', { params: { search: selectedVehicle.vehicle_registration_no } });
          const whItems = whRes.data?.items || whRes.data?.data || whRes.data || [];
          if (whItems.length > 0) {
            setLinkedDispatch(whItems[0]);
          } else {
            setLinkedDispatch(null);
          }"""

new_fetch = """        // Fallback to warehouse dispatches
          const whRes = await api.get('/warehouse/dispatch', { params: { search: selectedVehicle.vehicle_registration_no } });
          const whItems = whRes.data?.items || whRes.data?.data || whRes.data || [];
          if (whItems.length > 0) {
            setLinkedDispatch(whItems[0]);
          } else {
            setLinkedDispatch(null);
          }
        // Fetch consignment packages for the linked dispatch
        if (matched || whItems.length > 0) {
          const dispatchData = matched || whItems[0];
          const miId = dispatchData.material_issue_id;
          if (miId) {
            try {
              const conRes = await api.get('/consignment/by-mi/' + miId);
              if (conRes.data && conRes.data.length > 0) {
                const conId = conRes.data[0].id;
                const [conDetailRes, ackRes] = await Promise.all([
                  api.get('/consignment/' + conId),
                  api.get('/consignment/' + conId + '/acknowledgements')
                ]);
                if (conDetailRes.data && conDetailRes.data.packages) {
                  setConsignmentPackages(conDetailRes.data.packages);
                }
                if (ackRes.data) {
                  setConsignmentAcks(ackRes.data);
                }
              }
            } catch (e2) {
              console.warn('Failed to fetch consignment:', e2);
            }
          }
        }"""

if old_fetch in content:
    content = content.replace(old_fetch, new_fetch, 1)
    print('1. Added consignment fetch after dispatch lookup')
else:
    print('1. FAILED - marker not found')

# 2. Add packages display in the acknowledge tab before linkedDispatch section
old_section = """                      ) : linkedDispatch ? (
                        <div style={{ padding: '8px' }}>"""

new_section = """                      ) : consignmentPackages.length > 0 ? (
                        <div style={{ padding: '8px' }}>
                          <Alert
                            message={<span style={{ fontWeight: 600 }}><GiftOutlined /> Consignment Packages Ready for Acknowledgment</span>}
                            description={
                              <div style={{ marginTop: '8px', fontSize: '12px' }}>
                                <p>Scan barcodes below to acknowledge delivery package by package.</p>
                                {consignmentPackages.map((pkg, idx) => (
                                  <Card
                                    key={pkg.id}
                                    size="small"
                                    style={{ marginBottom: '8px', borderRadius: '8px', border: '1px solid #e2e8f0' }}
                                    title={
                                      <Space>
                                        <Tag color="blue" style={{ fontFamily: 'monospace' }}>#{idx + 1}</Tag>
                                        <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{pkg.package_number}</span>
                                        <Tag>{pkg.package_type}</Tag>
                                        <Tag color={pkg.status === 'RECEIVED' ? 'success' : 'default'}>
                                          {pkg.status?.replace('_', ' ')}
                                        </Tag>
                                      </Space>
                                    }
                                    extra={
                                      <Space>
                                        {pkg.status !== 'RECEIVED' && (
                                          <Button size="small" icon={<BarcodeOutlined />}
                                            onClick={() => window.open('/consignment/package/' + pkg.id + '/label', '_blank')}>
                                            View Barcode
                                          </Button>
                                        )}
                                      </Space>
                                    }
                                  >
                                    <Row gutter={[12, 8]}>
                                      <Col span={8}><strong>Weight:</strong> {pkg.gross_weight_kg || 0} KG</Col>
                                      <Col span={8}><strong>Seal:</strong> {pkg.seal_number || 'N/A'}</Col>
                                      <Col span={8}><strong>Items:</strong> {pkg.material_count || 0}</Col>
                                    </Row>
                                    {pkg.items && pkg.items.length > 0 && (
                                      <Table
                                        size="small"
                                        pagination={false}
                                        rowKey="id"
                                        style={{ marginTop: '8px' }}
                                        dataSource={pkg.items}
                                        columns={[
                                          { title: 'Code', dataIndex: 'material_code', render: t => <span style={{ fontFamily: 'monospace', fontSize: '11px' }}>{t}</span> },
                                          { title: 'Material', dataIndex: 'material_name', render: t => <span style={{ fontSize: '11px' }}>{t}</span> },
                                          { title: 'Packed', dataIndex: 'quantity_packed', render: val => <b>{val}</b> },
                                          { title: 'Received', dataIndex: 'quantity_received', render: val => val ? <span style={{ color: '#16a34a', fontWeight: 600 }}>{val}</span> : <span style={{ color: '#94a3b8' }}>--</span> },
                                        ]}
                                      />
                                    )}
                                  </Card>
                                ))}
                              </div>
                            }
                            type="success"
                            showIcon
                          />
                          {consignmentAcks.length > 0 && (
                            <Card
                              size="small"
                              title={<span style={{ fontSize: '12px', fontWeight: 700 }}>Package Acknowledgements</span>}
                              style={{ marginTop: '12px', borderRadius: '8px' }}
                            >
                              <Table
                                size="small"
                                pagination={false}
                                rowKey="id"
                                dataSource={consignmentAcks}
                                columns={[
                                  { title: 'Package', dataIndex: 'package_number', render: t => <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{t}</span> },
                                  { title: 'Status', dataIndex: 'acknowledgement_status', render: t => <Tag color={t === 'ACCEPTED' ? 'success' : 'warning'}>{t}</Tag> },
                                  { title: 'By', dataIndex: 'acknowledged_by_name', render: t => t || '--' },
                                  { title: 'Condition', dataIndex: 'packaging_condition', render: t => t || '--' },
                                ]}
                              />
                            </Card>
                          )}
                          <Divider />
                          <Button type="primary" icon={<CheckCircleOutlined />} block
                            onClick={() => window.open('/logistics/dispatch-orders/' + (linkedDispatch?.dispatch_id || linkedDispatch?.id) + '/acknowledge', '_self')}
                            style={{ marginTop: '12px' }}>
                            Proceed to Acknowledge All Packages
                          </Button>
                        </div>
                      ) : linkedDispatch ? (
                        <div style={{ padding: '8px' }}>"""

if 'consignmentPackages.length' not in content:
    if old_section in content:
        content = content.replace(old_section, new_section, 1)
        print('2. Added packages display section')
    else:
        print('2. FAILED - section not found')
else:
    print('2. Already present')

with open('frontend/src/pages/logistics/LogisticsSO.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Script completed successfully!')
