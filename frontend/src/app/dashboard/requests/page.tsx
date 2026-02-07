'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, ArrowLeft, Clock, CheckCircle, XCircle, AlertTriangle, ExternalLink } from 'lucide-react';
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

  const handleSubmit = async (requestId: string) => {
    try {
      await api.submitRequest(requestId);
      fetchData();
    } catch (err: any) {
      setError('Failed to submit request');
    }
  };

  const handleComplete = async (requestId: string) => {
    try {
      await api.completeRequest(requestId);
      fetchData();
    } catch (err: any) {
      setError('Failed to complete request');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'submitted':
        return <Clock className="h-5 w-5 text-blue-500" />;
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
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-slate-100 text-slate-700'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
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
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold">{stats.total}</div>
              <div className="text-sm text-slate-600">Total</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
              <div className="text-sm text-slate-600">Pending</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-blue-600">{stats.submitted}</div>
              <div className="text-sm text-slate-600">Submitted</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
              <div className="text-sm text-slate-600">Completed</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl font-bold text-orange-600">{stats.requires_action}</div>
              <div className="text-sm text-slate-600">Needs Action</div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">{error}</div>
        )}

        {/* Requests List */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="p-6 border-b">
            <h2 className="font-semibold">All Requests</h2>
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
                          {request.submitted_at && (
                            <> • Submitted: {new Date(request.submitted_at).toLocaleDateString()}</>
                          )}
                          {request.expected_completion && (
                            <> • Expected: {new Date(request.expected_completion).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {getStatusBadge(request.status)}
                      {request.requires_user_action && (
                        <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          Action Needed
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-4 flex gap-3">
                    {request.status === 'pending' && (
                      <button
                        onClick={() => handleSubmit(request.id)}
                        className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90"
                      >
                        Submit Request
                      </button>
                    )}
                    {request.status === 'submitted' && (
                      <button
                        onClick={() => handleComplete(request.id)}
                        className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
                      >
                        Mark as Complete
                      </button>
                    )}
                    {request.instructions && (
                      <button
                        onClick={() => setSelectedRequest(request)}
                        className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50"
                      >
                        View Instructions
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
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-auto">
            <div className="p-6 border-b">
              <h3 className="font-semibold">Instructions for {selectedRequest.broker_name}</h3>
            </div>
            <div className="p-6">
              <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 p-4 rounded-lg">
                {selectedRequest.instructions}
              </pre>
            </div>
            <div className="p-6 border-t flex justify-end">
              <button
                onClick={() => setSelectedRequest(null)}
                className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium"
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
