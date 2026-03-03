import type { GuideRequest, GuideResponse, ProductInfo } from '../types';

const API_BASE = '/api';

export async function generateGuide(request: GuideRequest): Promise<{ guide_id: string }> {
  const res = await fetch(`${API_BASE}/guides/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`Failed to generate: ${res.statusText}`);
  return res.json();
}

export async function getGuide(guideId: string): Promise<GuideResponse> {
  const res = await fetch(`${API_BASE}/guides/${guideId}`);
  if (!res.ok) throw new Error(`Failed to fetch guide: ${res.statusText}`);
  return res.json();
}

export async function listProducts(): Promise<{ products: ProductInfo[] }> {
  const res = await fetch(`${API_BASE}/products/`);
  if (!res.ok) throw new Error(`Failed to fetch products: ${res.statusText}`);
  return res.json();
}
