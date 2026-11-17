import { FormEvent, useEffect, useState } from "react";

import { api, Campaign, KeitaroOffer } from "./api";
import CampaignCard from "./CampaignCard";
import Select, { SelectOption } from "./Select";

export default function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [offers, setOffers] = useState<KeitaroOffer[]>([]);
  const [geos, setGeos] = useState<SelectOption[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);

  const [name, setName] = useState("");
  const [geo, setGeo] = useState("");
  const [offerId, setOfferId] = useState("");

  // Любое действие: блокируем кнопки, показываем ошибку сервера как есть.
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    // Три независимые загрузки: сбой одной не оставляет пустыми остальные списки.
    run(async () => {
      const [campaignList, countries, offerList] = await Promise.allSettled([
        api.campaigns(),
        api.geos(),
        api.keitaroOffers(),
      ]);
      if (campaignList.status === "fulfilled") setCampaigns(campaignList.value);
      // id пункта — код страны, он же уходит в Keitaro в фильтр country.
      if (countries.status === "fulfilled") {
        setGeos(countries.value.map((geo) => ({ id: geo.code, name: `${geo.code} — ${geo.name}` })));
      }
      if (offerList.status === "fulfilled") setOffers(offerList.value);

      const failed = [campaignList, countries, offerList].find((r) => r.status === "rejected");
      if (failed?.status === "rejected") throw failed.reason;
    });
  }, []);

  function replace(updated: Campaign) {
    setCampaigns((list) => list.map((c) => (c.id === updated.id ? updated : c)));
  }

  const canCreate = Boolean(name.trim() && geo && offerId);

  function create(event: FormEvent) {
    event.preventDefault();
    if (busy || !canCreate) return;
    setCreating(true);
    run(async () => {
      const created = await api.create(name.trim(), geo, [Number(offerId)]);
      setCampaigns((list) => [created, ...list]);
      setName("");
    }).finally(() => setCreating(false));
  }

  return (
    <main>
      <h1>Кампании Keitaro</h1>
      {error && <p className="error">{error}</p>}

      <form className="panel row" onSubmit={create}>
        <input
          placeholder="Название"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={creating}
        />
        <Select
          options={geos}
          value={geo}
          placeholder="Гео…"
          searchPlaceholder="Поиск по стране или коду…"
          onChange={setGeo}
        />
        <Select
          options={offers}
          value={offerId}
          placeholder="Оффер…"
          searchPlaceholder="Поиск по названию или ID…"
          onChange={setOfferId}
        />
        <button disabled={busy || !canCreate} aria-busy={creating}>
          {creating && <span className="spinner" aria-hidden />}
          {creating ? "Создаём…" : "Создать кампанию"}
        </button>
      </form>

      {campaigns.map((campaign) => (
        <CampaignCard
          key={campaign.id}
          campaign={campaign}
          keitaroOffers={offers}
          busy={busy}
          onAction={(action) => run(async () => replace(await action()))}
        />
      ))}
      {campaigns.length === 0 && !busy && <p className="muted">Кампаний пока нет.</p>}
    </main>
  );
}
