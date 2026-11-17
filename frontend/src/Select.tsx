import { useEffect, useRef, useState } from "react";

export interface SelectOption {
  id: number | string;
  name: string;
}

interface Props {
  options: SelectOption[];
  value: string;
  placeholder: string;
  searchPlaceholder?: string;
  onChange: (value: string) => void;
}

// Свой выпадающий список вместо нативного <select>: тот не стилизуется
// и растягивается на ширину самого длинного пункта.
export default function Select({
  options,
  value,
  placeholder,
  searchPlaceholder = "Поиск…",
  onChange,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);

  const selected = options.find((option) => String(option.id) === value);
  const needle = query.trim().toLowerCase();
  const filtered = needle
    ? options.filter((option) => option.name.toLowerCase().includes(needle))
    : options;

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => {
    list.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [active]);

  function toggle() {
    setOpen(!open);
    setQuery("");
    setActive(0);
  }

  function choose(option: SelectOption) {
    onChange(String(option.id));
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(Math.min(active + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(Math.max(active - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[active]) choose(filtered[active]);
    }
  }

  return (
    <div className="select" ref={root}>
      <button
        type="button"
        className={open ? "select-trigger open" : "select-trigger"}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={toggle}
      >
        <span className={selected ? "select-value" : "select-value placeholder"}>
          {selected ? selected.name : placeholder}
        </span>
        <span className="select-arrow" aria-hidden>
          ▾
        </span>
      </button>

      {open && (
        <div className="select-popup">
          <input
            autoFocus
            className="select-search"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
          />
          <ul className="select-list" role="listbox" ref={list}>
            {filtered.map((option, index) => (
              <li
                key={option.id}
                role="option"
                aria-selected={String(option.id) === value}
                className={[
                  "select-option",
                  index === active ? "active" : "",
                  String(option.id) === value ? "selected" : "",
                ].join(" ")}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(option)}
              >
                {option.name}
              </li>
            ))}
            {filtered.length === 0 && <li className="select-empty">Ничего не найдено</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
