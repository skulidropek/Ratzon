"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Layers3,
  Loader2,
  Radio,
  ShieldCheck,
  Terminal,
  Wallet,
  Zap,
} from "lucide-react";
import IntentInput from "@/components/IntentInput";
import ResultCard from "@/components/ResultCard";
import QuickActions from "@/components/QuickActions";

const STATUS_ITEMS = [
  { label: "Intent API", value: "Live", icon: Radio },
  { label: "Route score", value: "0-100", icon: Gauge },
  { label: "Wallet handoff", value: "Phantom", icon: Wallet },
];

const ROUTE_ROWS = [
  ["Resolver", "Natural-language parser"],
  ["Liquidity", "Jupiter route selection"],
  ["Protection", "Risk and slippage checks"],
  ["Execution", "Phantom transaction link"],
];

const CAPABILITIES = [
  {
    title: "Intent console",
    body: "A focused command surface for swaps, prices, balances, and comparisons.",
    icon: Terminal,
  },
  {
    title: "Route intelligence",
    body: "Quotes are shown with route labels, output amount, price impact, and network cost.",
    icon: Layers3,
  },
  {
    title: "Execution guardrails",
    body: "Wallet entry, risk warnings, and Phantom handoff stay in one review flow.",
    icon: ShieldCheck,
  },
];

function getPhantomProvider() {
  if (typeof window === "undefined") return null;

  const browserWindow = window as typeof window & {
    phantom?: { solana?: any };
    solana?: any;
  };
  const provider = browserWindow.phantom?.solana || browserWindow.solana;
  return provider?.isPhantom ? provider : null;
}

function isMobileDevice() {
  if (typeof navigator === "undefined") return false;

  return (
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    (navigator.maxTouchPoints > 1 && /Macintosh/i.test(navigator.userAgent))
  );
}

