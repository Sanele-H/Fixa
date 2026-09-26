import { NavLink } from "react-router";
import { Icon, type IconName } from "./Icon";

export type NavItem = {
  to: string;
  icon: IconName;
  /** Translated text, shown under the circle as well as read out. */
  label: string;
};

type BottomNavProps = {
  /** Screen-reader name for the whole bar. Pass a translated string. */
  label: string;
  items: NavItem[];
};

/**
 * The floating row of round buttons at the bottom of tab screens.
 * The current tab's circle turns black. Each circle has a short word under it,
 * because icons alone are hard for people who read slowly.
 */
export function BottomNav({ label, items }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label={label}>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className="bottom-nav__item">
          <span className="bottom-nav__circle">
            <Icon name={item.icon} />
          </span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
