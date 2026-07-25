"use client";

import type { ComponentPropsWithoutRef, MouseEvent } from "react";
import { handleIosStandaloneLinkClick } from "./iosStandaloneNavigation.mjs";

type IosStandaloneLinkProps = Omit<
  ComponentPropsWithoutRef<"a">,
  "href" | "onClick" | "target"
> & {
  href: string;
};

function isIosStandaloneWebApp() {
  const navigatorWithStandalone = navigator as Navigator & {
    standalone?: boolean;
  };

  return navigatorWithStandalone.standalone === true;
}

export default function IosStandaloneLink({
  href,
  ...props
}: IosStandaloneLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    handleIosStandaloneLinkClick({
      event,
      isIosStandalone: isIosStandaloneWebApp(),
      openWindow: (destination, target) =>
        window.open(destination, target),
      assignLocation: (destination) =>
        window.location.assign(destination),
    });
  }

  return <a {...props} href={href} onClick={handleClick} />;
}
