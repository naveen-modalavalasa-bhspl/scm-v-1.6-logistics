import React, { useState, useEffect, useCallback } from 'react';
import Barcode from 'react-barcode';
import {
  Modal, Table, Tag, Button, Form, Select, InputNumber, Input,
  Space, Spin, App, Row, Col, Divider, Alert, Tooltip, Empty,
  Typography, Card, Badge, Popconfirm
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, PrinterOutlined, DownloadOutlined,
  BoxPlotOutlined, GiftOutlined, CheckCircleOutlined,
  CloseCircleOutlined, LockOutlined, WarningOutlined
} from '@ant-design/icons';
import api from '../../config/api';
import { formatNumber } from '../../utils/helpers';

const { Text } = Typography;
const { Option } = Select;

const PARENT_TYPES = ['PALLET', 'CONTAINER', 'BUNDLE', 'CRATE', 'CAGE', 'SHRINK_WRAP'];

export default function ParentPackagingModal({ visible, onClose, consignment, onUpdated }) {
  const { message } = App.useApp();

  const [loading, setLoading] = useState(false);
  const [parentPackages, setParentPackages] = useState([]);
  const [availablePackages, setAvailablePackages] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [addToParentId, setAddToParentId] = useState(null);
  const [form] = Form.useForm();
  const [selectedChildIds, setSelectedChildIds] = useState([]);
  const [printLabel, setPrintLabel] = useState(null);

  const fetchData = useCallback(async () => {
    if (!consignment?.id) return;
    try {
      setLoading(true);
      const [parentsRes, availRes] = await Promise.all([
        api.get(`/consignment/${consignment.id}/parent-packages`),
        api.get(`/consignment/${consignment.id}/parent-packages/available-packages`),
      ]);
      setParentPackages(parentsRes.data || []);
      setAvailablePackages(availRes.data || []);
    } catch (err) {
      console.error('Failed to fetch parent packages:', err);
      message.error('Failed to load parent packaging data');
    } finally {
      setLoading(false);
    }
  }, [consignment?.id, message]);

  useEffect(() => {
    if (visible) {
      fetchData();
      setShowCreateForm(false);
      setPrintLabel(null);
      form.resetFields();
      setSelectedChildIds([]);
      setAddToParentId(null);
    }
  }, [visible, fetchData, form]);

  // Packages that are NOT assigned to any parent
  const unassignedPackages = availablePackages.filter(p => !p.assigned_to_parent);

  const handleCreateSubmit = async (values) => {
    if (selectedChildIds.length === 0) {
      message.warning('Select at least one package to add to the parent');
      return;
    }
    try {
      setCreateLoading(true);
      await api.post(`/consignment/${consignment.id}/parent-packages`, {
        parent_package_type: values.parent_package_type || 'PALLET',
        tare_weight_kg: values.tare_weight_kg || 0,
        length_cm: values.length_cm || null,
        width_cm: values.width_cm || null,
        height_cm: values.height_cm || null,
        seal_number: values.seal_number || null,
        child_package_ids: selectedChildIds,
      });
      message.success('Parent package created successfully!');
      setShowCreateForm(false);
      form.resetFields();
      setSelectedChildIds([]);
      await fetchData();
      if (onUpdated) onUpdated();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to create parent package';
      message.error(detail);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleAddChildren = async (parentId) => {
    if (selectedChildIds.length === 0) {
      message.warning('Select packages to add');
      return;
    }
    try {
      setCreateLoading(true);
      await api.post(`/consignment/${consignment.id}/parent-packages/${parentId}/children`, {
        child_package_ids: selectedChildIds,
      });
      message.success('Packages added to parent!');
      setSelectedChildIds([]);
      setAddToParentId(null);
      await fetchData();
      if (onUpdated) onUpdated();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to add packages');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleRemoveChild = async (parentId, childPackageId) => {
    try {
      await api.delete(`/consignment/${consignment.id}/parent-packages/${parentId}/children/${childPackageId}`);
      message.success('Package removed from parent');
      await fetchData();
      if (onUpdated) onUpdated();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to remove package');
    }
  };

  const handleDeleteParent = async (parentId) => {
    try {
      await api.delete(`/consignment/${consignment.id}/parent-packages/${parentId}`);
      message.success('Parent package deleted');
      await fetchData();
      if (onUpdated) onUpdated();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to delete parent package');
    }
  };

  const handlePrintLabel = async (pp) => {
    try {
      const res = await api.get(`/consignment/${consignment.id}/parent-packages/${pp.id}/label`);
      setPrintLabel(res.data);
    } catch (err) {
      message.error('Failed to load label data');
    }
  };

  const handleDownloadLabel = async (pp) => {
    try {
      const res = await api.get(`/consignment/${consignment.id}/parent-packages/${pp.id}/label`);
      const label = res.data;
      _openPrintWindow(label);
    } catch (err) {
      message.error('Failed to generate label');
    }
  };

  const _openPrintWindow = (label) => {
    const w = window.open('', '_blank', 'width=500,height=700');
    if (!w) {
      message.error('Pop-up blocked. Please allow pop-ups for this site.');
      return;
    }
    const childList = (label.children || []).map((c, i) =>
      `<tr><td style="padding:3px 8px;border-bottom:1px solid #ddd;font-size:12px;">${i + 1}</td>
       <td style="padding:3px 8px;border-bottom:1px solid #ddd;font-size:12px;font-family:monospace;">${c.package_number || '-'}</td>
       <td style="padding:3px 8px;border-bottom:1px solid #ddd;font-size:12px;">${c.package_type || '-'}</td>
       <td style="padding:3px 8px;border-bottom:1px solid #ddd;font-size:12px;text-align:right;">${c.gross_weight_kg || 0} kg</td></tr>`
    ).join('');

    w.document.write(`<!DOCTYPE html><html><head><title>Label: ${label.parent_package_number}</title>
      <style>
        @page { size: 4in 6in; margin: 6mm; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Courier New', Courier, monospace; font-size: 11px; color: #000; }
        .label { border: 2px solid #000; padding: 10px; width: 100%; max-width: 3.8in; }
        .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 8px; }
        .header h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
        .header .type { font-size: 12px; font-weight: bold; }
        .barcode-section { text-align: center; margin: 8px 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .barcode-section svg { max-width: 100%; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; margin: 8px 0; }
        .info-grid div { margin-bottom: 2px; }
        .info-grid .label-text { font-size: 9px; color: #555; font-weight: bold; text-transform: uppercase; }
        .info-grid .value { font-size: 11px; font-weight: bold; }
        .child-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        .child-table th { background: #000; color: #fff; padding: 4px 8px; font-size: 10px; text-align: left; }
        .footer { margin-top: 8px; border-top: 1px solid #000; padding-top: 4px; font-size: 9px; text-align: center; }
      </style>
    </head><body>
      <div class="label">
        <div class="header">
          <h2>PARENT PACKAGE</h2>
          <div class="type">${label.parent_package_type}</div>
        </div>
        <div style="text-align:center;margin:6px 0;">
          <strong style="font-size:16px;letter-spacing:0.5px;">${label.parent_package_number}</strong>
        </div>
        <div class="barcode-section">
          <svg id="barcode-svg"></svg>
        </div>
        <div class="info-grid">
          <div><span class="label-text">Consignment:</span><br/><span class="value">${label.consignment_number || '-'}</span></div>
          <div><span class="label-text">Seal #:</span><br/><span class="value">${label.seal_number || '-'}</span></div>
          <div><span class="label-text">Receiver:</span><br/><span class="value">${label.receiver_name || '-'} (${label.receiver_employee_code || '-'})</span></div>
          <div><span class="label-text">Position:</span><br/><span class="value">${label.receiver_position_code || '-'}</span></div>
          <div><span class="label-text">Destination:</span><br/><span class="value">${label.destination_warehouse_name || '-'}</span></div>
          <div><span class="label-text">Child Pkgs:</span><br/><span class="value">${label.child_package_count} &nbsp;|&nbsp; Items: ${label.total_items}</span></div>
          <div><span class="label-text">Gross Wt:</span><br/><span class="value">${label.gross_weight_kg || 0} KG</span></div>
          <div><span class="label-text">Volume:</span><br/><span class="value">${label.total_volume_cft || 0} CFT</span></div>
          ${label.length_cm ? `<div><span class="label-text">Dims (L×W×H):</span><br/><span class="value">${label.length_cm}×${label.width_cm}×${label.height_cm} cm</span></div>` : ''}
        </div>
        ${label.children && label.children.length > 0 ? `
        <table class="child-table">
          <thead><tr><th>#</th><th>Package</th><th>Type</th><th style="text-align:right;">Weight</th></tr></thead>
          <tbody>${childList}</tbody>
        </table>` : ''}
        <div class="footer">
          Printed: ${new Date().toLocaleString()} | ${label.parent_package_number}
        </div>
      </div>
      <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"><\/script>
      <script>
        try { JsBarcode('#barcode-svg', '${label.parent_package_number}', { width: 1.5, height: 40, fontSize: 10, margin: 2 }); } catch(e) {}
        window.onload = function() { setTimeout(function() { window.print(); }, 500); };
      <\/script>
    </body></html>`);
    w.document.close();
  };

  // ── Package selection table columns ──
  const selectionColumns = [
    {
      title: '',
      key: 'select',
      width: 50,
      render: (_, record) => {
        const isSelected = selectedChildIds.includes(record.id);
        const isAssigned = !!record.assigned_to_parent;
        if (isAssigned) {
          return (
            <Tooltip title={`Already in ${record.assigned_to_parent.parent_package_number}`}>
              <LockOutlined style={{ color: '#d9d9d9', fontSize: 16 }} />
            </Tooltip>
          );
        }
        return (
          <CheckCircleOutlined
            style={{
              fontSize: 18,
              color: isSelected ? '#16a34a' : '#d9d9d9',
              cursor: 'pointer',
            }}
            onClick={() => {
              if (isSelected) {
                setSelectedChildIds(prev => prev.filter(id => id !== record.id));
              } else {
                setSelectedChildIds(prev => [...prev, record.id]);
              }
            }}
          />
        );
      },
    },
    {
      title: 'Package #',
      dataIndex: 'package_number',
      key: 'pkg',
      render: (v) => <span style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: 12 }}>{v}</span>,
    },
    { title: 'Type', dataIndex: 'package_type', key: 'type', width: 70 },
    {
      title: 'Weight',
      dataIndex: 'gross_weight_kg',
      key: 'wt',
      width: 90,
      render: (v) => <span style={{ fontFamily: 'monospace' }}>{v || 0} KG</span>,
    },
    { title: 'Items', dataIndex: 'material_count', key: 'items', width: 60, align: 'center' },
    {
      title: 'Status',
      key: 'status',
      width: 140,
      render: (_, r) => {
        if (r.assigned_to_parent) {
          return (
            <Tag icon={<LockOutlined />} color="default" style={{ fontSize: 11 }}>
              {r.assigned_to_parent.parent_package_number}
            </Tag>
          );
        }
        return <Tag color="green" style={{ fontSize: 11 }}>Available</Tag>;
      },
    },
  ];

  return (
    <>
      <Modal
        title={
          <Space>
            <BoxPlotOutlined style={{ color: '#4f46e5' }} />
            <span style={{ fontWeight: 700 }}>Parent Packaging</span>
            <Tag color="blue">{consignment?.consignment_number}</Tag>
          </Space>
        }
        open={visible}
        onCancel={onClose}
        width={950}
        footer={null}
        destroyOnHidden
        styles={{ body: { maxHeight: '75vh', overflowY: 'auto' } }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : (
          <div>
            {/* ── Existing Parent Packages ── */}
            {parentPackages.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <Divider orientation="left" style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 700 }}>
                  Existing Parent Packages ({parentPackages.length})
                </Divider>
                {parentPackages.map((pp) => (
                  <Card
                    key={pp.id}
                    size="small"
                    style={{
                      marginBottom: 12,
                      borderRadius: 10,
                      border: '1px solid #e2e8f0',
                      background: '#fafafa',
                    }}
                    title={
                      <Space>
                        <BoxPlotOutlined style={{ color: '#4f46e5' }} />
                        <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 13 }}>
                          {pp.parent_package_number}
                        </span>
                        <Tag color="purple">{pp.parent_package_type}</Tag>
                        <Badge count={pp.child_package_count} style={{ backgroundColor: '#4f46e5' }} />
                        <Tag color={pp.status === 'PACKED' ? 'blue' : 'default'} style={{ fontSize: 11 }}>
                          {pp.status}
                        </Tag>
                      </Space>
                    }
                    extra={
                      <Space size="small">
                        {consignment?.status in { DRAFT: 1, PACKED: 1 } && (
                          <Tooltip title="Add more packages to this parent">
                            <Button
                              size="small"
                              icon={<PlusOutlined />}
                              onClick={() => {
                                setAddToParentId(addToParentId === pp.id ? null : pp.id);
                                setShowCreateForm(false);
                                setSelectedChildIds([]);
                              }}
                              type={addToParentId === pp.id ? 'primary' : 'default'}
                            >
                              Add Pkgs
                            </Button>
                          </Tooltip>
                        )}
                        <Tooltip title="Print / Download Label">
                          <Button
                            size="small"
                            icon={<PrinterOutlined />}
                            onClick={() => handlePrintLabel(pp)}
                          />
                        </Tooltip>
                        <Tooltip title="Download Label (opens print window)">
                          <Button
                            size="small"
                            icon={<DownloadOutlined />}
                            onClick={() => handleDownloadLabel(pp)}
                          />
                        </Tooltip>
                        {consignment?.status in { DRAFT: 1, PACKED: 1 } && (
                          <Popconfirm
                            title="Delete this parent package?"
                            description="All child packages will be released."
                            onConfirm={() => handleDeleteParent(pp.id)}
                            okText="Delete"
                            cancelText="Cancel"
                            okButtonProps={{ danger: true }}
                          >
                            <Tooltip title="Delete parent package">
                              <Button size="small" danger icon={<DeleteOutlined />} />
                            </Tooltip>
                          </Popconfirm>
                        )}
                      </Space>
                    }
                  >
                    <Row gutter={[16, 8]}>
                      <Col xs={5}><Text type="secondary" style={{ fontSize: 11 }}>Tare Wt</Text><br/><strong>{pp.tare_weight_kg || 0} KG</strong></Col>
                      <Col xs={5}><Text type="secondary" style={{ fontSize: 11 }}>Gross Wt</Text><br/><strong>{pp.gross_weight_kg || 0} KG</strong></Col>
                      <Col xs={5}><Text type="secondary" style={{ fontSize: 11 }}>Volume</Text><br/><strong>{pp.total_volume_cft || 0} CFT</strong></Col>
                      <Col xs={5}><Text type="secondary" style={{ fontSize: 11 }}>Total Items</Text><br/><strong>{pp.total_items}</strong></Col>
                      <Col xs={4}><Text type="secondary" style={{ fontSize: 11 }}>Seal #</Text><br/><strong>{pp.seal_number || '—'}</strong></Col>
                    </Row>

                    {/* Children list */}
                    {pp.children && pp.children.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', fontWeight: 600 }}>Child Packages:</Text>
                        <div style={{ marginTop: 4 }}>
                          {pp.children.map((c) => (
                            <div
                              key={c.child_package_id}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '4px 8px',
                                background: '#fff',
                                border: '1px solid #f0f0f0',
                                borderRadius: 6,
                                marginBottom: 4,
                              }}
                            >
                              <Space size="small">
                                <Text style={{ fontSize: 11, color: '#94a3b8' }}>#{c.sequence_number}</Text>
                                <Text style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: 12 }}>
                                  {c.package_number}
                                </Text>
                                <Tag style={{ fontSize: 10 }}>{c.package_type}</Tag>
                                <Text style={{ fontSize: 11, color: '#64748b' }}>{c.gross_weight_kg || 0} KG</Text>
                                <Text style={{ fontSize: 11, color: '#64748b' }}>{c.material_count || 0} items</Text>
                              </Space>
                              {consignment?.status in { DRAFT: 1, PACKED: 1 } && (
                                <Popconfirm
                                  title={`Remove ${c.package_number} from this parent?`}
                                  onConfirm={() => handleRemoveChild(pp.id, c.child_package_id)}
                                  okText="Remove"
                                  cancelText="Cancel"
                                  okButtonProps={{ danger: true, size: 'small' }}
                                >
                                  <Button size="small" type="text" danger icon={<CloseCircleOutlined />} />
                                </Popconfirm>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}

            {parentPackages.length === 0 && !showCreateForm && (
              <Empty
                description="No parent packages created yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ marginBottom: 20 }}
              />
            )}

            {/* ── Add to Existing Parent: Package Selector ── */}
            {addToParentId && (
              <div style={{ marginBottom: 20, background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 10, padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <Space>
                    <PlusOutlined style={{ color: '#2563eb' }} />
                    <Text strong style={{ color: '#1d4ed8' }}>
                      Select packages to add to parent
                    </Text>
                  </Space>
                  <Space>
                    <Button size="small" onClick={() => setAddToParentId(null)}>Cancel</Button>
                    <Button
                      size="small"
                      type="primary"
                      disabled={selectedChildIds.length === 0}
                      loading={createLoading}
                      onClick={() => handleAddChildren(addToParentId)}
                    >
                      Add Selected ({selectedChildIds.length})
                    </Button>
                  </Space>
                </div>
                {unassignedPackages.length === 0 ? (
                  <Alert message="No unassigned packages available in this consignment" type="warning" showIcon />
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <Text strong>Select packages to add:</Text>
                    <Select
                      mode="multiple"
                      placeholder="Select packages to add..."
                      style={{ width: '100%' }}
                      value={selectedChildIds}
                      onChange={(vals) => setSelectedChildIds(vals)}
                    >
                      {unassignedPackages.map(pkg => (
                        <Option key={pkg.id} value={pkg.id}>
                          {pkg.package_number} ({pkg.package_type} - {pkg.gross_weight_kg || 0} KG)
                        </Option>
                      ))}
                    </Select>
                  </div>
                )}
              </div>
            )}

            {/* ── Create Form ── */}
            {showCreateForm && (
              <Card
                title={
                  <Space>
                    <PlusOutlined />
                    <span>Create Parent Package</span>
                  </Space>
                }
                size="small"
                style={{ marginBottom: 20, borderRadius: 10, border: '1px solid #cbd5e1' }}
                extra={<Button size="small" onClick={() => setShowCreateForm(false)}>Cancel</Button>}
              >
                <Form form={form} layout="vertical" onFinish={handleCreateSubmit} initialValues={{ parent_package_type: 'PALLET', tare_weight_kg: 0 }}>
                  <Row gutter={12}>
                    <Col xs={12} md={6}>
                      <Form.Item label="Parent Type" name="parent_package_type" rules={[{ required: true }]}>
                        <Select>
                          {PARENT_TYPES.map(t => <Option key={t} value={t}>{t}</Option>)}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col xs={12} md={6}>
                      <Form.Item label="Tare Weight (KG)" name="tare_weight_kg" rules={[{ required: true }]}>
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={8} md={4}>
                      <Form.Item label="Length (cm)" name="length_cm">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={8} md={4}>
                      <Form.Item label="Width (cm)" name="width_cm">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={8} md={4}>
                      <Form.Item label="Height (cm)" name="height_cm">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item label="Seal Number" name="seal_number">
                        <Input placeholder="Optional seal number..." />
                      </Form.Item>
                    </Col>
                  </Row>

                  <div style={{ marginBottom: 12 }}>
                    <Text strong>Select Child Packages for this Parent ({selectedChildIds.length} selected):</Text>
                  </div>

                  {unassignedPackages.length === 0 ? (
                    <Alert message="All packages in this consignment are already assigned to other parent packages." type="error" showIcon style={{ marginBottom: 16 }} />
                  ) : (
                    <Form.Item
                      label="Select Child Packages (Multi-select)"
                      name="child_package_ids"
                      rules={[{ required: true, message: 'Please select at least one package' }]}
                      style={{ marginBottom: 16 }}
                    >
                      <Select
                        mode="multiple"
                        placeholder="Select packages to group..."
                        style={{ width: '100%' }}
                        onChange={(vals) => setSelectedChildIds(vals)}
                      >
                        {unassignedPackages.map(pkg => (
                          <Option key={pkg.id} value={pkg.id}>
                            {pkg.package_number} ({pkg.package_type} - {pkg.gross_weight_kg || 0} KG)
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  )}

                  <Form.Item style={{ margin: 0, textAlign: 'right' }}>
                    <Button type="primary" htmlType="submit" loading={createLoading} disabled={selectedChildIds.length === 0}>
                      Create and Link Packages
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            )}

            {/* Actions Footer */}
            {!showCreateForm && !addToParentId && consignment?.status in { DRAFT: 1, PACKED: 1 } && (
              <div style={{ textAlign: 'center', marginTop: 12 }}>
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setShowCreateForm(true);
                    setSelectedChildIds([]);
                    form.resetFields();
                  }}
                  style={{ width: '40%', height: 38, borderRadius: 8, fontWeight: 600 }}
                >
                  Create Parent Package
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Label Print Preview Modal */}
      <Modal
        title="Print Label Preview"
        open={!!printLabel}
        onCancel={() => setPrintLabel(null)}
        footer={[
          <Button key="close" onClick={() => setPrintLabel(null)}>Close</Button>,
          <Button key="print" type="primary" icon={<PrinterOutlined />} onClick={() => _openPrintWindow(printLabel)}>
            Print Label
          </Button>
        ]}
        width={400}
      >
        {printLabel && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '10px 0' }}>
            <div style={{ border: '2px solid #000', padding: 15, width: '100%', fontFamily: 'monospace', fontSize: 11 }}>
              <div style={{ textAlign: 'center', borderBottom: '2px solid #000', paddingBottom: 6, marginBottom: 8 }}>
                <h3 style={{ margin: 0 }}>PARENT PACKAGE</h3>
                <strong>{printLabel.parent_package_type}</strong>
              </div>
              <div style={{ textAlign: 'center', margin: '8px 0' }}>
                <strong style={{ fontSize: 14 }}>{printLabel.parent_package_number}</strong>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '8px 0', gap: 8 }}>
                <Barcode value={printLabel.parent_package_number} width={1.2} height={40} fontSize={10} />
              </div>
              <Divider style={{ margin: '8px 0', borderBlockStart: '1px solid #000' }} />
              <div><strong>Consignment:</strong> {printLabel.consignment_number}</div>
              <div><strong>Seal #:</strong> {printLabel.seal_number || '—'}</div>
              <div><strong>Destination:</strong> {printLabel.destination_warehouse_name || '—'}</div>
              <div><strong>Receiver:</strong> {printLabel.receiver_name} ({printLabel.receiver_employee_code})</div>
              <div><strong>Child Packages:</strong> {printLabel.child_package_count}</div>
              <div><strong>Gross Weight:</strong> {printLabel.gross_weight_kg} KG</div>
              <div><strong>Volume:</strong> {printLabel.total_volume_cft} CFT</div>
              {printLabel.length_cm && (
                <div><strong>Dims:</strong> {printLabel.length_cm}×{printLabel.width_cm}×{printLabel.height_cm} cm</div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
