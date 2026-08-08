from cartography.regions.mediterranean import run_site_pipeline


def main() -> int:
    return run_site_pipeline("var-est", "Var Est")


if __name__ == "__main__":
    raise SystemExit(main())
