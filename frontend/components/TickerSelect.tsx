"use client";

import { useState } from "react";

export const POPULAR_TICKERS: { ticker: string; name: string; sector: string }[] = [
  // Technology
  { ticker: "AAPL",  name: "Apple",            sector: "Technology" },
  { ticker: "MSFT",  name: "Microsoft",         sector: "Technology" },
  { ticker: "GOOGL", name: "Alphabet",          sector: "Technology" },
  { ticker: "AMZN",  name: "Amazon",            sector: "Technology" },
  { ticker: "META",  name: "Meta Platforms",    sector: "Technology" },
  { ticker: "NVDA",  name: "NVIDIA",            sector: "Technology" },
  { ticker: "TSLA",  name: "Tesla",             sector: "Technology" },
  { ticker: "ORCL",  name: "Oracle",            sector: "Technology" },
  { ticker: "CRM",   name: "Salesforce",        sector: "Technology" },
  { ticker: "ADBE",  name: "Adobe",             sector: "Technology" },
  // Finance
  { ticker: "JPM",   name: "JPMorgan Chase",    sector: "Finance" },
  { ticker: "GS",    name: "Goldman Sachs",     sector: "Finance" },
  { ticker: "MS",    name: "Morgan Stanley",    sector: "Finance" },
  { ticker: "BAC",   name: "Bank of America",   sector: "Finance" },
  { ticker: "WFC",   name: "Wells Fargo",       sector: "Finance" },
  { ticker: "BRK-B", name: "Berkshire Hathaway",sector: "Finance" },
  { ticker: "SCHW",  name: "Charles Schwab",    sector: "Finance" },
  { ticker: "BLK",   name: "BlackRock",         sector: "Finance" },
  // Healthcare
  { ticker: "JNJ",   name: "Johnson & Johnson", sector: "Healthcare" },
  { ticker: "UNH",   name: "UnitedHealth",      sector: "Healthcare" },
  { ticker: "PFE",   name: "Pfizer",            sector: "Healthcare" },
  { ticker: "ABBV",  name: "AbbVie",            sector: "Healthcare" },
  { ticker: "LLY",   name: "Eli Lilly",         sector: "Healthcare" },
  { ticker: "MRK",   name: "Merck",             sector: "Healthcare" },
  // Consumer
  { ticker: "WMT",   name: "Walmart",           sector: "Consumer" },
  { ticker: "KO",    name: "Coca-Cola",         sector: "Consumer" },
  { ticker: "PG",    name: "Procter & Gamble",  sector: "Consumer" },
  { ticker: "MCD",   name: "McDonald's",        sector: "Consumer" },
  { ticker: "NKE",   name: "Nike",              sector: "Consumer" },
  { ticker: "COST",  name: "Costco",            sector: "Consumer" },
  // Energy
  { ticker: "XOM",   name: "ExxonMobil",        sector: "Energy" },
  { ticker: "CVX",   name: "Chevron",           sector: "Energy" },
  // Telecom & Media
  { ticker: "VZ",    name: "Verizon",           sector: "Telecom" },
  { ticker: "T",     name: "AT&T",              sector: "Telecom" },
  { ticker: "NFLX",  name: "Netflix",           sector: "Telecom" },
  { ticker: "DIS",   name: "Disney",            sector: "Telecom" },
];

const CUSTOM_VALUE = "__custom__";

const sectors = Array.from(new Set(POPULAR_TICKERS.map((t) => t.sector)));

interface Props {
  value: string;
  onChange: (ticker: string) => void;
  label?: string;
}

export default function TickerSelect({ value, onChange, label = "Ticker" }: Props) {
  const isCustom = !POPULAR_TICKERS.some((t) => t.ticker === value);
  const [selectValue, setSelectValue] = useState(isCustom ? CUSTOM_VALUE : value);
  const [customInput, setCustomInput] = useState(isCustom ? value : "");

  function handleSelect(e: React.ChangeEvent<HTMLSelectElement>) {
    const v = e.target.value;
    setSelectValue(v);
    if (v !== CUSTOM_VALUE) {
      setCustomInput("");
      onChange(v);
    }
  }

  function handleCustom(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value.toUpperCase();
    setCustomInput(v);
    onChange(v);
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-700">{label}</label>
      <select className="field" value={selectValue} onChange={handleSelect}>
        {sectors.map((sector) => (
          <optgroup key={sector} label={sector}>
            {POPULAR_TICKERS.filter((t) => t.sector === sector).map((t) => (
              <option key={t.ticker} value={t.ticker}>
                {t.ticker} — {t.name}
              </option>
            ))}
          </optgroup>
        ))}
        <optgroup label="Other">
          <option value={CUSTOM_VALUE}>Enter custom ticker…</option>
        </optgroup>
      </select>

      {selectValue === CUSTOM_VALUE && (
        <input
          className="field"
          placeholder="e.g. TSM, BABA, SPOT"
          value={customInput}
          onChange={handleCustom}
          autoFocus
        />
      )}
    </div>
  );
}
