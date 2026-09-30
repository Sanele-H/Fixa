// The ways to pay for a job, where a quote is made and read: the provider ticks which they
// accept (with a deposit for a split), each quote card lists them, and the customer picks one
// when accepting.

import type { TFunction } from "i18next";
import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { PAYMENT_METHODS, type PaymentMethod, type Quote } from "../api/types";
import { formatRands } from "../format";
import { Segmented, TextField } from "../ui";

/** A deposit is at most half the quote, the same rule as the server (payment_plans.MAX_DEPOSIT_SHARE). */
const MAX_DEPOSIT_SHARE = 0.5;
const NON_DIGITS = /\D/g;

/** The biggest deposit allowed on this price, in whole rands. */
export function findLargestDeposit(totalRands: number) {
  return Math.floor(totalRands * MAX_DEPOSIT_SHARE);
}

/** "Deposit, then the rest (R200 deposit)" when there's a deposit, else just the method's name. */
export function describeMethod(t: TFunction, language: string, method: PaymentMethod, depositRands: number | null) {
  const label = t(`payment.method.${method}`);
  if (method !== "in_app_split" || !depositRands) {
    return label;
  }
  return t("payment.withDeposit", { method: label, deposit: formatRands(depositRands, language) });
}

/** What the provider fills in on the quote form. */
export type OfferedPayment = {
  methods: PaymentMethod[];
  /** Digits only, as typed. Only used when in_app_split is ticked. */
  depositText: string;
};

/** True when the provider's choice can be sent: at least one way, and a deposit within the cap if split. */
export function isOfferedPaymentValid({ methods, depositText }: OfferedPayment, totalRands: number) {
  if (methods.length === 0) {
    return false;
  }
  if (!methods.includes("in_app_split")) {
    return true;
  }
  const depositRands = Number(depositText);
  return depositRands >= 1 && depositRands <= findLargestDeposit(totalRands);
}

type PaymentMethodsFieldProps = {
  value: OfferedPayment;
  totalRands: number;
  onChange: (value: OfferedPayment) => void;
};

/** The quote form's "How can the customer pay?": a tick per way, and the deposit for a split. */
export function PaymentMethodsField({ value, totalRands, onChange }: PaymentMethodsFieldProps) {
  const { t, i18n } = useTranslation();
  const largestDeposit = formatRands(findLargestDeposit(totalRands), i18n.language);
  const depositRands = Number(value.depositText);
  const isDepositTooHigh = totalRands > 0 && depositRands > findLargestDeposit(totalRands);

  /** Ticks or unticks one way, keeping them in the usual order. */
  function toggleMethod(method: PaymentMethod) {
    const isTicked = value.methods.includes(method);
    const methods = PAYMENT_METHODS.filter((option) => (option === method ? !isTicked : value.methods.includes(option)));
    onChange({ ...value, methods });
  }

  return (
    <fieldset className="stack stack--tight plain-fieldset">
      <legend className="field__label">{t("payment.methodsLabel")}</legend>
      {PAYMENT_METHODS.map((method) => (
        <label key={method} className="checkbox-row">
          <input type="checkbox" checked={value.methods.includes(method)} onChange={() => toggleMethod(method)} />
          <span>
            {t(`payment.method.${method}`)}
            <span className="muted small"> · {t(`payment.methodHint.${method}`)}</span>
          </span>
        </label>
      ))}
      {value.methods.length === 0 && <p className="small muted">{t("payment.pickOne")}</p>}
      {value.methods.includes("in_app_split") && (
        <TextField
          label={t("payment.depositLabel", { max: largestDeposit })}
          inputMode="numeric"
          required
          value={value.depositText}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            onChange({ ...value, depositText: event.target.value.replace(NON_DIGITS, "") })
          }
        />
      )}
      {isDepositTooHigh && <p className="small">{t("payment.depositTooHigh", { max: largestDeposit })}</p>}
    </fieldset>
  );
}

/** "Pay: In the app, after the job · Cash", on a quote card. */
export function OfferedMethods({ quote }: { quote: Quote }) {
  const { t, i18n } = useTranslation();
  const methods = quote.payment_methods
    .map((method) => describeMethod(t, i18n.language, method, quote.deposit_rands))
    .join(" · ");
  return <p className="small">{t("payment.offered", { methods })}</p>;
}

type PaymentMethodPickerProps = {
  quote: Quote;
  value: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
};

/** "How will you pay?": one of the quote's ways, picked before accepting it. */
export function PaymentMethodPicker({ quote, value, onChange }: PaymentMethodPickerProps) {
  const { t, i18n } = useTranslation();
  const options = quote.payment_methods.map((method) => ({
    value: method,
    label: describeMethod(t, i18n.language, method, quote.deposit_rands),
  }));
  return (
    <div className="stack stack--tight">
      <p className="eyebrow">{t("payment.chooseLabel")}</p>
      <Segmented label={t("payment.chooseLabel")} options={options} value={value} onChange={onChange} />
    </div>
  );
}
