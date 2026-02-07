'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, ArrowLeft, Clock, CheckCircle, XCircle, AlertTriangle, ExternalLink, FileText } from 'lucide-react';
import api from '@/lib/api';

interface Request {
  id: string;
  broker_id: string;
  broker_name: string;
  exposure_id: string | null;
  request_type: string;
  status: string;
  submitted_at: string | null;
  expected_completion: string | null;
  completed_at: string | null;
  requires_user_action: boolean;
  instructions: string | null;
  opt_out_url: string | null;
  profile_url: string | null;
  created_at: string;
}

interface RequestStats {
  total: number;
  pending: number;
  submitted: number;
  completed: number;
  failed: number;
  requires_action: number;
}

export default function RequestsPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<Request[]>([]);
  const [stats, setStats] = useState<RequestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedRequest, setSelectedRequest] = useState<Request | null>(null);
  const [completing, setCompleting] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [requestsData, statsData] = await Promise.all([
        api.listRequests(),
        api.getRequestStats(),
      ]);
      setRequests(requestsData);
      setStats(statsData);
    } catch (err: any) {
      if (err.message?.includes('401')) {
        router.push('/auth/login');
        return;
      }
      setError('Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (requestId: string) => {
    setCompleting(requestId);
    try {
      await api.completeRequest(requestId);
      fetchData();
    } catch (err: any) {
      setError('Failed to complete request');
    } finally {
      setCompleting(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'submitted':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      submitted: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    };
    const labels: Record<string, string> = {
      pending: 'Pending',
      submitted: 'In Progress',
      completed: 'Removed',
      failed: 'Failed',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-slate-100 text-slate-700'}`}>
        {labels[status] || status}
      </span>
    );
  };

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
            <Shield className="h-6 w-6 text-primary" />
            <span className="font-bold">Removal Requests</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-8">
          <div className="flex items-start gap-3">
            <FileText className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h3 className="font-medium text-blue-800">How Removal Works</h3>
              <p className="text-sm text-blue-700 mt-1">
                Each site has different opt-out procedures. Click "View Instructions" to see step-by-step
                guide for each site. After completing the opt-out on their website, click "Mark as Removed"
                to update your dashboard. Most removals take 24-72 hours to process.
              </p>
            </div>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold">{stats.total}</div>
              <div className="text-sm text-slate-600">Total</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-blue-600">{stats.submitted}</div>
              <div className="text-sm text-slate-600">In Progress</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
              <div className="text-sm text-slate-600">Removed</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-orange-600">{stats.requires_action}</div>
              <div className="text-sm text-slate-600">Needs Action</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
              <div className="text-sm text-slate-600">Failed</div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">{error}</div>
        )}

        {/* Requests List */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="p-6 border-b">
            <h2 className="font-semibold">All Removal Requests</h2>
          </div>

          {requests.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No removal requests yet</p>
              <Link href="/dashboard" className="text-primary mt-2 inline-block">
                Go to dashboard to start removing your data
              </Link>
            </div>
          ) : (
            <div className="divide-y">
              {requests.map((request) => (
                <div key={request.id} className="p-6 hover:bg-slate-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      {getStatusIcon(request.status)}
                      <div>
                        <div className="font-medium">{request.broker_name}</div>
                        <div className="text-sm text-slate-600">
                          {request.request_type === 'opt_out' && 'Opt-out Request'}
                          {request.request_type === 'gdpr_delete' && 'GDPR Deletion Request'}
                          {request.request_type === 'ccpa_delete' && 'CCPA Deletion Request'}
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          Created: {new Date(request.created_at).toLocaleDateString()}
                          {request.expected_completion && request.status !== 'completed' && (
                            <> • Expected removal by: <strong>{new Date(request.expected_completion).toLocaleDateString()}</strong></>
                          )}
                          {request.completed_at && (
                            <> • Removed: {new Date(request.completed_at).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {getStatusBadge(request.status)}
                      {request.requires_user_action && request.status !== 'completed' && (
                        <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          Action Needed
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-4 flex flex-wrap gap-3">
                    {/* Opt-out link */}
                    {request.opt_out_url && request.status !== 'completed' && (
                      <a
                        href={request.opt_out_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 flex items-center gap-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Go to Opt-Out Page
                      </a>
                    )}

                    {/* View profile */}
                    {request.profile_url && (
                      <a
                        href={request.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center gap-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        View Your Profile
                      </a>
                    )}

                    {/* Instructions */}
                    {request.instructions && (
                      <button
                        onClick={() => setSelectedRequest(request)}
                        className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center gap-2"
                      >
                        <FileText className="h-4 w-4" />
                        View Instructions
                      </button>
                    )}

                    {/* Mark complete */}
                    {request.status === 'submitted' && (
                      <button
                        onClick={() => handleComplete(request.id)}
                        disabled={completing === request.id}
                        className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        <CheckCircle className="h-4 w-4" />
                        {completing === request.id ? 'Updating...' : 'Mark as Removed'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Instructions Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="p-6 border-b sticky top-0 bg-white">
              <h3 className="font-semibold text-lg">Removal Instructions for {selectedRequest.broker_name}</h3>
            </div>
            <div className="p-6">
              <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 p-4 rounded-lg font-sans leading-relaxed">
                {selectedRequest.instructions}
              </pre>

              {selectedRequest.opt_out_url && (
                <a
                  href={selectedRequest.opt_out_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 flex items-center gap-2 inline-flex"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open Opt-Out Page
                </a>
              )}
            </div>
            <div className="p-6 border-t flex justify-between items-center sticky bottom-0 bg-white">
              <p className="text-sm text-slate-500">
                After completing the opt-out, click "Mark as Removed" to update your dashboard.
              </p>
              <button
                onClick={() => setSelectedRequest(null)}
                className="bg-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
