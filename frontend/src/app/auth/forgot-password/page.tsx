'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';
import api from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err: any) {
      setError(err.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Link href="/" className="inline-flex items-center gap-2">
              <Shield className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold">Privacy Eraser</span>
            </Link>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="h-8 w-8 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Check your email</h1>
            <p className="text-slate-600 mb-6">
              If an account exists for {email}, we've sent a password reset link.
            </p>
            <Link
              href="/auth/login"
              className="text-primary font-medium hover:underline"
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">Privacy Eraser</span>
          </Link>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-8">
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-1 text-slate-600 text-sm mb-6 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to login
          </Link>

          <h1 className="text-2xl font-bold mb-2">Forgot password?</h1>
          <p className="text-slate-600 text-sm mb-6">
            No worries, we'll send you reset instructions.
          </p>

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="you@example.com"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white py-2 rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Reset password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
