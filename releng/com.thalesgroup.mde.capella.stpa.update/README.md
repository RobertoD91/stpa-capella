# STPA update site (releng)

This module assembles the STPA p2 update site and the matching dropins archive
from the reactor features/plugins, driven by [`category.xml`](category.xml).

The build produces, under `target/`:

* `STPA-updateSite-capella<version>-<revision>.zip` &mdash; the p2 update site;
* `STPA-dropins-capella<version>-<revision>.zip` &mdash; the runnable dropins;
* `repository/` &mdash; the exploded p2 repository used by both archives.

## Update site layout

`category.xml` exposes three categories:

| Category | Content | Clean-Capella install |
| --- | --- | --- |
| `STPA Add-On (Experimental)` | core STPA viewpoint feature | yes, no extra update site |
| `STPA Add-On - HTML Documentation Generation (Optional)` | optional docgen feature | requires the Capella XHTML Documentation Generation add-on |
| `STPA Add-On Dependencies` | Sirius/EEF features mirrored for the core feature | n/a |

The optional `com.thalesgroup.mde.capella.stpa.docgen.feature` genuinely requires
`org.polarsys.capella.docgen`, `org.eclipse.egf.pattern` and
`org.eclipse.egf.pattern.ftask`. None of these are part of a clean Capella; they
are provided by the official **Capella XHTML Documentation Generation** add-on.
Rather than re-bundling that add-on (and a second copy of EGF) into this site,
`category.xml` declares a p2 `<repository-reference>` to the add-on update site.
With Tycho >= 2.4.0 this emits both a metadata and an artifact reference into the
generated `content.xml`, so the Capella install wizard (and `p2 director` with
`-followRepositoryReferences`) resolves the docgen dependencies automatically.

> Maintainers: the reference URL is pinned to the 7.0.x add-on (matching the
> Capella 7.0 / 7.0.1 target platform). Update it when releasing for another
> Capella line.

## Build

Requires JDK 17 (the Kitalpha 7.0.1 bundles declare a `JavaSE-17` execution
environment) and Maven.

```bash
# from the repository root
mvn clean package -P capella-7.0.1 -Declipse.p2.mirrors=false
```

## Validate

### 1. Structural check (fast, offline)

Confirms the core feature is free of EGF/docgen, the optional feature keeps its
real requirements, and the add-on `repository-reference` is present for both the
metadata and artifact repositories:

```bash
python3 releng/com.thalesgroup.mde.capella.stpa.update/validate-repository.py \
  releng/com.thalesgroup.mde.capella.stpa.update/target/repository
```

### 2. Clean-install check with p2 director (end-to-end)

Resolves the features against the Capella 7.0.1 platform repositories. The core
feature is installed **without** the EGF / XHTML Documentation Generation
repositories to prove it is self-contained.

> The Capella **install wizard** follows the enabled `repository-reference`
> declared by the update site, so an end user only adds the STPA update site and
> keeps "Contact all update sites during install to find required software"
> enabled. The `p2 director` **CLI** does not follow references, so the command
> below adds the add-on repository explicitly to prove the docgen dependency
> closure (`capella.docgen` + EGF) is resolvable.

```bash
ECLIPSE=/path/to/eclipse            # any 2023-03+ Eclipse with the p2 director
SITE="file://$PWD/releng/com.thalesgroup.mde.capella.stpa.update/target/repository"
ADDON="https://download.eclipse.org/capella/addons/xhtmldocgen/updates/releases/7.0.0/"
PLATFORM="https://download.eclipse.org/capella/core/updates/releases/7.0.0/org.polarsys.capella.rcp.site/,\
https://download.eclipse.org/kitalpha/updates/releases/runtime/7.0.1/,\
https://download.eclipse.org/kitalpha/updates/releases/sdk/7.0.1/,\
https://download.eclipse.org/sirius/updates/releases/7.4.5/2023-03,\
https://download.eclipse.org/modeling/amalgam/updates/releases/1.14.0/capella/,\
https://download.eclipse.org/modeling/gmp/gmf-runtime/updates/milestones/S202401081627,\
https://download.eclipse.org/modeling/gmp/gmf-notation/updates/releases/R202211151334,\
https://download.eclipse.org/nattable/releases/2.1.0/repository/,\
https://download.eclipse.org/nebula/releases/3.0.0/,\
https://download.eclipse.org/tools/gef/classic/releases/3.17.0,\
https://download.eclipse.org/diffmerge/releases/0.15.0/emf-diffmerge-site/,\
https://download.eclipse.org/mylyn/releases/3.26/,\
https://download.eclipse.org/tools/orbit/downloads/drops/R20230302014618/repository/,\
https://download.eclipse.org/releases/2023-03"

# Core: must succeed without the docgen/EGF repositories.
"$ECLIPSE" -nosplash -application org.eclipse.equinox.p2.director \
  -repository "$SITE,$PLATFORM" \
  -installIU com.thalesgroup.mde.capella.stpa.feature.feature.group \
  -destination /tmp/install-core -profile STPACore \
  -p2.os linux -p2.ws gtk -p2.arch x86_64 -roaming

# Docgen: must succeed with the referenced add-on repository available.
"$ECLIPSE" -nosplash -application org.eclipse.equinox.p2.director \
  -repository "$SITE,$PLATFORM,$ADDON" \
  -installIU com.thalesgroup.mde.capella.stpa.docgen.feature.feature.group \
  -destination /tmp/install-docgen -profile STPADocgen \
  -p2.os linux -p2.ws gtk -p2.arch x86_64 -roaming
```

Both invocations are also run automatically by the
[`Build and Validate STPA Update Site`](../../.github/workflows/build.yml)
GitHub Actions workflow (on pushes to `main` and on manual dispatch).
