import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router";
import { Icon, type IconName } from "./Icon";

export type ButtonVariant = "primary" | "secondary" | "lime";

type ButtonLookProps = {
  variant?: ButtonVariant;
  isBlock?: boolean;
  isSmall?: boolean;
  icon?: IconName;
};

/**
 * Builds the class list for a pill button, shared by Button and ButtonLink.
 * `isBlock` makes it full width; `isSmall` drops it to the 44px minimum tap height.
 */
function buildButtonClassName({ variant = "primary", isBlock, isSmall }: ButtonLookProps) {
  return ["btn", `btn--${variant}`, isBlock && "btn--block", isSmall && "btn--small"]
    .filter(Boolean)
    .join(" ");
}

type ButtonProps = ButtonLookProps & ButtonHTMLAttributes<HTMLButtonElement>;

/** A pill-shaped button. Primary is black, the one main action on a screen. */
export function Button({ variant, isBlock, isSmall, icon, children, type = "button", ...buttonProps }: ButtonProps) {
  return (
    <button type={type} className={buildButtonClassName({ variant, isBlock, isSmall })} {...buttonProps}>
      {icon && <Icon name={icon} sizePx={20} />}
      {children}
    </button>
  );
}

type ButtonLinkProps = ButtonLookProps & { to: string; children: ReactNode };

/** Looks like a Button but navigates. Use it when the action is "go to another screen". */
export function ButtonLink({ to, variant, isBlock, isSmall, icon, children }: ButtonLinkProps) {
  return (
    <Link to={to} className={buildButtonClassName({ variant, isBlock, isSmall })}>
      {icon && <Icon name={icon} sizePx={20} />}
      {children}
    </Link>
  );
}

type IconButtonLookProps = {
  icon: IconName;
  /** Read out by screen readers, since the button shows no text. Always pass a translated string. */
  label: string;
  isInverse?: boolean;
  isSmall?: boolean;
};

/** Builds the class list for a round icon button, shared by IconButton and IconLink. */
function buildIconButtonClassName({ isInverse, isSmall }: Pick<IconButtonLookProps, "isInverse" | "isSmall">) {
  return ["icon-btn", isInverse && "icon-btn--inverse", isSmall && "icon-btn--small"].filter(Boolean).join(" ");
}

type IconButtonProps = IconButtonLookProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">;

/** A round white button holding one icon, like the clock and globe buttons in the design. */
export function IconButton({ icon, label, isInverse, isSmall, type = "button", ...buttonProps }: IconButtonProps) {
  return (
    <button
      type={type}
      className={buildIconButtonClassName({ isInverse, isSmall })}
      aria-label={label}
      title={label}
      {...buttonProps}
    >
      <Icon name={icon} />
    </button>
  );
}

/** A round icon button that navigates, for example the back arrow in a screen header. */
export function IconLink({ to, icon, label, isInverse, isSmall }: IconButtonLookProps & { to: string }) {
  return (
    <Link to={to} className={buildIconButtonClassName({ isInverse, isSmall })} aria-label={label} title={label}>
      <Icon name={icon} />
    </Link>
  );
}
