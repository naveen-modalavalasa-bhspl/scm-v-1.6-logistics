import React, { useEffect, useMemo, useState } from 'react';
import {
  App as AntApp, Button, Card, Checkbox, Col, Empty, Form, Input, Row,
  Space, Spin, Statistic, Table, Tag, Popconfirm, Typography
} from 'antd';
import { ReloadOutlined, SaveOutlined, DeleteOutlined } from '@ant-design/icons';
import PageHeader from '../../components/PageHeader';
import api from '../../config/api';
import { getErrorMessage, formatDate } from '../../utils/helpers';

const { Text } = Typography;

const AssetSpareMapping = () => {
  const { message } = AntApp.useApp();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState({ assets: [], spares: [] });
  const [selectedAssetKeys, setSelectedAssetKeys] = useState([]);
  const [selectedSpareKeys, setSelectedSpareKeys] = useState([]);
  const [assetSearch, setAssetSearch] = useState('');
  const [spareSearch, setSpareSearch] = useState('');
  
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [form] = Form.useForm();

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/assets/spare-mapping/tree');
      setData(res.data || {});
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (page = historyPage, search = historySearch) => {
    setHistoryLoading(true);
    try {
      const res = await api.get('/assets/spare-mappings', {
        params: { page, page_size: 15, search: search || undefined },
      });
      setHistory(res.data?.items || []);
      setHistoryTotal(res.data?.total || 0);
      setHistoryPage(page);
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    loadHistory(1, '');
    form.setFieldsValue({ replace_existing: false });
  }, []);

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    if (!q) return data.assets || [];
    return (data.assets || []).filter(
      (item) =>
        String(item.item_code || '').toLowerCase().includes(q) ||
        String(item.name || '').toLowerCase().includes(q)
    );
  }, [data.assets, assetSearch]);

  const filteredSpares = useMemo(() => {
    const q = spareSearch.trim().toLowerCase();
    if (!q) return data.spares || [];
    return (data.spares || []).filter(
      (item) =>
        String(item.item_code || '').toLowerCase().includes(q) ||
        String(item.name || '').toLowerCase().includes(q)
    );
  }, [data.spares, spareSearch]);

  const selectAllVisibleAssets = () => {
    const visibleIds = filteredAssets.map((item) => item.id);
    setSelectedAssetKeys((prev) => Array.from(new Set([...prev, ...visibleIds])));
  };

  const selectAllVisibleSpares = () => {
    const visibleIds = filteredSpares.map((item) => item.id);
    setSelectedSpareKeys((prev) => Array.from(new Set([...prev, ...visibleIds])));
  };

  const handleSave = async () => {
    if (!selectedAssetKeys.length) {
      message.warning('Select at least one asset item');
      return;
    }
    if (!selectedSpareKeys.length) {
      message.warning('Select at least one spare item');
      return;
    }
    try {
      const values = await form.validateFields();
      setSaving(true);
      const res = await api.post('/assets/spare-mappings/bulk', {
        asset_ids: selectedAssetKeys,
        spare_ids: selectedSpareKeys,
        replace_existing: values.replace_existing,
      });
      message.success(res.data?.message || 'Asset - Spare mappings saved');
      setSelectedAssetKeys([]);
      setSelectedSpareKeys([]);
      loadHistory(1, historySearch);
    } catch (err) {
      if (err.errorFields) return;
      message.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMapping = async (id) => {
    try {
      await api.delete(`/assets/spare-mappings/${id}`);
      message.success('Mapping deleted successfully');
      loadHistory(historyPage, historySearch);
    } catch (err) {
      message.error(getErrorMessage(err));
    }
  };

  const itemColumns = [
    {
      title: 'Code',
      dataIndex: 'item_code',
      key: 'item_code',
      width: 130,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
  ];

  const historyColumns = [
    {
      title: 'Asset Code',
      dataIndex: 'asset_code',
      key: 'asset_code',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Asset Name',
      dataIndex: 'asset_name',
      key: 'asset_name',
    },
    {
      title: 'Spare Code',
      dataIndex: 'spare_code',
      key: 'spare_code',
    },
    {
      title: 'Spare Name',
      dataIndex: 'spare_name',
      key: 'spare_name',
    },
    {
      title: 'Mapped Date',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val) => formatDate(val),
    },
    {
      title: 'Action',
      key: 'action',
      width: 80,
      align: 'center',
      render: (_, row) => (
        <Popconfirm
          title="Delete this mapping?"
          description="Are you sure you want to delete this asset-spare relationship?"
          onConfirm={() => handleDeleteMapping(row.id)}
          okText="Delete"
          okButtonProps={{ danger: true }}
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="Asset - Spare Mapping" subtitle="Map organization assets to their compatible spare parts">
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>Refresh</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>Save Mapping</Button>
        </Space>
      </PageHeader>

      <Spin spinning={loading}>
        <Row gutter={16}>
          <Col xs={24} lg={10}>
            <Card
              title="Assets"
              extra={<Button size="small" onClick={selectAllVisibleAssets}>Select visible</Button>}
            >
              <Input.Search placeholder="Search assets..." allowClear onChange={(e) => setAssetSearch(e.target.value)} style={{ marginBottom: 12 }} />
              <Table
                rowKey="id"
                size="small"
                columns={itemColumns}
                dataSource={filteredAssets}
                pagination={{ pageSize: 10, showSizeChanger: false, size: 'small' }}
                rowSelection={{
                  selectedRowKeys: selectedAssetKeys,
                  onChange: (keys) => setSelectedAssetKeys(keys),
                }}
                scroll={{ y: 400 }}
              />
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Card
              title="Spare Parts"
              extra={<Button size="small" onClick={selectAllVisibleSpares}>Select visible spares</Button>}
            >
              <Input.Search placeholder="Search items or categories..." allowClear onChange={(e) => setSpareSearch(e.target.value)} style={{ marginBottom: 12 }} />
              <Table
                rowKey="id"
                size="small"
                columns={itemColumns}
                dataSource={filteredSpares}
                pagination={{ pageSize: 10, showSizeChanger: false, size: 'small' }}
                rowSelection={{
                  selectedRowKeys: selectedSpareKeys,
                  onChange: (keys) => setSelectedSpareKeys(keys),
                }}
                scroll={{ y: 400 }}
              />
            </Card>
          </Col>

          <Col xs={24} lg={4}>
            <Card title="Mapping Control">
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Row gutter={8}>
                  <Col span={12}><Statistic title="ASSETS" value={selectedAssetKeys.length} /></Col>
                  <Col span={12}><Statistic title="SPARES" value={selectedSpareKeys.length} /></Col>
                </Row>
                <Tag color="purple">{selectedAssetKeys.length * selectedSpareKeys.length} COMBINATIONS</Tag>
                <Form form={form} layout="vertical">
                  <Form.Item name="replace_existing" valuePropName="checked" style={{ marginBottom: 0 }}>
                    <Checkbox>Replace existing mappings for selected assets</Checkbox>
                  </Form.Item>
                </Form>
                <Checkbox
                  checked={!selectedAssetKeys.length && !selectedSpareKeys.length}
                  onChange={() => {
                    setSelectedAssetKeys([]);
                    setSelectedSpareKeys([]);
                  }}
                >
                  Clear selection
                </Checkbox>
              </Space>
            </Card>
          </Col>
        </Row>

        <Card
          title="Mapping History"
          style={{ marginTop: 16 }}
          extra={(
            <Input.Search
              placeholder="Search history..."
              allowClear
              onSearch={(value) => {
                setHistorySearch(value);
                loadHistory(1, value);
              }}
              onChange={(e) => {
                if (!e.target.value) {
                  setHistorySearch('');
                  loadHistory(1, '');
                }
              }}
              style={{ width: 260 }}
            />
          )}
        >
          <Table
            rowKey="id"
            size="small"
            columns={historyColumns}
            dataSource={history}
            loading={historyLoading}
            pagination={{
              current: historyPage,
              total: historyTotal,
              pageSize: 15,
              showSizeChanger: false,
              onChange: (page) => loadHistory(page, historySearch),
            }}
          />
        </Card>
      </Spin>
    </div>
  );
};

export default AssetSpareMapping;
