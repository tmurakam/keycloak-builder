# keycloak-builder

[English](./README.md)

[Keycloak](https://github.com/keycloak/keycloak) をソースからビルドするためのスクリプトとMaven設定。
`repository.jboss.org` が不安定/到達不可な状況を回避するためのもの。

## これが存在する理由

Keycloakをリリースタグからビルドすると、`repository.jboss.org`(古いNexusインスタンス)に依存する
アーティファクトが大量に絡んでくる: 配布物の組み立てに使うWildFly Galleonプラグイン、
opensaml/Shibboleth関連のアーティファクト、そしてどこにも公開されていない
JBoss独自の再パッケージ版サードパーティjar(`-jbossorg-`サフィックス付きのバージョン)など。
このサーバーはしばしば遅い・到達不可・一部のパスだけ応答しないといった状態になり、
普通に `mvn install` を実行するとビルド途中でハングしたり失敗したりする。

このリポジトリでは以下を用意している:

- **Maven Central を最初に試し、次にShibbolethのリポジトリ、最後に repository.jboss.org** の順で
  問い合わせ、最初に応答が返ってきたものを返す小さなローカルHTTPプロキシ(`mvn-repo-proxy.py`)。
  Mavenが毎回不安定なJBossサーバーに直接アクセスするのを避けられる。
- そのプロキシ経由になるように設定したMavenの `settings.xml` エントリ。
- 途中失敗後の再実行時に、それまでの進捗を消さずにビルドを実行するビルドスクリプト。

## 前提条件

- JDK 17、21、または25
- Python 3(標準ライブラリのみ、追加パッケージ不要)
- `keycloak/keycloak` のローカルクローン

## セットアップ

1. [`settings-snippet.xml`](./settings-snippet.xml) の `<mirrors>` と `<profiles>` のブロックを
   `~/.m2/settings.xml` にマージする。
2. [`maven.config.example`](./maven.config.example) の内容を、Keycloakのチェックアウト先の
   `.mvn/maven.config` にコピーする(ファイルが無ければ新規作成)。これはMaven Enforcerプラグインの
   `BannedRepositories` ルール(`org.jboss:jboss-parent` 親POM由来で、デフォルトでは
   `http://` のリポジトリを禁止する)を警告扱いに落とすためのもの。ローカルプロキシが
   HTTPで動いているために必要。
3. プロキシを起動し、ビルド中はそのまま起動したままにしておく:

   ```bash
   python3 ./mvn-repo-proxy.py
   ```

   デフォルトで `127.0.0.1:8477` で待ち受ける(`PROXY_PORT` で変更可)。

## ビルドする

`build.sh` は、ビルドしたいもの(リリースタグでもブランチでも何でも)がKeycloakのクローン内で
既にチェックアウト済みであることを前提にしている。今チェックアウトされているものをそのままビルドするだけ。

> [!TIP]
> このプロジェクトのリリースタグは、どのブランチからも辿れないコミットになっていることがある
> — リリース作業でバージョンを上げたコミットが、対応する `release/X.Y` ブランチ本体には
> マージされないため。タグを直接チェックアウトするとdetached HEAD状態になり、ビルドすること自体は
> 問題ないが作業を再開しづらいので、先にタグからローカルブランチを作っておくと良い:
> `git branch release/26.6.6 26.6.6 && git checkout release/26.6.6`

```bash
./build.sh <keycloakチェックアウトのパス>
# 例:
./build.sh ~/src/keycloak
```

これは以下を行う:

1. `clean` を付けずに `./mvnw install -DskipTests -Pdistribution` を実行する。
   これにより、途中失敗後の再実行時に、既にビルド成功している部分を再利用できる。
2. 生成されたサーバー配布物ZIP(`quarkus/dist/target/keycloak-<バージョン>.zip`)のパスを表示する。

追加の引数は `./mvnw` にそのまま渡される。失敗したモジュールから再開したい場合に便利:

```bash
./build.sh ~/src/keycloak -rf :keycloak-saml-adapter-galleon-pack
```

## 備考

- Keycloakサーバー本体の配布物ZIPと、レガシーなWildFly/EAP向けSAMLアダプタ配布物は、
  リアクター内の別々のモジュールでビルドされる。サーバー本体だけ必要で、
  アダプタ側のモジュールだけがアーティファクト不足で失敗している場合、
  そのエラーは無視して構わないことが多い — サーバーZIPは同じ実行の中で既に
  それより前にビルドされているはず。
- `mvn-repo-proxy.py` は `GET`/`HEAD`(アーティファクトのダウンロード)のみ実装しており、
  アーティファクトのデプロイには対応していない。release/deployのワークフローには使わないこと。