function decodeBase64Transaction(transaction: string) {
  const binary = window.atob(transaction);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function buildPhantomBrowseUrl() {
  const targetUrl = window.location.href;
  const refUrl = window.location.origin;
  return `https://phantom.app/ul/browse/${encodeURIComponent(targetUrl)}?ref=${encodeURIComponent(refUrl)}`;
}

async function connectInjectedPhantom(provider: any) {
  const connection = await provider.connect();
  return connection?.publicKey?.toString?.() || provider.publicKey?.toString?.();
}

async function signWithInjectedPhantom(provider: any, transaction: string) {
  const { VersionedTransaction } = await import("@solana/web3.js");
  const versionedTransaction = VersionedTransaction.deserialize(
    decodeBase64Transaction(transaction),
  );
  const result = await provider.signAndSendTransaction(versionedTransaction);
  return result?.signature || result?.hash || (typeof result === "string" ? result : null);
}

export default function Home() {
  const [lastQuery, setLastQuery] = useState("");
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [wallet, setWallet] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [phantomUrl, setPhantomUrl] = useState<string | null>(null);
  const [txSignature, setTxSignature] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!result || !resultRef.current) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    resultRef.current.scrollIntoView({
      block: "start",
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }, [result]);

  async function handleSubmit(text: string) {
    setLastQuery(text);
    setLoading(true);
    setError(null);
    setResult(null);
    setConfirmError(null);
    setPhantomUrl(null);
    setTxSignature(null);

    try {
      const res = await fetch("/api/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!lastQuery) return;

    setConfirmError(null);
    setConfirmLoading(true);
    setPhantomUrl(null);
    setTxSignature(null);

    try {
      const provider = getPhantomProvider();

      if (!provider && isMobileDevice()) {
        window.location.assign(buildPhantomBrowseUrl());
        return;
      }

      let walletForSwap = wallet.trim();
      if (provider) {
        walletForSwap = await connectInjectedPhantom(provider);
        if (walletForSwap) setWallet(walletForSwap);
      }

      if (!walletForSwap) {
        throw new Error(
          "Connect Phantom or enter a Solana wallet address before preparing the transaction.",
        );
      }

      const res = await fetch("/api/swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: lastQuery, wallet: walletForSwap }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.error || "Failed to prepare swap");
      }

      const data = await res.json();
      if (!data.phantom_url) {
        throw new Error("Phantom URL not returned");
      }

      setPhantomUrl(data.phantom_url);

      if (provider && data.transaction) {
        const signature = await signWithInjectedPhantom(provider, data.transaction);
        if (signature) {
          setTxSignature(signature);
          return;
        }
        throw new Error("Phantom did not return a transaction signature.");
      }

      if (isMobileDevice()) {
        window.location.assign(data.phantom_browse_url || buildPhantomBrowseUrl());
        return;
      }

      throw new Error(
        "Phantom extension was not detected in this browser tab. Enable Phantom in Brave, refresh, and try again.",
      );
    } catch (e: any) {
      setConfirmError(e?.message || "Could not prepare Phantom transaction.");
    } finally {
      setConfirmLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#080b0d] text-[#f4f7f5]">
      <header className="sticky top-0 z-20 border-b border-[#202a2e] bg-[#080b0d]/90 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 md:flex-row md:items-center">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#ff353b] text-lg font-black text-white shadow-[0_10px_28px_rgba(255,53,59,0.24)]">
              R
            </div>
            <div>
              <p className="text-base font-semibold tracking-[0.18em] text-white">
                RATZON
              </p>
              <p className="text-xs uppercase text-[#8d9a9f]">
                Solana intent execution
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-[#9aa7ab] md:ml-auto">
            {STATUS_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <span
                  key={item.label}
                  className="inline-flex items-center gap-2 rounded-full border border-[#263237] bg-[#11181b] px-3 py-2 shadow-[0_10px_30px_rgba(0,0,0,0.18)]"
                >
                  <Icon className="h-3.5 w-3.5 text-[#ff4a50]" />
                  <span className="font-medium text-white">{item.value}</span>
                  <span>{item.label}</span>
                </span>
              );
            })}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 pb-12 pt-5 sm:px-6 lg:px-8">
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="overflow-hidden rounded-[20px] border border-[#263237] bg-[#0f1416] shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
            <div className="border-b border-[#202a2e] px-5 py-5 sm:px-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div className="max-w-2xl">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#ff4a50]">
                    Intent workstation
                  </p>
                  <h1 className="mt-3 text-3xl font-semibold leading-tight text-white sm:text-4xl">
                    Ratzon
                  </h1>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-[#a8b4b8] sm:text-base">
                    Describe a Solana action, review the route, then hand the prepared transaction to Phantom.
                  </p>
                </div>
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[#263237] bg-[#151d20] px-3 py-2 text-xs font-medium text-[#c2cbce]">
                  <CheckCircle2 className="h-4 w-4 text-[#36d27f]" />
                  Mainnet routing
                </div>
              </div>
            </div>

            <div className="grid gap-5 px-5 py-5 sm:px-6 lg:grid-cols-[minmax(0,1fr)_260px]">
              <div className="space-y-5">
                <IntentInput onSubmit={handleSubmit} loading={loading} />

                <div className="border-t border-[#202a2e] pt-5">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8d9a9f]">
                      Fast intents
                    </p>
                    <Zap className="h-4 w-4 text-[#ff4a50]" />
                  </div>
                  <QuickActions onSelect={handleSubmit} />
                </div>
              </div>

              <div className="rounded-2xl border border-[#202a2e] bg-[#12191b] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8d9a9f]">
                  Session
                </p>
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-[#263237] pb-3 text-sm">
                    <span className="text-[#8d9a9f]">Parser</span>
                    <span className="font-medium text-white">QVAC</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-[#263237] pb-3 text-sm">
                    <span className="text-[#8d9a9f]">Routing</span>
                    <span className="font-medium text-white">Jupiter</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[#8d9a9f]">Keys</span>
                    <span className="font-medium text-white">Not stored</span>
                  </div>
                </div>
                <div className="mt-5 rounded-xl border border-[#263237] bg-[#0d1214] px-4 py-3 text-xs leading-5 text-[#9aa7ab]">
                  The wallet address is only used to prepare the transaction link.
                </div>
              </div>
            </div>
          </div>

          <aside className="overflow-hidden rounded-[20px] border border-[#263237] bg-[#0f1416] text-white shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
            <div className="route-map px-5 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#8d9a9f]">
                    Route preview
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold">SOL to USDC</h2>
                </div>
                <div className="rounded-full border border-white/15 bg-white/[0.08] px-3 py-1 text-xs text-[#d8e1e3]">
                  Demo state
                </div>
              </div>

              <div className="mt-8 flex items-center justify-between gap-3">
                <div className="route-node">
                  <span>SOL</span>
                </div>
                <div className="h-px min-w-8 flex-1 bg-[#4a565a]" />
                <div className="route-node route-node-accent">
                  <span>R</span>
                </div>
                <div className="h-px min-w-8 flex-1 bg-[#4a565a]" />
                <div className="route-node">
                  <span>USDC</span>
                </div>
              </div>

              <div className="mt-8 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-xl border border-white/10 bg-white/[0.08] px-3 py-3">
                  <p className="text-[#8d9a9f]">Impact</p>
                  <p className="mt-1 font-semibold text-white">0.08%</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.08] px-3 py-3">
                  <p className="text-[#8d9a9f]">Score</p>
                  <p className="mt-1 font-semibold text-white">94</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.08] px-3 py-3">
                  <p className="text-[#8d9a9f]">Fee</p>
                  <p className="mt-1 font-semibold text-white">~0.000005</p>
                </div>
              </div>
            </div>

            <div className="divide-y divide-white/10 px-5 py-2">
              {ROUTE_ROWS.map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 py-4 text-sm">
                  <span className="text-[#8d9a9f]">{label}</span>
                  <span className="text-right font-medium text-white">{value}</span>
                </div>
              ))}
            </div>
          </aside>
        </section>

        {error && (
          <div
            role="alert"
            className="mt-5 flex items-start gap-3 rounded-2xl border border-[#6b2428] bg-[#2a1013] p-4 text-sm text-[#ffb8ba]"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="mt-5 flex items-center justify-center gap-3 rounded-2xl border border-[#263237] bg-[#0f1416] p-8 text-center text-[#9aa7ab] shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
            <Loader2 className="h-5 w-5 animate-spin text-[#ff4a50]" />
            <p>Searching best route and preparing quote...</p>
          </div>
        )}

        {result && (
          <div ref={resultRef} aria-live="polite" className="scroll-mt-[180px]">
            <ResultCard
              result={result}
              wallet={wallet}
              onWalletChange={setWallet}
              onConfirm={handleConfirm}
              confirmLoading={confirmLoading}
              confirmError={confirmError}
              phantomUrl={phantomUrl}
              txSignature={txSignature}
              onReset={() => {
                setResult(null);
                setWallet("");
                setPhantomUrl(null);
                setTxSignature(null);
                setConfirmError(null);
              }}
            />
          </div>
        )}

        <section className="mt-6 grid gap-4 lg:grid-cols-3">
          {CAPABILITIES.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="rounded-2xl border border-[#263237] bg-[#0f1416] p-5 shadow-[0_16px_50px_rgba(0,0,0,0.24)]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1b2428] text-[#ff4a50]">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-white">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[#9aa7ab]">
                  {item.body}
                </p>
              </div>
            );
          })}
        </section>
      </div>
    </main>
  );
}
