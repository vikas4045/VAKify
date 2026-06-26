import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Target, Brain, AlertCircle, CheckCircle2, Lightbulb } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { apiFetch } from '../lib/api';

type StudyPlan = {
  title: string;
  learning_style: string;
  overview: string;
  focus_area: string;
  strengths: string[];
  gaps: string[];
  today_plan: Array<{ title: string; minutes: number; action: string; success_criteria: string }>;
  weekly_plan: Array<{ day: string; focus: string; task: string }>;
  quick_wins: string[];
  next_action: string;
  motivation: string;
  source?: string;
};

type DashboardInsights = {
  mastery_score: number;
  streak_days: number;
  recommended_topic: string;
  daily_chat: Array<{ date: string; count: number }>;
  daily_practice: Array<{ date: string; count: number }>;
  daily_downloads: Array<{ date: string; count: number }>;
  topic_confidence: Array<{ topic: string; confidence: number; trend: string }>;
  learning_style_breakdown: Array<{ subject: string; value: number }>;
  weak_topics: Array<{ name: string; score: number; priority: string; color: string }>;
  performance_over_time: Array<{ week: string; score: number }>;
  skill_distribution: Array<{ name: string; value: number }>;
};

export function Insights() {
  const [summary, setSummary] = useState<DashboardInsights | null>(null);
  const [studyPlan, setStudyPlan] = useState<StudyPlan | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadPlan = async () => {
      try {
        const [summaryRes, planRes] = await Promise.allSettled([
          apiFetch<DashboardInsights>('/api/dashboard/insights'),
          apiFetch<StudyPlan>('/api/ai/study-plan'),
        ]);
        if (cancelled) {
          return;
        }
        if (summaryRes.status === 'fulfilled') {
          setSummary(summaryRes.value);
        }
        if (planRes.status === 'fulfilled') {
          setStudyPlan(planRes.value);
        }
      } catch {
        if (!cancelled) {
          setSummary(null);
          setStudyPlan(null);
        }
      }
    };

    void loadPlan();
    return () => {
      cancelled = true;
    };
  }, []);

  const topicConfidence = summary?.topic_confidence ?? [];
  const learningStyleData = summary?.learning_style_breakdown ?? [];
  const weakTopics = summary?.weak_topics ?? [];
  const performanceOverTime = summary?.performance_over_time ?? [];
  const skillDistribution = summary?.skill_distribution ?? [];

  const COLORS = ['#1B998B', '#F4A261', '#E76F51', '#1E3A5F'];

  const recommendations = studyPlan
    ? [
        {
          title: studyPlan.title,
          description: studyPlan.overview,
          impact: 'High',
          icon: Target,
        },
        {
          title: `Focus: ${studyPlan.focus_area}`,
          description: studyPlan.next_action,
          impact: 'High',
          icon: Brain,
        },
        {
          title: 'Quick Wins',
          description: studyPlan.quick_wins.slice(0, 2).join(' • '),
          impact: 'Medium',
          icon: CheckCircle2,
        },
      ]
    : weakTopics.length
      ? [
          {
            title: `${weakTopics[0].name} Focus`,
            description: `Your current ${weakTopics[0].name.toLowerCase()} score is ${weakTopics[0].score}%. Build it with daily practice.`,
            impact: weakTopics[0].priority,
            icon: Target,
          },
          {
            title: 'Learning Style Match',
            description: 'Use the live style analysis to balance visual, audio, and hands-on learning.',
            impact: 'Medium',
            icon: Brain,
          },
          {
            title: 'Streak Growth',
            description: summary?.streak_days ? `You have a ${summary.streak_days}-day streak. Keep it going.` : 'Start a streak by completing one task each day.',
            impact: 'Medium',
            icon: CheckCircle2,
          },
        ]
      : [];

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">Learning Insights</h1>
        <p className="text-muted-foreground">
          Understand your strengths, weaknesses, and personalized recommendations
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="bg-gradient-to-br from-secondary to-secondary/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              This Month
            </div>
          </div>
          <div className="text-3xl mb-1">+15%</div>
          <div className="text-white/80 text-sm">Overall Improvement</div>
        </div>

        <div className="bg-gradient-to-br from-accent to-accent/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <Target className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              Average
            </div>
          </div>
          <div className="text-3xl mb-1">78%</div>
          <div className="text-white/80 text-sm">Confidence Score</div>
        </div>

        <div className="bg-gradient-to-br from-destructive to-destructive/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <AlertCircle className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              Focus Areas
            </div>
          </div>
          <div className="text-3xl mb-1">3</div>
          <div className="text-white/80 text-sm">Topics Need Work</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <Target className="w-5 h-5 text-destructive" />
            Topic Confidence
          </h3>

          <div className="space-y-4">
            {topicConfidence.length ? topicConfidence.map((topic) => (
              <div key={topic.topic}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{topic.topic}</span>
                    {topic.trend === 'up' && <TrendingUp className="w-4 h-4 text-secondary" />}
                    {topic.trend === 'down' && <TrendingDown className="w-4 h-4 text-destructive" />}
                  </div>
                  <span className="text-sm text-muted-foreground">{topic.confidence}%</span>
                </div>
                <div className="bg-muted rounded-full h-2">
                  <div
                    className={`h-full rounded-full transition-all ${
                      topic.confidence >= 70 ? 'bg-secondary' :
                      topic.confidence >= 50 ? 'bg-accent' :
                      'bg-destructive'
                    }`}
                    style={{ width: `${topic.confidence}%` }}
                  />
                </div>
              </div>
            )) : (
              <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                Start chatting or solving tasks to build topic confidence.
              </div>
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Learning Style Analysis
          </h3>

          {learningStyleData.length ? (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={learningStyleData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" stroke="#64748b" />
                  <PolarRadiusAxis stroke="#64748b" />
                  <Radar name="Preference" dataKey="value" stroke="#1B998B" fill="#1B998B" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
              <p className="text-sm text-muted-foreground mt-4">
                This chart is driven by your saved learning style profile.
              </p>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
              Set up your learning style in onboarding to see the live radar chart.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-secondary" />
            Performance Over Time
          </h3>

          {performanceOverTime.length ? (
            <>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={performanceOverTime}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="week" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Bar dataKey="score" fill="#1B998B" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-4 flex items-center gap-2 text-sm text-secondary">
                <TrendingUp className="w-4 h-4" />
                <span>Live performance based on tasks and quizzes.</span>
              </div>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
              Complete a few tasks and quizzes to build performance history.
            </div>
          )}
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-accent" />
            Skill Distribution
          </h3>

          {skillDistribution.length ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={skillDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {skillDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
              Your activity breakdown will appear here after a few sessions.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            Weak Topics
          </h3>

          <div className="space-y-4">
            {weakTopics.length ? weakTopics.map((topic) => (
              <div
                key={topic.name}
                className="p-4 rounded-lg border border-border bg-muted/30"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm">{topic.name}</h4>
                  <div
                    className="px-3 py-1 rounded-full text-xs"
                    style={{
                      backgroundColor: `${topic.color}20`,
                      color: topic.color
                    }}
                  >
                    {topic.priority} Priority
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-muted rounded-full h-2">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${topic.score}%`,
                        backgroundColor: topic.color
                      }}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground">{topic.score}%</span>
                </div>
              </div>
            )) : (
              <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                Weak topic signals will appear here once you have enough learning activity.
              </div>
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg mb-6 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-accent" />
            Personalized Recommendations
          </h3>

          {studyPlan && (
            <div className="mb-4 rounded-lg border border-secondary/20 bg-secondary/5 p-4">
              <div className="text-xs uppercase tracking-wide text-secondary mb-1">AI Study Plan</div>
              <div className="text-sm font-medium mb-2">{studyPlan.title}</div>
              <p className="text-xs text-muted-foreground mb-3">{studyPlan.motivation}</p>
              <div className="space-y-2 text-xs text-muted-foreground">
                {studyPlan.today_plan.slice(0, 2).map((item) => (
                  <div key={item.title} className="rounded-md bg-background/80 p-3 border border-border">
                    <div className="font-medium text-foreground">{item.title} • {item.minutes} min</div>
                    <div>{item.action}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {recommendations.map((rec, index) => {
              const Icon = rec.icon;
              return (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-border bg-muted/30"
                >
                  <div className="flex items-start gap-3 mb-2">
                    <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-secondary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-sm">{rec.title}</h4>
                        <div className="px-2 py-1 rounded text-xs bg-accent/10 text-accent">
                          {rec.impact} Impact
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">{rec.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
