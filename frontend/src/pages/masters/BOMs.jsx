import React, { useState, useEffect, useCallback } from 'react';
import {
  Button, Form, Input, Space, Popconfirm, Switch, message, Select, InputNumber, Tag, Row, Col, Drawer, Tooltip
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import StatusTag from '../../components/StatusTag';
import ItemSelector from '../../components/ItemSelector';
import api from '../../config/api';
import { getErrorMessage } from '../../utils/helpers';

const documentTypeOptions = [
  { label: 'Indent', value: 'Indent' },
  { label: 'Material issue', value: 'Material issue' },
];

const BOMs = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [projects, setProjects] = useState([]);
  const [uoms, setUoms] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch Lookups
  const loadLookups = useCallback(async () => {
    try {
      const [projRes, uomRes] = await Promise.allSettled([
        api.get('/masters/org-projects', { params: { page_size: 500 } }),
        api.get('/masters/uom', { params: { page_size: 500 } }),
      ]);

      if (projRes.status === 'fulfilled') {
        const data = projRes.value.data?.items || projRes.value.data?.data || projRes.value.data || [];
        setProjects(data.map((p) => ({ label: `[${p.code}] ${p.name}`, value: p.id })));
      }

      if (uomRes.status === 'fulfilled') {
        const data = uomRes.value.data?.items || uomRes.value.data?.data || uomRes.value.data || [];
        setUoms(data.map((u) => ({ label: `${u.name} (${u.abbreviation || ''})`, value: u.id })));
      }
    } catch (err) {
      console.error('Failed to load lookups', err);
    }
  }, []);

  useEffect(() => {
    loadLookups();
  }, [loadLookups]);

  const fetchBOMs = async (params) => {
    return api.get('/masters/boms', { params });
  };

  const handleAdd = () => {
    setEditingRow(null);
    form.resetFields();
    form.setFieldsValue({
      is_active: true,
      components: [{ item_id: undefined, qty: 1, uom_id: undefined }],
    });
    setDrawerOpen(true);
  };

  const handleEdit = (record) => {
    setEditingRow(record);
    form.setFieldsValue({
      name: record.name,
      project_id: record.project_id,
      document_types: record.document_types,
      is_active: record.is_active,
      components: record.components.map((c) => ({
        item_id: c.item_id,
        qty: c.qty,
        uom_id: c.uom_id,
      })),
    });
    setDrawerOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/masters/boms/${id}`);
      message.success('BOM deleted successfully');
      setRefreshKey((k) => k + 1);
    } catch (err) {
      message.error(getErrorMessage(err));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (!values.components || values.components.length === 0) {
        message.error('At least one item component is required');
        return;
      }

      const payload = {
        name: values.name,
        project_id: values.project_id || null,
        document_types: values.document_types || [],
        components: values.components.map((c) => ({
          item_id: c.item_id,
          qty: c.qty,
          uom_id: c.uom_id || null,
        })),
        is_active: values.is_active !== false,
      };

      setSubmitting(true);
      if (editingRow) {
        await api.put(`/masters/boms/${editingRow.id}`, payload);
        message.success('BOM updated successfully');
      } else {
        await api.post('/masters/boms', payload);
        message.success('BOM created successfully');
      }
      setDrawerOpen(false);
      form.resetFields();
      setRefreshKey((k) => k + 1);
    } catch (err) {
      if (err.errorFields) return;
      message.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleItemChange = (val, itemObj, index) => {
    if (itemObj) {
      const currentComponents = form.getFieldValue('components') || [];
      currentComponents[index] = {
        ...currentComponents[index],
        item_id: val,
        uom_id: itemObj.primary_uom_id || undefined,
      };
      form.setFieldsValue({ components: currentComponents });
    }
  };

  const columns = [
    { title: 'BOM Code', dataIndex: 'bom_code', width: 180, render: (text, record) => <a onClick={() => handleEdit(record)}>{text}</a> },
    { title: 'BOM Name', dataIndex: 'name' },
    { title: 'Project', dataIndex: 'project_name', render: (text) => text || '-' },
    {
      title: 'Document Types',
      dataIndex: 'document_types',
      render: (types) => (
        <>
          {(types || []).map((type) => {
            let color = type === 'Indent' ? 'blue' : 'purple';
            return (
              <Tag color={color} key={type}>
                {type}
              </Tag>
            );
          })}
        </>
      ),
    },
    { title: 'Active', dataIndex: 'is_active', width: 100, render: (v) => <StatusTag status={v ? 'active' : 'inactive'} /> },
    {
      title: 'Actions',
      width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          <Popconfirm title="Delete this BOM?" onConfirm={() => handleDelete(r.id)} okButtonProps={{ danger: true }}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="BOM (Bill of Materials)" subtitle="Manage BOM master definitions for Indents and Material Issues">
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Add BOM</Button>
      </PageHeader>
      
      <DataTable
        key={refreshKey}
        columns={columns}
        fetchFunction={fetchBOMs}
        rowKey="id"
        searchPlaceholder="Search by BOM code or name..."
        exportFileName="bill_of_materials"
      />

      <Drawer
        title={editingRow ? `Edit BOM: ${editingRow.bom_code}` : 'Add BOM'}
        placement="right"
        width={720}
        onClose={() => {
          if (submitting) return;
          setDrawerOpen(false);
          setEditingRow(null);
          form.resetFields();
        }}
        open={drawerOpen}
        extra={
          <Space>
            <Button disabled={submitting} onClick={() => setDrawerOpen(false)}>Cancel</Button>
            <Button type="primary" loading={submitting} onClick={handleSubmit}>Save</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="name"
                label="BOM Name"
                rules={[{ required: true, message: 'Please enter BOM name' }]}
              >
                <Input placeholder="e.g. Paracetamol Kit, Cardiology Dept BOM" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="project_id" label="Project">
                <Select
                  placeholder="Select project (optional)"
                  options={projects}
                  allowClear
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="document_types"
                label="Document Types"
                rules={[{ required: true, type: 'array', min: 1, message: 'Please select at least one Document Type' }]}
              >
                <Select
                  mode="multiple"
                  placeholder="Select document types"
                  options={documentTypeOptions}
                  allowClear
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_active" label="Active Status" valuePropName="checked" initialValue={true}>
                <Switch checkedChildren="Active" unCheckedChildren="Inactive" />
              </Form.Item>
            </Col>
          </Row>

          <div style={{ marginTop: 24 }}>
            <span style={{ fontWeight: 'bold', fontSize: 16 }}>BOM Components</span>
            <div style={{ marginTop: 12 }}>
              <Form.List
                name="components"
                rules={[
                  {
                    validator: async (_, names) => {
                      if (!names || names.length < 1) {
                        return Promise.reject(new Error('At least one component item is required'));
                      }
                    },
                  },
                ]}
              >
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }, index) => (
                      <Row key={key} gutter={16} align="middle" style={{ marginBottom: 8 }}>
                        <Col span={12}>
                          <Form.Item
                            {...restField}
                            name={[name, 'item_id']}
                            rules={[{ required: true, message: 'Select an item' }]}
                            style={{ margin: 0 }}
                          >
                            <ItemSelector
                              placeholder="Search item..."
                              onChange={(val, itemObj) => handleItemChange(val, itemObj, index)}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={5}>
                          <Form.Item
                            {...restField}
                            name={[name, 'qty']}
                            rules={[{ required: true, message: 'Enter qty' }]}
                            style={{ margin: 0 }}
                          >
                            <InputNumber
                              placeholder="Qty"
                              min={0.001}
                              style={{ width: '100%' }}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={5}>
                          <Form.Item
                            {...restField}
                            name={[name, 'uom_id']}
                            rules={[{ required: true, message: 'UOM' }]}
                            style={{ margin: 0 }}
                          >
                            <Select
                              placeholder="UOM"
                              options={uoms}
                              showSearch
                              optionFilterProp="label"
                              style={{ width: '100%' }}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={2} style={{ textAlign: 'center' }}>
                          {fields.length > 1 && (
                            <Tooltip title="Remove item">
                              <DeleteOutlined
                                onClick={() => remove(name)}
                                style={{ color: '#ff4d4f', cursor: 'pointer', fontSize: 16 }}
                              />
                            </Tooltip>
                          )}
                        </Col>
                      </Row>
                    ))}
                    <Form.Item style={{ marginTop: 12 }}>
                      <Button
                        type="dashed"
                        onClick={() => add()}
                        block
                        icon={<PlusOutlined />}
                      >
                        + New ITEM
                      </Button>
                    </Form.Item>
                  </>
                )}
              </Form.List>
            </div>
          </div>
        </Form>
      </Drawer>
    </div>
  );
};

export default BOMs;
