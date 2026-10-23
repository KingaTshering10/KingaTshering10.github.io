export interface Allocation {
  id: string;
  harvest_listing_id: string;
  allocated_quantity: string;
  agreed_unit_price: string;
  farmer_response: "pending" | "accepted" | "declined";
}

export interface Proposal {
  id: string;
  buyer_order_item_id: string;
  buyer_order_id: string | null;
  product_name: string | null;
  proposed_quantity: string;
  unit: string;
  estimated_transport_cost: string | null;
  estimated_delivery_time_hours: string | null;
  estimated_spoilage_risk: string | null;
  matching_method: string;
  score: number;
  score_factors: Record<string, number>;
  score_explanation: string[];
  status: string;
  allocations: Allocation[];
}

export interface Stop {
  id: string;
  stop_type: "pickup" | "delivery";
  sequence_number: number;
  location_name: string | null;
  farmer_display_name: string | null;
  planned_quantity: string | null;
  collected_quantity: string | null;
  status: string;
}

export interface Shipment {
  id: string;
  match_proposal_id: string;
  vehicle: { id: string; registration_number: string; capacity_kg: string } | null;
  driver_name: string | null;
  driver_phone: string | null;
  planned_pickup_at: string | null;
  planned_delivery_at: string | null;
  planned_distance_km: string | null;
  route_estimate_method: string | null;
  route_estimate_is_approximate: boolean;
  estimated_transport_cost: string | null;
  status: string;
  incident_notes: string | null;
  stops: Stop[];
}

export interface Payment {
  id: string;
  payer_type: string;
  recipient_type: string;
  related_order_id: string | null;
  amount: string;
  amount_paid: string;
  currency: string;
  due_date: string | null;
  status: string;
  payment_method: string | null;
  payment_reference: string | null;
}

export interface CollectionReceipt {
  id: string;
  receipt_number: string;
  farmer_display_name: string | null;
  product_name: string | null;
  unit: string;
  expected_quantity: string;
  presented_quantity: string;
  accepted_quantity: string;
  rejected_quantity: string;
  unit_price: string;
  gross_amount: string;
  transport_deduction: string;
  platform_fee: string;
  other_deduction: string;
  net_amount_due: string;
  rejection_reason: string | null;
  farmer_confirmation: boolean;
  coordinator_confirmation: boolean;
  created_at: string;
}

export interface Order {
  id: string;
  order_status: string;
  required_delivery_date: string;
  payment_terms: string | null;
  items?: OrderItem[];
}

export interface OrderItem {
  id: string;
  product_id: string;
  required_quantity: string;
  unit: string;
  offered_unit_price: string;
  maximum_unit_price: string | null;
  accepted_quantity: string | null;
}

export interface Dispute {
  id: string;
  category: string;
  description: string;
  status: string;
  resolution: string | null;
  created_at: string;
}
