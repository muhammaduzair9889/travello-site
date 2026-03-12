import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaArrowLeft, FaHotel, FaCalendarAlt, FaCreditCard, FaUser, FaCheckCircle, FaClock, FaTimes } from 'react-icons/fa';
import { bookingAPI } from '../services/api';

const statusConfig = {
  PENDING:   { icon: FaClock,       bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-400', label: 'Pending' },
  PAID:      { icon: FaCheckCircle, bg: 'bg-green-100 dark:bg-green-900/30',  text: 'text-green-700 dark:text-green-400',   label: 'Paid' },
  CONFIRMED: { icon: FaCheckCircle, bg: 'bg-blue-100 dark:bg-blue-900/30',   text: 'text-blue-700 dark:text-blue-400',    label: 'Confirmed' },
  COMPLETED: { icon: FaCheckCircle, bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-400', label: 'Completed' },
  CANCELLED: { icon: FaTimes,       bg: 'bg-red-100 dark:bg-red-900/30',     text: 'text-red-700 dark:text-red-400',      label: 'Cancelled' },
};

export default function BookingDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await bookingAPI.getBooking(id);
        setBooking(res.data);
      } catch (err) {
        setError(err?.response?.data?.error || err?.message || 'Failed to load booking details');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-sky-600" />
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col items-center justify-center gap-4">
        <p className="text-red-600 dark:text-red-400 text-lg">{error || 'Booking not found'}</p>
        <button onClick={() => navigate('/my-bookings')} className="px-4 py-2 bg-sky-600 text-white rounded-lg">Back to Bookings</button>
      </div>
    );
  }

  const sc = statusConfig[booking.status] || statusConfig.PENDING;
  const StatusIcon = sc.icon;
  const nights = booking.number_of_nights || Math.max(1, Math.ceil((new Date(booking.check_out) - new Date(booking.check_in)) / 86400000));
  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <button onClick={() => navigate('/my-bookings')} className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
          <FaArrowLeft /> Back to My Bookings
        </button>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-r from-sky-400 to-blue-500 rounded-lg flex items-center justify-center text-white text-2xl font-bold shadow-md">
                {booking.hotel_details?.name?.charAt(0)?.toUpperCase() || 'H'}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-800 dark:text-white">{booking.hotel_details?.name}</h1>
                <p className="text-gray-500 dark:text-gray-400">{booking.hotel_details?.city}</p>
                {booking.booking_reference && <p className="text-xs text-gray-400 mt-1">Ref: {booking.booking_reference}</p>}
              </div>
            </div>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${sc.bg} ${sc.text} font-semibold`}>
              <StatusIcon /> {sc.label}
            </div>
          </div>

          {/* Details grid */}
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Booking ID */}
            <InfoCard icon={FaHotel} label="Booking ID" value={`#${booking.id}`} sub={booking.invoice_number ? `Invoice: ${booking.invoice_number}` : null} />

            {/* Room */}
            <InfoCard icon={FaHotel} label="Room Type" value={booking.room_type_details?.type || 'N/A'} sub={`${booking.rooms_booked || 1} room(s)`} />

            {/* Check-in */}
            <InfoCard icon={FaCalendarAlt} label="Check-in" value={fmtDate(booking.check_in)} />

            {/* Check-out */}
            <InfoCard icon={FaCalendarAlt} label="Check-out" value={fmtDate(booking.check_out)} sub={`${nights} night(s)`} />

            {/* Payment */}
            <InfoCard icon={FaCreditCard} label="Payment Method" value={booking.payment_method === 'ONLINE' ? 'Online Payment' : 'Pay on Arrival'} />

            {/* Payment Status */}
            <InfoCard icon={FaCreditCard} label="Payment Status" value={booking.payment?.status || (booking.status === 'PAID' ? 'Paid' : 'Awaiting Payment')} sub={booking.payment ? `${booking.payment.amount} ${booking.payment.currency}` : null} />

            {/* Guest */}
            {booking.guest_name && <InfoCard icon={FaUser} label="Guest" value={booking.guest_name} sub={booking.guest_email} />}

            {/* Status */}
            <InfoCard icon={FaCheckCircle} label="Booking Status" value={booking.status} sub={`Created ${fmtDate(booking.created_at)}`} />
          </div>

          {/* Price breakdown */}
          <div className="px-6 pb-6">
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300 uppercase mb-3">Price Breakdown</h3>
              <div className="space-y-1 text-sm">
                {booking.base_price && <Row label="Base Price" value={`PKR ${parseFloat(booking.base_price).toLocaleString()}`} />}
                {booking.tax_amount && <Row label="Tax (16% GST)" value={`PKR ${parseFloat(booking.tax_amount).toLocaleString()}`} />}
                {booking.service_charge && <Row label="Service Charge (5%)" value={`PKR ${parseFloat(booking.service_charge).toLocaleString()}`} />}
                <div className="border-t border-gray-300 dark:border-gray-600 pt-2 mt-2 flex justify-between text-lg font-bold text-sky-600 dark:text-sky-400">
                  <span>Total</span>
                  <span>PKR {parseFloat(booking.total_price).toLocaleString('en-PK', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Cancellation info */}
          {booking.status === 'CANCELLED' && (
            <div className="px-6 pb-6">
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
                <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 uppercase mb-2">Cancellation Details</h3>
                {booking.cancelled_at && <p className="text-sm text-gray-700 dark:text-gray-300">Cancelled: {fmtDate(booking.cancelled_at)}</p>}
                {booking.cancellation_reason && <p className="text-sm text-gray-700 dark:text-gray-300">Reason: {booking.cancellation_reason}</p>}
                {booking.refund_status && booking.refund_status !== 'NONE' && (
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                    Refund: <span className={booking.refund_status === 'PROCESSED' ? 'text-green-600 font-semibold' : 'text-yellow-600 font-semibold'}>{booking.refund_status}</span>
                    {booking.refund_amount && ` — PKR ${parseFloat(booking.refund_amount).toLocaleString()}`}
                  </p>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

function InfoCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1 flex items-center gap-2">
        <Icon className="text-sky-600" /> {label}
      </p>
      <p className="text-lg font-bold text-gray-800 dark:text-white capitalize">{value}</p>
      {sub && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between text-gray-600 dark:text-gray-300">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
