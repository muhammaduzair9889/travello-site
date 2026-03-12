from django.contrib import admin
from django.utils.html import format_html
from .models import Hotel, RoomType, Booking, Payment


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'rating', 'get_total_rooms', 'get_available_rooms', 'wifi_available', 'parking_available', 'created_at')
    list_filter = ('wifi_available', 'parking_available', 'city', 'rating')
    search_fields = ('name', 'city', 'address', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'get_total_rooms', 'get_available_rooms')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'city', 'address', 'description')
        }),
        ('Media & Rating', {
            'fields': ('image', 'rating')
        }),
        ('Amenities', {
            'fields': ('wifi_available', 'parking_available')
        }),
        ('Statistics', {
            'fields': ('get_total_rooms', 'get_available_rooms', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_rooms(self, obj):
        return obj.total_rooms
    get_total_rooms.short_description = 'Total Rooms'
    
    def get_available_rooms(self, obj):
        return obj.available_rooms
    get_available_rooms.short_description = 'Available Rooms'


class RoomTypeInline(admin.TabularInline):
    model = RoomType
    extra = 1
    fields = ('type', 'price_per_night', 'total_rooms', 'max_occupancy', 'amenities')


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'type', 'price_per_night', 'total_rooms', 'get_available_rooms', 'max_occupancy')
    list_filter = ('type', 'hotel__city')
    search_fields = ('hotel__name', 'type', 'description')
    ordering = ('hotel', 'price_per_night')
    readonly_fields = ('created_at', 'updated_at', 'get_available_rooms')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('hotel', 'type', 'price_per_night')
        }),
        ('Capacity', {
            'fields': ('total_rooms', 'max_occupancy', 'get_available_rooms')
        }),
        ('Details', {
            'fields': ('description', 'amenities')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_available_rooms(self, obj):
        available = obj.available_rooms
        color = 'green' if available > 5 else 'orange' if available > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            available
        )
    get_available_rooms.short_description = 'Available'


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = (
        'stripe_payment_intent', 'stripe_session_id', 'amount', 'currency',
        'status', 'payment_method_type', 'last4', 'brand',
        'error_message', 'metadata', 'created_at', 'updated_at',
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_reference', 'get_user_info', 'hotel', 'room_type', 'rooms_booked',
        'check_in', 'check_out', 'get_nights', 'total_price',
        'payment_method', 'get_status', 'get_cancellation_date', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'refund_status', 'check_in', 'check_out', 'created_at')
    search_fields = (
        'booking_reference', 'user__email', 'user__username',
        'hotel__name', 'guest_name', 'guest_email', 'guest_phone'
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'get_nights', 'booking_reference',
        'invoice_number', 'base_price', 'tax_amount', 'service_charge',
        'cancelled_at', 'cancelled_by', 'get_user_detail', 'get_payment_summary',
    )
    date_hierarchy = 'check_in'
    inlines = [PaymentInline]

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_reference', 'invoice_number', 'user', 'hotel', 'room_type', 'rooms_booked')
        }),
        ('User Details', {
            'fields': ('get_user_detail',),
        }),
        ('Stay Dates', {
            'fields': ('check_in', 'check_out', 'get_nights')
        }),
        ('Guest Information', {
            'fields': ('guest_name', 'guest_email', 'guest_phone', 'special_requests'),
        }),
        ('Price Breakdown', {
            'fields': ('base_price', 'tax_amount', 'service_charge', 'total_price'),
        }),
        ('Payment & Status', {
            'fields': ('payment_method', 'status', 'get_payment_summary')
        }),
        ('Cancellation Details', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason', 'refund_amount', 'refund_status'),
            'description': 'Populated automatically when a booking is cancelled.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_completed']

    # ── column helpers ──────────────────────────────────────
    def get_nights(self, obj):
        return obj.number_of_nights
    get_nights.short_description = 'Nights'

    def get_user_info(self, obj):
        return format_html('{} &lt;{}&gt;', obj.user.username, obj.user.email)
    get_user_info.short_description = 'User'

    def get_status(self, obj):
        colors = {
            'PENDING': 'orange',
            'PAID': 'blue',
            'CONFIRMED': 'green',
            'CANCELLED': 'red',
            'COMPLETED': 'gray',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    get_status.short_description = 'Status'

    def get_cancellation_date(self, obj):
        if obj.cancelled_at:
            return format_html(
                '<span style="color: red;">{}</span>',
                obj.cancelled_at.strftime('%Y-%m-%d %H:%M')
            )
        return '-'
    get_cancellation_date.short_description = 'Cancelled At'

    # ── detail-page helpers ─────────────────────────────────
    def get_user_detail(self, obj):
        u = obj.user
        return format_html(
            '<strong>Username:</strong> {}<br>'
            '<strong>Email:</strong> {}<br>'
            '<strong>Name:</strong> {} {}',
            u.username, u.email,
            getattr(u, 'first_name', ''), getattr(u, 'last_name', ''),
        )
    get_user_detail.short_description = 'User Account Details'

    def get_payment_summary(self, obj):
        try:
            p = obj.payment
            return format_html(
                '<strong>Amount:</strong> {} {}<br>'
                '<strong>Status:</strong> {}<br>'
                '<strong>Method:</strong> {}<br>'
                '<strong>Card:</strong> {} ****{}<br>'
                '<strong>Stripe PI:</strong> {}',
                p.amount, p.currency,
                p.get_status_display(),
                p.payment_method_type or '-',
                p.brand or '-', p.last4 or '-',
                p.stripe_payment_intent or '-',
            )
        except Payment.DoesNotExist:
            return 'No payment record'
    get_payment_summary.short_description = 'Payment Summary'

    # ── bulk actions ────────────────────────────────────────
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='CONFIRMED')
    mark_as_confirmed.short_description = 'Mark as Confirmed'

    def mark_as_cancelled(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='CANCELLED', cancelled_at=timezone.now(), cancelled_by=request.user)
    mark_as_cancelled.short_description = 'Mark as Cancelled'

    def mark_as_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    mark_as_completed.short_description = 'Mark as Completed'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'booking', 'amount', 'currency', 'get_status', 
        'stripe_payment_intent', 'payment_method_type', 'created_at'
    )
    list_filter = ('status', 'currency', 'payment_method_type', 'created_at')
    search_fields = (
        'booking__id', 'booking__user__email', 
        'stripe_payment_intent', 'last4'
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'stripe_payment_intent', 
        'last4', 'brand', 'payment_method_type'
    )
    
    fieldsets = (
        ('Booking Reference', {
            'fields': ('booking',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'status')
        }),
        ('Stripe Information', {
            'fields': (
                'stripe_payment_intent', 'payment_method_type', 
                'last4', 'brand'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('error_message', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status(self, obj):
        colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'SUCCEEDED': 'green',
            'FAILED': 'red',
            'REFUNDED': 'purple',
            'CANCELLED': 'gray',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    get_status.short_description = 'Status'


# Optionally add inline to Hotel admin
HotelAdmin.inlines = [RoomTypeInline]