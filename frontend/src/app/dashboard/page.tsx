'use client';

import { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Clock, Bell, Search, RefreshCw, LogOut } from 'lucide-react';
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
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileComplete, setProfileComplete] = useState(false);

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
    try {
      await api.startScan();
      // Poll for results or wait
      setTimeout(() => {
        fetchData();
        setScanning(false);
      }, 5000);
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

  const [removingId, setRemovingId] = useState<string | null>(null);

  const handleRemove = async (exposureId: string) => {
    setRemovingId(exposureId);
    setError('');
    try {
      await api.createRequest(exposureId, 'opt_out');
      // Show success message briefly
      setError('');
      await fetchData();
    } catch (err: any) {
      console.error('Remove error:', err);
      if (err.message?.includes('already exists')) {
        setError('A removal request already exists for this exposure.');
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
        return <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full text-xs font-medium">Pending</span>;
      case 'removed':
        return <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-medium">Removed</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded-full text-xs font-medium">{status}</span>;
    }
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
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-4 h-4 rounded-full flex items-center justify-center">
                3
              </span>
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
                <div className="text-2xl font-bold">{stats?.total_exposures}</div>
                <div className="text-sm text-slate-600">Active Exposures</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-yellow-100 p-3 rounded-lg">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.pending_removals}</div>
                <div className="text-sm text-slate-600">Pending Removals</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-green-100 p-3 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.completed_removals}</div>
                <div className="text-sm text-slate-600">Removed</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="bg-blue-100 p-3 rounded-lg">
                <Search className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold">{stats?.brokers_scanned}</div>
                <div className="text-sm text-slate-600">Brokers Scanned</div>
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
                <h3 className="font-medium text-amber-800">Complete Your Profile to Start Scanning</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Add your personal information (name, addresses, phone numbers) so we can search for your data on broker sites.
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
              disabled={scanning}
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {scanning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Run New Scan
                </>
              )}
            </button>
            <Link
              href="/dashboard/requests"
              className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50"
            >
              View All Requests
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
          <div className="p-6 border-b">
            <h2 className="font-semibold">Your Exposures</h2>
          </div>
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
                      Detected: {new Date(exposure.first_detected_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {getStatusBadge(exposure.status)}
                  {exposure.status === 'found' && (
                    <button
                      onClick={() => handleRemove(exposure.id)}
                      disabled={removingId === exposure.id}
                      className="bg-primary text-white px-3 py-1 rounded text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
                    >
                      {removingId === exposure.id ? 'Removing...' : 'Remove'}
                    </button>
                  )}
                  {exposure.profile_url && (
                    <a
                      href={exposure.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-600 text-sm hover:underline"
                    >
                      View
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
