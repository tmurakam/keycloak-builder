# keycloak-builder

[日本語](./README.ja.md)

Scripts and Maven configuration for building [Keycloak](https://github.com/keycloak/keycloak)
from source, working around `repository.jboss.org` being unreliable/unavailable.

## Why this exists

Building Keycloak from a release tag pulls in a lot of dependencies from
`repository.jboss.org` (a legacy Nexus instance): the WildFly Galleon plugins
used to assemble distributions, opensaml/Shibboleth artifacts, and a handful
of JBoss-specific rebuilds of third-party jars (versions with a `-jbossorg-`
suffix) that were never published anywhere else. That server is frequently
slow, unreachable, or serves some paths but not others, which turns a normal
`mvn install` into a build that hangs or fails partway through.

This repo sets up:

- a small local HTTP proxy (`mvn-repo-proxy.py`) that tries **Maven Central
  first, then Shibboleth's repository, then repository.jboss.org**, in that
  order, and returns whichever responds first — instead of Maven hitting the
  flaky JBoss server directly for every dependency;
- Maven `settings.xml` entries that route through that proxy;
- a build script that runs the build without wiping previous progress on
  retry.

## Prerequisites

- JDK 17, 21, or 25
- Python 3 (stdlib only, no extra packages)
- A local clone of `keycloak/keycloak`

## Setup

1. Merge [`settings-snippet.xml`](./settings-snippet.xml) into `~/.m2/settings.xml`
   (the `<mirrors>` and `<profiles>` blocks).
2. Copy the contents of [`maven.config.example`](./maven.config.example) into
   `.mvn/maven.config` in your Keycloak checkout (create the file if it
   doesn't exist). This tells the Maven Enforcer plugin's `BannedRepositories`
   rule (inherited from the `org.jboss:jboss-parent` parent POM, which bans
   plain `http://` repositories by default) to only warn, since the local
   proxy is plain HTTP.
3. Start the proxy and leave it running for the duration of the build:

   ```bash
   python3 ./mvn-repo-proxy.py
   ```

   Listens on `127.0.0.1:8477` by default (override with `PROXY_PORT`).

## Building a release

`build.sh` assumes you've already checked out what you want to build (a
release tag, a branch, whatever) in your Keycloak clone — it just builds
whatever is currently checked out there.

> [!TIP]
> Release tags in this project are sometimes commits that no branch
> actually points at — the release process bumps the version for the tag
> but that commit never gets merged back into the corresponding
> `release/X.Y` branch. Checking out the tag directly leaves you in
> detached-HEAD state, which is fine to build but awkward to resume work
> on, so it's usually worth creating a local branch from the tag first:
> `git branch release/26.6.6 26.6.6 && git checkout release/26.6.6`.

```bash
./build.sh <path-to-keycloak-checkout>
# e.g.
./build.sh ~/src/keycloak
```

This will:

1. Run `./mvnw install -DskipTests -Pdistribution`, without `clean`, so a
   retry after a partial failure reuses whatever already built successfully.
2. Print the path to the resulting server distribution ZIP
   (`quarkus/dist/target/keycloak-<version>.zip`).

Extra arguments are forwarded to `./mvnw`, which is useful for resuming a
partially-failed build from the module that failed:

```bash
./build.sh ~/src/keycloak -rf :keycloak-saml-adapter-galleon-pack
```

## Notes

- The core Keycloak server distribution ZIP and the legacy WildFly/EAP SAML
  adapter distribution are built by separate reactor modules. If you only
  need the server, and the adapter module is the one hitting missing
  artifacts, you can usually ignore that failure — the server ZIP will
  already have been built earlier in the same run.
- `mvn-repo-proxy.py` only implements `GET`/`HEAD` (artifact downloads); it
  doesn't support deploying artifacts, so don't point release/deploy
  workflows at it.
