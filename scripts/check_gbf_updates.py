import hashlib
import html as html_lib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

STATE_FILE = ".gbf-update-state.json"
OUTPUT_FILE = "gbf-update-report.md"
INDEX_FILE = "index.html"

SOURCES = [
    {
        "name": "グランブルーファンタジー公式",
        "url": "https://granbluefantasy.jp/news/",
    },
]

# 「仕組み・用語」に関係する可能性が高い語
SYSTEM_KEYWORDS = [
    # 武器・スキル
    "スキル",
    "武器スキル",
    "スキル効果",
    "スキルLv",
    "スキルレベル",
    "攻刃",
    "守護",
    "神威",
    "渾身",
    "背水",
    "技巧",
    "堅守",
    "進境",
    "与ダメージ",
    "ダメージ上限",
    "奥義性能",
    "アビリティダメージ",
    "禁呪",
    "魔蝕",
    "退魔Lv",
    "深度",

    # 編成
    "編成",
    "武器編成",
    "召喚石編成",
    "専用編成",
    "メイン武器",
    "サブ加護",
    "加護効果",

    # バトル
    "バトルシステム",
    "新バトル",
    "予兆",
    "予兆解除",
    "ガード",
    "フェイタルチェイン",
    "特殊技",
    "特殊行動",
    "CT",
    "弱体効果",
    "強化効果",
    "フルオート",
    "オートガード",
    "クイック召喚",

    # 育成
    "育成",
    "限界超越",
    "上限解放",
    "覚醒",
    "LB",
    "EXLB",
    "マスターレベル",
    "極致の証",

    # ジョブ
    "ジョブ",
    "Class.",
    "クラス5",
    "オリジンジョブ",
    "マナベリ",

    # 十天衆・十賢者
    "十天衆",
    "十賢者",
    "アーカルム",
    "ソロモナス",
    "探索Lv",
    "アーカルムの祝福",
    "祝福の輪煌",

    # 召喚石
    "召喚石",
    "加護",
    "メイン加護",
    "サブ加護",
    "サポーター召喚石",

    # マルチ・報酬システム
    "マルチバトル",
    "貢献度",
    "青箱",
    "赤箱",
    "緑箱",
    "自発",
    "救援",

    # 周回・便利機能
    "Pro",
    "まとめてPro",
    "スキップ",
    "周回",
    "AP",
    "BP",

    # 古戦場などのゲームシステム
    "SWARM",
    "古戦場",
    "HELL",

    # 新しいシステムを拾うための一般語
    "新機能",
    "新システム",
    "新たな機能",
    "新要素",
    "仕様変更",
    "調整",
    "変更します",
    "追加します",
    "実装します",
]

# これだけなら攻略ノートには基本不要
IGNORE_KEYWORDS = [
    "レジェンドフェス",
    "グランデフェス",
    "スターレジェンド",
    "スタレ",
    "サプライズ！！スペシャルガチャセット",
    "サプチケ",
    "ピックアップ",
    "出現率アップ",
    "新キャラクター",
    "新キャラ",
    "キャラクター紹介",
    "スキンセット",
    "コスチューム",
    "ログインボーナス",
    "ログインキャンペーン",
    "無料10連",
    "無料ガチャ",
    "キャンペーン開催",
    "半額キャンペーン",
    "プレゼント",
    "キャラクターソング",
    "グッズ",
    "CD",
    "Blu-ray",
]

