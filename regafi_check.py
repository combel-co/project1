import requests
import json
import sys
import argparse

BASE_URL = "https://api.regafi.banque-france.fr/regafi-en/v1/en"

SAFEKEEPING_KEYWORDS = [
    "safekeeping",
    "administration of financial instruments",
    "custodianship",
    "conservation",
    "tenue de compte",
]

TARGETS = [
    {"label": "Uptevia",                  "queries": ["uptevia"]},
    {"label": "SG Securities Services",   "queries": ["sg securities", "societe generale securities", "sgss"]},
    {"label": "Natixis Interépargne",     "queries": ["natixis interepargne", "natixis intere"]},
    {"label": "Amundi ESR",               "queries": ["amundi esr", "amundi epargne salariale"]},
    {"label": "CIC Market Solutions",     "queries": ["cic market", "credit industriel"]},
]


def search(denomination: str, client_id: str = None) -> list:
    url = f"{BASE_URL}/entities/searchbydenomination"
    params = {"denomination": denomination}
    headers = {"Accept": "application/json"}
    if client_id:
        headers["X-IBM-Client-Id"] = client_id

    r = requests.get(url, params=params, headers=headers, timeout=15)
    if r.status_code == 401:
        print("  ⚠️  401 — API key requise. Ajoute --client-id VOTRE_CLE")
        print("       Inscription gratuite : https://developer.banque-france.fr")
        return []
    if r.status_code != 200:
        print(f"  ⚠️  HTTP {r.status_code} pour '{denomination}'")
        return []
    data = r.json()
    if isinstance(data, list):
        return data
    return data.get("entities", data.get("data", []))


def fetch_detail(entity_id: str, client_id: str = None) -> dict:
    """Fetches full entity detail including ancillary/connected services."""
    url = f"{BASE_URL}/entities/{entity_id}"
    headers = {"Accept": "application/json"}
    if client_id:
        headers["X-IBM-Client-Id"] = client_id
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        return r.json()
    return {}


def has_safekeeping(entity: dict) -> bool:
    text = json.dumps(entity).lower()
    return any(kw in text for kw in SAFEKEEPING_KEYWORDS)


def print_services(detail: dict):
    """Prints investment services and ancillary services from entity detail."""
    france = detail.get("france_activities", {})

    # Services d'investissement principaux
    inv = france.get("investment_services", {})
    inv_items = inv.get("data", inv) if isinstance(inv, dict) else inv
    if inv_items:
        print("      ▸ Services d'investissement :")
        raw = json.dumps(inv_items).lower()
        for kw in SAFEKEEPING_KEYWORDS:
            if kw in raw:
                print(f"          → '{kw}' ✅")

    # Services connexes (ancillary) — c'est là que vit la TCC
    ancillary = france.get("ancillary_services", france.get("connected_services", {}))
    anc_items = ancillary.get("data", ancillary) if isinstance(ancillary, dict) else ancillary
    if anc_items:
        print("      ▸ Services connexes (ancillary) :")
        raw = json.dumps(anc_items)
        print(f"          {raw[:300]}")
        for kw in SAFEKEEPING_KEYWORDS:
            if kw in raw.lower():
                print(f"          → '{kw}' ✅")

    # Dump brut si rien trouvé ci-dessus
    if not inv_items and not anc_items:
        keys = list(france.keys()) if france else list(detail.keys())
        print(f"      ▸ Clés disponibles dans le détail : {keys}")


def check_target(target: dict, client_id: str = None):
    label = target["label"]
    print(f"\n{'='*55}")
    print(f"🔍  {label}")
    print(f"{'='*55}")

    found = []
    for q in target["queries"]:
        results = search(q, client_id)
        if results:
            found.extend(results)
            break

    if not found:
        print("  ❌  Aucune entité trouvée dans REGAFI")
        return

    print(f"  {len(found)} entité(s) trouvée(s)")
    for entity in found[:5]:
        name = (
            entity.get("company_description", {}).get("denomination", "")
            or entity.get("denomination", "")
            or entity.get("name", "?")
        )
        siren = (
            entity.get("company_description", {}).get("siren", "")
            or entity.get("siren", "")
        )
        status = (
            entity.get("company_description", {}).get("status", "")
            or entity.get("status", "")
        )
        category = (
            entity.get("company_description", {}).get("category", "")
            or entity.get("category", "")
        )
        entity_id = (
            entity.get("id", "")
            or entity.get("entity_id", "")
        )

        # Fetch full detail to get ancillary services (TCC lives there)
        detail = fetch_detail(str(entity_id), client_id) if entity_id else entity
        merged = {**entity, **detail}
        safekeeping = has_safekeeping(merged)
        icon = "✅" if safekeeping else "❌"

        print(f"\n  {icon}  {name}")
        print(f"      SIREN    : {siren}")
        print(f"      Statut   : {status}")
        print(f"      Catégorie: {category}")
        print(f"      ID REGAFI: {entity_id}")
        print(f"      Tenue de compte (L542-1) : {'OUI ✅' if safekeeping else 'NON ❌'}")
        print_services(merged)


def main():
    parser = argparse.ArgumentParser(description="REGAFI Checker — Capitali")
    parser.add_argument("--client-id", default=None,
                        help="Clé API X-IBM-Client-Id (optionnelle si accès public)")
    parser.add_argument("--json-out", action="store_true",
                        help="Sortie JSON brute pour débogage")
    parser.add_argument("--id", default=None,
                        help="Fetch le détail d'une entité par son ID REGAFI")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  REGAFI CHECKER — Capitali")
    print("  Vérification habilitation TCC (L542-1 CMF)")
    print("="*55)

    if args.id:
        detail = fetch_detail(args.id, args.client_id)
        print(json.dumps(detail, indent=2, ensure_ascii=False))
        return

    if args.json_out:
        results = search("uptevia", args.client_id)
        print(json.dumps(results[:1], indent=2, ensure_ascii=False))
        return

    for target in TARGETS:
        check_target(target, args.client_id)

    print(f"\n{'='*55}")
    print("  Fin de l'analyse REGAFI")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
