from cartography.regions.mediterranean import run_site_pipeline


def main() -> int:
    return run_site_pipeline("var-ouest", "Var Ouest")


if __name__ == "__main__":
    raise SystemExit(main())
