import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { DimensionScore } from '../types';

interface EvalRadarChartProps {
  dimensions: DimensionScore[];
  overallScore: number;
}

const DIMENSION_LABELS: Record<string, string> = {
  completeness: 'Completeness',
  role_relevance: 'Role Relevance',
  actionability: 'Actionability',
  clarity: 'Clarity',
  progressive_complexity: 'Complexity',
};

function getScoreColor(score: number): string {
  if (score >= 0.8) return '#16a34a';
  if (score >= 0.7) return '#d97706';
  return '#dc2626';
}

export function EvalRadarChart({ dimensions, overallScore }: EvalRadarChartProps) {
  const color = getScoreColor(overallScore);

  const data = dimensions.map((d) => ({
    dimension: DIMENSION_LABELS[d.dimension] ?? d.dimension,
    score: Math.round(d.score * 100),
    fullMark: 100,
  }));

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 11, fill: '#64748b' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickCount={6}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke={color}
            fill={color}
            fillOpacity={0.2}
            strokeWidth={2}
            animationDuration={800}
          />
          <Tooltip
            formatter={(value) => [`${value}%`, 'Score']}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
              fontSize: '12px',
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="text-center">
          <span className="text-3xl font-bold" style={{ color }}>
            {Math.round(overallScore * 100)}%
          </span>
          <p className="text-xs text-slate-500 mt-0.5">Overall</p>
        </div>
      </div>
    </div>
  );
}
