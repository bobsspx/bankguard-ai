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