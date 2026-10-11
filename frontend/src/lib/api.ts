const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
import { firebaseAuth, localDevelopment } from './firebase';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const user = firebaseAuth?.currentUser;
  if (!user && !localDevelopment) throw new ApiError('Sign in is required.', 401);
  if (user) headers.set('Authorization', `Bearer ${await user.getIdToken()}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: unknown; message?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
      else if (typeof body.message === 'string') detail = body.message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface InventoryItem {
  id: string;
  item_name: string;
  category: string;
  storage_location: string;
  base_unit: string;
  unit_cost_inr: number;
  reorder_threshold: number;
  safety_stock: number;
  current_quantity_in_store: number;
  current_quantity_in_use: number;
  total_current_quantity: number;
  status: string;
}

export interface WasteRecord {
  id: string;
  date: string;
  item_name: string;
  inventory_item_id?: string | null;
  quantity: number;
  unit: string;
  reason: string;
  checked_by: string;
  financial_loss_inr: number;
}

export interface DashboardMetrics {
  inventory_risk_items: number;
  pending_interventions: number;
  total_waste_week_kg: number;
  waste_trend_percentage: number;
  financial_loss_week_inr: number;
  donation_handovers: number;
}

export interface ReorderRecommendation {
  item_name: string;
  current_stock: number;
  expected_lead_time_demand: number;
  target_stock_level: number;
  recommended_purchase_quantity: number;
  recommended_packs: number;
  reasoning: string;
  data_quality_status: string;
  unit?: string;
  pack_size?: number;
  item_id?: string;
}

export interface BuffetRecommendation {
  dish_name: string;
  expected_covers: number;
  base_requirement: number;
  target_production: number;
  recommended_batches: number;
  actual_planned_production: number;
  predicted_surplus_portions: number;
  unit: string;
  reasoning: string;
  confidence: string;
}

export interface DonationMatch {
  centre: {
    id: string;
    name: string;
    contact_person: string;
    phone: string;
    address: string;
    pickup_service_available: boolean;
    verified: boolean;
  };
  match_score: number;
  distance_km: number;
  eligibility_notes: string[];
  is_eligible: boolean;
}

export interface Intervention {
  intervention_id: string;
  action_type: string;
  title: string;
  details: string;
  expected_impact_inr: number;
  feasibility_rating: string;
}

export interface Investigation {
  id: string;
  target_item_name: string;
  investigation_summary: string;
  verified_facts: string[];
  hypotheses: string[];
  data_gaps: string[];
  financial_risk_inr: number;
  recommended_interventions: Intervention[];
}
