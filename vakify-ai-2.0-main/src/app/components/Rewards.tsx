import { useEffect, useState } from 'react';
import { Trophy, Award, Star, TrendingUp, Gift, Crown, Zap, Loader2 } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

type RewardSummary = {
  wallet: { current_xp: number; level: number; reward_points: number };
  streak: { current_streak: number; longest_streak: number; last_active_date: string | null };
  recent_xp_events: Array<{ event_id: number; source: string; points: number; created_at: string }>;
  earned_badges: Array<{ name: string; description: string; icon: string; earned: boolean }>;
  reward_vault: Array<{ reward_key: string; name: string; cost: number; description: string; icon: string; available: boolean }>;
  reward_redemptions: Array<{ redemption_id: number; reward_key: string; reward_name: string; cost: number; status: string; created_at: string }>;
};

type LeaderboardRow = { rank: number; name: string; score: number };

export function Rewards() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<RewardSummary | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [redeeming, setRedeeming] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const results = await Promise.allSettled([
          apiFetch<RewardSummary>('/api/rewards/summary'),
          apiFetch<{ rows: LeaderboardRow[] }>('/api/leaderboard?scope=all_time'),
        ]);
        if (cancelled) {
          return;
        }

        const [summaryRes, leaderboardRes] = results;
        if (summaryRes.status === 'fulfilled') {
          setSummary(summaryRes.value);
        }
        if (leaderboardRes.status === 'fulfilled') {
          setLeaderboard(leaderboardRes.value.rows || []);
        }
      } catch {
        if (!cancelled) {
          setSummary(null);
          setLeaderboard([]);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const badges = summary?.earned_badges ?? [];
  const rewardVault = summary?.reward_vault ?? [];
  const earnedBadges = badges.filter((badge) => badge.earned);
  const lockedBadges = badges.filter((badge) => !badge.earned);

  const leaderboardRows = leaderboard;

  const xpHistory = summary?.recent_xp_events?.length
    ? summary.recent_xp_events.slice(0, 5).map((event) => ({
        date: event.created_at.slice(0, 10),
        activity: event.source.replace(/_/g, ' '),
        xp: event.points,
      }))
    : [];

  const redeemReward = async (rewardKey: string) => {
    setMessage(null);
    setRedeeming(rewardKey);
    try {
      const updated = await apiFetch<{ wallet: RewardSummary['wallet']; reward: { reward_key: string; reward_name: string; cost: number } }>(
        '/api/rewards/redeem',
        {
          method: 'POST',
          body: JSON.stringify({ reward_key: rewardKey }),
        },
      );
      setMessage(`Redeemed ${updated.reward.reward_name}.`);
      const [summaryRes, leaderboardRes] = await Promise.allSettled([
        apiFetch<RewardSummary>('/api/rewards/summary'),
        apiFetch<{ rows: LeaderboardRow[] }>('/api/leaderboard?scope=all_time'),
      ]);
      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value);
      }
      if (leaderboardRes.status === 'fulfilled') {
        setLeaderboard(leaderboardRes.value.rows || []);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not redeem reward');
    } finally {
      setRedeeming(null);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">Rewards & Achievements</h1>
        <p className="text-muted-foreground">
          Track your progress, unlock badges, and climb the leaderboard
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Total XP</div>
          <div className="text-3xl text-primary">{summary?.wallet.current_xp ?? user?.xp ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Reward Points</div>
          <div className="text-3xl text-secondary">{summary?.wallet.reward_points ?? user?.xp ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Current Streak</div>
          <div className="text-3xl text-accent">{summary?.streak.current_streak ?? user?.streak ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl flex items-center gap-2">
                <Award className="w-6 h-6 text-accent" />
                Badges
              </h2>
              <span className="text-sm text-muted-foreground">
                {earnedBadges.length}/{badges.length} Unlocked
              </span>
            </div>

            <div className="mb-6">
              <h3 className="text-sm text-muted-foreground mb-3">Earned Badges</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {earnedBadges.length ? earnedBadges.map((badge, index) => (
                  <div
                    key={`${badge.name}-${index}`}
                    className="bg-gradient-to-br from-secondary/10 to-accent/10 border border-secondary/20 rounded-xl p-4 hover:scale-105 transition-transform cursor-pointer"
                  >
                    <div className="text-4xl mb-2">{badge.icon}</div>
                    <div className="text-sm mb-1">{badge.name}</div>
                    <div className="text-xs text-muted-foreground">{badge.description}</div>
                  </div>
                )) : (
                  <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                    Earn badges by completing tasks, quizzes, and streak goals.
                  </div>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-sm text-muted-foreground mb-3">Locked Badges</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {lockedBadges.length ? lockedBadges.map((badge, index) => (
                  <div
                    key={`${badge.name}-${index}`}
                    className="bg-muted/50 border border-border rounded-xl p-4 opacity-50"
                  >
                    <div className="text-4xl mb-2 grayscale">{badge.icon}</div>
                    <div className="text-sm mb-1">{badge.name}</div>
                    <div className="text-xs text-muted-foreground">{badge.description}</div>
                  </div>
                )) : (
                  <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                    No locked badges right now. Keep progressing to unlock more.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="text-xl flex items-center gap-2 mb-6">
              <Gift className="w-6 h-6 text-destructive" />
              Reward Vault
            </h2>

            {message && (
              <div className="mb-4 rounded-lg border border-secondary/20 bg-secondary/5 px-4 py-3 text-sm text-secondary">
                {message}
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {rewardVault.length ? rewardVault.map((reward) => {
                const Icon = reward.icon === 'Crown' ? Crown : reward.icon === 'Zap' ? Zap : reward.icon === 'Star' ? Star : reward.icon === 'Award' ? Award : Trophy;
                return (
                  <div
                    key={reward.reward_key}
                    className={`border rounded-xl p-4 ${
                      reward.available
                        ? 'border-border bg-card hover:border-secondary hover:bg-secondary/5'
                        : 'border-border bg-muted/50 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-6 h-6 text-primary" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-sm mb-1">{reward.name}</h3>
                        <p className="text-xs text-muted-foreground mb-2">{reward.description}</p>
                        <div className="flex items-center gap-2">
                          <span className="text-lg text-accent">{reward.cost}</span>
                          <span className="text-xs text-muted-foreground">XP</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => void redeemReward(reward.reward_key)}
                      disabled={!reward.available || redeeming === reward.reward_key}
                      className={`w-full mt-4 py-2 rounded-lg text-sm transition-opacity ${
                        reward.available && redeeming !== reward.reward_key
                          ? 'bg-primary text-primary-foreground hover:opacity-90'
                          : 'bg-muted text-muted-foreground cursor-not-allowed'
                      }`}
                    >
                      {redeeming === reward.reward_key ? (
                        <span className="inline-flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Redeeming
                        </span>
                      ) : reward.available ? 'Redeem' : 'Locked'}
                    </button>
                  </div>
                );
              }) : (
                <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                  Reward vault items will appear once the backend catalog is loaded.
                </div>
              )}
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="text-xl flex items-center gap-2 mb-6">
              <TrendingUp className="w-6 h-6 text-secondary" />
              XP History
            </h2>

            {xpHistory.length ? (
              <div className="space-y-2">
                {xpHistory.map((entry, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                  >
                    <div>
                      <div className="text-sm">{entry.activity}</div>
                      <div className="text-xs text-muted-foreground">{entry.date}</div>
                    </div>
                    <div className="text-lg text-accent">+{entry.xp}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                XP history will appear after tasks, quizzes, and labs are completed.
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="text-xl flex items-center gap-2 mb-6">
              <Gift className="w-6 h-6 text-primary" />
              Redemption History
            </h2>

            {summary?.reward_redemptions?.length ? (
              <div className="space-y-2">
                {summary.reward_redemptions.map((item) => (
                  <div key={item.redemption_id} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div>
                      <div className="text-sm">{item.reward_name}</div>
                      <div className="text-xs text-muted-foreground">{item.created_at.slice(0, 10)}</div>
                    </div>
                    <div className="text-sm text-accent">-{item.cost} XP</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                Redeemed rewards will show up here.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-primary to-secondary text-white rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-4">
              <Trophy className="w-8 h-8" />
              <h2 className="text-xl">Your Rank</h2>
            </div>
            {leaderboardRows.length ? (
              <>
                <div className="text-5xl mb-2">
                  #{leaderboardRows.find((row) => row.name === user?.displayName)?.rank ?? '--'}
                </div>
                <div className="text-white/80 mb-4">Global Ranking</div>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3">
                  <div className="text-sm text-white/60 mb-1">Next Rank</div>
                  <div className="text-lg">
                    {Math.max(0, (leaderboardRows.find((row) => row.name === user?.displayName)?.score || 0) - 530)} XP to go
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg bg-white/10 backdrop-blur-sm p-3 text-sm text-white/80">
                Keep earning XP to appear on the leaderboard.
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h2 className="text-xl flex items-center gap-2 mb-6">
              <Trophy className="w-6 h-6 text-accent" />
              Leaderboard
            </h2>

            <div className="space-y-2">
              {leaderboardRows.length ? leaderboardRows.map((entry) => (
                <div
                  key={entry.rank}
                  className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                    entry.name === user?.displayName
                      ? 'bg-secondary/10 border border-secondary'
                      : 'bg-muted/50 hover:bg-muted'
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm flex-shrink-0">
                    {entry.rank === 1 ? '👑' : entry.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{entry.name}</div>
                    <div className="text-xs text-muted-foreground">Score</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm">{entry.score}</div>
                    <div className="text-xs text-muted-foreground">XP</div>
                  </div>
                </div>
              )) : (
                <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No leaderboard data yet. Start earning XP to appear here.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
