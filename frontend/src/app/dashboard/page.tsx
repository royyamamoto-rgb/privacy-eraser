'use client';

import { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Clock, Bell, Search, RefreshCw, LogOut, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface DashboardStats {
  total_exposures: number;
  pending_removals: number;
  completed_removals: number;
  brokers_scanned: number;
}

interface Exposure {
  id: string;
  broker_name: string;
  status: string;
  profile_url: string | null;
  first_detected_at: string;
}

interface UserProfile {
  first_name: string | null;
  last_name: string | null;
}

export default function Dashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [exposures, setExposures] = useState<Exposure[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileComplete, setProfileComplete] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [statsData, exposuresData, userData] = await Promise.all([
        api.getDashboardStats(),
        api.getExposures(),
        api.getProfile(),
      ]);
      setStats(statsData);
      setExposures(exposuresData);
      if (userData?.profile) {
        setProfile(userData.profile);
        setProfileComplete(!!userData.profile.first_name && !!userData.profile.last_name);
      }
      setError('');
    } catch (err: any) {
      if (err.message?.includes('401') || err.message?.includes('Unauthorized')) {
        router.push('/auth/login');
        return;
      }
      setError('Failed to load dashboard data. Please try refreshing the page.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleScan = async () => {
    if (!profileComplete) {
      setError('Please complete your profile with at least your name before scanning.');
      return;
    }
    setScanning(true);
    setError('');
    setSuccessMessage('');
    try {
      await api.startScan();
      setSuccessMessage('Scanning in progress... This may take a minute.');
      // Poll for results
      setTimeout(() => {
        fetchData();
        setScanning(false);
        setSuccessMessage('Scan complete! Check your exposures below.');
      }, 10000);
    } catch (err: any) {
      if (err.message?.includes('profile')) {
        setError('Please complete your profile before scanning. Go to Profile Settings to add your personal information.');
      } else {
        setError(err.message || 'Scan failed. Please try again.');
      }
      setScanning(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    router.push('/');
  };

  const handleRemove = async (exposureId: string) => {
    setRemovingId(exposureId);
    setError('');
    setSuccessMessage('');

    try {
      const result = await api.createRequest(exposureId, 'opt_out');

      // Show success message
      setSuccessMessage('✅ Opt-out request submitted automatically! We\'re processing your removal now.');

      // Refresh data to update the exposure status to "pending_removal"
      await fetchData();

      // Redirect to requests page after a delay so user sees the status change
      setTimeout(() => {
        router.push('/dashboard/requests');
      }, 2000);

    } catch (err: any) {
      console.error('Remove error:', err);

      // If request already exists, refresh data and show the updated status
      if (err.message?.includes('already exists') || err.message?.includes('already in progress')) {
        setSuccessMessage('Request already in progress. Refreshing status...');
        await fetchData();
        setTimeout(() => {
          router.push('/dashboard/requests');
        }, 1500);
      } else if (err.message?.includes('profile')) {
        setError('Please complete your profile before requesting removal.');
      } else {
        setError(err.message || 'Failed to create removal request. Please try again.');
      }
    } finally {
      setRemovingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'found':
        return <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-medium">Exposed</span>;
      case 'pending_removal':
        return <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium animate-pulse">Processing</span>;
      case 'removed':
        return <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-medium">✓ Removed</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded-full text-xs font-medium">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading your privacy dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="font-bold">Privacy Eraser</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/dashboard/alerts" className="relative">
              <Bell className="h-5 w-5 text-slate-600" />
            </Link>
            <Link href="/dashboard/profile" className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-primary">ME</span>
            </Link>
            <button onClick={handleLogout} className="text-slate-500 hover:text-slate-700">
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-red-100 p-3 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.total_exposures || 0}</div>
                <div className="text-sm text-slate-600">Active Exposures</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-blue-100 p-3 rounded-lg">
                <Clock className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.pending_removals || 0}</div>
                <div className="text-sm text-slate-600">Being Removed</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-green-100 p-3 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.completed_removals || 0}</div>
                <div className="text-sm text-slate-600">Removed</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-purple-100 p-3 rounded-lg">
                <Search className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.brokers_scanned || 0}</div>
                <div className="text-sm text-slate-600">Sites Scanned</div>
              </div>
            </div>
          </div>
        </div>

        {/* Profile Incomplete Banner */}
        {!profileComplete && (
          <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg mb-8">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-amber-800">Complete Your Profile to Start</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Add your personal information (name, addresses, phone numbers) so we can search for and remove your data.
                </p>
                <Link
                  href="/dashboard/profile"
                  className="inline-block mt-3 bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-700"
                >
                  Complete Profile Now
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg mb-8 flex items-center gap-3">
            <CheckCircle className="h-5 w-5" />
            {successMessage}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-8">
            {error}
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-xl p-6 shadow-sm mb-8">
          <h2 className="font-semibold mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={handleScan}
              disabled={scanning || !profileComplete}
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {scanning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Scanning 70+ Sites...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Run Deep Scan
                </>
              )}
            </button>
            <Link
              href="/dashboard/requests"
              className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center gap-2"
            >
              <Clock className="h-4 w-4" />
              View Removal Progress
            </Link>
            <Link
              href="/dashboard/profile"
              className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50"
            >
              Update Profile
            </Link>
          </div>
        </div>

        {/* Exposures List */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="p-6 border-b flex justify-between items-center">
            <h2 className="font-semibold">Your Exposures</h2>
            {exposures.length > 0 && (
              <span className="text-sm text-slate-500">{exposures.length} found</span>
            )}
          </div>

          {exposures.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p className="font-medium">No exposures found yet</p>
              <p className="text-sm mt-1">Run a scan to find where your data is exposed online</p>
            </div>
          ) : (
            <div className="divide-y">
              {exposures.map((exposure) => (
                <div key={exposure.id} className="p-6 flex items-center justify-between hover:bg-slate-50">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Shield className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <div className="font-medium">{exposure.broker_name}</div>
                      <div className="text-sm text-slate-600">
                        Found: {new Date(exposure.first_detected_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(exposure.status)}

                    {/* Show Remove button only for "found" status */}
                    {exposure.status === 'found' && (
                      <button
                        onClick={() => handleRemove(exposure.id)}
                        disabled={removingId === exposure.id}
                        className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                      >
                        {removingId === exposure.id ? 'Processing...' : 'Remove'}
                      </button>
                    )}

                    {/* Show View Progress for pending_removal */}
                    {exposure.status === 'pending_removal' && (
                      <Link
                        href="/dashboard/requests"
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
                      >
                        View Progress
                      </Link>
                    )}

                    {/* View profile link */}
                    {exposure.profile_url && (
                      <a
                        href={exposure.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-500 hover:text-slate-700 p-2"
                        title="View on site"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
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
