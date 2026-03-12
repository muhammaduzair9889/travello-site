import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaHotel, FaBook, FaSignOutAlt, FaBars, FaChartLine, FaMoneyBillWave,
  FaPercentage, FaArrowUp, FaArrowDown, FaSyncAlt, FaTimesCircle,
  FaHandHoldingUsd, FaUsers
} from 'react-icons/fa';
import { bookingAPI, hotelAPI } from '../services/api';
import {
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';

/* ─── Color Palette ─── */
const STATUS_COLORS = { PAID: '#22c55e', CONFIRMED: '#3b82f6', COMPLETED: '#6366f1', PENDING: '#f59e0b', CANCELLED: '#ef4444' };
const STATUS_LABELS = { PAID: 'Paid', CONFIRMED: 'Confirmed', COMPLETED: 'Completed', PENDING: 'Pending', CANCELLED: 'Cancelled' };

/* ─── Chart Tooltip ─── */
const ChartTooltip = ({ active, payload, label, prefix = '' }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 dark:text-gray-200 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="flex justify-between gap-4">
          <span>{p.name}:</span>
          <span className="font-bold">{prefix}{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</span>
        </p>
      ))}
    </div>
  );
};

/* ─── Period Filter ─── */
const PERIODS = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '1y', label: '1 Year' },
  { value: 'all', label: 'All Time' },
];

