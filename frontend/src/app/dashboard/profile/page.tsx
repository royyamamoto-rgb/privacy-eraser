'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, ArrowLeft, Plus, Trash2, Save } from 'lucide-react';
import api from '@/lib/api';

interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface ProfileData {
  first_name: string;
  last_name: string;
  middle_name: string;
  maiden_name: string;
  nicknames: string[];
  emails: string[];
  phone_numbers: string[];
  addresses: Address[];
  date_of_birth: string;
  relatives: string[];
}

export default function ProfilePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [profile, setProfile] = useState<ProfileData>({
    first_name: '',
    last_name: '',
    middle_name: '',
    maiden_name: '',
    nicknames: [],
    emails: [],
    phone_numbers: [],
    addresses: [{ street: '', city: '', state: '', zip: '' }],
    date_of_birth: '',
    relatives: [],
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const data = await api.getProfile();
      if (data.profile) {
        setProfile({
          first_name: data.profile.first_name || '',
          last_name: data.profile.last_name || '',
          middle_name: data.profile.middle_name || '',
          maiden_name: data.profile.maiden_name || '',
          nicknames: data.profile.nicknames || [],
          emails: data.profile.emails || [data.email],
          phone_numbers: data.profile.phone_numbers || [],
          addresses: data.profile.addresses || [{ street: '', city: '', state: '', zip: '' }],
          date_of_birth: data.profile.date_of_birth || '',
          relatives: data.profile.relatives || [],
        });
      }
    } catch (err: any) {
      if (err.message?.includes('401')) {
        router.push('/auth/login');
        return;
      }
      setError('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      await api.updateProfile(profile);
      setSuccess('Profile updated successfully');
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const addAddress = () => {
    setProfile({
      ...profile,
      addresses: [...profile.addresses, { street: '', city: '', state: '', zip: '' }],
    });
  };

  const removeAddress = (index: number) => {
    setProfile({
      ...profile,
      addresses: profile.addresses.filter((_, i) => i !== index),
    });
  };

  const updateAddress = (index: number, field: keyof Address, value: string) => {
    const newAddresses = [...profile.addresses];
    newAddresses[index] = { ...newAddresses[index], [field]: value };
    setProfile({ ...profile, addresses: newAddresses });
  };

  const addArrayField = (field: 'emails' | 'phone_numbers' | 'nicknames' | 'relatives') => {
    setProfile({
      ...profile,
      [field]: [...profile[field], ''],
    });
  };

  const removeArrayField = (field: 'emails' | 'phone_numbers' | 'nicknames' | 'relatives', index: number) => {
    setProfile({
      ...profile,
      [field]: profile[field].filter((_, i) => i !== index),
    });
  };

  const updateArrayField = (field: 'emails' | 'phone_numbers' | 'nicknames' | 'relatives', index: number, value: string) => {
    const newArr = [...profile[field]];
    newArr[index] = value;
    setProfile({ ...profile, [field]: newArr });
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
            <span className="font-bold">Profile Settings</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-3xl">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h1 className="text-xl font-bold mb-2">Personal Information</h1>
          <p className="text-slate-600 text-sm mb-6">
            The more information you provide, the better we can scan for your data across data broker sites.
          </p>

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>
          )}

          {success && (
            <div className="bg-green-50 text-green-600 p-3 rounded-lg mb-4 text-sm">{success}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Name */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">First Name *</label>
                <input
                  type="text"
                  value={profile.first_name}
                  onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Last Name *</label>
                <input
                  type="text"
                  value={profile.last_name}
                  onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Middle Name</label>
                <input
                  type="text"
                  value={profile.middle_name}
                  onChange={(e) => setProfile({ ...profile, middle_name: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Maiden Name</label>
                <input
                  type="text"
                  value={profile.maiden_name}
                  onChange={(e) => setProfile({ ...profile, maiden_name: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {/* Date of Birth */}
            <div>
              <label className="block text-sm font-medium mb-1">Date of Birth</label>
              <input
                type="date"
                value={profile.date_of_birth}
                onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Addresses */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Addresses (Current and Past)</label>
                <button
                  type="button"
                  onClick={addAddress}
                  className="text-primary text-sm flex items-center gap-1"
                >
                  <Plus className="h-4 w-4" /> Add Address
                </button>
              </div>
              {profile.addresses.map((addr, index) => (
                <div key={index} className="border rounded-lg p-4 mb-3 relative">
                  {profile.addresses.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeAddress(index)}
                      className="absolute top-2 right-2 text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                  <div className="grid grid-cols-1 gap-3">
                    <input
                      type="text"
                      placeholder="Street Address"
                      value={addr.street}
                      onChange={(e) => updateAddress(index, 'street', e.target.value)}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <div className="grid grid-cols-3 gap-3">
                      <input
                        type="text"
                        placeholder="City"
                        value={addr.city}
                        onChange={(e) => updateAddress(index, 'city', e.target.value)}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <input
                        type="text"
                        placeholder="State"
                        value={addr.state}
                        onChange={(e) => updateAddress(index, 'state', e.target.value)}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <input
                        type="text"
                        placeholder="ZIP"
                        value={addr.zip}
                        onChange={(e) => updateAddress(index, 'zip', e.target.value)}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Emails */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Email Addresses</label>
                <button
                  type="button"
                  onClick={() => addArrayField('emails')}
                  className="text-primary text-sm flex items-center gap-1"
                >
                  <Plus className="h-4 w-4" /> Add Email
                </button>
              </div>
              {profile.emails.map((email, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => updateArrayField('emails', index, e.target.value)}
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="email@example.com"
                  />
                  {profile.emails.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeArrayField('emails', index)}
                      className="text-red-500 px-2"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Phone Numbers */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Phone Numbers</label>
                <button
                  type="button"
                  onClick={() => addArrayField('phone_numbers')}
                  className="text-primary text-sm flex items-center gap-1"
                >
                  <Plus className="h-4 w-4" /> Add Phone
                </button>
              </div>
              {profile.phone_numbers.map((phone, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => updateArrayField('phone_numbers', index, e.target.value)}
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="(555) 123-4567"
                  />
                  <button
                    type="button"
                    onClick={() => removeArrayField('phone_numbers', index)}
                    className="text-red-500 px-2"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {profile.phone_numbers.length === 0 && (
                <button
                  type="button"
                  onClick={() => addArrayField('phone_numbers')}
                  className="text-slate-500 text-sm"
                >
                  + Add a phone number
                </button>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={saving}
              className="w-full bg-primary text-white py-3 rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving ? (
                'Saving...'
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Profile
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
