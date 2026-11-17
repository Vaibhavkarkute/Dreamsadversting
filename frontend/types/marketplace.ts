export type MediaFormatCode = 'FL' | 'NL' | 'BL' | 'LED';

export type VerificationStatus =
  | 'Pending Verification'
  | 'Under Review'
  | 'Approved'
  | 'Rejected'
  | 'Suspended';

export type BookingStatus =
  | 'Draft'
  | 'Enquiry Submitted'
  | 'Quotation Pending'
  | 'Quotation Sent'
  | 'Awaiting Approval'
  | 'Payment Pending'
  | 'Confirmed'
  | 'In Execution'
  | 'Completed'
  | 'Cancelled'
  | 'Refund Pending'
  | 'Refunded';

export interface MediaAsset {
  id: string;
  sr_no: string;
  city: string;
  area: string;
  media_category: string;
  title: string;
  format_code: MediaFormatCode;
  format_label: string;
  is_digital: boolean;
  width_ft: number;
  height_ft: number;
  qty: number;
  area_sqft: number;
  display_cost_pm: number;
  installation_cost: number;
  printing_cost: number;
  availability: string;
  is_immediate: boolean;
  remark: string;
  lat: number;
  lng: number;
  vendor_name: string;
  vendor_verified: boolean;
  status: VerificationStatus;
  min_booking_days: number;
  is_demo_data: boolean;
}