/* ─── Format helpers ─── */
const fmtPKR = (v) => `PKR ${Number(v || 0).toLocaleString('en-PK', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
const fmtShort = (v) => {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v?.toString() || '0';
};
const fmtDate = (d) => {
  if (!d) return '';
  const date = new Date(d);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

/* ════════════════════════════════════════════════════
   ADMIN DASHBOARD
════════════════════════════════════════════════════ */
const AdminDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [period, setPeriod] = useState('30d');
  const [hotelFilter, setHotelFilter] = useState('');
  const [hotels, setHotels] = useState([]);
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // overview | manage

  /* ── Auth check ── */
  useEffect(() => {
    const isAdmin = localStorage.getItem('isAdmin') === 'true';
    if (!isAdmin) { navigate('/login'); return; }
    hotelAPI.getAllHotels().then(r => setHotels(r.data || [])).catch(() => {});
  }, [navigate]);

  /* ── Fetch analytics ── */
  const fetchAnalytics = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    else setRefreshing(true);
    try {
      const params = { period };
      if (hotelFilter) params.hotel = hotelFilter;
      const res = await bookingAPI.getAnalytics(params);
      setData(res.data);
    } catch (err) {
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [period, hotelFilter]);

  useEffect(() => { fetchAnalytics(); }, [fetchAnalytics]);

  const handleSignOut = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('admin_access_token');
    localStorage.removeItem('admin_refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('admin');
    localStorage.removeItem('isAdmin');
    navigate('/admin-login', { replace: true });
  };

  /* ── KPI data ── */
  const kpi = data?.kpi || {};

  /* ── Pie data ── */
  const statusPie = useMemo(() =>
    (data?.status_distribution || []).map(s => ({
      name: STATUS_LABELS[s.status] || s.status,
      value: s.count,
      revenue: s.revenue,
      color: STATUS_COLORS[s.status] || '#9ca3af',
    })), [data]);

  const paymentPie = useMemo(() =>
    (data?.payment_distribution || []).map(p => ({
      name: p.payment_method === 'ONLINE' ? 'Online Payment' : 'Pay on Arrival',
      value: p.count,
      revenue: p.revenue,
      color: p.payment_method === 'ONLINE' ? '#6366f1' : '#f59e0b',
    })), [data]);

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-gray-600 dark:text-gray-300 font-medium">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* ─── Header ─── */}
      <header className="sticky top-0 z-20 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FaBars className="text-gray-500 w-5 h-5 md:hidden cursor-pointer" />
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-800 dark:text-white">Admin Dashboard</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">Analytics & Management</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => fetchAnalytics(false)} disabled={refreshing}
              className="p-2 text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
              <FaSyncAlt className={`text-sm ${refreshing ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={handleSignOut}
              className="flex items-center gap-2 px-3 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-all shadow-sm">
              <FaSignOutAlt /><span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
        {/* ─── Tabs ─── */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <button onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${activeTab === 'overview' ? 'bg-indigo-600 text-white shadow-md' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            <FaChartLine className="inline mr-2" />Analytics Overview
          </button>
          <button onClick={() => setActiveTab('manage')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${activeTab === 'manage' ? 'bg-indigo-600 text-white shadow-md' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            <FaHotel className="inline mr-2" />Quick Actions
          </button>
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'overview' ? (
            <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>

              {/* ─── Filters ─── */}
              <div className="flex flex-wrap items-center gap-3 mb-6">
                <div className="flex bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-sm">
                  {PERIODS.map(p => (
                    <button key={p.value} onClick={() => setPeriod(p.value)}
                      className={`px-3 py-2 text-xs font-semibold transition-colors ${period === p.value ? 'bg-indigo-600 text-white' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                      {p.label}
                    </button>
                  ))}
                </div>
                <select value={hotelFilter} onChange={e => setHotelFilter(e.target.value)}
                  className="px-3 py-2 text-xs font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-700 dark:text-gray-200 shadow-sm focus:ring-2 focus:ring-indigo-500 outline-none">
                  <option value="">All Hotels</option>
                  {hotels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
                </select>
              </div>

              {/* ─── KPI Cards ─── */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
                <KPICard icon={FaMoneyBillWave} iconBg="bg-green-100 dark:bg-green-900/30" iconColor="text-green-600 dark:text-green-400"
                  label="Total Revenue" value={fmtPKR(kpi.total_revenue)} change={kpi.revenue_growth} delay={0} />
                <KPICard icon={FaBook} iconBg="bg-indigo-100 dark:bg-indigo-900/30" iconColor="text-indigo-600 dark:text-indigo-400"
                  label="Total Bookings" value={kpi.total_bookings} change={kpi.booking_growth} delay={0.05} />
                <KPICard icon={FaPercentage} iconBg="bg-amber-100 dark:bg-amber-900/30" iconColor="text-amber-600 dark:text-amber-400"
                  label="Conversion Rate" value={`${kpi.conversion_rate || 0}%`} delay={0.1} />
                <KPICard icon={FaHandHoldingUsd} iconBg="bg-purple-100 dark:bg-purple-900/30" iconColor="text-purple-600 dark:text-purple-400"
                  label="Avg. Booking Value" value={fmtPKR(kpi.avg_booking_value)} delay={0.15} />
              </div>

              {/* ─── Row 1: Revenue Trend + Booking Status Pie ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
                <ChartCard title="Revenue Trend" subtitle="Over time" className="lg:col-span-2">
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={data?.revenue_over_time || []} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                      <defs>
                        <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                      <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis tickFormatter={fmtShort} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip content={<ChartTooltip prefix="PKR " />} />
                      <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#revGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Booking Status" subtitle="Distribution">
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={statusPie} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}
                        style={{ fontSize: 10, fontWeight: 600 }}>
                        {statusPie.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                      </Pie>
                      <Tooltip formatter={(v, n, p) => [v, p.payload.name]} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* ─── Row 2: Daily Bookings Bar + Cumulative Revenue ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                <ChartCard title="Bookings Over Time" subtitle="Paid vs Cancelled">
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={data?.bookings_over_time || []} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                      <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip content={<ChartTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="paid" name="Paid" fill="#22c55e" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="cancelled" name="Cancelled" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Cumulative Revenue" subtitle="Growth over time">
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={data?.cumulative_revenue || []} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                      <defs>
                        <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                      <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis tickFormatter={fmtShort} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip content={<ChartTooltip prefix="PKR " />} />
                      <Area type="monotone" dataKey="cumulative" name="Cumulative" stroke="#22c55e" strokeWidth={2.5} fill="url(#cumGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* ─── Row 3: Payment Method Donut + Top Hotels + Room Types ─── */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                <ChartCard title="Payment Methods" subtitle="Online vs Arrival">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={paymentPie} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={5} dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}
                        style={{ fontSize: 10, fontWeight: 600 }}>
                        {paymentPie.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Top Hotels" subtitle="By revenue">
                  <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
                    {(data?.top_hotels || []).map((h, i) => (
                      <div key={h.hotel_id} className="flex items-center gap-3">
                        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0 ${i < 3 ? 'bg-indigo-500' : 'bg-gray-400'}`}>
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-gray-800 dark:text-white truncate">{h.name}</p>
                          <p className="text-[10px] text-gray-500">{h.bookings} bookings</p>
                        </div>
                        <span className="text-xs font-bold text-green-600 dark:text-green-400 whitespace-nowrap">{fmtPKR(h.revenue)}</span>
                      </div>
                    ))}
                    {(!data?.top_hotels?.length) && <p className="text-xs text-gray-400 text-center py-6">No data yet</p>}
                  </div>
                </ChartCard>

                <ChartCard title="Room Types" subtitle="Distribution">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={data?.room_type_distribution || []} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis dataKey="type" type="category" width={60} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar dataKey="count" name="Bookings" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* ─── Row 4: Recent Bookings Table ─── */}
              <ChartCard title="Recent Bookings" subtitle={`Latest ${data?.recent_bookings?.length || 0} entries`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-2 px-3 font-semibold text-gray-500 dark:text-gray-400">Hotel</th>
                        <th className="text-left py-2 px-3 font-semibold text-gray-500 dark:text-gray-400">Guest</th>
                        <th className="text-left py-2 px-3 font-semibold text-gray-500 dark:text-gray-400">Check-in</th>
                        <th className="text-left py-2 px-3 font-semibold text-gray-500 dark:text-gray-400">Amount</th>
                        <th className="text-left py-2 px-3 font-semibold text-gray-500 dark:text-gray-400">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data?.recent_bookings || []).map(b => (
                        <tr key={b.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                          <td className="py-2.5 px-3 font-medium text-gray-800 dark:text-white truncate max-w-[150px]">{b.hotel_name}</td>
                          <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300">{b.guest_name || '—'}</td>
                          <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300">{fmtDate(b.check_in)}</td>
                          <td className="py-2.5 px-3 font-semibold text-gray-800 dark:text-white">{fmtPKR(b.total_price)}</td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              b.status === 'PAID' || b.status === 'COMPLETED' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : b.status === 'CONFIRMED' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                              : b.status === 'CANCELLED' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            }`}>{STATUS_LABELS[b.status] || b.status}</span>
                          </td>
                        </tr>
                      ))}
                      {!data?.recent_bookings?.length && (
                        <tr><td colSpan={5} className="text-center py-8 text-gray-400">No bookings in this period</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </ChartCard>

            </motion.div>
          ) : (
            <motion.div key="manage" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              {/* ─── Quick Stats Row ─── */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
                <KPICard icon={FaHotel} iconBg="bg-sky-100 dark:bg-sky-900/30" iconColor="text-sky-600 dark:text-sky-400"
                  label="Total Hotels" value={kpi.total_hotels || hotels.length} delay={0} />
                <KPICard icon={FaBook} iconBg="bg-indigo-100 dark:bg-indigo-900/30" iconColor="text-indigo-600 dark:text-indigo-400"
                  label="Total Bookings" value={kpi.total_bookings} delay={0.05} />
                <KPICard icon={FaMoneyBillWave} iconBg="bg-green-100 dark:bg-green-900/30" iconColor="text-green-600 dark:text-green-400"
                  label="Total Revenue" value={fmtPKR(kpi.total_revenue)} delay={0.1} />
                <KPICard icon={FaTimesCircle} iconBg="bg-red-100 dark:bg-red-900/30" iconColor="text-red-600 dark:text-red-400"
                  label="Cancelled" value={kpi.cancelled_count || 0} delay={0.15} />
              </div>

              {/* ─── Quick Actions ─── */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => navigate('/admin/hotels')}
                  className="p-6 bg-gradient-to-br from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all">
                  <FaHotel className="text-3xl mb-3" />
                  <h3 className="text-lg font-bold mb-1">Manage Hotels</h3>
                  <p className="text-xs opacity-90">Add, edit, or remove hotels</p>
                </motion.button>

                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => navigate('/admin/bookings')}
                  className="p-6 bg-gradient-to-br from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all">
                  <FaBook className="text-3xl mb-3" />
                  <h3 className="text-lg font-bold mb-1">Manage Bookings</h3>
                  <p className="text-xs opacity-90">View, filter, and update all bookings</p>
                </motion.button>

                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
                    const baseUrl = apiUrl.replace(/\/api$/, '');
                    window.open(`${baseUrl}/admin/`, '_blank');
                  }}
                  className="p-6 bg-gradient-to-br from-gray-600 to-gray-800 hover:from-gray-700 hover:to-gray-900 text-white rounded-xl shadow-lg hover:shadow-xl transition-all">
                  <FaUsers className="text-3xl mb-3" />
                  <h3 className="text-lg font-bold mb-1">Django Admin</h3>
                  <p className="text-xs opacity-90">Users, payments, raw data</p>
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

/* ─── KPI Card Component ─── */
const KPICard = ({ icon: Icon, iconBg, iconColor, label, value, change, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 15 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 sm:p-5 hover:shadow-md transition-shadow"
  >
    <div className="flex items-start justify-between mb-3">
      <div className={`w-10 h-10 ${iconBg} rounded-xl flex items-center justify-center`}>
        <Icon className={`${iconColor} text-lg`} />
      </div>
      {change !== undefined && change !== null && (
        <span className={`flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${
          change >= 0 ? 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30' : 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
        }`}>
          {change >= 0 ? <FaArrowUp className="text-[8px]" /> : <FaArrowDown className="text-[8px]" />}
          {Math.abs(change)}%
        </span>
      )}
    </div>
    <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mb-0.5">{label}</p>
    <p className="text-xl sm:text-2xl font-bold text-gray-800 dark:text-white truncate">{value}</p>
  </motion.div>
);

/* ─── Chart Card Wrapper ─── */
const ChartCard = ({ title, subtitle, children, className = '' }) => (
  <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 sm:p-5 ${className}`}>
    <div className="mb-4">
      <h3 className="text-sm font-bold text-gray-800 dark:text-white">{title}</h3>
      {subtitle && <p className="text-[11px] text-gray-500 dark:text-gray-400">{subtitle}</p>}
    </div>
    {children}
  </div>
);

export default AdminDashboard;