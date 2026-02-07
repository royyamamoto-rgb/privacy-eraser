'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Shield, ArrowLeft, Check, CreditCard, Zap, Crown } from 'lucide-react';
import api from '@/lib/api';

interface Subscription {
  plan: string;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    features: [
      '1 scan per month',
      '5 broker coverage',
      'Manual removal instructions',
      'Email support',
    ],
    cta: 'Current Plan',
    popular: false,
  },
  {
    id: 'basic',
    name: 'Basic',
    price: '$5',
    yearlyPrice: '$49',
    period: 'per month',
    yearlyPeriod: 'per year',
    features: [
      'Unlimited scans',
      '50+ broker coverage',
      'Auto-submit removals',
      'Email notifications',
      'Priority support',
    ],
    cta: 'Upgrade to Basic',
    popular: true,
    monthlyPriceId: 'basic_monthly',
    yearlyPriceId: 'basic_yearly',
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$9',
    yearlyPrice: '$89',
    period: 'per month',
    yearlyPeriod: 'per year',
    features: [
      'Everything in Basic',
      '100+ broker coverage',
      'GDPR/CCPA requests',
      'Dark web monitoring',
      'Family protection (up to 5)',
      'Dedicated support',
    ],
    cta: 'Upgrade to Premium',
    popular: false,
    monthlyPriceId: 'premium_monthly',
    yearlyPriceId: 'premium_yearly',
  },
];

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchSubscription();

    // Check for success/cancel from Stripe
    if (searchParams.get('success')) {
      setMessage({ type: 'success', text: 'Subscription activated successfully!' });
    } else if (searchParams.get('canceled')) {
      setMessage({ type: 'error', text: 'Checkout was canceled.' });
    }
  }, [searchParams]);

  const fetchSubscription = async () => {
    try {
      const data = await api.getSubscription();
      setSubscription(data);
    } catch (err: any) {
      if (err.message?.includes('401')) {
        router.push('/auth/login');
        return;
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (priceId: string) => {
    setProcessing(priceId);
    try {
      const { checkout_url } = await api.createCheckout(priceId);
      window.location.href = checkout_url;
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to start checkout' });
      setProcessing(null);
    }
  };

  const handleManageBilling = async () => {
    setProcessing('portal');
    try {
      const { portal_url } = await api.createBillingPortal();
      window.location.href = portal_url;
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to open billing portal' });
      setProcessing(null);
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
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/dashboard" className="text-slate-500 hover:text-slate-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2">
            <CreditCard className="h-6 w-6 text-primary" />
            <span className="font-bold">Billing & Subscription</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-5xl">
        {message && (
          <div className={`p-4 rounded-lg mb-6 ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
            {message.text}
          </div>
        )}

        {/* Current Plan */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
          <h2 className="font-semibold mb-4">Current Plan</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                {subscription?.plan === 'premium' && <Crown className="h-5 w-5 text-yellow-500" />}
                {subscription?.plan === 'basic' && <Zap className="h-5 w-5 text-blue-500" />}
                <span className="text-xl font-bold capitalize">{subscription?.plan || 'Free'}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  subscription?.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                }`}>
                  {subscription?.status || 'Active'}
                </span>
              </div>
              {subscription?.current_period_end && (
                <p className="text-sm text-slate-600 mt-1">
                  {subscription.cancel_at_period_end ? 'Cancels' : 'Renews'} on {new Date(subscription.current_period_end).toLocaleDateString()}
                </p>
              )}
            </div>
            {subscription?.plan !== 'free' && (
              <button
                onClick={handleManageBilling}
                disabled={processing === 'portal'}
                className="border border-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                {processing === 'portal' ? 'Loading...' : 'Manage Billing'}
              </button>
            )}
          </div>
        </div>

        {/* Billing Cycle Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-lg p-1 inline-flex shadow-sm">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingCycle === 'monthly' ? 'bg-primary text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('yearly')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingCycle === 'yearly' ? 'bg-primary text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Yearly
              <span className="ml-1 text-xs opacity-75">(Save 20%)</span>
            </button>
          </div>
        </div>

        {/* Plans */}
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const isCurrentPlan = subscription?.plan === plan.id;
            const priceId = billingCycle === 'yearly' ? plan.yearlyPriceId : plan.monthlyPriceId;
            const price = billingCycle === 'yearly' ? plan.yearlyPrice : plan.price;
            const period = billingCycle === 'yearly' ? plan.yearlyPeriod : plan.period;

            return (
              <div
                key={plan.id}
                className={`bg-white rounded-xl shadow-sm p-6 relative ${
                  plan.popular ? 'ring-2 ring-primary' : ''
                }`}
              >
                {plan.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-medium px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                )}

                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold">{plan.name}</h3>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{price || plan.price}</span>
                    <span className="text-slate-600 text-sm">/{period || plan.period}</span>
                  </div>
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                {plan.id === 'free' ? (
                  <button
                    disabled
                    className="w-full py-2 rounded-lg text-sm font-medium bg-slate-100 text-slate-500 cursor-not-allowed"
                  >
                    {isCurrentPlan ? 'Current Plan' : 'Free Forever'}
                  </button>
                ) : isCurrentPlan ? (
                  <button
                    disabled
                    className="w-full py-2 rounded-lg text-sm font-medium bg-green-100 text-green-700 cursor-not-allowed"
                  >
                    Current Plan
                  </button>
                ) : (
                  <button
                    onClick={() => priceId && handleUpgrade(priceId)}
                    disabled={processing === priceId || !priceId}
                    className={`w-full py-2 rounded-lg text-sm font-medium disabled:opacity-50 ${
                      plan.popular
                        ? 'bg-primary text-white hover:bg-primary/90'
                        : 'border border-primary text-primary hover:bg-primary/5'
                    }`}
                  >
                    {processing === priceId ? 'Loading...' : plan.cta}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* FAQ */}
        <div className="mt-12 bg-white rounded-xl shadow-sm p-6">
          <h2 className="font-semibold mb-4">Frequently Asked Questions</h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium">Can I cancel anytime?</h3>
              <p className="text-sm text-slate-600 mt-1">
                Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period.
              </p>
            </div>
            <div>
              <h3 className="font-medium">What payment methods do you accept?</h3>
              <p className="text-sm text-slate-600 mt-1">
                We accept all major credit cards through our secure payment processor, Stripe.
              </p>
            </div>
            <div>
              <h3 className="font-medium">Is there a refund policy?</h3>
              <p className="text-sm text-slate-600 mt-1">
                We offer a 30-day money-back guarantee. If you're not satisfied, contact us for a full refund.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
