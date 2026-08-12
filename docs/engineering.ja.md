# Family OS — エンジニア向けドキュメント

[← 玄関へ戻る](../README.ja.md)

このページは地図の技術面です。エージェント・プロセス・契約という言葉に慣れている方を想定しています。同じ内容を専門用語なしで読みたい場合は、玄関がそのまま対応しています。

正確な契約 — 権限・エッジ・失敗時の扱いのすべて — は[詳細仕様](reference.ja.md)にあります。このページは形を説明し、あちらが形を固定します。

---

<a id="what-this-is"></a>

## このリポジトリは何か

Family OS は **non-runtime な層**です。方針・地図・ポインタ・観測の描画だけを持ちます。あなたが入れるものを配らず、あなたの環境でプロセスを起動せず、ポートを開かず、認証情報を保管しません。リポジトリにある唯一のコードは `tools/` で、これは `registry/modules.json` からこのページ群を生成し、書いてあることがまだ本当かを検査するためのものです。

実務上の帰結が、いちばん覚えておく価値のある部分です。

- **すべての runtime モジュールは、このリポジトリを削除しても動き続けなければなりません。** 地図が無いと動かないモジュールがあるなら、地図はすでに制御装置になっており、設計が壊れています。
- **ここはレジストリではありません。** サービスディスカバリも、コールバック経路も、死活判定もありません。
- **ここはモジュールの契約を複製しません。** 各モジュールの挙動はそのリポジトリが正本で、ここが持つのはポインタと、そのポインタの鮮度だけです。

Family OS が権限を持って答える問いは、ただ1つ — *この文書は、自分の鮮度メタデータに照らして最新か*。それ以外に描画されているものは、すべて誰か他の所有物です。

---

<a id="layers"></a>

## 3つの層

```mermaid
flowchart TB
  OS["Family OS<br/>地図 — non-runtime"]

  subgraph Rule["掟 — Family Dev Handbook"]
    direction LR
    V["縦軸<br/>1体のAIを育てる"]
    H["横軸<br/>家族をつなぐ"]
  end

  OS -.-|"案内のみ"| Rule
```

