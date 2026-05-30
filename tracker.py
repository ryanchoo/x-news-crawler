
import os
import requests
from playwright.sync_api import sync_playwright

# 1. 깃허브 금고에서 슬랙 주소 가져오기
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 2. 🔥 1안(주요 외신)과 2안(우주 전문/머스크) 두 개 주소를 모두 등록!
TARGET_URLS = {
    "글로벌 외신 (테슬라/우주/AI)": "https://x.com/search?q=(from%3AReuters%20OR%20from%3ABloomberg%20OR%20from%3ACNBC%20OR%20from%3ATechCrunch%20OR%20from%3AWSJ)%20(Musk%20OR%20SpaceX%20OR%20xAI%20OR%20Tesla%20OR%20NVIDIA%20OR%20%22Rocket%20Lab%22%20OR%20%22Intuitive%20Machines%22)%20-filter%3Areplies&f=live",
    "우주 전문 매체 & 일론 머스크": "https://x.com/search?q=(from%3Aelonmusk%20OR%20from%3ASpaceX%20OR%20from%3ASpaceflightNow%20OR%20from%3AInt_Machines%20OR%20from%3ARocketLab)%20-filter%3Areplies&f=live"
}

DB_FILE = "last_tweet.txt"

def get_latest_tweet(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.goto(url, wait_until="networkidle")
        page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)

        tweet_element = page.locator('article[data-testid="tweet"]').first
        tweet_text = tweet_element.locator('[data-testid="tweetText"]').inner_text()

        try:
            tweet_link_element = tweet_element.locator('time').parent()
            tweet_href = tweet_link_element.get_attribute("href")
            tweet_url = f"https://x.com{tweet_href}" if tweet_href else ""
        except:
            tweet_url = "링크를 가져올 수 없음"

        browser.close()
        return tweet_text, tweet_url

def send_slack(category, text, url):
    payload = {
        "text": f"🚀 *[TIGER 우주테크 알림 - {category}]*\n\n{text}\n\n🔗 바로가기: {url}"
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    try:
        # 이전에 저장된 각 채널별 마지막 트윗 주소들 로드
        prev_urls = {}
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if "==" in line:
                            cat, url = line.strip().split("==", 1)
                            prev_urls[cat] = url
            except:
                pass

        current_urls_state = []

        # 1안, 2안 차례대로 돌면서 새 트윗 검사
        for category, url in TARGET_URLS.items():
            print(f"[{category}] 크롤링 시작...")
            try:
                current_text, current_url = get_latest_tweet(url)

                # 해당 카테고리에 새 글이 올라왔다면 슬랙 전송
                if current_url and current_url != prev_urls.get(category, ""):
                    print(f"-> 새로운 뉴스 발견! 슬랙 전송")
                    send_slack(category, current_text, current_url)
                    current_urls_state.append(f"{category}=={current_url}\n")
                else:
                    print(f"-> 새로운 뉴스 없음.")
                    current_urls_state.append(f"{category}=={prev_urls.get(category, '')}\n")
            except Exception as e:
                print(f"{category} 처리 중 오류: {e}")
                current_urls_state.append(f"{category}=={prev_urls.get(category, '')}\n")

        # 최신 상태를 파일에 저장
        with open(DB_FILE, "w", encoding="utf-8") as f:
            f.writelines(current_urls_state)

    except Exception as e:
        print(f"전체 시스템 작동 중 오류 발생: {e}")
