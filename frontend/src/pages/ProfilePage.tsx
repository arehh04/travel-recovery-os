/** Profile page — Enterprise Passenger Profile, Preferences & Frequent Flyer Manager. */

import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { UserProfile, LoyaltyAccount } from '../api/types';

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');
  
  // New loyalty modal state
  const [showAddLoyalty, setShowAddLoyalty] = useState(false);
  const [newProgram, setNewProgram] = useState('British Airways Executive Club');
  const [newAlliance, setNewAlliance] = useState('Oneworld');
  const [newTier, setNewTier] = useState('Gold');
  const [newMemberNum, setNewMemberNum] = useState('');
  const [newPoints, setNewPoints] = useState(25000);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await api.get<UserProfile>('/profile');
      setProfile(data);
    } catch (e) {
      console.error('Failed to load profile from backend:', e);
    } finally {
      setLoading(false);
    }
  };

  const showSaved = (msg: string) => {
    setSavedMessage(msg);
    setTimeout(() => setSavedMessage(''), 3000);
  };

  const handleUpdateField = async (field: keyof UserProfile, value: any) => {
    if (!profile) return;
    const updated = { ...profile, [field]: value };
    setProfile(updated);
    try {
      setSaving(true);
      await api.put<UserProfile>('/profile', updated);
      showSaved('Profile updated successfully');
    } catch (e) {
      console.error('Failed to update profile:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleAddLoyalty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberNum.trim()) return;

    try {
      const newAcc: LoyaltyAccount = {
        program_name: newProgram,
        alliance: newAlliance,
        tier_status: newTier,
        member_number: newMemberNum.trim(),
        points_balance: newPoints,
      };
      await api.post<LoyaltyAccount>('/profile/loyalty', newAcc);
      setShowAddLoyalty(false);
      setNewMemberNum('');
      await loadProfile();
      showSaved('Frequent flyer account linked');
    } catch (e) {
      console.error('Failed to add loyalty account:', e);
    }
  };

  const handleDeleteLoyalty = async (id?: number) => {
    if (!id) return;
    try {
      await api.delete(`/profile/loyalty/${id}`);
      await loadProfile();
      showSaved('Loyalty account removed');
    } catch (e) {
      console.error('Failed to delete loyalty account:', e);
    }
  };

  if (loading || !profile) {
    return (
      <main className="max-w-4xl mx-auto px-container-margin py-12 flex flex-col items-center justify-center min-h-[50vh]">
        <div className="w-10 h-10 border-4 border-secondary/30 border-t-secondary rounded-full animate-spin"></div>
        <p className="font-label-md text-on-surface-variant mt-4">Loading passenger profile...</p>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-container-margin pt-6 pb-24 flex flex-col gap-stack-lg">
      {/* Toast Notification */}
      {savedMessage && (
        <div className="fixed top-20 right-4 bg-tertiary text-on-tertiary px-4 py-2.5 rounded-lg shadow-xl z-50 flex items-center gap-2 animate-[fadeIn_0.3s_ease]">
          <span className="material-symbols-outlined text-[18px]">verified</span>
          <span className="font-label-md">{savedMessage}</span>
        </div>
      )}

      {/* Header Profile Section */}
      <section className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-center gap-6">
        <div className="relative">
          <div className="w-24 h-24 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-headline-lg shadow-inner">
            <span className="material-symbols-outlined text-[48px]">person</span>
          </div>
          <div className="absolute -bottom-1 -right-1 bg-secondary text-on-secondary w-7 h-7 rounded-full flex items-center justify-center shadow-md">
            <span className="material-symbols-outlined text-[16px]">verified_user</span>
          </div>
        </div>

        <div className="flex-1 text-center md:text-left space-y-1">
          <div className="flex items-center justify-center md:justify-start gap-2">
            <h1 className="font-headline-lg text-primary">{profile.full_name}</h1>
            <span className="bg-secondary-container text-on-secondary-container text-xs px-2.5 py-0.5 rounded-full font-label-sm font-semibold">
              Enterprise Verified
            </span>
          </div>
          <p className="font-body-md text-on-surface-variant">{profile.email} • {profile.phone}</p>
          <div className="flex flex-wrap gap-2 pt-2 justify-center md:justify-start">
            <span className="bg-surface-container-high px-3 py-1 rounded-md text-xs font-label-sm flex items-center gap-1 text-on-surface">
              <span className="material-symbols-outlined text-[14px]">flag</span>
              {profile.nationality} ({profile.passport_number})
            </span>
            <span className="bg-surface-container-high px-3 py-1 rounded-md text-xs font-label-sm flex items-center gap-1 text-on-surface">
              <span className="material-symbols-outlined text-[14px]">event_seat</span>
              Seat: {profile.seat_preference}
            </span>
            <span className="bg-surface-container-high px-3 py-1 rounded-md text-xs font-label-sm flex items-center gap-1 text-on-surface">
              <span className="material-symbols-outlined text-[14px]">restaurant</span>
              Meal: {profile.meal_preference}
            </span>
          </div>
        </div>
      </section>

      {/* Travel Preferences Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Personal & Travel Settings */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col gap-4">
          <h2 className="font-headline-md text-primary flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">tune</span>
            Recovery Travel Preferences
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-label-md text-on-surface-variant mb-1">Full Legal Name</label>
              <input
                type="text"
                className="tr-input w-full"
                value={profile.full_name}
                onChange={(e) => handleUpdateField('full_name', e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-label-md text-on-surface-variant mb-1">Passport Number</label>
                <input
                  type="text"
                  className="tr-input w-full"
                  value={profile.passport_number}
                  onChange={(e) => handleUpdateField('passport_number', e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-label-md text-on-surface-variant mb-1">Nationality</label>
                <input
                  type="text"
                  className="tr-input w-full"
                  value={profile.nationality}
                  onChange={(e) => handleUpdateField('nationality', e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-label-md text-on-surface-variant mb-1">Seat Preference</label>
                <select
                  className="tr-select w-full"
                  value={profile.seat_preference}
                  onChange={(e) => handleUpdateField('seat_preference', e.target.value)}
                >
                  <option value="AISLE">Aisle Seat</option>
                  <option value="WINDOW">Window Seat</option>
                  <option value="EXTRA_LEGROOM">Extra Legroom</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-label-md text-on-surface-variant mb-1">Meal Requirement</label>
                <select
                  className="tr-select w-full"
                  value={profile.meal_preference}
                  onChange={(e) => handleUpdateField('meal_preference', e.target.value)}
                >
                  <option value="STANDARD">Standard Meal</option>
                  <option value="HALAL">Halal</option>
                  <option value="VEGETARIAN">Vegetarian / Vegan</option>
                  <option value="KOSHER">Kosher</option>
                  <option value="GLUTEN_FREE">Gluten Free</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-label-md text-on-surface-variant mb-1">
                Max Layover Tolerance: {profile.max_layover_hours} Hours
              </label>
              <input
                type="range"
                min="1"
                max="12"
                className="w-full accent-secondary"
                value={profile.max_layover_hours}
                onChange={(e) => handleUpdateField('max_layover_hours', parseInt(e.target.value))}
              />
            </div>
          </div>
        </div>

        {/* Frequent Flyer Loyalty Hub */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-headline-md text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">card_membership</span>
              Frequent Flyer Programs
            </h2>
            <button
              onClick={() => setShowAddLoyalty(true)}
              className="bg-primary-container text-on-primary text-xs px-3 py-1.5 rounded-lg flex items-center gap-1 hover:bg-primary-container/90 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              Link Program
            </button>
          </div>

          <div className="space-y-3">
            {profile.loyalty_accounts.map((acc) => (
              <div
                key={acc.id}
                className="p-3.5 rounded-xl border border-outline-variant bg-surface-bright flex items-center justify-between hover:shadow-sm transition-all"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-label-md font-semibold text-on-surface">{acc.program_name}</span>
                    <span className="text-[10px] bg-secondary-fixed/30 text-secondary px-1.5 py-0.5 rounded font-mono">
                      {acc.alliance}
                    </span>
                  </div>
                  <div className="text-xs text-on-surface-variant mt-0.5 font-mono">
                    {acc.member_number} • <span className="text-secondary font-sans font-medium">{acc.tier_status}</span>
                  </div>
                  <div className="text-[11px] text-tertiary-container font-medium mt-1">
                    {acc.points_balance.toLocaleString()} Miles Available
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteLoyalty(acc.id)}
                  className="text-on-surface-variant hover:text-error p-1.5 rounded-lg transition-colors"
                  title="Remove program"
                >
                  <span className="material-symbols-outlined text-[18px]">delete</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Add Loyalty Modal */}
      {showAddLoyalty && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 animate-[scaleIn_0.2s_ease]">
            <div className="flex items-center justify-between">
              <h3 className="font-headline-md text-primary">Link Loyalty Program</h3>
              <button onClick={() => setShowAddLoyalty(false)} className="text-on-surface-variant hover:text-on-surface">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleAddLoyalty} className="space-y-3">
              <div>
                <label className="block text-xs font-label-md mb-1">Airline Program</label>
                <select
                  className="tr-select w-full"
                  value={newProgram}
                  onChange={(e) => {
                    setNewProgram(e.target.value);
                    if (e.target.value.includes('British') || e.target.value.includes('American') || e.target.value.includes('Qatar') || e.target.value.includes('Malaysia')) {
                      setNewAlliance('Oneworld');
                    } else if (e.target.value.includes('KrisFlyer') || e.target.value.includes('Lufthansa') || e.target.value.includes('United') || e.target.value.includes('ANA')) {
                      setNewAlliance('Star Alliance');
                    } else {
                      setNewAlliance('SkyTeam');
                    }
                  }}
                >
                  <option value="British Airways Executive Club">British Airways Executive Club</option>
                  <option value="Malaysia Airlines Enrich">Malaysia Airlines Enrich</option>
                  <option value="Singapore Airlines KrisFlyer">Singapore Airlines KrisFlyer</option>
                  <option value="American Airlines AAdvantage">American Airlines AAdvantage</option>
                  <option value="Qatar Airways Privilege Club">Qatar Airways Privilege Club</option>
                  <option value="Lufthansa Miles & More">Lufthansa Miles & More</option>
                  <option value="Delta SkyMiles">Delta SkyMiles</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-label-md mb-1">Alliance</label>
                  <input type="text" className="tr-input w-full bg-surface-variant/30" value={newAlliance} readOnly />
                </div>
                <div>
                  <label className="block text-xs font-label-md mb-1">Tier Status</label>
                  <input type="text" className="tr-input w-full" value={newTier} onChange={(e) => setNewTier(e.target.value)} />
                </div>
              </div>

              <div>
                <label className="block text-xs font-label-md mb-1">Member Number</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. BA-10948291"
                  className="tr-input w-full"
                  value={newMemberNum}
                  onChange={(e) => setNewMemberNum(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-label-md mb-1">Points / Miles Balance</label>
                <input
                  type="number"
                  className="tr-input w-full"
                  value={newPoints}
                  onChange={(e) => setNewPoints(parseInt(e.target.value) || 0)}
                />
              </div>

              <div className="flex gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddLoyalty(false)}
                  className="flex-1 border border-outline-variant py-2.5 rounded-lg text-sm hover:bg-surface-variant"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-primary-container text-on-primary py-2.5 rounded-lg text-sm font-semibold hover:bg-primary-container/90"
                >
                  Save Program
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
