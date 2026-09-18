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

# =========================================================
# 攻略ノートで監視する「用語・仕組み」
# =========================================================

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
    "予兆",
    "予兆解除",
    "ガード",
    "フェイタルチェイン",
    "特殊技",
    "特殊行動",
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
    "マスターレベル",
    "極致の証",

    # ジョブ
    "ジョブ",
    "Class.",
    "クラス5",
    "オリジンジョブ",
    "マナベリ",

    # 十天衆・十賢者・アーカルム
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

    # マルチ
    "マルチバトル",
    "貢献度",
    "青箱",
    "赤箱",
    "緑箱",
    "自発",
    "救援",

    # 周回・便利機能
    "まとめてPro",
    "スキップ",
    "周回",

    # 古戦場など
    "SWARM",
    "古戦場",
    "HELL",

    # 新しい仕組み
    "新機能",
    "新システム",
    "新たな機能",
    "新要素",
    "仕様変更",
    "バランス調整",
    "機能追加",
]


# 短い用語。
# 普通の部分一致では誤検出しやすいので別処理する。
SHORT_KEYWORDS = [
    "CT",
    "LB",
    "EXLB",
    "AP",
    "BP",
    "Pro",
]


# =========================================================
# 明らかに攻略ノートの更新対象ではないもの
# =========================================================

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
    "半額キャンペーン",
    "プレゼント",
    "キャラクターソング",
    "グッズ",
    "Blu-ray",
    "CD",
]


# 公式サイトのメニュー等。
# これらだけの行は完全に無視する。
NAVIGATION_WORDS = {
    "news",
    "world",
    "character",
    "system",
    "interview",
    "channel",
    "special",
    "about",
    "top",
    "menu",
    "home",
    "game",
    "story",
    "contents",
    "information",
    "official",
    "twitter",
    "youtube",
    "x",
    "close",
    "open",
    "next",
    "prev",
    "back",
}


# 除外語を含んでいても、
# 本当に仕様の話なら候補として残す。
IMPORTANT_OVERRIDE = [
    "武器スキル",
    "スキル効果",
    "仕様変更",
    "新機能",
    "新システム",
    "新たな機能",
    "新要素",
    "バトルシステム",
    "機能追加",
    "加護効果",
    "限界超越",
]


# =========================================================
# 通信
# =========================================================

def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 GBF-Guide-Update-Checker/3.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="ignore",
        )


# =========================================================
# HTML整理
# =========================================================

def clean_html(raw_html):
    raw_html = re.sub(
        r"<script\b[^>]*>.*?</script>",
        "",
        raw_html,
        flags=re.S | re.I,
    )

    raw_html = re.sub(
        r"<style\b[^>]*>.*?</style>",
        "",
        raw_html,
        flags=re.S | re.I,
    )

    raw_html = re.sub(
        r"<!--.*?-->",
        "",
        raw_html,
        flags=re.S,
    )

    text = re.sub(
        r"<[^>]+>",
        "\n",
        raw_html,
    )

    text = html_lib.unescape(text)
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text,
    )

    return text.strip()


# =========================================================
# 基本処理
# =========================================================

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

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value.lower()


# =========================================================
# ナビゲーション除外
# =========================================================

def is_navigation_line(line):
    cleaned = line.strip()

    if not cleaned:
        return True

    # URLだけ
    if re.fullmatch(
        r"https?://\S+",
        cleaned,
        flags=re.I,
    ):
        return True

    # 記号だけ
    if not re.search(
        r"[A-Za-z0-9ぁ-んァ-ヶ一-龠]",
        cleaned,
    ):
        return True

    # 英字メニュー1語
    lowered = cleaned.lower()

    if lowered in NAVIGATION_WORDS:
        return True

    # "NEWS | WORLD | CHARACTER" のようなメニュー
    menu_parts = [
        part.strip().lower()
        for part in re.split(
            r"[/|｜・>\s]+",
            cleaned,
        )
        if part.strip()
    ]

    if (
        menu_parts
        and len(menu_parts) <= 10
        and all(
            part in NAVIGATION_WORDS
            for part in menu_parts
        )
    ):
        return True

    return False


