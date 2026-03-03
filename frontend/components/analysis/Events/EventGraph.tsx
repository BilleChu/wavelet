'use client';

import React, { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

interface EventGraphProps {
  eventId?: number;
  entityId?: string;
  entityType?: string;
  height?: number;
}

interface GraphNode {
  id: string;
  name: string;
  category: number;
  value: number;
  symbolSize: number;
}

interface GraphLink {
  source: string;
  target: string;
  value: number;
}

const CATEGORY_COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'];
const CATEGORY_NAMES = ['事件', '股票', '行业', '概念', '人物', '机构', '指数', '其他'];

export default function EventGraph({
  eventId,
  entityId,
  entityType,
  height = 400,
}: EventGraphProps) {
  const [graphData, setGraphData] = useState<{
    nodes: GraphNode[];
    links: GraphLink[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        let url = 'http://localhost:8000/api/graph/default';
        
        if (entityId) {
          url = `http://localhost:8000/api/graph/entity/${entityId}`;
        }

        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          
          const nodes: GraphNode[] = (data.nodes || []).map((n: any, idx: number) => ({
            id: n.id || String(idx),
            name: n.name || n.title || n.entity_name,
            category: getCategoryIndex(n.type || n.entity_type),
            value: n.importance || n.score || 50,
            symbolSize: Math.max(20, Math.min(60, (n.importance || n.score || 50) * 0.6)),
          }));

          const links: GraphLink[] = (data.edges || data.relations || []).map((e: any) => ({
            source: e.source || e.from_id || e.entity_id,
            target: e.target || e.to_id,
            value: e.weight || e.impact_score || 1,
          }));

          setGraphData({ nodes, links });
        }
      } catch (error) {
        console.error('Failed to fetch graph:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [eventId, entityId, entityType]);

  const getCategoryIndex = (type?: string): number => {
    if (!type) return 7;
    const typeMap: Record<string, number> = {
      'event': 0,
      'stock': 1,
      'industry': 2,
      'concept': 3,
      'person': 4,
      'organization': 5,
      'index': 6,
    };
    return typeMap[type.toLowerCase()] ?? 7;
  };

  if (loading) {
    return (
      <div style={{ height }} className="flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-gray-400">
        暂无图谱数据
      </div>
    );
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<div style="font-weight:bold">${params.data.name}</div>
                  <div style="color:#999;font-size:12px">${CATEGORY_NAMES[params.data.category]}</div>`;
        }
        return '';
      },
    },
    legend: {
      data: CATEGORY_NAMES,
      bottom: 0,
      textStyle: { color: '#666', fontSize: 11 },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: graphData.nodes,
        links: graphData.links,
        categories: CATEGORY_NAMES.map((name, idx) => ({
          name,
          itemStyle: { color: CATEGORY_COLORS[idx] },
        })),
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 11,
          color: '#333',
        },
        labelLayout: {
          hideOverlap: true,
        },
        force: {
          repulsion: 200,
          edgeLength: [50, 150],
          gravity: 0.1,
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3,
          opacity: 0.6,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3,
          },
        },
      },
    ],
  };

  return (
    <div>
      <ReactECharts
        option={option}
        style={{ height }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
