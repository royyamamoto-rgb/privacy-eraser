'use client';

import Link from 'next/link';
import { Shield, Search, Bell, CheckCircle, ArrowRight } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Navigation */}
      <nav className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">Privacy Eraser</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/auth/login" className="text-sm font-medium hover:text-primary">
            Log in
          </Link>
          <Link
            href="/auth/register"
            className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-slate-900 mb-6">
          Remove Your Personal Data<br />
          <span className="text-primary">From the Internet</span>
        </h1>
        <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-8">
          We scan 100+ data broker and people search sites, automatically submit
          opt-out requests on your behalf, and monitor daily to keep your information private.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/auth/register"
            className="bg-primary text-white px-8 py-3 rounded-lg font-medium hover:bg-primary/90 flex items-center gap-2"
          >
            Start Free Scan <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="#how-it-works"
            className="border border-slate-300 text-slate-700 px-8 py-3 rounded-lg font-medium hover:bg-slate-50"
          >
            How It Works
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 max-w-3xl mx-auto mt-16">
          <div>
            <div className="text-4xl font-bold text-primary">100+</div>
            <div className="text-slate-600">Sites Scanned</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary">Daily</div>
            <div className="text-slate-600">Monitoring</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary">50+</div>
            <div className="text-slate-600">Auto-Opt-Out</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="how-it-works" className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="h-8 w-8 text-primary" />
            </div>
            <h3 className="font-semibold mb-2">1. Scan</h3>
            <p className="text-slate-600 text-sm">
              We search 100+ data broker and people search sites to find where your information is exposed.
            </p>
          </div>
          <div className="text-center">
            <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="h-8 w-8 text-primary" />
            </div>
            <h3 className="font-semibold mb-2">2. Remove</h3>
            <p className="text-slate-600 text-sm">
              We automatically submit opt-out requests to remove your data.
            </p>
          </div>
          <div className="text-center">
            <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <Bell className="h-8 w-8 text-primary" />
            </div>
            <h3 className="font-semibold mb-2">3. Monitor</h3>
            <p className="text-slate-600 text-sm">
              Daily monitoring alerts you if your data reappears after removal.
            </p>
          </div>
          <div className="text-center">
            <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-primary" />
            </div>
            <h3 className="font-semibold mb-2">4. Protect</h3>
            <p className="text-slate-600 text-sm">
              Your personal information stays private and protected.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="container mx-auto px-4 py-20 bg-slate-50 rounded-3xl">
        <h2 className="text-3xl font-bold text-center mb-4">Simple Pricing</h2>
        <p className="text-slate-600 text-center mb-12">No hidden fees. Cancel anytime.</p>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {/* Free */}
          <div className="bg-white rounded-2xl p-8 border border-slate-200">
            <h3 className="font-semibold text-lg mb-2">Free</h3>
            <div className="text-4xl font-bold mb-4">$0</div>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                One-time scan
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                See your exposures
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-400">
                <CheckCircle className="h-4 w-4" />
                Auto-removal
              </li>
            </ul>
            <Link
              href="/auth/register"
              className="block text-center border border-slate-300 py-2 rounded-lg font-medium hover:bg-slate-50"
            >
              Get Started
            </Link>
          </div>

          {/* Basic */}
          <div className="bg-white rounded-2xl p-8 border-2 border-primary relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs px-3 py-1 rounded-full">
              Most Popular
            </div>
            <h3 className="font-semibold text-lg mb-2">Basic</h3>
            <div className="text-4xl font-bold mb-4">
              $59<span className="text-lg font-normal text-slate-500">/year</span>
            </div>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                100+ sites scanned
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                50+ auto opt-out
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Monthly monitoring
              </li>
            </ul>
            <Link
              href="/auth/register?plan=basic"
              className="block text-center bg-primary text-white py-2 rounded-lg font-medium hover:bg-primary/90"
            >
              Start Now
            </Link>
          </div>

          {/* Premium */}
          <div className="bg-white rounded-2xl p-8 border border-slate-200">
            <h3 className="font-semibold text-lg mb-2">Premium</h3>
            <div className="text-4xl font-bold mb-4">
              $99<span className="text-lg font-normal text-slate-500">/year</span>
            </div>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Everything in Basic
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                GDPR/CCPA requests
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Daily monitoring
              </li>
              <li className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                Priority support
              </li>
            </ul>
            <Link
              href="/auth/register?plan=premium"
              className="block text-center border border-slate-300 py-2 rounded-lg font-medium hover:bg-slate-50"
            >
              Start Now
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-12 text-center text-slate-600 text-sm">
        <p>&copy; 2026 Privacy Eraser. All rights reserved.</p>
      </footer>
    </div>
  );
}
