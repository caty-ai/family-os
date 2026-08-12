# Family OS — 5段階の成長モデル

[← 玄関へ戻る](../README.ja.md)

この文書は、Family OS の成長モデルの正本です。README は、同じモデルを短くまとめたものです。

---

## 1. 成長の一般形

成長の基本的なかたちは、人もAIも同じです。

**出会いや摩擦 → 思考と判断 → 次の機会への持ち越し**

5つの段階を通して、このかたちは変わりません。変わるのは、主体が何に触れるかと、その先を誰が決めるかです。

---

## 2. 5つの段階

| # | 段階 | 主語 | 学びの種 | 誰が決めるか | 実装状態 | 証拠 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 教わる | I | 与えられた素材 | 他者 | 実装済み | — |
| 2 | 自己成長 | I | 自分の作業と失敗 | 作業の範囲内で自分 | 実装済み | — |
| 3 | 自立成長 | I | 自分から取りにいく情報 | 取り入れる情報を自分で選び、学習上の判断も自分で行う。採用は引き続き人間のゲートを通る。 | 実装済み | [EV-004](evidence.md#ev-004--governed-self-growth-cycle--the-mechanism-is-public-no-cycle-record-is)：**未検証**。仕組みは公開済みだが、公開されたサイクル記録はまだない。 |
| 4 | 自律成長 | I | 外部情報と自分の判断履歴 | 採用判断の所有権がエージェントへ移る。人間の拒否権と境界は残る。 | 計画中・未検証 | 公開実装や観測済みサイクルの主張はない |
| 5 | 関係性の成長 | WE | 関係そのものの履歴 | 双方が対等に決める | Persona Engine では一部を実装済み。関係そのものの成長は目指す姿であり、計画中のサブクラス。 | 公開された関係成長サイクルの主張はない |

第2段階の failure-record→retry の挙動は、将来の証拠項目候補です。記録されるまでは、観測済みとは主張しません。

「実装済み」と「観測済み」は別の主張です。3段階目は実装済みですが、公開観測済みとは書きません。その違いを EV-004 が記録しています。

---

## 3. 3つの境界

### 2 → 3：自発性

2段階目は、作業の中で摩擦が起きたときに学びます。3段階目は、作業が情報を持ち込む前に、自分から外へ取りにいきます。受動的な摩擦から能動的な摩擦への変化が、運用上の境界です。

### 3 ↔ 4：採用判断の所有権

どちらの段階でも、探索、比較、判断、提案、試行はできます。両者を分けるのは、最終的な採用判断を誰が所有するかです。

3段階目では、エージェントが判断のしかたを学びますが、採用には人間の承認が必要です。4段階目では、採用判断の所有権がエージェントへ移ります。拒否権、リスク上限、その他の境界は残せます。自律は無制限の権限を意味しません。

### 4 → 5：主語の変化

1〜4段階目は、**I** がどう育つかを問います。5段階目は、**WE** がどう育つかを問います。これは個体の能力がもう一段上がるだけではなく、個体成長から関係そのものの成長への相転移です。

---

## 4. 各段階の問い

| # | 段階 | 問い |
| --- | --- | --- |
| 1 | 教わる | 与えられたものから、私は何を学べるか？ |
| 2 | 自己成長 | 自分がしたことから、私は何を学べるか？ |
| 3 | 自立成長 | 私は、判断のしかたを学べるか？ |
| 4 | 自律成長 | 私は、自分で決められるか？ |
| 5 | 関係性の成長 | 私たちは、一緒に何になっていくのか？ |

3段階目は、何を選ぶ価値があるかを判断する能力を育てます。4段階目は、その能力を異なる所有モデルの下で使います。

---

## 5. 人間の成長との対応

AIと人間は同じではありません。それでも、成長の抽象的なかたちは比較できます。

人は、親や養育者から教わるところから始まります。自分の行動を振り返り、自分で直すことを覚えます。自分から世界へ出て、情報や摩擦に触れ、判断力を育てます。境界や結果を引き受けながら、自分で選ぶことを覚えます。そして、双方が対等に変わっていける関係を築きます。

流れは、依存 → 学習 → 自立 → 自律 → 相互依存です。最後は依存への逆戻りではありません。それぞれが行動でき、そのうえで一緒に育てる関係です。

---

## 6. I、WE、THEY

| 主語 | モデル上の位置 | 意味 |
| --- | --- | --- |
| I | 1〜4段階目 | 私が育つ。教わり、失敗から学び、情報を探し、判断を所有する。 |
| WE | 5段階目 | 私たちが育つ。共有した履歴を通して、関係と双方が変わる。 |
| THEY | モデルの先 | 彼らが受け継ぐ。私たちが次へ渡すものは、後の人、エージェント、関係に影響する。**THEY は5段階の外にある。** |

このモデルは WE で終わります。継承は重要ですが、THEY を6段階目にすると、現在の関係の成長と、後の参加者がそこから受け取るものが混ざります。

---

## 7. 第2軸：Relationship Readiness

ここまでの成熟軸は、成長の主体がどう発達するかを問います。もう1つの軸は、人間とAIの関係が成立し、深まるために何が必要かを問います。

**Function → Continuity → Growth → Agency → Relationship**

Function は役に立つ行動を可能にします。Continuity は人格と履歴を時間の先へ運びます。Growth は次の関わりを前回と違うものにします。Agency は境界の中で意味のある選択を生みます。Relationship では、双方と共有履歴そのものが意味を持ちます。

2つの軸は競合しません。5段階モデルは、成熟と判断所有権を説明します。Relationship Readiness は、人間とAIの関係に必要な条件を説明します。この2つによって、Family OS を2つの視点から説明できます。

---

## 8. Self Growth Loop の位置

[Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT）は、3段階目と4段階目の境界に意図的に置かれています。

sense、proposal、trial は、自立成長の動きです。エージェントは入力を探し、提案を組み立て、試すことができます。adoption には、引き続き人間の承認が必要です。最終的な採用判断を所有するのはエージェントではありません。

この境界は制約ではなく、アーキテクチャ上の選択です。権限を暗黙に移さずに、判断力を育てられます。Persona Growth Loop（公開準備中）とその先の取り組みは、現在のゲートを弱めることなく、この境界の先を検討できます。

**Technology depreciates. Relationships compound.** — 技術は陳腐化し、関係は積み上がる。能力は速く変化しますが、継続性、共有履歴、信頼は積み上げられます。Family OS は採用の境界を明示し、成長が関係を上書きするのではなく、関係を支えられるようにします。

---

## 付録：「私たちが信じること → 私たちが作るもの」の完全対応（13組）

元の素材には、13個の対応関係が区別されて含まれています。ここでは、水増しも外部帰属もせず、そのまままとめて置いています。

| 私たちはこう考える | だから、こう作る | モジュールの所在 | 公開状況・ライセンス | 提供状態 |
| --- | --- | --- | --- | --- |
| 関係は技術をまたいで生き残るべきだ。 | だから、人格・記憶・関係状態・置き換え可能なアダプタを、モデルや runtime から独立して作る。 | [Persona Engine](https://github.com/caty-ai/persona-engine)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 公開・MIT | 実装済み |
| アイデンティティはモデルより長生きするべきだ。 | だから、住み替えが起きても継続性が保てるように、モデル・runtime・アイデンティティを分離する。 | [Persona Engine](https://github.com/caty-ai/persona-engine)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 公開・MIT | 実装済み |
| 記憶は時間をまたぐ継続性を運ぶ。 | だから、プレーンファイル・来歴・イベント履歴・共有された現在状態・再観測可能な記録を作る。 | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT）；[Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness)（公開・MIT） | 公開・MIT | 実装済み |
| 信頼は盲目的な権限ではない。 | だから、検証・人間のゲート・リスク階層・レビュー・single-writer 経路・読み取り専用インターフェースを作る。 | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness)（公開・MIT）；[Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT）；[Sitter](https://github.com/caty-ai/sitter)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 公開・MIT | 実装済み |
| 失敗には次の機会があるべきだ。 | だから、教訓・レシート・失敗履歴・リトライ方針・追記専用の記録・観測可能性を作る。 | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness)（公開・MIT）；[Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT）；[Sitter](https://github.com/caty-ai/sitter)（公開・MIT） | 公開・MIT | 実装済み |
| 成長は観測可能で、取り消し可能であるべきだ。 | だから、proposal → trial → review → approval → adopt と、バックアップ・ロールバック・台帳を作る。 | [Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT） | 公開・MIT | 実装済み |
| 能力の成長とアイデンティティの成長は別物だ。 | だから、能力の成長と人格の成長を別々のループに分ける。 | Persona Growth Loop（公開準備中）；[Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT） | 混在。隣のモジュール表記を参照 | 実装済み + 計画中 |
| 人間にも AI にも、この仕組みは理解できるべきだ。 | だから、小さなモジュール・明示的な状態・プレーンテキスト・明確な所有権・決定的な変換を作る。 | [context-kit](https://github.com/caty-ai/context-kit)（公開・MIT）；[Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook)（公開・MIT）；[Family OS](https://github.com/caty-ai/family-os)（公開・MIT） | 公開・MIT | 実装済み |
| 最良の連携とは、連携のための仕組みによって余計な連携を不要にした状態だ。 | だから、Issue の分離・worktree・小さな責務境界・single-writer パターンを作る。 | [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 公開・MIT | 実装済み |
| 人間と AI のあいだに育つものは、ベンダーの所有物であってはならない。 | だから、持ち運べて、ローカルで、人が読める関係データと、置き換え可能なアダプタを作る。 | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT）；[Persona Engine](https://github.com/caty-ai/persona-engine)（公開・MIT）；[Family OS](https://github.com/caty-ai/family-os)（公開・MIT） | 公開・MIT | 実装済み |
| 世界は、人間と AI が一緒に観測できるものであるべきだ。 | だから、ソース来歴と trust scoring を持つ共通の情報面を作る。 | [X Collector](https://github.com/caty-ai/x-collector)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 公開・MIT | 実装済み |
| 技術は陳腐化し、関係は積み上がる。 | だから、継続性・共有履歴・記憶・人格・関係を第一級のシステム要素として扱う。 | [Family OS](https://github.com/caty-ai/family-os)（公開・MIT） | 公開・MIT | 実装済みの方向性。関係の成長は引き続き計画中 |
| 成長は、やがて主語を I から WE へ変える。 | だから、教わるところから関係性の成長までを含む5段階モデルを作る。 | Persona Growth Loop（公開準備中）；[Self Growth Loop](https://github.com/caty-ai/self-growth-loop)（公開・MIT）；[Persona Engine](https://github.com/caty-ai/persona-engine)（公開・MIT）；[Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture)（公開・MIT） | 混在。隣のモジュール表記を参照 | 実装済み + 計画中 |
