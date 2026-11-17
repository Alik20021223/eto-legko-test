import { FormEvent, useEffect, useState } from "react";

import { CampaignOffer } from "./api";

interface Props {
  offer: CampaignOffer;
  // Сумма весов остальных закреплённых офферов потока.
  otherPinnedTotal: number;
  onSave: (share: number) => void;
  onClose: () => void;
}

export default function PinModal({ offer, otherPinnedTotal, onSave, onClose }: Props) {
  const [value, setValue] = useState(String(offer.share));

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const share = Number(value);
  let problem = "";
  if (!/^\d+$/.test(value.trim()) || share < 1 || share > 100) {
    problem = "Вес — целое число от 1 до 100";
  } else if (otherPinnedTotal + share > 100) {
    problem = `Сумма закреплённых весов ${otherPinnedTotal + share}%, должно быть не больше 100%`;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!problem) onSave(share);
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pin-title"
        onMouseDown={(e) => e.stopPropagation()}
        onSubmit={submit}
      >
        <h3 id="pin-title">Закрепить вес</h3>
        <p className="modal-offer">{offer.name}</p>
        <label className="modal-field">
          Вес, %
          <input
            autoFocus
            inputMode="numeric"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={(e) => e.target.select()}
            aria-invalid={Boolean(problem)}
          />
        </label>
        {problem && <p className="field-error">{problem}</p>}
        <div className="row end">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={Boolean(problem)}>
            Save
          </button>
        </div>
      </form>
    </div>
  );
}
