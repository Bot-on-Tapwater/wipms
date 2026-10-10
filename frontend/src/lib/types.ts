// Shapes of the data returned by the backend API (see /docs on the backend).
// Money values arrive as strings (e.g. "1500.00") so no precision is lost.

export interface User {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone_number: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserBrief {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse extends TokenPair {
  user: User;
  permissions: string[];
}

export interface MyPermissions {
  role: string;
  permissions: string[];
}

export interface Choice {
  value: string;
  label: string;
}

export interface Choices {
  labourer_titles: Choice[];
  task_categories: Choice[];
  roles: Choice[];
}

export interface Message {
  message: string;
}

export interface Project {
  id: string;
  name: string;
  location: string;
  description: string;
  wallet_balance: string;
  is_completed: boolean;
  created_by: UserBrief | null;
  contractor_supervisors: UserBrief[];
  consultant_supervisors: UserBrief[];
  subcontractors: UserBrief[];
  created_at: string;
  updated_at: string;
}

export interface WalletTransaction {
  id: string;
  transaction_type: string;
  amount: string;
  balance_after: string;
  reference: string;
  created_at: string;
}

export type PaymentStatus = "pending" | "approved" | "paid";

export interface Work {
  id: string;
  project_id: string;
  title: string;
  description: string;
  category: string;
  cost_labor: string;
  cost_overhead: string;
  total_cost: string;
  retention_money: string;
  assigned_subcontractor: UserBrief | null;
  created_by: UserBrief | null;
  contractor_supervisor_comments: string;
  consultant_supervisor_comments: string;
  consultant_approval: boolean;
  contractor_supervisor_approval: boolean;
  attendance_approval: boolean;
  cost_approval: boolean;
  contractor_supervisor_payment_approval: boolean;
  main_contractor_payment_approval: boolean;
  is_fully_approved: boolean;
  payment_requested: boolean;
  payment_status: PaymentStatus;
  payment_requested_at: string | null;
  payment_approved_at: string | null;
  payment_completed_at: string | null;
  total_labourers_paid_out: string;
  retention_payment_requested: boolean;
  retention_payment_approved: boolean;
  retention_paid: boolean;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Labourer {
  id: string;
  name: string;
  title: string;
  national_id_number: string;
  phone_number: string;
  daily_rate: string;
  overhead_cost: string;
  project_lifetime_approved_working_days: number;
  created_at: string;
  updated_at: string;
}

export interface LabourerSuggestion {
  id: string;
  name: string;
  national_id_number: string;
  title: string;
  phone_number: string;
  daily_rate: string;
  overhead_cost: string;
}

export interface WorkLabourer {
  labourer: Labourer;
  days_worked: number;
  amount_due: string;
}

export interface WorkImage {
  id: string;
  work_id: string;
  description: string;
  created_at: string;
  file_url: string;
}

export interface PaymentSummary {
  work_id: string;
  total_cost: string;
  cost_labor: string;
  cost_overhead: string;
  total_labour_due: string;
  retention_money: string;
  subcontractor_amount: string;
  total_labourers_paid_out: string;
  usable_wallet_balance: string;
  payment_status: PaymentStatus;
  failed_payments_outstanding: number;
}

export interface PaymentOutcome {
  message: string;
  payments_made: number;
  payments_failed: number;
  work: Work;
}

export interface PaymentRecord {
  id: string;
  project_id: string;
  work_id: string;
  labourer_id: string | null;
  recipient_user_id: string | null;
  initiated_by_id: string | null;
  payment_type: string;
  recipient_name: string;
  recipient_phone: string;
  amount_requested: string;
  amount_paid: string;
  successful: boolean;
  provider: string;
  provider_reference: string;
  failure_reason: string;
  is_retried: boolean;
  paid_at: string | null;
  created_at: string;
}

export interface ReportItem {
  label: string;
  value: string;
}

export interface Report {
  report_type: string;
  title: string;
  generated_at: string;
  generated_by: string;
  filters: ReportItem[];
  columns: string[];
  rows: string[][];
  summary: ReportItem[];
}