| 層 | 答えるもの | 正本 |
| --- | --- | --- |
| 掟 | 並行作業を壊さない進め方 — Issue・ブランチ・worktree・受け渡し | [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) |
| 縦軸 | 1体のAIが、覚え・やり切り・育つ方法 | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) と成長ループ |
| 横軸 | 複数のAIが記憶を共有し、仕事を渡す方法 | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) と [Sitter](https://github.com/caty-ai/sitter) |

掟の層は、どちらかの軸の内側ではなく**両方の上**にあります。掟はプログラムではなく文書です。人とAIがモジュールをどう開発するかを縛るだけで、runtime では何も強制しません。

---

<a id="modules"></a>

## モジュール一覧

<!-- family:generated:module-inventory:start -->
| モジュール | 種別 | 所有するもの | 状態 |
| --- | --- | --- | --- |
| [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) | non-runtime・ガバナンス | Issue・PR・worktree・受け渡し・並行開発のルール | 公開・MIT |
| [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) | runtime・縦軸の基盤 | タスクの意味・試行・リトライ・チェックポイント・完了判定・完了・DLQ | 公開・MIT |
| [context-kit](https://github.com/caty-ai/context-kit) | runtime・机まわりの装備 | ツール出力の退避と抜粋・委譲ブリーフ検査・危険削除/公開事故/キー漏れのガード・1体分の記憶検索 | 公開・MIT |
| [Persona Engine](https://github.com/caty-ai/persona-engine) | runtime・単独利用可能 | 人格のレイヤーと感情のグラデーション | 公開・MIT |
| [Persona Growth Loop](https://github.com/shojikumaru/persona-growth-loop) | 計画中のフロントエンド | 最小化された冪等な提案の生成 | 公開準備中・計画中 |
| [X Collector](https://github.com/caty-ai/x-collector) | runtime・任意の入力 | 能力ループ向けの外部素材の収集 | 公開・MIT |
| [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) | runtime・アプリケーション | 提案・ガバナンス・採用記録・成長の解釈 | 公開・MIT |
| [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) | runtime・横方向の基盤 | 記憶バス・登録されたスケジュールの期待・check-in・来歴 | 公開・MIT |
| [Sitter](https://github.com/caty-ai/sitter) | runtime・観測 | ローカルのプロセスと返信の事実・発注試行の証拠・委譲された同一試行の再起動 | 公開・MIT |
<!-- family:generated:module-inventory:end -->

この表は [`registry/modules.json`](../registry/modules.json) から生成しています。「公開準備中」のリンクは、いまはまだ開けません。何が存在し、どこに置かれるのかを地図として正直に保つために載せています。

Persona Engine と X Collector は単独で使え、他のどれからも必須とされていません。X Collector は能力ループへの現在の既定の入力経路ですが、唯一の経路ではなく置き換えられます。

---

<a id="detailed-diagrams"></a>

## 詳細図

以下の図は、README にある詳細トポロジをエンジニア向けの見取り図へ移したものです。隣接する表が、ノードと関係についての意味上の正本です。モジュールの公開状態とライセンスの事実は、引き続き `registry/modules.json` を正本とします。

<a id="vertical-axis-detail"></a>

### 縦軸の詳細

![1体のエージェントに対する縦軸トポロジ。Harness の基盤の上に、人格と能力の成長分岐が別々にある。正本は下の表](../assets/readme/vertical-axis.svg)

| ノード | 役割 | 関係 | 状態 |
| --- | --- | --- | --- |
| Family OS | non-runtime な地図 | エージェントの縦軸へ、点線の案内専用経路を持つ | 公開・MIT |
| [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness)（公開・MIT） | 1エージェントにつき1つの縦軸基盤。完了を所有する | Self Growth Loop と trial 要求および終端結果をやり取りする | 実装済み |
| [context-kit](https://github.com/caty-ai/context-kit)（公開・MIT） | 単独利用可能な机まわりの装備 | 完了権限を持たずにエージェントを装備する | 実装済み |
| [Persona Engine](https://github.com/caty-ai/persona-engine)（公開・MIT） | 単独利用可能な人格の source / target | Persona Growth Loop と接続する | 実装済み |
| Persona Growth Loop（公開準備中） | 独立した人格成長ループ | Persona Engine との人格 source / target 関係が計画中。Self Growth Loop への governance 経路も計画中 | 計画中 |
| [X Collector](https://github.com/caty-ai/x-collector)（公開・MIT） | 単独利用可能で置き換え可能な外部情報源 | `family-feed` / sense を morning agents へ供給する | 実装済み |
| morning agents | 現在 / 既定の sense bridge | 収集した素材を Self Growth Loop 向けの proposal に変える | 実装済み |
| human / evaluator | 帰属可能な別入力 | Self Growth Loop へ別の入力を与えられる | 実装済みの入力形 |
| [Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT） | 能力成長ループ | proposal を受け取り、実装済みの trial / result の継ぎ目として Harness を使う。将来の人格成長に対しても governance 経路であり続ける | 実装済み |

<details>
<summary>テキスト版: 縦軸の旧 Mermaid ソース</summary>

```mermaid
flowchart TB
  OS["Family OS<br/>the whole map"]
  Caty["Caty Agent Harness<br/>vertical foundation — self growth from the work<br/>one per agent"]
  OS -.-|"navigation only"| Caty

  subgraph PersonaAxis["Growth of personality"]
    direction LR
    PersonaEngine["Persona Engine<br/>persona layers and a gradation of feeling<br/>usable on its own"]
    PersonaGrowth["Persona Growth Loop<br/>independent growth of personality<br/>planned"]
    PersonaEngine ---|"persona source / target"| PersonaGrowth
  end

  subgraph AbilityAxis["Growth of ability"]
    direction LR
    X["X Collector<br/>gathers information from outside<br/>usable on its own · replaceable"]
    Morning["morning agents"]
    SelfGrowth["Self Growth Loop<br/>independent growth of ability"]
    Other["human / evaluator<br/>attributable input"]
    X -->|"family-feed / sense"| Morning
    Morning -->|"proposal"| SelfGrowth
    Other -.->|"another input source"| SelfGrowth
  end

  Caty <==>|"implemented: trial / result"| SelfGrowth
  PersonaGrowth -.->|"planned: governance"| SelfGrowth
```

</details>

<a id="horizontal-axis-detail"></a>

### 横軸の詳細

![完全なエージェントの流れが FMA によってつながれ、Sitter が外側から handoff を見守る横軸トポロジ。正本は下の表](../assets/readme/horizontal-axis.svg)

| ノード | 役割 | 関係 | 状態 |
| --- | --- | --- | --- |
| Family OS | non-runtime な地図 | ファミリーの見取り図へ、点線の案内専用経路を持つ | 公開・MIT |
| Agent A / B / C | 独立した完全な縦軸の流れ | それぞれが実行権限を渡さずに FMA へ接続する | 代表トポロジ |
| [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 共有記憶と coordination 情報 | 完全なエージェントの流れをつなぎ、handoff へ共有文脈を供給する | 実装済み |
| delegated sub-agent work | メンバーの主経路の外へ渡される仕事 | 共有文脈を運び、停止について Sitter の観測対象になる | 実装済みの仕事形 |
| family nudges | メンバー間で交わされるメッセージ | 共有文脈を運び、返信欠落について Sitter の観測対象になる | 実装済みの仕事形 |
| [Sitter](https://github.com/caty-ai/sitter)（公開・MIT） | 独立した外側の観測者 | 期限を見守り、止まった handoff をエスカレーションする。ドメイン上の成功判定はしない | 実装済み |

<details>
<summary>テキスト版: 横軸の旧 Mermaid ソース</summary>

```mermaid
flowchart TB
  OS["Family OS<br/>the whole map"]

  subgraph Family["The AI agent family"]
    direction TB

    subgraph Members["each agent holds a complete vertical axis of its own"]
      direction LR
      A["Agent A<br/>foundation + chosen growth loops"]
      B["Agent B<br/>foundation + chosen growth loops"]
      C["Agent C<br/>foundation + chosen growth loops"]
    end

    FMA["FMA<br/>sharing and coordination across the family"]
    A --- FMA
    B --- FMA
    C --- FMA

    subgraph Handoff["work that gets handed over"]
      direction LR
      Sub["delegated sub-agent work"]
      Nudge["nudges between family members<br/>messages back and forth"]
    end

    Sitter["Sitter<br/>watches from outside for anything stalled"]
    FMA -.->|"shared context"| Handoff
    Sitter -.->|"watching / deadlines / escalation"| Handoff
  end

  OS -.-|"navigation only"| Family
```

</details>

---

<a id="edges"></a>

## どうつながっているか

今日この時点で実装済みのモジュール間エッジは2本だけです。それ以外は、まだ消費者のいない形か、家族の外側の誰かが所有する境界です。

```mermaid
flowchart LR
  SG["Self Growth Loop"]
  H["Caty Agent Harness"]
  S["Sitter"]
  P["Persona Growth Loop"]

  SG -->|"実装済み: tr-enqueue タスク要求"| H
  H -->|"実装済み・読み取り専用: 終端成果物"| SG
  H -.->|"提案: LaunchRequest 監督要求"| S
  S -.->|"提案: 判定を含まない証拠"| H
  P -.->|"計画中: 最小化された提案"| SG
```

実装済みの2本は、後続のすべてのエッジの雛形なので、よく読む価値があります。

- **要求は、次の判断を所有するモジュールへ向かって流れます。** Self Growth Loop はタスクを投入しますが、タスクの状態・試行番号・リトライ方針・DLQ には決して書き込みません。それらは基盤のものです。
- **証拠は、権限を移さずに戻ってきます。** 基盤は相関づけられた終端成果物を publish します。終端は、採用でも適用でも有効でもありません — それらは別の3者が持つ、別の3つの事実です。

要求と証拠は逆向きに流れ、どちらも権限を運びません。このページから1文だけ持ち帰るなら、この1文にしてください。

---

<a id="claim-states"></a>

## 主張の状態

[詳細仕様](reference.ja.md)のすべての記述は、4つの状態のいずれかを持ちます。飾りではなく、何の上に作ってよいかを決めるものです。

- **実装済み** — 今日存在し、証拠に裏付けられたインターフェース
- **決定済み** — 受け入れられた境界または慣行。コードがあるとは限らない
- **提案** — 形のみ。実装の承認ではない
- **不明** — 唯一の権限者が答えるまで、いかなる事実も推論してはならない

提案のエッジは、その契約所有者がバージョン交渉・移行・ロールバックまたはダウングレードの挙動を記録するまで、消費者を持てません。形を「進んでよい合図」と読むのが、ここで最も高くつく間違いです。

---

<a id="never"></a>

## Family OS が決してしないこと

これらは現時点の制約ではなく、構造上の拒否です。プロジェクトが大きくなっても失効しません。

- **runtime へのエッジを持ちません。** Family OS からも掟からも、runtime モジュールへ向かう矢印は1本もありません。足した時点で地図は制御装置になります。
- **権限を奪いません。** 他モジュールの事実を描画しても、その事実の所有権は動きません。
- **完了を捏造しません。** 任意や提案のエッジが存在しないとき、結果はローカルの進捗の保持か `unknown` であり、合成された成功ではありません。
- **秘密を持ちません。** 認証情報・スケジューラ・break-glass の経路は、そのデプロイを所有する人のものです。

いちばん被害が大きいのは曖昧な語です。`returned` `ack` `delivered` `healthy` `adopted` `applied` `effective` にはそれぞれ所有者がちょうど1人おり、[詳細仕様](reference.ja.md#vocabulary)で意図的に分割してあります。

---

<a id="removal"></a>

## 1つ外したらどうなるか

境界が本物かどうかを試すいい方法は、そのモジュールを消して何が実際に壊れるかを問うことです。

| 外すもの | 失うもの | 残るもの |
| --- | --- | --- |
| Family OS | 連携の見通し | すべての runtime モジュール（無傷） |
| Family Dev Handbook | 開発の指針 | runtime の稼働 |
| Family Memory Architecture | 共有記憶と check-in の観測 | 各モジュール自身のドメイン状態 |
| Sitter | 任意の外部監督 | 基盤のタスク意味論とローカルの失敗時の姿勢 |
| Self Growth Loop | 成長のガバナンスと解釈 | 基盤の中のタスクと証拠 |
| Persona Growth Loop | 将来の提案入力 | いま動いているものすべて |

この表の上半分は、どれも runtime の状態を道連れにしません。層を分けている理由がまさにそこです。

---

<a id="compatibility"></a>

## 使える環境

地図を読むだけなら Markdown ビューアがあれば足ります。下の表は、地図が指しているモジュールについてのものです。

| 観点 | 対応 |
| --- | --- |
| この地図を読む | ✅ macOS ／ ✅ Windows ／ ✅ Linux |
| 実運用が確認できているAIエージェント環境 | ✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw |
| 対応検証を予定している環境 | ⚠️ Kimi Code ／ ⚠️ Codex |

> **メモ:** 「実運用が確認できている」は、その環境で関連する仕組みを実際に動かしているという意味で、Family OS の全モジュールへの完全対応を保証するものではありません。2026-07-28 時点の実測です。モジュールごとの対応状況は、各モジュールの README が正本です。

---

<a id="reading-on"></a>

## 次に読むもの

| 読みたいこと | 行き先 |
| --- | --- |
| 正確な契約 — 権限・エッジ・失敗時の扱い | [詳細仕様](reference.ja.md) |
| 5段階の成長モデルと believe-to-build 対応 | [成長モデル](growth-model.ja.md) |
| 一緒に使うと効く、私たちが作ったものではない部品 | [推奨スタック](recommended-stack.ja.md) |
| このREADMEと画像の視覚ルール | [README visual system](readme-visual-system.md)（英語） |