# これらが含まれる場合はIGNORE対象でも残す
IMPORTANT_OVERRIDE = [
    "スキル",
    "仕様変更",
    "新機能",
    "新システム",
    "バトルシステム",
    "編成",
    "加護",
    "限界超越",
    "新たな機能",
    "新要素",
]


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 GBF-Guide-Update-Checker/2.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_html(raw_html):
    raw_html = re.sub(
        r"<script.*?</script>",
        "",
        raw_html,
        flags=re.S | re.I,
    )

    raw_html = re.sub(
        r"<style.*?</style>",
        "",
        raw_html,
        flags=re.S | re.I,
    )

    text = re.sub(r"<[^>]+>", "\n", raw_html)
    text = html_lib.unescape(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def digest(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


def load_existing_guide():
    if not os.path.exists(INDEX_FILE):
        return ""

    try:
        with open(
            INDEX_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            return f.read()
    except Exception:
        return ""


def normalize(value):
    value = html_lib.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", "", value)
    return value.lower()


def is_ignored(block):
    lower = block.lower()

    has_ignore = any(
        word.lower() in lower
        for word in IGNORE_KEYWORDS
    )

    if not has_ignore:
        return False

    has_override = any(
        word.lower() in lower
        for word in IMPORTANT_OVERRIDE
    )

    return not has_override


def system_score(block):
    lower = block.lower()
    score = 0
    found = []

    for keyword in SYSTEM_KEYWORDS:
        if keyword.lower() in lower:
            score += 1
            found.append(keyword)

    return score, found


def extract_relevant(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    results = []
    seen = set()

    for i, line in enumerate(lines):
        line_score, _ = system_score(line)

        if line_score == 0:
            continue

        # 前後の文章も一緒に見る
        start = max(0, i - 2)
        end = min(len(lines), i + 4)

        block = "\n".join(lines[start:end]).strip()

        if is_ignored(block):
            continue

        score, keywords = system_score(block)

        # 単なる「武器」「召喚石」だけでは拾わない。
        # 仕組みを示す語が最低1つ必要。
        if score < 1:
            continue

        key = normalize(block)

        if not key or key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "text": block,
                "keywords": sorted(set(keywords)),
                "score": score,
            }
        )

    # 関連度が高いものを優先
    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return results[:40]


def classify_candidate(item, guide_html):
    """
    厳密なAI判定ではなく、
    index.html内に関連語が既に存在するかを確認して
    Issue上で確認しやすく分類する。
    """

    normalized_guide = normalize(guide_html)

    existing = []

    for keyword in item["keywords"]:
        normalized_keyword = normalize(keyword)

        if (
            normalized_keyword
            and normalized_keyword in normalized_guide
        ):
            existing.append(keyword)

    text = item["text"]

    lesson_signals = [
        "新システム",
        "バトルシステム",
        "新機能",
        "新要素",
        "仕様変更",
        "編成",
        "限界超越",
    ]

    if existing:
        return (
            "既存用語・Lessonの修正候補",
            existing,
        )

    if any(
        signal in text
        for signal in lesson_signals
    ):
        return (
            "Lesson追加候補",
            [],
        )

    return (
        "新規用語候補",
        [],
    )


def build_report(changes, guide_html):
    sections = {
        "新規用語候補": [],
        "既存用語・Lessonの修正候補": [],
        "Lesson追加候補": [],
    }

    for change in changes:
        for item in change["items"]:
            category, existing = classify_candidate(
                item,
                guide_html,
            )

            sections[category].append(
                {
                    "source_name": change["name"],
                    "source_url": change["url"],
                    "text": item["text"],
                    "keywords": item["keywords"],
                    "existing": existing,
                }
            )

    report = [
        "# グラブル攻略ノート 更新候補",
        "",
        "公式情報の変更から、"
        "「用語・仕組み」に関係する可能性がある内容だけを抽出しました。",
        "",
        "## 判定ルール",
        "",
        "- 新キャラ・新武器そのものの追加は原則対象外",
        "- ガチャ・イベント・キャンペーン情報は原則対象外",
        "- 新しい武器スキルやゲームシステムは対象",
        "- 既存の用語・仕組みの仕様変更は対象",
        "- このIssueだけでは index.html を自動変更しない",
        "- 内容確認後、必要なものだけ攻略ノートへ反映する",
        "",
    ]

    total = 0

    for category in [
        "新規用語候補",
        "既存用語・Lessonの修正候補",
        "Lesson追加候補",
    ]:
        items = sections[category]

        if not items:
            continue

        report.extend(
            [
                f"## {category}",
                "",
            ]
        )

        for item in items:
            total += 1

            report.extend(
                [
                    f"### 候補 {total}",
                    "",
                    f"**検出語:** "
                    f"{', '.join(item['keywords'])}",
                    "",
                ]
            )

            if item["existing"]:
                report.extend(
                    [
                        "**攻略ノート内で確認できた関連語:** "
                        + ", ".join(item["existing"]),
                        "",
                    ]
                )

            report.extend(
                [
                    "```text",
                    item["text"],
                    "```",
                    "",
                    f"出典: {item['source_name']}",
                    "",
                    f"Source: {item['source_url']}",
                    "",
                ]
            )

    if total == 0:
        report.extend(
            [
                "今回、攻略ノートに関係する"
                "用語・仕組みの更新候補はありませんでした。",
                "",
            ]
        )

    return "\n".join(report), total


def main():
    old_state = load_state()
    new_state = {}
    changes = []

    guide_html = load_existing_guide()

    for source in SOURCES:
        name = source["name"]
        url = source["url"]

        try:
            raw_html = fetch(url)
            text = clean_html(raw_html)
            current_hash = digest(text)

            previous_hash = old_state.get(
                url,
                {},
            ).get("hash")

            new_state[url] = {
                "name": name,
                "hash": current_hash,
                "checked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            # 初回実行では基準状態を保存するだけ
            if not previous_hash:
                print(
                    f"初回状態を保存: {name}"
                )
                continue

            # ページ自体に変化がなければ解析不要
            if previous_hash == current_hash:
                print(
                    f"変更なし: {name}"
                )
                continue

            relevant = extract_relevant(text)

            if relevant:
                changes.append(
                    {
                        "name": name,
                        "url": url,
                        "items": relevant,
                    }
                )
            else:
                print(
                    f"ページ変更あり・攻略ノート対象候補なし: {name}"
                )

        except Exception as e:
            print(
                f"確認失敗: {name}: {e}"
            )

            # 取得失敗時に以前の状態を消さない
            if url in old_state:
                new_state[url] = old_state[url]

    save_state(new_state)

    if not changes:
        print(
            "攻略ノートに追加・修正する"
            "用語/仕組みの候補はありません。"
        )
        return

    report, candidate_count = build_report(
        changes,
        guide_html,
    )

    if candidate_count == 0:
        print(
            "攻略ノートに追加・修正する"
            "用語/仕組みの候補はありません。"
        )
        return

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    print(
        f"攻略ノート更新候補: {candidate_count}件"
    )
    print(
        "UPDATE_FOUND=true"
    )


if __name__ == "__main__":
    main()
