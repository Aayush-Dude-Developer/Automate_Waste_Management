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

const GET_CACHE_TTL_MS = 30_000;
const getCache = new Map<string, { expiresAt: number; value: unknown }>();
const pendingGets = new Map<string, Promise<unknown>>();
let cacheVersion = 0;

export function invalidateApiCache() {
  cacheVersion += 1;
  getCache.clear();
  pendingGets.clear();
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const user = firebaseAuth?.currentUser;
  if (!user && !localDevelopment) throw new ApiError('Sign in is required.', 401);
  if (user) headers.set('Authorization', `Bearer ${await user.getIdToken()}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const method = (init.method ?? 'GET').toUpperCase();
  const cacheKey = method === 'GET' ? `${user?.uid ?? 'local'}:${path}` : '';
  if (cacheKey) {
    const cached = getCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) return cached.value as T;
    const pending = pendingGets.get(cacheKey);
    if (pending) return pending as Promise<T>;
  } else {
    invalidateApiCache();
  }

  const requestCacheVersion = cacheVersion;
  const request = (async () => {
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
  })();

  if (!cacheKey) return request;
  const cachedRequest = request.then((value) => {
    if (requestCacheVersion === cacheVersion) {
      getCache.set(cacheKey, { expiresAt: Date.now() + GET_CACHE_TTL_MS, value });
    }
    return value;
  }).finally(() => {
    if (pendingGets.get(cacheKey) === cachedRequest) pendingGets.delete(cacheKey);
  });
  pendingGets.set(cacheKey, cachedRequest);
  return cachedRequest;
}

export interface InventoryItem {
  id: string;
  ingredient_id?: string;
  item_name: string;
  category: string;
  storage_location: string;
  base_unit: string;
  unit_cost_inr: number;
  unit_cost?: number;
  input_unit?: string;
  output_unit?: string;
  yield_percentage?: number;
  yield_type?: 'negative' | 'positive' | 'no change';
  yield_stage?: string | null;
  yield_stages?: Array<{
    stage_name: string;
    input_stage: string;
    output_stage: string;
    input_unit: string;
    output_unit: string;
    yield_percentage: number;
  }>;
  lead_time_days?: number;
  minimum_order_quantity?: number | null;
  pack_size?: number | null;
  lot_tracking_enabled?: boolean;
  untracked_stock_quantity?: number;
  supplier_id?: string | null;
  reorder_threshold: number;
  safety_stock: number;
  current_quantity_in_store: number;
  current_quantity_in_use: number;
  total_current_quantity: number;
  status: string;
}

export interface PurchaseLine {
  purchase_line_id: string;
  purchase_id: string;
  ingredient_id: string;
  quantity_purchased: number;
  purchase_unit: string;
  unit_price: number;
  quantity_received: number;
  expiry_date?: string | null;
  batch_number?: string | null;
  usable_quantity?: number | null;
  usable_unit?: string | null;
}

export interface PurchaseInvoice {
  purchase_id: string;
  supplier_id: string;
  invoice_number: string;
  invoice_date: string;
  received_date?: string | null;
  total_amount: number;
  bill_document_url?: string | null;
  verification_status: 'pending' | 'verified' | 'rejected';
  line_items: PurchaseLine[];
}

export interface RecipeIngredient {
  ingredient_id: string;
  required_quantity: number;
  required_unit: string;
  required_stage: string;
  yield_stage_reference?: string | null;
  servings_per_batch: number;
}

export interface Recipe {
  recipe_id: string;
  recipe_name: string;
  recipe_version: string;
  serving_size: number;
  serving_unit: string;
  menu_category: string;
  selling_price: number;
  is_active: boolean;
  ingredients: RecipeIngredient[];
}

export interface DailySale {
  sale_record_id: string;
  sale_date: string;
  recipe_id: string;
  quantity_sold: number;
  quantity_cancelled: number;
  net_quantity_sold: number;
  quantity_prepared?: number | null;
  net_sales_amount: number;
  sales_source: string;
  source_reference?: string | null;
}

export interface MonthlyStockBalance {
  ingredient_id: string;
  month: string;
  opening_stock: number;
  total_purchased_stock: number;
  total_recipe_consumption: number;
  total_staff_consumption: number;
  total_wasted_stock: number;
  other_stock_inflows: number;
  other_stock_outflows: number;
  calculated_closing_stock: number;
  actual_closing_stock: number | null;
  stock_variance: number | null;
  physical_count_verified: boolean;
  provisional: boolean;
}

export interface TheoreticalConsumption {
  ingredient_id: string;
  item_name: string;
  month: string;
  unit: string;
  theoretical_raw_consumption: number;
}

export interface StaffConsumption {
  consumption_id: string;
  consumption_date: string;
  ingredient_id?: string | null;
  quantity?: number | null;
  unit?: string | null;
  recipe_id?: string | null;
  portions?: number | null;
  staff_count?: number | null;
  recorded_by: string;
  source_reference?: string | null;
}

export interface WasteRecordV2 {
  waste_record_id: string;
  waste_date: string;
  ingredient_id: string;
  quantity: number;
  unit: string;
  waste_reason: string;
  stage: string;
  estimated_cost?: number | null;
  recorded_by: string;
  recipe_id?: string | null;
  waste_type: 'raw_ingredient' | 'prepared_food';
}

export interface RestaurantProfile {
  id: string;
  name: string;
  outlet_name: string;
  location: string;
  address: string;
  timezone: string;
  currency: string;
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
  waste_trend: Array<{ day: string; waste: number }>;
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

export type PurchaseRecommendationStatus = 'needs_review' | 'approved' | 'ordered' | 'received' | 'no_action';

export interface PurchaseRecommendation {
  recommendation_id: string;
  ingredient_id: string;
  ingredient_name: string;
  forecast_start_date: string;
  forecast_period_days: number;
  current_usable_stock: number;
  stock_unit: string;
  stock_source: string;
  forecast_daily_consumption: number;
  reorder_threshold: number;
  safety_stock: number;
  supplier_id: string | null;
  supplier_lead_time_days: number | null;
  projected_stockout_date: string | null;
  recommended_order_date: string | null;
  recommended_purchase_quantity: number;
  estimated_purchase_cost: number | null;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: PurchaseRecommendationStatus;
  explanation: string;
  reliability_warnings: string[];
  demand_forecast: Record<string, number>;
  sales_basis: Array<{
    recipe_id: string;
    recipe_name: string;
    forecast_portions: number;
    raw_quantity_per_portion: number;
    trend_factor: number;
    unit: string;
    yield_stages_applied: string[];
  }>;
  incoming_orders: Array<{
    recommendation_id: string;
    quantity: number;
    expected_delivery_date: string;
    order_reference: string;
  }>;
  expiry_batches: Array<{
    purchase_id: string;
    batch_number: string | null;
    expiry_date: string;
    quantity_received: number;
    remaining_usable_quantity: number;
    expired: boolean;
    unit: string;
  }>;
  expected_delivery_date: string | null;
  order_reference: string | null;
  purchase_line_id: string | null;
}

export interface PurchaseRecommendationDashboard {
  forecast_period_days: number;
  forecast_start_date: string;
  generated_at: string;
  ingredients_requiring_replenishment: number;
  upcoming_stockout_risks: number;
  recommendations_awaiting_approval: number;
  data_warnings: string[];
  recommendations: PurchaseRecommendation[];
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
