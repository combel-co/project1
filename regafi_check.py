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


def has_safekeeping(entity: dict) -> bool:
    text = json.dumps(entity).lower()
    return any(kw in text for kw in SAFEKEEPING_KEYWORDS)


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

        safekeeping = has_safekeeping(entity)
        icon = "✅" if safekeeping else "❌"

        print(f"\n  {icon}  {name}")
        print(f"      SIREN    : {siren}")
        print(f"      Statut   : {status}")
        print(f"      Catégorie: {category}")
        print(f"      Tenue de compte (L542-1) : {'OUI ✅' if safekeeping else 'NON ❌'}")

        france = entity.get("france_activities", {})
        inv = france.get("investment_services", {})
        inv_data = inv.get("data", {})
        if inv_data:
            print("      Services d'investissement :")
            raw = json.dumps(inv_data)
            for kw in SAFEKEEPING_KEYWORDS:
                if kw in raw.lower():
                    print(f"        → '{kw}' détecté ✅")


def main():
    parser = argparse.ArgumentParser(description="REGAFI Checker — Capitali")
    parser.add_argument("--client-id", default=None,
                        help="Clé API X-IBM-Client-Id (optionnelle si accès public)")
    parser.add_argument("--json-out", action="store_true",
                        help="Sortie JSON brute pour débogage")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  REGAFI CHECKER — Capitali")
    print("  Vérification habilitation TCC (L542-1 CMF)")
    print("="*55)

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
