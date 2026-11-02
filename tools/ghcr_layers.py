#!/usr/bin/env python3
"""Check whether pulling ghcr.io/enij90/armada-tb321fu:<target> will repair the
preview-4 install's missing ostree container refs (issue #4).

bootc computes the booted deployment's state from the manifest embedded in its
commit and needs the ref ostree/container/blob/<first layer digest> to exist.
The preview-4 install images never recorded it. Pulling any image whose first
layer has the same digest creates the ref, so compare the installed build's
manifest with the target's. Run on the PC before the update; no credentials.

usage: ghcr_layers.py [target-tag] [installed-build-tag]
"""
import json
import sys
import urllib.request

REPO = "enij90/armada-tb321fu"
INSTALLED = "build-20261015.0544305-38757030059-1"  # preview 4, what the tablet runs
ACCEPT = ", ".join([
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
])


def get(url, token=None, accept=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if accept:
        req.add_header("Accept", accept)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()), r.headers


def manifest(tag, token):
    data, hdr = get(f"https://ghcr.io/v2/{REPO}/manifests/{tag}", token, ACCEPT)
    if "manifests" in data:  # multi-arch index: pick arm64
        for m in data["manifests"]:
            p = m.get("platform", {})
            if p.get("architecture") == "arm64":
                data, hdr = get(f"https://ghcr.io/v2/{REPO}/manifests/{m['digest']}", token, ACCEPT)
                break
    digest = hdr.get("Docker-Content-Digest", "?")
    return digest, [l["digest"] for l in data.get("layers", [])]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "latest"
    installed = sys.argv[2] if len(sys.argv) > 2 else INSTALLED
    token = get(f"https://ghcr.io/token?scope=repository:{REPO}:pull")[0]["token"]
    tags = get(f"https://ghcr.io/v2/{REPO}/tags/list", token)[0]["tags"]
    builds = [t for t in tags if t.startswith("build-")]
    print(f"newest build tags: {', '.join(builds[-3:])}")

    t_digest, t_layers = manifest(target, token)
    i_digest, i_layers = manifest(installed, token)
    print(f"{target}: manifest {t_digest}, {len(t_layers)} layers")
    print(f"{installed}: manifest {i_digest}, {len(i_layers)} layers")
    print(f"installed first layer: {i_layers[0]}")
    print(f"{target} first layer:  {t_layers[0]}")
    shared = len(set(t_layers) & set(i_layers))
    print(f"shared layers: {shared}/{len(i_layers)}")
    if t_layers[0] == i_layers[0]:
        print(f"OK: pulling :{target} creates the missing base-layer ref; "
              "the issue #4 in-place fix works as written.")
        return 0
    print(f"DIFFERENT base layer: pull :{installed} first (it is the installed image), "
          f"then bootc switch to :{target}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
