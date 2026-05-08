"use client";

import {
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Fuel,
  Gauge,
  Loader2,
  RefreshCcw,
  Route,
  ShieldCheck,
  TrendingDown,
  Wallet,
} from "lucide-react";

export default function ResultCard({
  result,
  wallet,
  onWalletChange,
  onConfirm,
  confirmLoading,
  confirmError,
  phantomUrl,
  txSignature,
  onReset,
}) {
  if (!result) return null;

  const { intent, quote, risk } = result;

  const riskLevel = risk?.level?.toLowerCase() || "unknown";
  const riskTone =
    {
      low: "bg-[#0d2a1d] text-[#70e1a6] border-[#1f6d4b]",
      medium: "bg-[#2d230b] text-[#ffd36a] border-[#766024]",
      high: "bg-[#321710] text-[#ff9c84] border-[#7a3a2d]",
      critical: "bg-[#341113] text-[#ffb8ba] border-[#7a2b30]",
    }[riskLevel] || "bg-[#151d20] text-[#9aa7ab] border-[#263237]";

  const outputAmount = Number(quote?.output_amount);
  const priceImpact = Number(quote?.price_impact_pct);
  const routeScore = quote?.route_score;
  const formattedOutput = Number.isFinite(outputAmount)
    ? outputAmount.toLocaleString(undefined, { maximumFractionDigits: 4 })
    : "--";
  const formattedImpact = Number.isFinite(priceImpact)
    ? `${priceImpact.toFixed(4)}%`
    : "--";

  return (
    <section className="mt-5 overflow-hidden rounded-[20px] border border-[#263237] bg-[#0f1416] shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
      <div className="border-b border-[#202a2e] px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#ff4a50]">
              Intent recognized
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-2xl font-semibold text-white">
              <span>{intent?.amount || "--"} {intent?.input_token || "--"}</span>
              <ArrowRight className="h-5 w-5 text-[#ff4a50]" />
              <span>{intent?.output_token || "--"}</span>
            </div>
          </div>
          <div className="flex h-20 w-20 flex-none flex-col items-center justify-center rounded-2xl border border-[#263237] bg-[#12191b]">
            <span className="text-2xl font-semibold text-white">
              {routeScore || "--"}
            </span>
            <span className="text-xs text-[#8d9a9f]">score</span>
          </div>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="px-5 py-5 sm:px-6">
          <div className="rounded-2xl border border-[#263237] bg-[#12191b] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#8d9a9f]">
              <Route className="h-4 w-4 text-[#ff4a50]" />
              Best route
            </div>
            <p className="mt-3 break-all font-mono text-sm leading-6 text-[#c2cbce]">
              {quote?.route_label || "Route label unavailable"}
            </p>
          </div>

          <div className="mt-5 divide-y divide-[#263237] rounded-2xl border border-[#263237]">
            <div className="grid gap-4 px-4 py-4 sm:grid-cols-[160px_1fr] sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium text-[#8d9a9f]">
                <TrendingDown className="h-4 w-4 text-[#ff4a50]" />
                You receive
              </div>
              <div className="text-right sm:text-left">
                <p className="text-2xl font-semibold text-white">
                  {formattedOutput}
                </p>
                <p className="text-sm text-[#8d9a9f]">{intent?.output_token || ""}</p>
              </div>
            </div>

            <div className="grid gap-4 px-4 py-4 sm:grid-cols-[160px_1fr] sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium text-[#8d9a9f]">
                <Gauge className="h-4 w-4 text-[#ff4a50]" />
                Price impact
              </div>
              <p className="text-right text-base font-semibold text-white sm:text-left">
                {formattedImpact}
              </p>
            </div>

            <div className="grid gap-4 px-4 py-4 sm:grid-cols-[160px_1fr] sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium text-[#8d9a9f]">
                <Fuel className="h-4 w-4 text-[#ff4a50]" />
                Network fee
              </div>
              <p className="text-right text-base font-semibold text-white sm:text-left">
                ~0.000005 SOL
              </p>
            </div>

            <div className="grid gap-4 px-4 py-4 sm:grid-cols-[160px_1fr] sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium text-[#8d9a9f]">
                <ShieldCheck className="h-4 w-4 text-[#ff4a50]" />
                Risk
              </div>
              <div className="text-right sm:text-left">
                <span className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${riskTone}`}>
                  {risk?.score ?? "--"}/100 {riskLevel}
                </span>
              </div>
            </div>
          </div>

          {risk?.warnings?.length > 0 && (
            <div className="mt-5 rounded-2xl border border-[#766024] bg-[#2d230b] p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#ffd36a]">
                <AlertTriangle className="h-4 w-4" />
                Route warnings
              </div>
              <div className="space-y-2">
                {risk.warnings.map((warning, index) => (
                  <p key={index} className="text-sm leading-5 text-[#f5d98a]">
                    {warning}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="border-t border-[#202a2e] bg-[#12191b] px-5 py-5 sm:px-6 lg:border-l lg:border-t-0">
          <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#8d9a9f]">
            <Wallet className="h-4 w-4 text-[#ff4a50]" />
            Wallet
          </div>
          <label
            htmlFor="wallet-address"
            className="mb-2 block text-sm font-medium text-white"
          >
            Solana address
          </label>
          <input
            id="wallet-address"
            value={wallet}
            onChange={(e) => onWalletChange(e.target.value)}
            placeholder="Enter Solana wallet address"
            className="w-full rounded-xl border border-[#263237] bg-[#0b1012] px-4 py-3 text-sm text-[#f4f7f5] outline-none transition placeholder:text-[#68777c] focus:border-[#ff4a50] focus:ring-4 focus:ring-[#ff4a50]/10"
          />
          <p className="mt-2 text-xs leading-5 text-[#8d9a9f]">
            No private keys are requested or stored.
          </p>

          {confirmError && (
            <div className="mt-4 rounded-xl border border-[#6b2428] bg-[#2a1013] p-3 text-sm text-[#ffb8ba]">
              {confirmError}
            </div>
          )}

          <div className="mt-5 flex flex-col gap-3">
            <button
              onClick={onConfirm}
              disabled={confirmLoading}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#ff353b] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#ff4f55] disabled:cursor-not-allowed disabled:bg-[#273034] disabled:text-[#68777c]"
            >
              {confirmLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Preparing Phantom
                </>
              ) : (
                <>
                  <ExternalLink className="h-4 w-4" />
                  Prepare in Phantom
                </>
              )}
            </button>
            <button
              onClick={onReset}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#263237] bg-[#0b1012] px-5 py-3 text-sm font-semibold text-[#c2cbce] transition-colors hover:border-[#ff4a50] hover:text-white"
            >
              <RefreshCcw className="h-4 w-4" />
              Reset
            </button>
          </div>

          {txSignature && (
            <a
              href={`https://solscan.io/tx/${txSignature}`}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-[#1f6d4b] bg-[#0d2a1d] px-5 py-3 text-sm font-semibold text-[#70e1a6] transition-colors hover:bg-[#113423]"
            >
              <ExternalLink className="h-4 w-4" />
              View submitted transaction
            </a>
          )}

          {phantomUrl && !txSignature && (
            <a
              href={phantomUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-[#ff4a50] bg-[#171f22] px-5 py-3 text-sm font-semibold text-[#ff8084] transition-colors hover:bg-[#221618]"
            >
              <ExternalLink className="h-4 w-4" />
              Open transaction in Phantom
            </a>
          )}

          <p className="mt-5 text-xs leading-5 text-[#8d9a9f]">
            This interface prepares a transaction link for wallet review before signing.
          </p>
        </aside>
      </div>
    </section>
  );
}
