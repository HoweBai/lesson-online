import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend
} from 'recharts';

interface LearningChartProps {
  tutorialStats: {
    by_month: Record<string, number>;
    total: number;
    draft: number;
    published: number;
  } | null;
  chapterStats: {
    total: number;
    completed: number;
    ready: number;
    in_progress: number;
    failed: number;
  } | null;
}

const CHAPTER_COLORS = ['#22c55e', '#f59e0b', '#3b82f6', '#ef4444'];

const ChapterPieChart: React.FC<{ stats: LearningChartProps['chapterStats'] }> = ({ stats }) => {
  const { t } = useTranslation('tutorials');
  if (!stats || stats.total === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>{t('no_chapter_data')}</p>
      </div>
    );
  }

  const data = [
    { name: t('chapter_status.completed'), value: stats.completed, color: CHAPTER_COLORS[0] },
    { name: t('chapter_status.pending'), value: stats.ready, color: CHAPTER_COLORS[1] },
    { name: t('chapter_status.generating'), value: stats.in_progress, color: CHAPTER_COLORS[2] },
    { name: t('chapter_status.failed'), value: stats.failed, color: CHAPTER_COLORS[3] },
  ].filter(d => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>{t('no_chapters_generated')}</p>
      </div>
    );
  }

  return (
    <PieChart width={280} height={220}>
      <Pie
        data={data}
        cx="50%"
        cy="50%"
        innerRadius={55}
        outerRadius={90}
        paddingAngle={4}
        dataKey="value"
        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
      >
        {data.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={entry.color} />
        ))}
      </Pie>
      <Tooltip formatter={(value: number) => `${value} chapters`} />
      <Legend />
    </PieChart>
  );
};

const TutorialBarChart: React.FC<{ stats: LearningChartProps['tutorialStats'] }> = ({ stats }) => {
  const { t } = useTranslation('tutorials');
  if (!stats || Object.keys(stats.by_month).length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>{t('no_tutorial_data')}</p>
      </div>
    );
  }

  const data = Object.entries(stats.by_month)
    .map(([month, count]) => ({ month, count }))
    .sort((a, b) => a.month.localeCompare(b.month));

  return (
    <BarChart width={500} height={220} data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
      <XAxis dataKey="month" tick={{ fontSize: 12 }} />
      <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
      <Tooltip
        formatter={(value: number) => [`${value} tutorial${value !== 1 ? 's' : ''}`, 'Created']}
        labelFormatter={(label) => `Month: ${label}`}
      />
      <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
    </BarChart>
  );
};

export const LearningChart: React.FC<LearningChartProps> = ({ tutorialStats, chapterStats }) => {
  const { t } = useTranslation('tutorials');
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <span>📊</span> {t('tutorials_by_month')}
        </h3>
        <div className="flex justify-center overflow-x-auto">
          <TutorialBarChart stats={tutorialStats} />
        </div>
      </div>
      <div className="card p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <span>📖</span> {t('chapters')}
        </h3>
        <div className="flex justify-center">
          <ChapterPieChart stats={chapterStats} />
        </div>
      </div>
    </div>
  );
};

export default LearningChart;
