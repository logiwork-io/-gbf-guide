import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

STATE_FILE = ".gbf-update-state.json"
OUTPUT_FILE = "gbf-update-report.md"

SOURCES = [
    {
        "name": "グランブルーファンタジー公式",
        "url": "https://granbluefantasy.jp/news/",
    },
]

KEYWORDS = [
    "アップデート",
    "新機能",
    "新コンテンツ",
    "武器",
    "召喚石",
    "ジョブ",
    "十天衆",
    "十賢者",
    "アーカルム",
    "古戦場",
    "バトル",
    "マルチバトル",
    "スキル",
    "ダメージ",
    "フルオート",
    "限界超越",
    "Pro",
]


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 GBF-Guide-Update-Checker/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_html(html):
    html = re.sub(
        r"<script.*?</script>",
        "",
        html,
        flags=re.S | re.I,
    )
    html = re.sub(
        r"<style.*?</style>",
        "",
        html,
        flags=re.S | re.I,
    )
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\n+", "\n", text)

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


def extract_relevant(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    matches = []

    for i, line in enumerate(lines):
        if any(
            keyword.lower() in line.lower()
            for keyword in KEYWORDS
        ):
            start = max(0, i - 1)
            end = min(len(lines), i + 3)

            block = "\n".join(lines[start:end])

            if block not in matches:
                matches.append(block)

    return matches[:30]


def main():
    old_state = load_state()
    new_state = {}
    changes = []

    for source in SOURCES:
        name = source["name"]
        url = source["url"]

        try:
            html = fetch(url)
            text = clean_html(html)
            current_hash = digest(text)

            previous_hash = old_state.get(
                url,
                {},
            ).get("hash")

            relevant = extract_relevant(text)

            new_state[url] = {
                "name": name,
                "hash": current_hash,
                "checked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            if (
                previous_hash
                and previous_hash != current_hash
            ):
                changes.append(
                    {
                        "name": name,
                        "url": url,
                        "items": relevant,
                    }
                )

        except Exception as e:
            print(
                f"確認失敗: {name}: {e}"
            )

    save_state(new_state)

    if not changes:
        print(
            "新しい更新候補はありません。"
        )
        return

    report = [
        "# グラブル攻略ノート 更新候補",
        "",
        "公式サイトに変更を検出しました。",
        "",
        "※ この結果だけで攻略ノートを"
        "自動更新しないでください。",
        "内容を確認してから反映してください。",
        "",
    ]

    for change in changes:
        report.extend(
            [
                f"## {change['name']}",
                "",
                f"Source: {change['url']}",
                "",
            ]
        )

        if change["items"]:
            for item in change["items"]:
                report.extend(
                    [
                        "### 検出内容",
                        "",
                        item,
                        "",
                    ]
                )
        else:
            report.extend(
                [
                    "ページ内容に変更がありました。",
                    "",
                ]
            )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        f.write("\n".join(report))

    print(
        "UPDATE_FOUND=true"
    )


if __name__ == "__main__":
    main()
