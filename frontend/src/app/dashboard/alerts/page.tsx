'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, ArrowLeft, Bell, AlertTriangle, CheckCircle, Info, ExternalLink, Check } from 'lucide-react';
import api from '@/lib/api';

interface Alert {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string | null;
  source_url: string | null;
  is_read: boolean;
  created_at: string;
}

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  useEffect(() => {
    fetchAlerts();
  }, [filter]);

  const fetchAlerts = async () => {
    try {
      const data = await api.getAlerts(filter === 'unread');
      setAlerts(data);
    } catch (err: any) {
      if (err.message?.includes('401')) {
        router.push('/auth/login');
        return;
      }
      setError('Failed to load alerts');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (alertId: string) => {
    try {
      await api.markAlertRead(alertId);
      setAlerts(alerts.map(a => a.id === alertId ? { ...a, is_read: true } : a));
    } catch (err) {
      setError('Failed to mark alert as read');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllAlertsRead();
      setAlerts(alerts.map(a => ({ ...a, is_read: true })));
    } catch (err) {
      setError('Failed to mark all alerts as read');
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'high':
        return <AlertTriangle className="h-5 w-5 text-orange-500" />;
      case 'medium':
        return <Info className="h-5 w-5 text-yellow-500" />;
      case 'low':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Bell className="h-5 w-5 text-slate-400" />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    const styles: Record<string, string> = {
      critical: 'bg-red-100 text-red-700',
      high: 'bg-orange-100 text-orange-700',
      medium: 'bg-yellow-100 text-yellow-700',
      low: 'bg-green-100 text-green-700',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[severity] || 'bg-slate-100 text-slate-700'}`}>
        {severity.charAt(0).toUpperCase() + severity.slice(1)}
      </span>
    );
  };

  const getAlertTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      new_exposure: 'New Exposure',
      re_listed: 'Re-listed',
      removal_confirmed: 'Removal Confirmed',
      breach_detected: 'Data Breach',
      new_account: 'Account Found',
    };
    return labels[type] || type;
  };

  const unreadCount = alerts.filter(a => !a.is_read).length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/dashboard" className="text-slate-500 hover:text-slate-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2">
            <Bell className="h-6 w-6 text-primary" />
            <span className="font-bold">Alerts</span>
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-3xl">
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">{error}</div>
        )}

        {/* Filters */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                filter === 'all'
                  ? 'bg-primary text-white'
                  : 'bg-white text-slate-600 border border-slate-300'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                filter === 'unread'
                  ? 'bg-primary text-white'
                  : 'bg-white text-slate-600 border border-slate-300'
              }`}
            >
              Unread
            </button>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-primary text-sm font-medium flex items-center gap-1"
            >
              <Check className="h-4 w-4" />
              Mark all as read
            </button>
          )}
        </div>

        {/* Alerts List */}
        <div className="bg-white rounded-xl shadow-sm">
          {alerts.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No alerts to show</p>
            </div>
          ) : (
            <div className="divide-y">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-6 hover:bg-slate-50 ${!alert.is_read ? 'bg-blue-50/50' : ''}`}
                >
                  <div className="flex items-start gap-4">
                    {getSeverityIcon(alert.severity)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{alert.title}</span>
                        {!alert.is_read && (
                          <span className="bg-blue-500 rounded-full w-2 h-2"></span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        {getSeverityBadge(alert.severity)}
                        <span className="text-xs text-slate-400">
                          {getAlertTypeLabel(alert.alert_type)}
                        </span>
                        <span className="text-xs text-slate-400">
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {alert.description && (
                        <p className="text-sm text-slate-600 mb-2">{alert.description}</p>
                      )}
                      <div className="flex items-center gap-3">
                        {alert.source_url && (
                          <a
                            href={alert.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary text-sm flex items-center gap-1"
                          >
                            View Source <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                        {!alert.is_read && (
                          <button
                            onClick={() => handleMarkRead(alert.id)}
                            className="text-slate-500 text-sm"
                          >
                            Mark as read
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
