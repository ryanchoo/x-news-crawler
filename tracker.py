
import os
import requests
from playwright.sync_api import sync_playwright

# 1. 깃허브 금고에 숨겨둔 슬랙 주소 자동으로 가져오기
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 2. X(트위터)에서 검색할 주소 설정
# 예시: 로이터(Reuters) 계정이 쓴 글 중 'Tesla' 또는 'EV'가 포함된 최신글(live) 보기 URL입니다.
# 나중에 본인이 원하는 검색어로 X에서 검색한 뒤 그 URL로 바꾸셔도 됩니다.
TARGET_URL = "https://x.com/search?q=from%3AReuters%20(Tesla%20OR%20EV)&f=live"
DB_FILE = "last_tweet.txt"

def get_latest_tweet():
    with sync_playwright() as p:
        # 가상 환경(리눅스 서버)에서 브라우저를 안정적으로 띄우기 위한 설정
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 설정한 X 검색 페이지로 이동 및 로딩 대기
        page.goto(TARGET_URL, wait_until="networkidle")
        page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)

        # 화면 맨 위에 있는 가장 최신 트윗 1개 지정
        tweet_element = page.locator('article[data-testid="tweet"]').first

        # 트윗의 본문 글자 추출
        tweet_text = tweet_element.locator('[data-testid="tweetText"]').inner_text()

        # 트윗의 고유 링크(URL) 주소 추출
        try:
            tweet_link_element = tweet_element.locator('time').parent()
            tweet_href = tweet_link_element.get_attribute("href")
            tweet_url = f"https://x.com{tweet_href}" if tweet_href else ""
        except:
            tweet_url = "링크를 가져올 수 없음"

        browser.close()
        return tweet_text, tweet_url

def send_slack(text, url):
    payload = {
        "text": f"📰 *[X 실시간 뉴스 알림]*\n\n{text}\n\n🔗 바로가기: {url}"
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    try:
        current_text, current_url = get_latest_tweet()

        # 중복 발송을 막기 위해 10분 전에 보냈던 마지막 트윗 주소 읽어오기
        prev_url = ""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                prev_url = f.read().strip()

        # 새로운 트윗이 올라왔을 때만 슬랙으로 전송
        if current_url and current_url != prev_url:
            print("새로운 뉴스 트윗을 발견했습니다! 슬랙 푸시 발송.")
            send_slack(current_text, current_url)

            # 방금 보낸 트윗 주소를 기억하기 위해 파일에 저장
            with open(DB_FILE, "w", encoding="utf-8") as f:
                f.write(current_url)
        else:
            print("새로 올라온 뉴스가 없습니다.")

    except Exception as e:
        print(f"작동 중 오류 발생: {e}")
