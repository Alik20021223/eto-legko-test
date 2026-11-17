export interface CampaignOffer {
  offer_id: number;
  name: string;
  share: number;
  pinned: boolean;
  removed: boolean;
  // Добавлен в черновик, но ещё не отправлен в Keitaro.
  new: boolean;
}

export interface CampaignStream {
  id: number;
  name: string;
  position: number;
  kind: string;
  editable: boolean;
}

export interface Campaign {
  id: number;
  keitaro_id: number;
  name: string;
  alias: string;
  geo: string;
  dirty: boolean;
  streams: CampaignStream[];
  offers: CampaignOffer[];
}

export interface KeitaroOffer {
  id: number;
  name: string;
}

export interface Geo {
  code: string;
  name: string;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Ошибка ${response.status}`);
  }
  return response.json();
}

export const api = {
  keitaroOffers: () => request<KeitaroOffer[]>("GET", "/offers"),
  geos: () => request<Geo[]>("GET", "/geos"),
  campaigns: () => request<Campaign[]>("GET", "/campaigns"),
  create: (name: string, geo: string, offerIds: number[]) =>
    request<Campaign>("POST", "/campaigns", { name, geo, offer_ids: offerIds }),
  fetch: (id: number) => request<Campaign>("POST", `/campaigns/${id}/fetch`),
  push: (id: number) => request<Campaign>("POST", `/campaigns/${id}/push`),
  cancel: (id: number) => request<Campaign>("POST", `/campaigns/${id}/cancel`),
  recalculate: (id: number) => request<Campaign>("POST", `/campaigns/${id}/weights/recalculate`),
  addOffer: (id: number, offerId: number) =>
    request<Campaign>("POST", `/campaigns/${id}/offers`, { offer_id: offerId }),
  removeOffer: (id: number, offerId: number) =>
    request<Campaign>("DELETE", `/campaigns/${id}/offers/${offerId}`),
  restoreOffer: (id: number, offerId: number) =>
    request<Campaign>("POST", `/campaigns/${id}/offers/${offerId}/restore`),
  pin: (id: number, offerId: number, share?: number) =>
    request<Campaign>("PUT", `/campaigns/${id}/offers/${offerId}/pin`, { share }),
  unpin: (id: number, offerId: number) =>
    request<Campaign>("DELETE", `/campaigns/${id}/offers/${offerId}/pin`),
};
