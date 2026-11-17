import { useEffect, useState } from "react";

import PinModal from "./PinModal";
import Select from "./Select";
import { api, Campaign, CampaignOffer, CampaignStream, KeitaroOffer } from "./api";

interface Props {
  campaign: Campaign;
  keitaroOffers: KeitaroOffer[];
  busy: boolean;
  onAction: (action: () => Promise<Campaign>) => void;
}

const KIND_LABELS: Record<string, string> = {
  redirect: "редирект",
  landings: "офферы",
  action: "действие",
};

export default function CampaignCard({ campaign, keitaroOffers, busy, onAction }: Props) {
  const [newOfferId, setNewOfferId] = useState("");
  const [menuOfferId, setMenuOfferId] = useState<number | null>(null);
  const [pinTarget, setPinTarget] = useState<CampaignOffer | null>(null);
  const { id } = campaign;

  // Мобильное меню «⋯» закрывается кликом в любом месте страницы.
  useEffect(() => {
    if (menuOfferId === null) return;
    const close = () => setMenuOfferId(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [menuOfferId]);

  const used = new Set(campaign.offers.map((offer) => offer.offer_id));
  const available = keitaroOffers.filter((offer) => !used.has(offer.id));
  const active = campaign.offers.filter((offer) => !offer.removed);
  const total = active.reduce((sum, offer) => sum + offer.share, 0);

  // У кампаний, созданных до появления списка потоков, он пуст до первого Fetch.
  const streams: CampaignStream[] = campaign.streams.length
    ? campaign.streams
    : [{ id: 0, name: "offers", position: 2, kind: "landings", editable: true }];

  function renderOffers() {
    return (
      <>
        {total !== 100 && (
          <p className="warning" role="alert">
            Сумма весов {total}%, должно быть 100%
          </p>
        )}

        <table>
          <thead>
            <tr>
              <th>Оффер</th>
              <th className="col-share">Вес</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {campaign.offers.map((offer) => (
              <tr key={offer.offer_id} className={offer.removed ? "removed" : undefined}>
                <td className="col-name">
                  <span className="offer-name">{offer.name}</span>
                  {offer.new && <span className="tag new">new</span>}
                  {offer.removed && <span className="tag">removed</span>}
                </td>
                <td className="col-share">
                  {offer.share}%{offer.pinned && " 📌"}
                </td>
                <td className="col-actions">
                  <button
                    className="menu-toggle"
                    aria-label="Действия"
                    aria-expanded={menuOfferId === offer.offer_id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOfferId(menuOfferId === offer.offer_id ? null : offer.offer_id);
                    }}
                  >
                    ⋯
                  </button>
                  <div className={menuOfferId === offer.offer_id ? "actions open" : "actions"}>
                    {offer.removed ? (
                      <button
                        disabled={busy}
                        onClick={() => onAction(() => api.restoreOffer(id, offer.offer_id))}
                      >
                        Вернуть
                      </button>
                    ) : (
                      <>
                        {offer.pinned ? (
                          <button
                            disabled={busy}
                            onClick={() => onAction(() => api.unpin(id, offer.offer_id))}
                          >
                            Открепить
                          </button>
                        ) : (
                          <button disabled={busy} onClick={() => setPinTarget(offer)}>
                            Закрепить
                          </button>
                        )}
                        <button
                          disabled={busy}
                          onClick={() => onAction(() => api.removeOffer(id, offer.offer_id))}
                        >
                          Убрать
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <footer className="row">
          <Select
            options={available}
            value={newOfferId}
            placeholder="Добавить оффер…"
            searchPlaceholder="Поиск по названию или ID…"
            onChange={setNewOfferId}
          />
          <button
            disabled={busy || !newOfferId}
            onClick={() => {
              onAction(() => api.addOffer(id, Number(newOfferId)));
              setNewOfferId("");
            }}
          >
            Добавить
          </button>
          <span className="spacer" />
          <button disabled={busy} onClick={() => onAction(() => api.recalculate(id))}>
            Пересчитать веса
          </button>
          <button disabled={busy} onClick={() => onAction(() => api.fetch(id))}>
            Fetch
          </button>
          <button disabled={busy || !campaign.dirty} onClick={() => onAction(() => api.cancel(id))}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={busy || !campaign.dirty}
            onClick={() => onAction(() => api.push(id))}
          >
            Push
          </button>
        </footer>
      </>
    );
  }

  return (
    <section className="panel">
      <header className="row">
        <h2>{campaign.name}</h2>
        <span className="muted">
          {campaign.geo} · Keitaro #{campaign.keitaro_id} · {campaign.alias}
        </span>
      </header>

      {streams.map((stream) => {
        const unsaved = stream.editable && campaign.dirty;
        return (
          <div key={stream.id} className={unsaved ? "stream unsaved" : "stream"}>
            <div className="row stream-head">
              <h3>Поток {stream.position}</h3>
              <span>{stream.name}</span>
              <span className="muted">{KIND_LABELS[stream.kind] ?? stream.kind}</span>
              {unsaved && <span className="badge">есть неотправленные правки</span>}
            </div>
            {stream.editable ? (
              renderOffers()
            ) : (
              <p className="muted stream-note">Поток без офферов, здесь не редактируется.</p>
            )}
          </div>
        );
      })}

      {pinTarget && (
        <PinModal
          offer={pinTarget}
          otherPinnedTotal={active
            .filter((offer) => offer.pinned && offer.offer_id !== pinTarget.offer_id)
            .reduce((sum, offer) => sum + offer.share, 0)}
          onClose={() => setPinTarget(null)}
          onSave={(share) => {
            setPinTarget(null);
            onAction(() => api.pin(id, pinTarget.offer_id, share));
          }}
        />
      )}
    </section>
  );
}