def prepare_lines(text):
    result = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if is_navigation_line(line):
            continue

        result.append(line)

    return result


# =========================================================
# キーワード判定
# =========================================================

def contains_short_keyword(text, keyword):
    """
    CTなどの短い英字語が
    CHARACTER等の一部として誤検出されないようにする。
    """

    pattern = (
        r"(?<![A-Za-z0-9])"
        + re.escape(keyword)
        + r"(?![A-Za-z0-9])"
    )

    return bool(
        re.search(
            pattern,
            text,
            flags=re.I,
        )
    )


def find_keywords(text):
    found = []

    lower = text.lower()

    for keyword in SYSTEM_KEYWORDS:
        if keyword.lower() in lower:
            found.append(keyword)

    for keyword in SHORT_KEYWORDS:
        if contains_short_keyword(
            text,
            keyword,
        ):
            found.append(keyword)

    return sorted(
        set(found),
        key=str.lower,
    )


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


# =========================================================
# 「単なる商品追加」と「仕組み変更」の区別
# =========================================================

def looks_like_plain_item_announcement(block):
    """
    新武器・新召喚石・新キャラが登場しただけのニュースを除外。
    新スキルや仕様変更を伴う場合は除外しない。
    """

    announcement_words = [
        "新武器",
        "新たな武器",
        "武器が登場",
        "武器を追加",
        "新召喚石",
        "新たな召喚石",
        "召喚石が登場",
        "召喚石を追加",
        "新キャラクター",
        "新キャラ",
    ]

    system_change_words = [
        "武器スキル",
        "スキル効果",
        "新スキル",
        "新たなスキル",
        "新機能",
        "新システム",
        "新要素",
        "仕様変更",
        "機能追加",
        "バトルシステム",
        "加護効果",
        "限界超越",
    ]

    has_announcement = any(
        word in block
        for word in announcement_words
    )

    has_system_change = any(
        word in block
        for word in system_change_words
    )

    return (
        has_announcement
        and not has_system_change
    )


# =========================================================
# 候補抽出
# =========================================================

def extract_relevant(text):
    lines = prepare_lines(text)

    results = []
    seen = set()

    for i, line in enumerate(lines):
        line_keywords = find_keywords(line)

        if not line_keywords:
            continue

        # 単独の短い単語だけでは候補にしない
        if (
            len(line) <= 8
            and all(
                keyword in SHORT_KEYWORDS
                for keyword in line_keywords
            )
        ):
            continue

        # 前後1行だけを付ける。
        # 前回より範囲を狭くして
        # 無関係なメニュー等を巻き込まない。
        start = max(
            0,
            i - 1,
        )

        end = min(
            len(lines),
            i + 2,
        )

        block_lines = lines[
            start:end
        ]

        block_lines = [
            item
            for item in block_lines
            if not is_navigation_line(item)
        ]

        block = "\n".join(
            block_lines
        ).strip()

        if not block:
            continue

        if is_ignored(block):
            continue

        if looks_like_plain_item_announcement(
            block
        ):
            continue

        keywords = find_keywords(block)

        if not keywords:
            continue

        # 短語しか見つかっていない場合は
        # ある程度の説明文が必要
        long_keywords = [
            keyword
            for keyword in keywords
            if keyword not in SHORT_KEYWORDS
        ]

        if (
            not long_keywords
            and len(block) < 25
        ):
            continue

        key = normalize(block)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "text": block,
                "keywords": keywords,
                "score": len(keywords),
            }
        )

    results.sort(
        key=lambda item: (
            item["score"],
            len(item["text"]),
        ),
        reverse=True,
    )

    return results[:30]


# =========================================================
# 既存攻略ノートとの比較
# =========================================================

