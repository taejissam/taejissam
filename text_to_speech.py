"""
========================================================
  한국어 텍스트 → 음성 파일 변환 (Korean TTS)
========================================================

[필수 라이브러리 설치]
  pip install edge-tts
  pip install gTTS

[실행 환경]
  Python 3.8 이상 / Windows · macOS · Linux 모두 지원
========================================================
"""

import asyncio
import os
import sys
import time

# Windows Python 3.11+ asyncio 이벤트 루프 충돌 방지
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _run_async(coro):
    """매번 새 이벤트 루프를 생성해 안전하게 실행"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ──────────────────────────────────────────────
# 1) Edge TTS (추천 - 가장 자연스러운 음성)
# ──────────────────────────────────────────────
class EdgeTTSKorean:
    """
    Microsoft Edge 신경망 TTS 기반 한국어 음성 변환.

    한국어 목소리:
      female → ko-KR-SunHiNeural  (여성, 기본값)
      male   → ko-KR-InJoonNeural (남성)
    """

    VOICES = {
        "female": "ko-KR-SunHiNeural",
        "male":   "ko-KR-InJoonNeural",
    }

    def __init__(
        self,
        voice: str = "female",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Args:
            voice       : "female" | "male" | 직접 voice 이름 입력
            rate        : 속도  예) "+10%" 빠르게, "-10%" 느리게
            volume      : 볼륨  예) "+20%", "-20%"
            pitch       : 음높이 예) "+10Hz", "-10Hz"
            max_retries : 실패 시 재시도 횟수 (기본 3)
            retry_delay : 재시도 간격(초) (기본 2.0)
        """
        self.voice       = self.VOICES.get(voice, voice)
        self.rate        = rate
        self.volume      = volume
        self.pitch       = pitch
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _synthesize(self, text: str, output_path: str):
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts 미설치. 'pip install edge-tts'를 실행하세요.")

        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        await communicate.save(output_path)

    def save(self, text: str, output_path: str = "output.mp3") -> str:
        """
        텍스트를 MP3 파일로 저장 (재시도 포함).

        Args:
            text        : 변환할 한국어 텍스트
            output_path : 저장할 파일 경로 (기본값: output.mp3)

        Returns:
            저장된 파일의 절대 경로
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"[Edge TTS] 변환 중... (시도 {attempt}/{self.max_retries})")
                _run_async(self._synthesize(text, output_path))
                abs_path = os.path.abspath(output_path)
                print(f"[Edge TTS] 저장 완료 → {abs_path}")
                return abs_path

            except KeyboardInterrupt:
                raise

            except Exception as e:
                last_error = e
                print(f"[Edge TTS] 시도 {attempt} 실패: {type(e).__name__}: {e}")
                if attempt < self.max_retries:
                    print(f"[Edge TTS] {self.retry_delay}초 후 재시도...")
                    time.sleep(self.retry_delay)

        raise RuntimeError(
            f"[Edge TTS] {self.max_retries}회 모두 실패.\n"
            f"마지막 오류: {last_error}\n"
            f"→ 인터넷 연결을 확인하거나 engine='gtts' 로 변경해보세요."
        )


# ──────────────────────────────────────────────
# 2) Google TTS (대안)
# ──────────────────────────────────────────────
class GTTSKorean:
    """Google Text-to-Speech 기반 한국어 음성 변환"""

    def __init__(self, slow: bool = False):
        """
        Args:
            slow : True이면 느린 속도로 읽기
        """
        self.slow = slow

    def save(self, text: str, output_path: str = "output.mp3") -> str:
        """
        텍스트를 MP3 파일로 저장.

        Args:
            text        : 변환할 한국어 텍스트
            output_path : 저장할 파일 경로 (기본값: output.mp3)

        Returns:
            저장된 파일의 절대 경로
        """
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("gTTS 미설치. 'pip install gTTS'를 실행하세요.")

        print("[Google TTS] 변환 중...")
        tts = gTTS(text=text, lang="ko", slow=self.slow)
        tts.save(output_path)
        abs_path = os.path.abspath(output_path)
        print(f"[Google TTS] 저장 완료 → {abs_path}")
        return abs_path


# ──────────────────────────────────────────────
# 3) 통합 인터페이스 (권장 사용 클래스)
# ──────────────────────────────────────────────
class KoreanTTS:
    """
    Edge TTS / Google TTS 통합 인터페이스.
    Edge TTS 실패 시 자동으로 Google TTS로 폴백합니다.

    사용 예시:
        tts = KoreanTTS(engine="edge", voice="female")
        tts.save("안녕하세요!", "output.mp3")
    """

    def __init__(
        self,
        engine: str = "edge",
        voice: str = "female",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        slow: bool = False,
        auto_fallback: bool = True,
    ):
        """
        Args:
            engine        : "edge" (기본값, 추천) | "gtts"
            voice         : "female" | "male"        (edge 전용)
            rate          : 속도 "+10%" / "-10%"     (edge 전용)
            volume        : 볼륨 "+20%" / "-20%"     (edge 전용)
            pitch         : 음높이 "+10Hz" / "-10Hz" (edge 전용)
            slow          : 느린 속도 여부            (gtts 전용)
            auto_fallback : Edge 실패 시 gTTS 자동 전환 (기본 True)
        """
        self.auto_fallback = auto_fallback

        if engine.lower() == "edge":
            self._engine   = EdgeTTSKorean(voice=voice, rate=rate, volume=volume, pitch=pitch)
            self._fallback = GTTSKorean(slow=slow)
        elif engine.lower() == "gtts":
            self._engine   = GTTSKorean(slow=slow)
            self._fallback = None
        else:
            raise ValueError(f"지원하지 않는 엔진: '{engine}'. 'edge' 또는 'gtts'를 입력하세요.")

    def save(self, text: str, output_path: str = "output.mp3") -> str:
        """
        텍스트를 MP3 파일로 저장.
        Edge TTS 실패 시 auto_fallback=True이면 Google TTS로 자동 전환.

        Args:
            text        : 변환할 한국어 텍스트
            output_path : 저장할 파일 경로 (기본값: output.mp3)

        Returns:
            저장된 파일의 절대 경로
        """
        try:
            return self._engine.save(text, output_path)

        except (KeyboardInterrupt, SystemExit):
            raise

        except Exception as e:
            if self.auto_fallback and self._fallback:
                print(f"\n[폴백] Edge TTS 실패 → Google TTS로 전환합니다.\n  원인: {e}\n")
                return self._fallback.save(text, output_path)
            raise


# ──────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────
def main():
    # ✅ 변환할 텍스트를 여기에 입력하세요
    text = """
    아파트 구할 때 제일 먼저 뭐 따지세요?
