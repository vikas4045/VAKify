import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, XCircle, Flag, Eye } from 'lucide-react';
import { apiFetch } from '../lib/api';

type ModerationItem = {
  moderation_id: number;
  item_type: string;
  source_id: number | null;
  user_id: number;
  content: string;
  reason: string;
  confidence: string;
  status: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
};

export function Moderation() {
  const [filter, setFilter] = useState<'all' | 'pending' | 'reviewed'>('all');
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await apiFetch<{ items: ModerationItem[] }>('/api/moderation/queue');
        if (!cancelled) {
          setItems(data.items || []);
        }
      } catch {
        if (!cancelled) {
          setItems([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredContent = useMemo(
    () => items.filter((item) => filter === 'all' || item.status === filter),
    [filter, items],
  );

  const stats = useMemo(
    () => ({
      pending: items.filter((i) => i.status === 'pending').length,
      reviewed: items.filter((i) => i.status !== 'pending').length,
      total: items.length,
    }),
    [items],
  );

  const handleResolve = async (moderationId: number, action: 'approve' | 'reject') => {
    await apiFetch(`/api/moderation/items/${moderationId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
    const data = await apiFetch<{ items: ModerationItem[] }>('/api/moderation/queue');
    setItems(data.items || []);
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">Content Moderation</h1>
        <p className="text-muted-foreground">
          Review flagged content, low confidence responses and user reports
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <AlertTriangle className="w-6 h-6 text-accent" />
          </div>
          <div className="text-3xl mb-1">{stats.pending}</div>
          <div className="text-sm text-muted-foreground">Pending Review</div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <CheckCircle2 className="w-6 h-6 text-secondary" />
          </div>
          <div className="text-3xl mb-1">{stats.reviewed}</div>
          <div className="text-sm text-muted-foreground">Reviewed</div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <Flag className="w-6 h-6 text-primary" />
          </div>
          <div className="text-3xl mb-1">{stats.total}</div>
          <div className="text-sm text-muted-foreground">Total Items</div>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        {[
          { id: 'all' as const, label: 'All Items' },
          { id: 'pending' as const, label: 'Pending' },
          { id: 'reviewed' as const, label: 'Reviewed' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={`px-6 py-3 rounded-lg transition-colors ${
              filter === tab.id
                ? 'bg-primary text-primary-foreground'
                : 'bg-card border border-border hover:bg-muted'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-card border border-border rounded-xl shadow-sm">
        <div className="p-6 border-b border-border">
          <h3 className="text-lg">Moderation Queue</h3>
        </div>

        <div className="divide-y divide-border">
          {!loading && filteredContent.map((item) => (
            <div key={item.moderation_id} className="p-6 hover:bg-muted/50 transition-colors">
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                  item.status === 'pending' ? 'bg-accent/10' : 'bg-secondary/10'
                }`}>
                  {item.status === 'pending' ? (
                    <AlertTriangle className="w-6 h-6 text-accent" />
                  ) : (
                    <CheckCircle2 className="w-6 h-6 text-secondary" />
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-sm">User #{item.user_id}</h4>
                        <div className={`px-2 py-1 rounded text-xs ${
                          item.confidence === 'High' ? 'bg-secondary/10 text-secondary' :
                          item.confidence === 'Medium' ? 'bg-accent/10 text-accent' :
                          'bg-destructive/10 text-destructive'
                        }`}>
                          {item.confidence} Confidence
                        </div>
                        <div className="px-2 py-1 rounded text-xs bg-muted text-muted-foreground">
                          {item.item_type}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{item.reason}</p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-xs ${
                      item.status === 'pending' ? 'bg-accent/10 text-accent' : 'bg-secondary/10 text-secondary'
                    }`}>
                      {item.status}
                    </div>
                  </div>

                  <div className="bg-muted/50 rounded-lg p-4 mb-3">
                    <p className="text-sm whitespace-pre-wrap">{item.content}</p>
                  </div>

                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
                    <span>Flagged: {item.created_at}</span>
                    {item.reviewed_at && <span>Reviewed: {item.reviewed_at}</span>}
                  </div>

                  {item.status === 'pending' && (
                    <div className="flex gap-3">
                      <button
                        onClick={() => void handleResolve(item.moderation_id, 'approve')}
                        className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition-opacity"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => void handleResolve(item.moderation_id, 'reject')}
                        className="flex items-center gap-2 px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:opacity-90 transition-opacity"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject
                      </button>
                      <button className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-muted transition-colors">
                        <Eye className="w-4 h-4" />
                        View Details
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {!loading && filteredContent.length === 0 && (
            <div className="p-12 text-center text-muted-foreground">
              <Flag className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No items to review</p>
            </div>
          )}

          {loading && (
            <div className="p-12 text-center text-muted-foreground">
              <Flag className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Loading moderation queue...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
