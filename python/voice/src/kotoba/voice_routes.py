"""Read voice agent choices from the desktop's registered Harness routes."""

from .local_models import HarnessRemote


def load_routes(url):
    remote = HarnessRemote(url)
    registered = remote.call("llm/listProviders", {})
    catalog = remote.call("session/modelCatalog", {})
    groups = {group["id"]: group["models"] for group in catalog["groups"]}
    directory = remote.call("llm/listConfigurableProviders", {})
    namespaces = {item["ns"]: item["value"] for item in remote.call("settings/describe", {})["namespaces"]}
    entries = {item["provider"]: item for item in directory}
    routes = []
    for provider in registered:
        entry = entries.get(provider["id"], {})
        profile = namespaces.get(entry.get("settingsNs"), {})
        for part in entry.get("settingsPath", []):
            profile = profile.get(part, {}) if isinstance(profile, dict) else {}
        ref = profile.get("apiKeyEnv", "") if isinstance(profile, dict) else ""
        routes.append({"id": provider["id"], "name": provider["name"], "key_ref": ref,
                       "configured": True,
                       "models": groups.get(provider["id"], [])})
    active = {route["id"] for route in routes}
    for entry in directory:
        if entry["provider"] not in active:
            routes.append({"id": entry["provider"], "name": entry["displayName"], "key_ref": "",
                           "configured": False, "models": []})
    preferred = ["openai", "anthropic", "moonshotai", "deepseek-official", "kotoba-local"]
    return sorted(routes, key=lambda r: (preferred.index(r["id"]) if r["id"] in preferred else len(preferred), r["name"]))