def keyword_exists_in_guide(
    keyword,
    guide_html,
):
    if not guide_html:
        return False

    if keyword in SHORT_KEYWORDS:
        return contains_short_keyword(
            guide_html,
            keyword,
        )

    return (
        normalize(keyword)
        in normalize(guide_html)
    )


def classify_candidate(
    item,
    guide_html,
):
    existing = []

    for keyword in item["keywords"]:
        if keyword_exists_in_guide(
            keyword,
            guide_html,
        ):
            existing.append(keyword)

    lesson_signals = [
        "新システム",
        "バトルシステム",
        "新機能",
        "新たな機能",
        "新要素",
        "仕様変更",
        "機能追加",
        "限界超越",
    ]

    if existing:
        return (
            "既存用語・Lessonの修正候補",
            existing,
        )

    if any(
        signal in item["text"]
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


# =========================================================
# Issue用レポート
# =========================================================

def build_report(
    changes,
    guide_html,
):
    sections = {
        "新規用語候補": [],
        "既存用語・Lessonの修正候補": [],
        "Lesson追加候補": [],
    }

    unique_candidates = set()

    for change in changes:
        for item in change["items"]:
            candidate_key = normalize(
                item["text"]
            )

            if candidate_key in unique_candidates:
                continue

            unique_candidates.add(
                candidate_key
            )

            category, existing = (
                classify_candidate(
                    item,
                    guide_html,
                )
            )

            sections[category].append(
                {
                    "source_name":
                        change["name"],
                    "source_url":
                        change["url"],
                    "text":
                        item["text"],
                    "keywords":
                        item["keywords"],
                    "existing":
                        existing,
                }
            )

    report = [
        "# グラブル攻略ノート 更新候補",
        "",
        "公式情報の変更から、"
        "攻略ノートの「用語・仕組み」に"
        "関係する可能性がある内容を抽出しました。",
        "",
        "## 対象",
        "",
        "- 新しい武器スキル",
        "- 新しいゲームシステム",
        "- バトル・編成・育成・召喚石などの新しい仕組み",
        "- 既存の用語・仕組みの仕様変更",
        "",
        "## 原則対象外",
        "",
        "- 新キャラクターそのもの",
        "- 新武器そのもの",
        "- 新召喚石そのもの",
        "- ガチャ",
        "- キャンペーン",
        "- グッズ等のお知らせ",
        "",
        "※ このIssueから index.html を"
        "自動変更することはありません。",
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
                    "**検出語:** "
                    + ", ".join(
                        item["keywords"]
                    ),
                    "",
                ]
            )

            if item["existing"]:
                report.extend(
                    [
                        "**攻略ノート内の関連語:** "
                        + ", ".join(
                            item["existing"]
                        ),
                        "",
                    ]
                )

            report.extend(
                [
                    "```text",
                    item["text"],
                    "```",
                    "",
                    "出典: "
                    + item["source_name"],
                    "",
                    "Source: "
                    + item["source_url"],
                    "",
                ]
            )

    return (
        "\n".join(report),
        total,
    )


# =========================================================
# メイン処理
# =========================================================

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

            # 初回は基準状態を保存
            if not previous_hash:
                print(
                    f"初回状態を保存: {name}"
                )
                continue

            if previous_hash == current_hash:
                print(
                    f"変更なし: {name}"
                )
                continue

            relevant = extract_relevant(
                text
            )

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
                    "ページ変更あり・"
                    "用語/仕組み候補なし: "
                    + name
                )

        except Exception as error:
            print(
                f"確認失敗: {name}: {error}"
            )

            # 通信失敗時に前回状態を消さない
            if url in old_state:
                new_state[url] = (
                    old_state[url]
                )

    save_state(new_state)

    if not changes:
        print(
            "攻略ノートに追加・修正する"
            "用語/仕組みの候補はありません。"
        )
        return

    report, candidate_count = (
        build_report(
            changes,
            guide_html,
        )
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
        "攻略ノート更新候補: "
        f"{candidate_count}件"
    )

    print(
        "UPDATE_FOUND=true"
    )


if __name__ == "__main__":
    main()
