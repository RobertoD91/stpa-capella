#!/usr/bin/env python3
# Copyright (c) 2020-2026 THALES.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0
#
# SPDX-License-Identifier: EPL-2.0
#
# Contributors:
#      THALES - initial API and implementation
"""
Structural validation of the generated STPA p2 update site.

It checks, on the assembled repository (the ``target/repository`` directory or
the unzipped update-site archive), that:

  1. the core STPA feature is present and does NOT pull in EGF or the Capella
     HTML documentation generation. The core viewpoint must install on a clean
     Capella with no extra update site;
  2. the optional HTML documentation generation feature is present and still
     declares its real requirements on EGF / capella.docgen (we never want to
     silently drop them);
  3. the update site carries a p2 ``repository-reference`` to the official
     Capella XHTML Documentation Generation add-on, for BOTH the metadata and
     the artifact repository (the Tycho >= 2.4.0 behaviour), so that a clean
     Capella can resolve the optional feature automatically;
  4. the update site does NOT redundantly bundle the EGF SDK bundles. EGF must
     come from the referenced add-on, not from a second copy shipped here.

Exit code is non-zero as soon as one mandatory check fails, so it can gate a CI
build or be run locally:

    python3 validate-repository.py path/to/target/repository
"""

import sys
import os
import io
import zipfile
import xml.etree.ElementTree as ET

CORE_FEATURE = "com.thalesgroup.mde.capella.stpa.feature.feature.group"
DOCGEN_FEATURE = "com.thalesgroup.mde.capella.stpa.docgen.feature.feature.group"
XHTMLDOCGEN_HINT = "xhtmldocgen"
FORBIDDEN_CORE_PREFIXES = ("org.eclipse.egf.", "org.polarsys.capella.docgen")
EXPECTED_DOCGEN_REQS = ("org.eclipse.egf.pattern", "org.polarsys.capella.docgen")

failures = []
checks = []


def ok(msg):
    checks.append("  [OK]   " + msg)


def fail(msg):
    checks.append("  [FAIL] " + msg)
    failures.append(msg)


def load_content_xml(repo_dir):
    """Return the parsed content.xml root, from content.jar or content.xml."""
    jar = os.path.join(repo_dir, "content.jar")
    xml = os.path.join(repo_dir, "content.xml")
    if os.path.isfile(jar):
        with zipfile.ZipFile(jar) as zf:
            with zf.open("content.xml") as fh:
                return ET.parse(io.BytesIO(fh.read())).getroot()
    if os.path.isfile(xml):
        return ET.parse(xml).getroot()
    raise SystemExit(f"ERROR: no content.jar or content.xml found in {repo_dir}")


def find_unit(root, unit_id):
    for unit in root.iter("unit"):
        if unit.get("id") == unit_id:
            return unit
    return None


def required_ids(unit):
    ids = []
    for req in unit.iter("required"):
        if req.get("namespace") == "org.eclipse.equinox.p2.iu":
            ids.append(req.get("name"))
    return ids


def main():
    repo_dir = sys.argv[1] if len(sys.argv) > 1 else "target/repository"
    if not os.path.isdir(repo_dir):
        raise SystemExit(f"ERROR: repository directory not found: {repo_dir}")

    root = load_content_xml(repo_dir)

    # 1. core feature present and clean of EGF / docgen.
    core = find_unit(root, CORE_FEATURE)
    if core is None:
        fail(f"core feature {CORE_FEATURE} is missing from the update site")
    else:
        ok(f"core feature {CORE_FEATURE} is present")
        leaked = [r for r in required_ids(core)
                  if r and r.startswith(FORBIDDEN_CORE_PREFIXES)]
        if leaked:
            fail("core feature must not depend on EGF / capella.docgen, "
                 f"but it requires: {sorted(set(leaked))}")
        else:
            ok("core feature has no EGF / capella.docgen requirement "
               "(installs on a clean Capella)")

    # 2. optional docgen feature present and still declares its real deps.
    docgen = find_unit(root, DOCGEN_FEATURE)
    if docgen is None:
        fail(f"docgen feature {DOCGEN_FEATURE} is missing from the update site")
    else:
        ok(f"docgen feature {DOCGEN_FEATURE} is present")
        reqs = required_ids(docgen)
        missing = [d for d in EXPECTED_DOCGEN_REQS if d not in reqs]
        if missing:
            fail("docgen feature lost its real requirements (regression): "
                 f"{missing}")
        else:
            ok("docgen feature still declares its EGF / capella.docgen "
               "requirements")

    # 3. repository-reference to the Capella XHTML Documentation Generation
    #    add-on, both metadata (type 0) and artifact (type 1).
    ref_types = set()
    ref_uri = None
    for refs in root.iter("references"):
        for repo in refs.iter("repository"):
            uri = repo.get("uri") or repo.get("url") or ""
            if XHTMLDOCGEN_HINT in uri:
                ref_uri = uri
                ref_types.add(repo.get("type"))
    if ref_uri is None:
        fail("no repository-reference to the Capella XHTML Documentation "
             "Generation add-on found in content.xml")
    else:
        ok(f"repository-reference to the docgen add-on is present: {ref_uri}")
        if {"0", "1"}.issubset(ref_types):
            ok("repository-reference covers both metadata (0) and artifact (1) "
               "repositories")
        else:
            fail("repository-reference must cover both metadata (type 0) and "
                 f"artifact (type 1); found types: {sorted(ref_types)}")

    # 4. no redundant EGF SDK bundles shipped in the site.
    egf_bundles = sorted({
        unit.get("id") for unit in root.iter("unit")
        if (unit.get("id") or "").startswith("org.eclipse.egf.")
        and unit.find("artifacts") is not None
    })
    if egf_bundles:
        fail("EGF bundles are redundantly bundled in the update site "
             f"(should come from the referenced add-on instead): {egf_bundles}")
    else:
        ok("no EGF bundles are redundantly shipped in the update site")

    print("STPA update site structural validation")
    print("repository: " + os.path.abspath(repo_dir))
    print("\n".join(checks))
    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} problem(s))")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
