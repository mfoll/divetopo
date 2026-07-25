import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { handleIosStandaloneLinkClick } from "../app/iosStandaloneNavigation.mjs";

const destination = "https://reunion.divetopo.com/fr";

function createClickEvent(overrides = {}) {
  let prevented = false;
  return {
    event: {
      defaultPrevented: false,
      button: 0,
      metaKey: false,
      ctrlKey: false,
      shiftKey: false,
      altKey: false,
      currentTarget: { href: destination },
      preventDefault() {
        prevented = true;
      },
      ...overrides,
    },
    wasPrevented() {
      return prevented;
    },
  };
}

test("keeps normal browser navigation native", () => {
  const click = createClickEvent();
  const openCalls = [];
  const assignCalls = [];
  const handled = handleIosStandaloneLinkClick({
    event: click.event,
    isIosStandalone: false,
    openWindow: (...args) => {
      openCalls.push(args);
      return { opener: null };
    },
    assignLocation: (url) => assignCalls.push(url),
  });

  assert.equal(handled, false);
  assert.equal(click.wasPrevented(), false);
  assert.deepEqual(openCalls, []);
  assert.deepEqual(assignCalls, []);
});

test("opens an external region inside the installed iOS web app", () => {
  const click = createClickEvent();
  const openCalls = [];
  const openedWindow = { opener: "homepage" };
  const handled = handleIosStandaloneLinkClick({
    event: click.event,
    isIosStandalone: true,
    openWindow: (...args) => {
      openCalls.push(args);
      return openedWindow;
    },
    assignLocation() {
      assert.fail("successful window.open must not navigate the original view");
    },
  });

  assert.equal(handled, true);
  assert.equal(click.wasPrevented(), true);
  assert.deepEqual(openCalls, [[destination, "_blank"]]);
  assert.equal(openedWindow.opener, null);
});

test("preserves modified, secondary, and cancelled clicks", () => {
  for (const overrides of [
    { defaultPrevented: true },
    { button: 1 },
    { metaKey: true },
    { ctrlKey: true },
    { shiftKey: true },
    { altKey: true },
  ]) {
    const click = createClickEvent(overrides);
    const handled = handleIosStandaloneLinkClick({
      event: click.event,
      isIosStandalone: true,
      openWindow() {
        assert.fail("modified or cancelled clicks must keep native behavior");
      },
      assignLocation() {
        assert.fail("modified or cancelled clicks must keep native behavior");
      },
    });

    assert.equal(handled, false);
    assert.equal(click.wasPrevented(), false);
  }
});

test("falls back to normal navigation when window.open fails", () => {
  for (const openWindow of [
    () => null,
    () => {
      throw new Error("popup blocked");
    },
  ]) {
    const click = createClickEvent();
    const assignCalls = [];
    const handled = handleIosStandaloneLinkClick({
      event: click.event,
      isIosStandalone: true,
      openWindow,
      assignLocation: (url) => assignCalls.push(url),
    });

    assert.equal(handled, true);
    assert.equal(click.wasPrevented(), true);
    assert.deepEqual(assignCalls, [destination]);
  }
});

test("uses the iOS-specific standalone signal", async () => {
  const componentSource = await readFile(
    new URL("../app/IosStandaloneLink.tsx", import.meta.url),
    "utf8",
  );

  assert.match(
    componentSource,
    /navigatorWithStandalone\.standalone === true/,
  );
  assert.doesNotMatch(componentSource, /userAgent|matchMedia/);
});
