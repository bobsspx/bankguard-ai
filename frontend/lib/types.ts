export type Transaction = {
  id: string;
  transaction_ref: string;
  account_ref: string;
  device_ref: string | null;

  amount: string;
  currency: string;

  transaction_type: string;
  merchant_category: string | null;

  country_code: string;
  channel: string;

  ip_address: string | null;

  status: string;

  occurred_at: string;
  created_at: string;
};

export type TransactionPage = {
  total: number;
  limit: number;
  offset: number;
  items: Transaction[];
};

export type CurrentUser = {
  id: string;
  email: string;
  role: string;
  permissions: string[];
};

export type RuleReason = {
  code: string;
  points: number;
  description: string;
};


export type FraudSummary = {
  total_scored: number;

  low: number;
  medium: number;
  high: number;
  critical: number;

  open_alerts: number;
};


export type FraudScoreItem = {
  transaction_id: string;
  transaction_ref: string;

  account_ref: string;

  amount: string;
  currency: string;

  country_code: string;
  channel: string;

  occurred_at: string;

  rule_score: string;
  ml_score: string;
  final_score: string;

  risk_level:
    | "low"
    | "medium"
    | "high"
    | "critical";

  rule_reasons: RuleReason[];

  model_version: string;
  scored_at: string;
};


export type FraudScorePage = {
  total: number;
  limit: number;
  offset: number;

  items: FraudScoreItem[];
};


export type FraudAlert = {
  id: string;

  transaction_id:
    | string
    | null;

  transaction_ref:
    | string
    | null;

  alert_type: string;

  severity:
    | "low"
    | "medium"
    | "high"
    | "critical";

  status:
    | "open"
    | "investigating"
    | "resolved"
    | "dismissed";

  title: string;
  description: string;

  created_at: string;

  resolved_at:
    | string
    | null;
};


export type FraudAlertPage = {
  total: number;
  limit: number;
  offset: number;

  items: FraudAlert[];
};