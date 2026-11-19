import sqlite3
import time
from playwright.sync_api import sync_playwright


# ----- URLとデータベースのファイル名を設定する -----

URL = "https://github.com/orgs/google/repositories"
DB_FILE = "google_repositories.db"


# ----- 取得する言語名を設定する -----

possible_languages = {
    "Python", "Java", "JavaScript", "TypeScript",
    "C", "C++", "C#", "Go", "Rust", "Kotlin",
    "Swift", "Dart", "Ruby", "PHP", "Scala",
    "Shell", "HTML", "CSS", "Lua", "Perl",
    "Objective-C", "CMake", "Makefile", "Starlark",
    "Jupyter Notebook", "Wolfram Language", "MLIR",
}


# ----- Playwrightで全ページのリポジトリ情報を集める -----

repositories = []
seen_names = set()
page_number = 1

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    while True:
        # リポジトリ一覧のページを開く
        page.goto(
        f"{URL}?page={page_number}",
        wait_until="domcontentloaded",
        timeout=60000
        )

        # ページごとに1秒待つ
        time.sleep(1)
        time.sleep(2)

        # Googleのリポジトリへのリンクを探す
        repo_links = page.locator("a[href^='/google/']")
        new_repositories_on_page = 0

        # ページ内のリンクを1件ずつ調べる
        for i in range(repo_links.count()):
            repo_link = repo_links.nth(i)
            href = repo_link.get_attribute("href")

            if href is None:
                continue

            # /google/リポジトリ名 の形のリンクだけを対象にする
            parts = href.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "google":
                continue

            repository_name = parts[1]

            # 同じリポジトリを重複して追加しない
            if repository_name in seen_names:
                continue

            seen_names.add(repository_name)
            new_repositories_on_page += 1

            # スター数などが含まれるリポジトリの範囲を探す
            item = repo_link.locator(
                "xpath=ancestor::*[.//a[contains(@href, '/stargazers')]][1]"
            )

            # spanの文字から主要な言語を探す
            language_spans = item.locator("span").all_inner_texts()
            language = ""

            for span_text in language_spans:
                span_text = span_text.strip()
                if span_text in possible_languages:
                    language = span_text
                    break

            # スター数を取得する（見つからない場合は0）
            star_locator = item.locator('a[href$="/stargazers"]')
            if star_locator.count() > 0:
                stars = star_locator.first.inner_text().strip()
            else:
                stars = "0"

            # 1件分の情報を追加する
            repositories.append((repository_name, language, stars))

        print(
            f"{page_number}ページ目："
            f"{new_repositories_on_page}件取得"
        )

        # 新しいリポジトリがなければ、最後のページと判断して終了する
        if new_repositories_on_page == 0:
            break

        page_number += 1

    browser.close()

print("取得したリポジトリ総数：", len(repositories))


# ----- SQLiteデータベースに保存する -----

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_name TEXT,
        language TEXT,
        stars TEXT
    );
""")

# 前回のデータを消して、今回取得したデータを保存する
cur.execute("DELETE FROM repositories")

cur.executemany(
    """
    INSERT INTO repositories (repository_name, language, stars)
    VALUES (?, ?, ?);
    """,
    repositories
)

conn.commit()
print(f"{DB_FILE} に保存しました。")


# ----- SELECT文で保存したデータを表示する -----

print("\n----- GoogleのGitHubリポジトリ -----")
print("リポジトリ名 | 主要な言語 | スター数")

rows = cur.execute("""
    SELECT repository_name, language, stars
    FROM repositories;
""")

for row in rows:
    print(f"{row[0]} | {row[1]} | {row[2]}")

conn.close()