층수요? 조망이요? 남향이요?
저도 그랬거든요. 근데요 —
직접 살아보고 나서야 알았습니다.
그게 다가 아니라는 걸.

오늘은 아무도 얘기 안 해주는,
근데 진짜 중요한 거 하나 알려드릴게요.

보통 아파트 얘기하면 다들 고층 고층 하잖아요.

이유는 명확해요.
전망 좋고, 채광 좋고, 아래층 눈치 안 봐도 되고.
실제로 고층이 시세도 더 높죠.

저도 예전엔 당연히 고층이 최고라고 생각했어요.
그래서 고층으로 들어갔습니다.

전망 진짜 좋았어요.
채광도 완벽했고요.

근데… 문제가 하나 있었습니다.

담배 연기.

아래층에서 담배를 피우더라고요.

처음엔 가끔이겠지 했죠.
근데 날마다예요. 날마다.

환기하려고 창문 열면, 딱 그 타이밍에 연기가 올라와요.
집에서 쉬려고 누워있으면 냄새가 들어오고.

관리사무소에 민원 넣었죠. 당연히.
안내방송 나갔어요.

아무 소용 없었습니다.

생각해보면 당연한 거예요.
남한테 피해 주는 걸 신경 쓰는 사람이었으면,
애초에 집 안에서 담배를 안 폈겠죠.

양심이 있으면 안 피우고,
양심이 없으면 민원이고 뭐고 신경도 안 써요.

법으로 강제할 수도 없고,
설득은 더더욱 안 되고.

공자님도 길 한가운데 똥 싸는 사람한테는 뭐라 안 하셨대요.
상대 자체가 안 되니까.
딱 그 경우인 거죠.

그래서 이사를 했어요.
이번엔 저층으로.

솔직히 처음엔 좀 아쉬웠어요.
"내가 왜 저층을…" 이런 기분 있잖아요.

근데요.

아래층이 비흡연자 세대예요.

창문 열면, 그냥 바람 들어와요.
그냥 공기. 그냥 바깥 냄새.

집에 있는 게 즐거워졌어요. 진짜로.

층수는 낮아졌는데, 삶의 질은 올라간 거예요.

고층이었을 때보다 지금이 훨씬 낫습니다.

저층이 좋은 이유, 하나 더 있어요.

엘리베이터 안 기다려도 돼요.

출근 시간에 이게 진짜 크거든요.
1~2분 기다리는 거 별거 아닌 것 같아도,
매일 반복되면 은근히 스트레스예요.
그냥 계단으로 뚜벅뚜벅 내려가면 끝.

단, 저층이라고 다 좋은 건 아니에요.
1층, 2층은 좀 달라요.

야외 주차장이나 현관 앞에서 피우는 담배 연기가
1~2층까지는 그냥 들어와요.

그러니까 저층의 장점을 누리면서
연기 피해는 피하려면, 최소 3층 이상은 돼야 합니다.

아파트 보러 가실 때 꼭 하나만 기억하세요.

"몇 층이에요?" 말고,

"위아래층이랑 이웃 세대에 흡연자 있나요?"

이거 먼저 물어보세요.

물론 집주인이 정확하게 답해준다는 보장은 없어요.
그러니까 직접 확인하는 방법도 있어요.

방문할 때 복도 냄새 맡아보세요.
엘리베이터 안 냄새도요.
담배 냄새 배어 있으면 이미 답 나온 거예요.

여유가 된다면 이웃 주민한테 슬쩍 물어보는 것도 방법이고요.

층수, 조망, 남향 — 다 중요합니다.
근데 이것들 전부 다 갖춰도,
담배 연기 들어오는 순간 끝이에요.

간접흡연 걱정없는 집이 먼저입니다.**

살아보고 나서야 알게 되는 것들이 있잖아요.
이게 그중 하나였어요.

도움이 됐다면 좋아요랑 구독 부탁드리고요,
비슷한 경험 있으신 분들, 댓글로 공유해주세요.

다음에 또 유용한 거 가져올게요. 안녕히 계세요!

    """

    print("=" * 50)
    print("  한국어 TTS 변환 시작")
    print("=" * 50)

    # Edge TTS - 여성 목소리
    tts_female = KoreanTTS(engine="edge", voice="female")
    tts_female.save(text, output_path="output_female.mp3")

    # Edge TTS - 남성 목소리
    tts_male = KoreanTTS(engine="edge", voice="male", rate="-5%")
    tts_male.save(text, output_path="output_male.mp3")

    # Google TTS
    tts_google = KoreanTTS(engine="gtts")
    tts_google.save(text, output_path="output_google.mp3")

    print("\n✅ 모든 변환 완료!")


if __name__ == "__main__":
    main()